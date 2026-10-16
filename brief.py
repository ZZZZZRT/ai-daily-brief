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

# ── 1. 信息源清单 (已实测可用) ──────────────────────────────
SOURCES = [
    ("OpenAI 官方",        "https://openai.com/blog/rss.xml"),
    ("Google DeepMind",    "https://deepmind.google/blog/rss.xml"),
    ("Google AI Blog",     "https://blog.google/technology/ai/rss/"),
    ("HuggingFace Blog",   "https://huggingface.co/blog/feed.xml"),
    ("arXiv cs.AI",        "http://export.arxiv.org/rss/cs.AI"),
    ("TLDR AI",            "https://tldr.tech/api/rss/ai"),
    ("Ben's Bites",        "https://www.bensbites.com/feed"),
    ("Simon Willison",     "https://simonwillison.net/atom/everything/"),
    ("MIT Tech Review AI", "https://www.technologyreview.com/topic/artificial-intelligence/feed"),
    ("量子位",             "https://www.qbitai.com/feed"),
    ("Hacker News",        "https://hnrss.org/frontpage"),
]

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
SITE_URL = "https://ai-daily-brief.pages.dev/"


def fetch(name, url):
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
        return out
    except Exception as ex:
        print(f"  [warn] {name}: {ex}", file=sys.stderr)
        return []


def collect():
    items = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        for res in ex.map(lambda s: fetch(*s), SOURCES):
            items.extend(res)
    cutoff = datetime.datetime.now(datetime.UTC).replace(tzinfo=None) - \
        datetime.timedelta(days=MAX_AGE_DAYS)
    fresh = [i for i in items if (i["ts"] is None or i["ts"] >= cutoff)]
    seen, dedup = set(), []
    for i in fresh:
        key = re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", i["title"].lower())[:60]
        if key and key not in seen:
            seen.add(key)
            dedup.append(i)
    return dedup


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
    items = collect()
    print(f"   去重后 {len(items)} 条", file=sys.stderr)
    print("② 调用 DeepSeek 生成晨报 ...", file=sys.stderr)
    brief = call_deepseek(items)
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
