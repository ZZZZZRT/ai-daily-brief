#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
健康检查：判断今天的「生成 / 推送 / 网站」是否完成。
用法:
  python3 check.py date       # 打印北京时间的今天
  python3 check.py generated  # 退出码 0 = 已生成
  python3 check.py pushed     # 退出码 0 = 已推送
  python3 check.py site       # 退出码 0 = 网站已更新
  python3 check.py all        # 三项都完成才退出 0，并打印明细
"""
import os, sys, json, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR = os.path.join(BASE, "reports")
SITE_DIR = os.path.join(BASE, "docs")
STATE_DIR = os.path.join(BASE, "state")


def bj_today():
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)).date().isoformat()


def generated(date):
    return os.path.exists(os.path.join(REPORT_DIR, f"brief-{date}.json"))


def pushed(date):
    p = os.path.join(STATE_DIR, f"{date}.json")
    try:
        with open(p, encoding="utf-8") as f:
            return bool(json.load(f).get("pushed_at"))
    except Exception:
        return False


def site(date):
    return os.path.exists(os.path.join(SITE_DIR, f"{date}.html"))


CHECKS = [("generated", generated), ("pushed", pushed), ("site", site)]


def main():
    date = bj_today()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"

    if cmd == "date":
        print(date)
        return 0
    for name, fn in CHECKS:
        if cmd == name:
            return 0 if fn(date) else 1
    if cmd != "all":
        print(f"unknown command: {cmd}", file=sys.stderr)
        return 2

    ok = True
    print(f"date: {date}")
    for name, fn in CHECKS:
        good = fn(date)
        ok = ok and good
        print(f"{name}: {'ok' if good else 'MISSING'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
