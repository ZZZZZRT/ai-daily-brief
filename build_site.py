#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 reports/ 里的每日晨报 (Markdown) 生成一个静态网站。
零第三方依赖，纯标准库。
样式与页面骨架来自 templates/ 目录（便于前端修改）：
    templates/style.css   样式
    templates/page.html   页面骨架（占位符：{{TITLE}} {{CSS_URL}} {{SITE}} {{SUB}} {{BODY}}）
输出到 docs/ : index.html + 每日页面 + style.css

用法: python3 build_site.py
"""
import os, re, glob, html

BASE = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR = os.path.join(BASE, "reports")
SITE_DIR = os.path.join(BASE, "docs")
TEMPLATE_DIR = os.path.join(BASE, "templates")
SITE_TITLE = "☀️ AI 晨报"


def load_templates():
    tpl = open(os.path.join(TEMPLATE_DIR, "page.html"), encoding="utf-8").read()
    css = open(os.path.join(TEMPLATE_DIR, "style.css"), encoding="utf-8").read()
    return tpl, css


def render(tpl, title, css_url, site, sub, body):
    return (tpl.replace("{{TITLE}}", title)
               .replace("{{CSS_URL}}", css_url)
               .replace("{{SITE}}", site)
               .replace("{{SUB}}", sub)
               .replace("{{BODY}}", body))


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


def build():
    os.makedirs(SITE_DIR, exist_ok=True)
    tpl, css = load_templates()
    open(os.path.join(SITE_DIR, "style.css"), "w", encoding="utf-8").write(css)

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
            render(tpl, f"{date} · {SITE_TITLE}", "style.css", SITE_TITLE, date, body))

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
        render(tpl, SITE_TITLE, "style.css", SITE_TITLE, "每日 AI 前沿资讯", body))

    print(f"[site] 生成 {len(reports)} 期 → {SITE_DIR}")
    for d in dates:
        print(f"        {d}.html")
    print(f"        首页: {os.path.join(SITE_DIR, 'index.html')}")


if __name__ == "__main__":
    build()
