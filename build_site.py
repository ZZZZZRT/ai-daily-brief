#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 reports/ 里的每日晨报 (Markdown) 生成一个静态网站。
零第三方依赖，纯标准库。
输出到 docs/ : index.html + 每日页面 + style.css
（docs/ 是 GitHub Pages "从分支发布" 支持的目录）

用法: python3 build_site.py
"""
import os, re, glob, html

BASE = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR = os.path.join(BASE, "reports")
SITE_DIR = os.path.join(BASE, "docs")
SITE_TITLE = "☀️ AI 晨报"

CSS = """
:root{--bg:#0f1115;--card:#171a21;--fg:#e6e8ec;--muted:#9aa3b2;--accent:#4f8cff;--line:#252a34}
@media (prefers-color-scheme:light){:root{--bg:#f5f6f8;--card:#fff;--fg:#1a1d23;--muted:#666e7a;--accent:#2563eb;--line:#e5e7eb}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.7 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}
.wrap{max-width:760px;margin:0 auto;padding:28px 18px 80px}
header.site{display:flex;align-items:baseline;gap:12px;margin-bottom:6px;flex-wrap:wrap}
header.site h1{font-size:24px;margin:0}
header.site .sub{color:var(--muted);font-size:13px}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin:14px 0}
.card h2{margin:.1em 0 .3em;font-size:18px}
.card .meta{color:var(--muted);font-size:13px;margin-bottom:8px}
.card p{margin:.4em 0}
.card .more{color:var(--accent);font-size:14px}
article h1{font-size:22px}
article h2{font-size:17px;margin-top:1.4em;border-bottom:1px solid var(--line);padding-bottom:.3em}
article li{margin:.35em 0}
article a{word-break:break-word}
.nav{display:flex;gap:14px;color:var(--muted);font-size:14px;margin:10px 0 22px;flex-wrap:wrap}
.nav a{color:var(--muted)}
footer{color:var(--muted);font-size:12px;text-align:center;margin-top:40px}
"""

TEMPLATE = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><link rel="stylesheet" href="{css}"></head>
<body><div class="wrap">
<header class="site"><h1>{site}</h1><span class="sub">{sub}</span></header>
{body}
<footer>由 GitHub Actions 自动生成 · 数据归你所有</footer>
</div></body></html>"""


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
        """把缩进的续行并入上一个块（列表项/段落/标题）。"""
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
            # 空行不关闭列表，以支持“松散列表”（条目之间有空行的常见写法）
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
        body = re.sub(r"^\s*#\s.*$", "", md, count=1, flags=re.M)  # 去掉一级标题
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


def build():
    os.makedirs(SITE_DIR, exist_ok=True)
    open(os.path.join(SITE_DIR, "style.css"), "w", encoding="utf-8").write(CSS)
    reports = read_reports()
    dates = [d for d, _ in reports]

    for idx, (date, content) in enumerate(reports):
        nav = ['<a href="index.html">← 全部</a>']
        if idx - 1 >= 0:
            nav.append(f'<a href="{dates[idx-1]}.html">更新的一天 →</a>')
        if idx + 1 < len(dates):
            nav.append(f'<a href="{dates[idx+1]}.html">← 更早的一天</a>')
        body = f'<div class="nav">{" ".join(nav)}</div><article>{content}</article>'
        open(os.path.join(SITE_DIR, f"{date}.html"), "w", encoding="utf-8").write(
            TEMPLATE.format(title=f"{date} · {SITE_TITLE}", css="style.css",
                            site=SITE_TITLE, sub=date, body=body))

    cards = []
    for date, content in reports:
        cards.append(
            f'<div class="card"><h2><a href="{date}.html">{date}</a></h2>'
            f'<div class="meta">AI 晨报</div>'
            f'<p>{html.escape(first_summary(content))}…</p>'
            f'<a class="more" href="{date}.html">阅读全文 →</a></div>')
    if not cards:
        cards.append('<div class="card"><p>还没有晨报，等第一次运行后就会出现。</p></div>')
    body = f'<p class="meta">共 {len(reports)} 期</p>' + "".join(cards)
    open(os.path.join(SITE_DIR, "index.html"), "w", encoding="utf-8").write(
        TEMPLATE.format(title=SITE_TITLE, css="style.css", site=SITE_TITLE,
                        sub="每日 AI 前沿资讯", body=body))

    print(f"[site] 生成 {len(reports)} 期 → {SITE_DIR}")
    for d in dates:
        print(f"        {d}.html")
    print(f"        首页: {os.path.join(SITE_DIR, 'index.html')}")


if __name__ == "__main__":
    build()
