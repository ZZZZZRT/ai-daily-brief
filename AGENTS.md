# 项目说明（给 AI agent 的交接文档）

> 这是 OpenCode 会在新会话中**自动加载**的项目指令文件。新窗口接手本项目时，先读这里。

## 这是什么

每天早 8:00 自动抓取 AI 前沿资讯 → DeepSeek 智能筛选与摘要 → 推送飞书 → 存档。
**线上运行**：GitHub Actions（仓库 `ZZZZZRT/ai-daily-brief`，私有）。
**本地目录**（`Documents/AI资讯Agent/`）只是编辑台与备份，不参与每日运行。

## 架构与关键文件

| 文件 | 作用 |
|---|---|
| `brief.py` | 引擎。含三处常改点：`SOURCES`(信息源)、`INTERESTS`(兴趣画像)、`call_deepseek` 里的 `prompt`(输出模板)；以及 `push_feishu`(飞书推送) |
| `requirements.txt` | 依赖（feedparser） |
| `.github/workflows/daily.yml` | 定时任务说明书（cron、环境变量、存档提交） |
| `reports/brief-日期.md` | 每日晨报存档（Actions 每天自动提交回仓库） |
| `build_site.py` | 网站生成器（零依赖）：把 `reports/` 渲染成 `docs/` 静态网站 |
| `docs/` | 生成的网站（首页 + 每日页面 + style.css，Actions 自动更新） |
| `wrangler.jsonc` | Cloudflare Worker 配置：入口 `worker.js`、静态资源目录 `./docs` |
| `worker.js` | Cloudflare Worker：HTTP Basic Auth + 提供静态网站 |
| `CHANGELOG.md` | 变更记录 |

## 网站托管与鉴权

- 托管：**Cloudflare Workers（Git 集成）**。Cloudflare 新版已把 Pages 并入 Workers，
  新项目是 Worker。构建命令 `npx wrangler deploy`，通过 `wrangler.jsonc`
  部署 `worker.js` + 静态资源 `./docs`。
- 鉴权：`worker.js` 提供 HTTP Basic Auth；用户名/密码存在 Worker 的
  **环境变量/密钥** `BASIC_USER` / `BASIC_PASS`（ASCII 字符）。
- 网址：部署成功后，将 Worker 的 URL 填入 `brief.py` 的 `SITE_URL`。
- 每日 Actions 提交 `docs/` 后，Cloudflare 自动重新构建部署。

## 本地 / 线上边界（重要，别搞错）

- 每天运行时，GitHub Actions **只使用 GitHub 仓库里的代码，完全不使用本地文件**。
- 本地改动**必须 `git push` 到 GitHub 才生效**。
- Actions 每天会自动向 GitHub 提交 `reports/`，因此**本地改动前必须先 `git pull`**，否则 push 会冲突。
- 密钥（`DEEPSEEK_API_KEY`、`FEISHU_WEBHOOK_URL`）存在 **GitHub Secrets**，不要写进代码。

## 常见改动怎么做

| 想改什么 | 改哪里 |
|---|---|
| 加/删信息源 | `brief.py` 的 `SOURCES`（每行 `("名称", "RSS地址")`） |
| 调兴趣 / 筛选偏好 | `brief.py` 的 `INTERESTS` |
| 改输出模板（分组、字数、结构） | `brief.py` 里 `call_deepseek` 的 `prompt` 中"要求"部分 |
| 改推送时间 | `.github/workflows/daily.yml` 的 `cron`（UTC；北京 8:00 = `0 0 * * *`） |
| 换推送渠道 | `brief.py` 的 `push_feishu` + 新增 Secrets |

## 工作约定（务必遵守）

1. **改动的默认流程**：用户让你改 → `git pull` → 改 → `git commit` → `git push` → 简要汇报。用户已授权"改完自动上传"。
2. **每次改动完成后，必须检查并更新文档**：
   - 更新本文件（`AGENTS.md`）的「当前进展」；
   - 在 `CHANGELOG.md` 追加一条；
   - 若"用法/配置方式"变了，同步更新 `README.md`。
3. 改完后建议：在 GitHub Actions 页面 **Run workflow** 验证一次。

## 当前进展

- [x] 第 1 期：抓取 + DeepSeek 筛选 + 飞书推送 + 存档（已上线，每天 8:00）
- [x] 第 3 期：网站生成器 `build_site.py` → `docs/`（每日自动更新）
- [x] 网站托管改用 Cloudflare Workers + 密码鉴权（`worker.js` + `wrangler.jsonc`），URL 待填
- [ ] 第 2 期：接入 X / Reddit / 小红书 / B站 等社交源
- [ ] 第 4 期：知识库 + AI 问答

## 如何验证

- 手动触发：GitHub → Actions → Daily AI Brief → Run workflow
- 看结果：飞书消息 + `reports/` 新增文件

## 已知限制

- 当前使用的 GitHub Token 是**细粒度只读**，无法用 CLI 创建仓库或写入 Secrets，需在网页操作。
- 信息源目前以英文 RSS 为主，中文源与社交源待第 2 期补充。
