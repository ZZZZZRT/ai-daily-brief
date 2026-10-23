#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地控制台（仅绑定 127.0.0.1，不对外网开放）

  http://localhost:8123/        -> 网站
  http://localhost:8123/admin   -> 控制台

功能：
  - 读取 / 保存 prompts/ 下的兴趣画像、提示词模板、配置
  - 保存后自动 build_site.py 重新生成网站，并 git commit + push
  - 预览最终提示词（不调用 AI）
  - 试跑一次（调用 AI，写入 reports/preview.*，不推送、不改状态）

启动： python3 admin.py
"""
import json
import os
import subprocess
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(BASE, "docs")
TEMPLATE_DIR = os.path.join(BASE, "templates")
PROMPT_DIR = os.path.join(BASE, "prompts")
PORT = 8123

sys.path.insert(0, BASE)
import promptlib  # noqa: E402

VENV_PY = os.path.expanduser("~/.agent-reach-venv/bin/python")
PY = VENV_PY if os.path.exists(VENV_PY) else sys.executable

INT_FIELDS = {
    "max_age_days": 3, "headline_min": 3, "headline_max": 5,
    "section_min": 3, "section_max": 8, "excerpt_chars": 180,
    "per_source_limit": 25,
}

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
}


def load_env():
    """读取项目根目录的 .env（已 gitignore），把变量注入当前进程。"""
    path = os.path.join(BASE, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def read_data():
    interests, brief = promptlib.load_prompts()
    return {"interests": interests, "brief": brief, "config": promptlib.load_config()}


def write_atomic(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def run(cmd, timeout=240):
    p = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True, timeout=timeout)
    return {"code": p.returncode, "out": (p.stdout or "").strip(),
            "err": (p.stderr or "").strip()}


def normalize_config(cfg):
    out = dict(cfg)
    out["temperature"] = float(cfg.get("temperature", 0.4))
    for k, default in INT_FIELDS.items():
        out[k] = int(cfg.get(k, default))
    if not isinstance(out.get("sections"), list) or not out["sections"]:
        raise ValueError("sections 必须是非空数组")
    if "section_emoji" not in out or not isinstance(out["section_emoji"], dict):
        out["section_emoji"] = {}
    if out["headline_min"] > out["headline_max"]:
        raise ValueError("头条最小条数不能大于最大条数")
    if out["section_min"] > out["section_max"]:
        raise ValueError("每节最小条数不能大于最大条数")
    return out


def save_prompts(body):
    interests = (body.get("interests") or "").strip()
    brief = body.get("brief") or ""
    if not interests:
        return {"ok": False, "error": "兴趣画像不能为空"}
    if not brief.strip():
        return {"ok": False, "error": "提示词模板不能为空"}
    if "{{LISTING}}" not in brief:
        return {"ok": False, "error": "提示词模板缺少 {{LISTING}}，会导致没有候选资讯"}
    try:
        cfg = normalize_config(body.get("config") or {})
    except Exception as e:
        return {"ok": False, "error": f"配置有误：{e}"}

    os.makedirs(PROMPT_DIR, exist_ok=True)
    new_i = interests + "\n"
    new_b = brief if brief.endswith("\n") else brief + "\n"
    new_c = json.dumps(cfg, ensure_ascii=False, indent=2) + "\n"

    def read_or_empty(name):
        p = os.path.join(PROMPT_DIR, name)
        try:
            with open(p, encoding="utf-8") as f:
                return f.read()
        except Exception:
            return None

    if (read_or_empty("interests.md") == new_i and
            read_or_empty("brief.md") == new_b and
            read_or_empty("config.json") == new_c):
        return {"ok": True, "changed": False,
                "steps": [{"name": "保存", "code": 0,
                           "out": "内容没有变化，未重新生成、未提交", "err": ""}]}

    write_atomic(os.path.join(PROMPT_DIR, "interests.md"), new_i)
    write_atomic(os.path.join(PROMPT_DIR, "brief.md"), new_b)
    write_atomic(os.path.join(PROMPT_DIR, "config.json"), new_c)

    build = run([PY, "build_site.py"])

    steps = [{"name": "build_site.py", **build}]
    run(["git", "add", "prompts/", "docs/"])
    diff = run(["git", "diff", "--cached", "--quiet"])
    if diff["code"] == 0:
        steps.append({"name": "git", "code": 0, "out": "没有变化，未提交", "err": ""})
        changed = False
    else:
        commit = run(["git", "commit", "-m", "prompts: update via local admin"])
        steps.append({"name": "git commit", **commit})
        push = run(["git", "push", "origin", "main"], timeout=240)
        steps.append({"name": "git push", **push})
        changed = True

    ok = build["code"] == 0 and all(s.get("code", 0) == 0 for s in steps)
    return {"ok": ok, "changed": changed, "steps": steps}


def preview_prompt():
    sample = [
        {"source": "OpenAI 官方", "title": "示例标题 A", "excerpt": "示例摘要 A", "url": "https://example.com/a"},
        {"source": "量子位", "title": "示例标题 B", "excerpt": "示例摘要 B", "url": "https://example.com/b"},
    ]
    return {"ok": True, "prompt": promptlib.build_prompt(sample)}


def run_preview():
    r = run([PY, "brief.py", "preview"], timeout=300)
    return {"ok": r["code"] == 0, "markdown": r["out"], "err": r["err"]}


def sync_repo():
    """把云端最新提交拉到本地（只允许 fast-forward，避免覆盖本地改动）。"""
    pull = run(["git", "pull", "--ff-only", "origin", "main"], timeout=300)
    head = run(["git", "rev-parse", "--short", "HEAD"])
    return {"ok": pull["code"] == 0, "head": head["out"],
            "steps": [{"name": "git pull", **pull}]}


class Handler(BaseHTTPRequestHandler):
    server_version = "AIBriefAdmin/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _json(self, obj, status=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _file(self, path, ctype):
        try:
            with open(path, "rb") as f:
                data = f.read()
        except Exception:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if path.endswith(("admin.html", ".json")):
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path in ("/admin", "/admin/"):
            return self._file(os.path.join(TEMPLATE_DIR, "admin.html"), "text/html; charset=utf-8")
        if path == "/api/data":
            try:
                return self._json(read_data())
            except Exception as e:
                return self._json({"ok": False, "error": str(e)}, 500)
        rel = path.lstrip("/") or "index.html"
        fp = os.path.normpath(os.path.join(DOCS, rel))
        if not fp.startswith(DOCS) or not os.path.isfile(fp):
            fp = os.path.join(DOCS, "index.html")
        ctype = CONTENT_TYPES.get(os.path.splitext(fp)[1], "application/octet-stream")
        self._file(fp, ctype)

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n) or b"{}") if n else {}
        except Exception as e:
            return self._json({"ok": False, "error": f"请求格式错误：{e}"}, 400)

        try:
            if path == "/api/save":
                return self._json(save_prompts(body))
            if path == "/api/preview":
                return self._json(preview_prompt())
            if path == "/api/run":
                return self._json(run_preview())
            if path == "/api/sync":
                return self._json(sync_repo())
            return self._json({"ok": False, "error": "not found"}, 404)
        except Exception as e:
            return self._json({"ok": False, "error": str(e)}, 500)


def main():
    load_env()
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"本地控制台已启动：")
    print(f"  网站   http://localhost:{PORT}/")
    print(f"  控制台 http://localhost:{PORT}/admin")
    print(f"  Python  {PY}")
    print("按 Ctrl+C 停止")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
