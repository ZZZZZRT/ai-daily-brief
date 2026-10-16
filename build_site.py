#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 reports/ 里的每日晨报 (Markdown) 生成一个静态网站。
零第三方依赖，纯标准库。
模板与内容：
    templates/style.css   样式
    templates/page.html   页面骨架（占位符 {{TITLE}} {{CSS_URL}} {{SITE}} {{SUB}} {{BODY}} {{TAB_*}}）
    config/sources.json   信息源清单（同时供“资讯源”页与 brief.py 使用）
输出到 docs/ : index.html / <日期>.html / workflow.html / sources.html / style.css

用法: python3 build_site.py
"""
import os, re, glob, html, json

BASE = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR = os.path.join(BASE, "reports")
SITE_DIR = os.path.join(BASE, "docs")
TEMPLATE_DIR = os.path.join(BASE, "templates")
CONFIG_DIR = os.path.join(BASE, "config")
SITE_TITLE = "☀️ AI 晨报"

# 工作流说明（与 .github/workflows/daily.yml 及 brief.py 保持一致）
SCHEDULE_TEXT = "每天 08:00（北京时间）"
MODEL_TEXT = "DeepSeek（deepseek-chat）"
MAX_AGE_DAYS = 3


def load_sources():
    with open(os.path.join(CONFIG_DIR, "sources.json"), encoding="utf-8") as f:
        return json.load(f)


def load_templates():
    tpl = open(os.path.join(TEMPLATE_DIR, "page.html"), encoding="utf-8").read()
    css = open(os.path.join(TEMPLATE_DIR, "style.css"), encoding="utf-8").read()
    return tpl, css


def render(tpl, **kw):
    out = tpl
    for k, v in kw.items():
        out = out.replace("{{" + k.upper() + "}}", str(v))
    return re.sub(r"\{\{[A-Z_]+\}\}", "", out)  # 清理未用占位符


# ── 极简 Markdown → HTML（只处理晨报用到的语法）──────────────
def _inline(s):
    s = html.escape(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
               r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)
    return s


def md_to_html(text):
    out, list_type = [], None

    def close_list():
        nonlocal list_type
        if list_type:
            out.append(f"</{list_type}>")
            list_type = None

    def append_continuation(frag):
        if not out:
            return False
        last = out[-1]
        for close in ("</li>", "</p>", "</h6>", "</h5>", "</h4>", "</h3>", "</h2>", "</h1>"):
            if last.endswith(close):
                out[-1] = last[:-len(close)] + "<br>" + frag + close
                return True
        return False

    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            continue
        if raw[:1].isspace() and append_continuation(_inline(s)):
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            close_list()
            lvl = min(len(m.group(1)), 6)
            out.append(f"<h{lvl}>{_inline(m.group(2))}</h{lvl}>")
            continue
        m = re.match(r"^[-*]\s+(.*)$", s)
        if m:
            if list_type != "ul":
                close_list(); out.append("<ul>"); list_type = "ul"
            out.append(f"<li>{_inline(m.group(1))}</li>")
            continue
        m = re.match(r"^\d+[.)]\s+(.*)$", s)
        if m:
            if list_type != "ol":
                close_list(); out.append("<ol>"); list_type = "ol"
            out.append(f"<li>{_inline(m.group(1))}</li>")
            continue
        close_list()
        out.append(f"<p>{_inline(s)}</p>")
    close_list()
    return "\n".join(out)


def read_reports():
    """返回 [(date, html_content)]，按日期倒序。"""
    out = []
    for path in glob.glob(os.path.join(REPORT_DIR, "brief-*.md")):
        m = re.search(r"brief-(\d{4}-\d{2}-\d{2})\.md$", path)
        if not m:
            continue
        md = open(path, encoding="utf-8").read()
        body = re.sub(r"^\s*#\s.*$", "", md, count=1, flags=re.M)
        out.append((m.group(1), md_to_html(body)))
    out.sort(key=lambda x: x[0], reverse=True)
    return out


def first_summary(html_content):
    seg = html_content
    for tag in ("今日头条", "模型与产品"):
        i = seg.find(tag)
        if i > -1:
            seg = seg[i:i + 500]
            break
    text = html.unescape(re.sub("<[^>]+>", " ", seg))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:180]


def build_sources_body():
    sources = load_sources()
    cats = {}
    for s in sources:
        cats.setdefault(s.get("category", "其他"), []).append(s)
    order = ["官方实验室", "研究论文", "媒体 & Newsletter", "开发者社区"]
    keys = [c for c in order if c in cats] + [c for c in cats if c not in order]

    parts = ['<h1 class="page-title">资讯源</h1>',
             f'<p class="page-sub">本站每天自动从 <b>{len(sources)}</b> 个信息源采集 AI 前沿资讯（RSS / 公开接口）。</p>',
             '<section class="sources">']
    for c in keys:
        items = cats[c]
        parts.append(f'<div class="source-group"><h2>{html.escape(c)}'
                     f'<span class="count">{len(items)}</span></h2><ul class="source-list">')
        for s in items:
            note = f'<span class="note">{html.escape(s["note"])}</span>' if s.get("note") else ''
            parts.append(f'<li><a href="{html.escape(s["url"])}" target="_blank" '
                         f'rel="noopener">{html.escape(s["name"])}</a>{note}</li>')
        parts.append('</ul></div>')
    parts.append('</section>')
    return "".join(parts)


def build_workflow_body():
    n = len(load_sources())
    steps = [
        ("定时触发", f"{SCHEDULE_TEXT}，云端的 GitHub Actions 自动启动（无需你的电脑开机）。"),
        ("采集", f"并行读取 <b>{n}</b> 个信息源：官方博客、媒体、论文与社区。"),
        ("清洗", f"按标题去重，并只保留最近 <b>{MAX_AGE_DAYS}</b> 天发布的资讯。"),
        ("AI 筛选与摘要", f"{MODEL_TEXT} 依据“兴趣画像”筛选、分组，写出中文摘要与“为什么重要”。"),
        ("推送", "生成飞书交互卡片，推送到你的飞书群（链接可直接点开）。"),
        ("存档与建站", "保存为 Markdown 存档，并重新生成这个网站（首页 + 历史）。"),
    ]
    parts = ['<h1 class="page-title">工作流</h1>',
             '<p class="page-sub">从采集到发布的完整自动化流程。</p>',
             '<ol class="flow">']
    for i, (t, d) in enumerate(steps, 1):
        parts.append(f'<li class="step"><span class="step-idx">{i}</span>'
                     f'<div class="step-body"><h3>{t}</h3><p>{d}</p></div></li>')
    parts.append('</ol>')

    facts = [("运行频率", SCHEDULE_TEXT), ("信息源", f"{n} 个"),
             ("AI 模型", MODEL_TEXT), ("鲜度", f"最近 {MAX_AGE_DAYS} 天"),
             ("输出", "飞书推送 · 网站")]
    parts.append('<div class="facts">')
    for k, v in facts:
        parts.append(f'<div class="fact"><span class="fact-k">{k}</span>'
                     f'<span class="fact-v">{v}</span></div>')
    parts.append('</div>')
    return "".join(parts)


def build():
    os.makedirs(SITE_DIR, exist_ok=True)
    tpl, css = load_templates()
    open(os.path.join(SITE_DIR, "style.css"), "w", encoding="utf-8").write(css)

    reports = read_reports()
    dates = [d for d, _ in reports]

    def write(name, title, sub, body, active):
        tabs = {
            "TAB_DAILY": "active" if active == "daily" else "",
            "TAB_WORKFLOW": "active" if active == "workflow" else "",
            "TAB_SOURCES": "active" if active == "sources" else "",
        }
        open(os.path.join(SITE_DIR, name), "w", encoding="utf-8").write(
            render(tpl, TITLE=title, CSS_URL="style.css", SITE=SITE_TITLE,
                   SUB=sub, BODY=body, **tabs))

    # 每天的独立页面
    for idx, (date, content) in enumerate(reports):
        nav = ['<a href="index.html">← 返回首页</a>']
        if idx - 1 >= 0:
            nav.append(f'<a href="{dates[idx-1]}.html">更新的一天 →</a>')
        if idx + 1 < len(dates):
            nav.append(f'<a href="{dates[idx+1]}.html">← 更早的一天</a>')
        body = f'<div class="nav">{" ".join(nav)}</div><article>{content}</article>'
        write(f"{date}.html", f"{date} · {SITE_TITLE}", date, body, "daily")

    # 首页：当前晨报全文 + 往期列表
    if reports:
        cur_date, cur_html = reports[0]
        current = ('<section class="current">'
                   '<div class="section-head"><h2>当前晨报</h2>'
                   f'<span class="date">{cur_date}</span></div>'
                   f'<div class="brief">{cur_html}</div></section>')
        past_items = "".join(
            f'<li><a href="{d}.html"><span class="d">{d}</span>'
            f'<span class="x">{html.escape(first_summary(c))}</span></a></li>'
            for d, c in reports[1:])
        if past_items:
            past = ('<section class="past">'
                    f'<div class="section-head"><h2>往期晨报</h2>'
                    f'<span class="count">共 {len(reports)-1} 期</span></div>'
                    f'<ul class="archive">{past_items}</ul></section>')
        else:
            past = ('<section class="past"><div class="section-head"><h2>往期晨报</h2></div>'
                    '<p class="meta">还没有往期，明天见。</p></section>')
        index_body = current + past
    else:
        index_body = '<div class="brief"><p class="meta">还没有晨报，等第一次运行后就会出现。</p></div>'
    write("index.html", SITE_TITLE, "每日 AI 前沿资讯", index_body, "daily")

    # 工作流页 / 资讯源页
    write("workflow.html", f"工作流 · {SITE_TITLE}", "工作流", build_workflow_body(), "workflow")
    write("sources.html", f"资讯源 · {SITE_TITLE}", "资讯源", build_sources_body(), "sources")

    print(f"[site] 生成 {len(reports)} 期 + 工作流 + 资讯源 → {SITE_DIR}")
    print(f"        首页: {os.path.join(SITE_DIR, 'index.html')}")


if __name__ == "__main__":
    build()
