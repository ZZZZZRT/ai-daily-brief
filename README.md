# ☀️ AI 晨报 (ai-daily-brief)

每天早 8:00 自动抓取 AI 前沿资讯 → DeepSeek 智能筛选与摘要 → 推送飞书。

## 文档说明

- `README.md`（本文件）：给**人**看的用法说明。
- `AGENTS.md`：给 **AI** 看的项目交接文档（OpenCode 新会话会自动加载），包含架构、约定、当前进展、改动位置。
- `CHANGELOG.md`：每次改动的记录。

> 用 AI 迭代本项目时，改动完成后记得同步更新 `AGENTS.md` / `CHANGELOG.md` / 本文件。

## 它做什么

1. 抓取一批已验证的 AI 信息源（RSS + Hacker News）
2. 按标题去重、按新鲜度过滤（默认最近 3 天）
3. 用 DeepSeek 按"兴趣画像"筛选、分组、写中文摘要
4. 推送到飞书（交互卡片，链接可点）
5. 存档到 `reports/brief-YYYY-MM-DD.md`（作为历史与知识库的原始数据）

## 信息源

见 `brief.py` 顶部的 `SOURCES`。当前包含：
OpenAI、Google DeepMind、Google AI Blog、HuggingFace、arXiv cs.AI、
TLDR AI、Ben's Bites、Simon Willison、MIT Tech Review AI、量子位、Hacker News。

## 本地运行

```bash
pip install -r requirements.txt
export DEEPSEEK_API_KEY="sk-..."
export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/..."
python brief.py
```

## 线上（GitHub Actions）

- 定时：每天 00:00 UTC（北京时间 08:00），见 `.github/workflows/daily.yml`
- 需要的仓库 Secrets：`DEEPSEEK_API_KEY`、`FEISHU_WEBHOOK_URL`
- 也可在 Actions 页面手动触发（workflow_dispatch）

## 路线图

- [x] 第一期：抓取 + AI 筛选 + 飞书推送 + 存档
- [ ] 第二期：接入 X / Reddit / 小红书 / B站 等社交源
- [ ] 第三期：自定义资讯网站（日报 / 历史 / 点原文）
- [ ] 第四期：知识库 + AI 问答
