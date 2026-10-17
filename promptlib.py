#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提示词加载与渲染（无第三方依赖）。
供 brief.py（生成晨报）与 admin.py（本地控制台）共用。
"""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
PROMPT_DIR = os.path.join(BASE, "prompts")


def load_config():
    with open(os.path.join(PROMPT_DIR, "config.json"), encoding="utf-8") as f:
        return json.load(f)


def load_prompts():
    with open(os.path.join(PROMPT_DIR, "interests.md"), encoding="utf-8") as f:
        interests = f.read().strip()
    with open(os.path.join(PROMPT_DIR, "brief.md"), encoding="utf-8") as f:
        template = f.read()
    return interests, template


def build_prompt(items, cfg=None, interests=None, template=None):
    """用 prompts/brief.md 模板渲染最终提示词。"""
    if cfg is None:
        cfg = load_config()
    if interests is None or template is None:
        interests, template = load_prompts()
    excerpt = int(cfg.get("excerpt_chars", 180))
    listing = "\n".join(
        f"{n+1}. [{i['source']}] {i['title']}\n   {i['excerpt'][:excerpt]}\n   {i['url']}"
        for n, i in enumerate(items))
    return (template
            .replace("{{INTERESTS}}", interests)
            .replace("{{MAX_AGE_DAYS}}", str(int(cfg.get("max_age_days", 3))))
            .replace("{{COUNT}}", str(len(items)))
            .replace("{{HEADLINE_MIN}}", str(cfg.get("headline_min", 3)))
            .replace("{{HEADLINE_MAX}}", str(cfg.get("headline_max", 5)))
            .replace("{{SECTION_MIN}}", str(cfg.get("section_min", 3)))
            .replace("{{SECTION_MAX}}", str(cfg.get("section_max", 8)))
            .replace("{{SECTIONS}}", "、".join(cfg.get("sections", [])))
            .replace("{{LISTING}}", listing))
