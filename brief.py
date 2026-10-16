#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 晨报 - 轻量自建引擎
流程: 抓取 RSS -> 去重 -> 鲜度过滤 -> DeepSeek 筛选+摘要 -> 推送飞书 + 存档 Markdown
环境变量:
  DEEPSEEK_API_KEY    DeepSeek API Key
  FEISHU_WEBHOOK_URL  飞书自定义机器人 Webhook
"""
import os, json, re, sys, datetime, urllib.request, concurrent.futures

import feedparser

# ── 1. 信息源清单（读取 config/sources.json，便于统一维护）────
BASE = os.path.dirname(os.path.abspath(__file__))


def load_sources():
    path = os.path.join(BASE, "config", "sources.json")
    with open(path, encoding="utf-8") as f:
        return [(s["name"], s["url"]) for s in json.load(f)]


SOURCES = load_sources()

# ── 2. 兴趣画像 (决定什么算重要) ────────────────────────────
INTERESTS = """我是 AI 从业者。我关心，按优先级：
1. 主流大模型的新能力/新版本 (GPT、Claude、Gemini、Llama、Qwen、DeepSeek)
2. AI Agent 与自动化工作流
3. AI 编程与开发工具、新火起来的 Skills/MCP
4. 开源模型与本地部署
5. AI 行业融资、政策与大事
请忽略纯营销、招聘、股价波动、以及无关的非 AI 话题。"""

UA = {"User-Agent": "Mozilla/5.0 (compatible; ai-brief/0.1)"}
MAX_AGE_DAYS = 3
REPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
DATA_DIR = os.path.join(BASE, "data")
SITE_URL = ""  # 网站最终网址（部署成功后填入，如 https://ai-daily-brief.<你的子域>.workers.dev/）


def fetch(name, url):
    """返回 (items, ok)。ok 表示本次抓取是否成功。"""
    try:
        raw = urllib.request.urlopen(
            urllib.request.Request(url, headers=UA), timeout=20).read()
        d = feedparser.parse(raw)
        out = []
        for e in d.entries[:25]:
            title = (getattr(e, "title", "") or "").strip()
            link = getattr(e, "link", "") or ""
            ts = None
            for k in ("published_parsed", "updated_parsed"):
                v = getattr(e, k, None)
                if v:
                    ts = datetime.datetime(*v[:6])
                    break
            summ = re.sub("<[^>]+>", " ", getattr(e, "summary", "") or "")
            summ = re.sub(r"\s+", " ", summ).strip()[:400]
            if title and link:
                out.append({"source": name, "title": title, "url": link,
                            "ts": ts, "excerpt": summ})
        return out, True
    except Exception as ex:
        print(f"  [warn] {name}: {ex}", file=sys.stderr)
        return [], False


def collect():
    """返回 (fresh_items, all_items, status)。"""
    items, status = [], {}
    now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(lambda s: (s[0], fetch(*s)), SOURCES))
    for name, (res, ok) in results:
        status[name] = {"ok": ok, "fetched": len(res),
                        "last_run": now.isoformat(timespec="seconds")}
        items.extend(res)

    seen, all_dedup = set(), []
    for i in items:
        key = re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", i["title"].lower())[:60]
        if key and key not in seen:
            seen.add(key)
            all_dedup.append(i)
    cutoff = now - datetime.timedelta(days=MAX_AGE_DAYS)
    fresh = [i for i in all_dedup if (i["ts"] is None or i["ts"] >= cutoff)]
    return fresh, all_dedup, status


def save_data(all_items, status):
    """持久化：每条资讯（按 URL 去重累积）+ 各源抓取状态。供网站使用。"""
    os.makedirs(DATA_DIR, exist_ok=True)
    store_path = os.path.join(DATA_DIR, "items.json")
    existing = []
    if os.path.exists(store_path):
        try:
            existing = json.load(open(store_path, encoding="utf-8"))
        except Exception:
            existing = []
    seen = {i.get("url") for i in existing}
    for it in all_items:
        if it["url"] in seen:
            continue
        seen.add(it["url"])
        existing.append({"source": it["source"], "title": it["title"],
                         "url": it["url"],
                         "ts": it["ts"].isoformat() if it["ts"] else None,
                         "excerpt": it["excerpt"][:300]})
    existing.sort(key=lambda x: x.get("ts") or "", reverse=True)
    existing = existing[:3000]
    with open(store_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False)
    with open(os.path.join(DATA_DIR, "sources_status.json"), "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)
    print(f"[数据] 累积 {len(existing)} 条 -> {store_path}", file=sys.stderr)


def call_deepseek(items):
    key = os.environ["DEEPSEEK_API_KEY"]
    listing = "\n".join(
        f"{n+1}. [{i['source']}] {i['title']}\n   {i['excerpt'][:180]}\n   {i['url']}"
        for n, i in enumerate(items))
    prompt = f"""{INTERESTS}

