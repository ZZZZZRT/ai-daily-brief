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

# ── 2. 提示词与配置（读取 prompts/ 目录）──────────────────
from promptlib import load_config, load_prompts, build_prompt

PROMPT_DIR = os.path.join(BASE, "prompts")
CFG = load_config()
INTERESTS, PROMPT_TEMPLATE = load_prompts()
EMOJI = CFG.get("section_emoji", {})
MAX_AGE_DAYS = int(CFG.get("max_age_days", 3))

UA = {"User-Agent": "Mozilla/5.0 (compatible; ai-brief/0.1)"}
REPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
DATA_DIR = os.path.join(BASE, "data")
STATE_DIR = os.path.join(BASE, "state")
SITE_URL = ""  # 网站最终网址（部署成功后填入，如 https://ai-daily-brief.<你的子域>.workers.dev/）


def bj_today():
    """北京时间的今天（服务器是 UTC）。"""
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)).date().isoformat()


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def load_state(date):
    p = os.path.join(STATE_DIR, f"{date}.json")
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"date": date}


def save_state(date, **kw):
    os.makedirs(STATE_DIR, exist_ok=True)
    st = load_state(date)
    st.update(kw)
    st["date"] = date
    st["updated_at"] = now_iso()
    with open(os.path.join(STATE_DIR, f"{date}.json"), "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=2)
    return st


def fetch(name, url):
    """返回 (items, ok)。ok 表示本次抓取是否成功。"""
    try:
        raw = urllib.request.urlopen(
            urllib.request.Request(url, headers=UA), timeout=20).read()
        d = feedparser.parse(raw)
        out = []
        for e in d.entries[:int(CFG.get("per_source_limit", 25))]:
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
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
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
    """让 DeepSeek 输出结构化 JSON：sections -> items。"""
    key = os.environ["DEEPSEEK_API_KEY"]
    prompt = build_prompt(items)
    body = json.dumps({
        "model": CFG.get("model", "deepseek-chat"),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": CFG.get("temperature", 0.4),
        "response_format": {"type": "json_object"},
    }).encode()
    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions", data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {key}"})
    r = json.loads(urllib.request.urlopen(req, timeout=180).read())
    return json.loads(r["choices"][0]["message"]["content"])


def enrich(data, all_items):
    """按 url 补上来源与时间（数据来自实际抓取，保证准确）。"""
    meta = {i["url"]: i for i in all_items}
    for sec in data.get("sections", []):
        for it in sec.get("items", []):
            m = meta.get(it.get("url", ""))
            if m:
                it["source"] = m["source"]
                it["ts"] = m["ts"].isoformat() if m["ts"] else None
    return data


def to_markdown(data, date):
    """由结构化数据生成 Markdown（用于存档与飞书推送）。"""
    out = [f"# ☀️ AI 晨报 · {date}", ""]
    for sec in data.get("sections", []):
        name = sec.get("name", "")
        out.append(f"## {EMOJI.get(name, '')} {name}".strip())
        out.append("")
        top = (name == "今日头条")
        for it in sec.get("items", []):
            t = (it.get("title") or "").strip()
            s = (it.get("summary") or "").strip()
            u = (it.get("url") or "").strip()
            if top:
                out.append(f"1. **{t}**")
                if s:
                    out.append(f"   {s}")
                w = (it.get("why") or "").strip()
                if w:
                    out.append(f"   *为什么重要：{w}*")
            else:
                line = f"- **{t}**"
                if s:
                    line += f"：{s}"
                if u:
                    line += f" [链接]({u})"
                out.append(line)
        out.append("")
    return "\n".join(out).strip() + "\n"


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


def generate():
    date = bj_today()
    print("① 抓取信息源 ...", file=sys.stderr)
    fresh, all_items, status = collect()
    print(f"   去重后 {len(fresh)} 条（累积候选 {len(all_items)} 条）", file=sys.stderr)
    save_data(all_items, status)

    print("② 调用 DeepSeek 生成结构化晨报 ...", file=sys.stderr)
    data = enrich(call_deepseek(fresh), all_items)

    os.makedirs(REPORT_DIR, exist_ok=True)
    json_path = os.path.join(REPORT_DIR, f"brief-{date}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"[已存档] {json_path}", file=sys.stderr)

    md = to_markdown(data, date)
    md = re.sub(r"^\s*#\s.*$", f"# ☀️ AI 晨报 · {date}", md, count=1, flags=re.M)
    md_path = os.path.join(REPORT_DIR, f"brief-{date}.md")
    open(md_path, "w", encoding="utf-8").write(md)
    print(f"[已存档] {md_path}", file=sys.stderr)

    st = load_state(date)
    save_state(date, generated_at=now_iso(),
               attempts=int(st.get("attempts", 0)) + 1, last_error=None)
    print(f"[状态] {date} 生成完成", file=sys.stderr)
    return date


def push_only():
    date = bj_today()
    st = load_state(date)
    if st.get("pushed_at"):
        print(f"[跳过] {date} 已推送过（{st['pushed_at']}）", file=sys.stderr)
        return False
    md_path = os.path.join(REPORT_DIR, f"brief-{date}.md")
    if not os.path.exists(md_path):
        raise SystemExit(f"缺少 {md_path}，请先运行 generate")
    md = open(md_path, encoding="utf-8").read()
    print("③ 推送飞书 ...", file=sys.stderr)
    push_feishu(md, f"☀️ AI 晨报 · {date}")
    save_state(date, pushed_at=now_iso())
    print(f"[已推送] {date}", file=sys.stderr)
    return True


def preview():
    """本地试跑：抓取 + 调用 AI，写入 reports/preview.*，不推送、不改状态。"""
    date = bj_today()
    print("① 抓取信息源 ...", file=sys.stderr)
    fresh, all_items, status = collect()
    print(f"   候选 {len(fresh)} 条", file=sys.stderr)
    print("② 调用 DeepSeek（试跑，不推送）...", file=sys.stderr)
    data = enrich(call_deepseek(fresh), all_items)
    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(os.path.join(REPORT_DIR, "preview.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    md = to_markdown(data, date)
    with open(os.path.join(REPORT_DIR, "preview.md"), "w", encoding="utf-8") as f:
        f.write(md)
    print(f"[试跑完成] {date}", file=sys.stderr)
    print(md)


def run_all():
    generate()
    push_only()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "generate":
        generate()
    elif cmd == "push":
        push_only()
    elif cmd == "preview":
        preview()
    elif cmd == "prompt":
        print(build_prompt([]))
    else:
        run_all()