下面是最近 3 天抓到的候选资讯（{len(items)} 条）。请帮我做一份《AI 晨报》：

要求：
- 只保留与上面兴趣相关的，无关的丢弃
- 第一行是标题 `# ☀️ AI 晨报 · YYYY-MM-DD`
- 按"☀️今日头条 / 🚀模型与产品 / 🛠️工具与Skills / 📄研究与论文 / 💰行业动态"分组，没有内容的分组省略
- 头条 3-5 条，每条一句中文摘要 + 一句"为什么重要"
- 其余条目一行一条：中文标题 + 短评 + 原文链接(用 Markdown 链接)
- 全文中文，简洁，控制在 700 字内

候选资讯：
{listing}
"""
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
    }).encode()
    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions", data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {key}"})
    r = json.loads(urllib.request.urlopen(req, timeout=180).read())
    return r["choices"][0]["message"]["content"]


def push_feishu(md, title):
    """推送到飞书：用交互卡片，Markdown 自动渲染，链接可点。"""
    url = os.environ["FEISHU_WEBHOOK_URL"]
    # 飞书卡片 Markdown 不渲染 #，把标题转成加粗
    body_md = re.sub(r"^#{1,6}\s*(.+)$", r"**\1**", md, flags=re.M)
    if SITE_URL:
        body_md += f"\n\n---\n🌐 [在网站上查看 / 浏览历史]({SITE_URL})"
    card = {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {"template": "blue",
                       "title": {"tag": "plain_text", "content": title}},
            "elements": [{"tag": "markdown", "content": body_md[:28000]}],
        },
    }
    req = urllib.request.Request(url, data=json.dumps(card).encode(),
                                 headers={"Content-Type": "application/json"})
    resp = json.loads(urllib.request.urlopen(req, timeout=30).read())
    if resp.get("code") not in (0, None):
        raise RuntimeError(f"飞书推送失败: {resp}")
    return resp


def main():
    today = datetime.date.today().isoformat()
    print("① 抓取信息源 ...", file=sys.stderr)
    fresh, all_items, status = collect()
    print(f"   去重后 {len(fresh)} 条（累积候选 {len(all_items)} 条）", file=sys.stderr)
    save_data(all_items, status)
    print("② 调用 DeepSeek 生成晨报 ...", file=sys.stderr)
    brief = call_deepseek(fresh)
    # 去掉 AI 可能生成的标题行，统一用当天日期
    body = re.sub(r"^\s*#\s.*$", "", brief, count=1, flags=re.M).strip()
    brief = f"# ☀️ AI 晨报 · {today}\n\n{body}\n"

    os.makedirs(REPORT_DIR, exist_ok=True)
    path = os.path.join(REPORT_DIR, f"brief-{today}.md")
    open(path, "w", encoding="utf-8").write(brief)
    print(f"[已存档] {path}", file=sys.stderr)

    print("③ 推送飞书 ...", file=sys.stderr)
    push_feishu(brief, f"☀️ AI 晨报 · {today}")
    print("[已推送飞书]", file=sys.stderr)
    print(brief)


if __name__ == "__main__":
    main()
