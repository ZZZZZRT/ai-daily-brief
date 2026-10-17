# 项目说明（给 AI agent 的交接文档）

> 这是 OpenCode 会在新会话中**自动加载**的项目指令文件。新窗口接手本项目时，先读这里。

## 这是什么

每天早 8:00 自动抓取 AI 前沿资讯 → DeepSeek 智能筛选与摘要 → 推送飞书 → 存档。
**线上运行**：GitHub Actions（仓库 `ZZZZZRT/ai-daily-brief`，私有）。
**本地目录**（`Documents/AI资讯Agent/`）只是编辑台与备份，不参与每日运行。

## 架构与关键文件

| 文件 | 作用 |
|---|---|
| `brief.py` | 引擎（子命令：`generate` 生成 / `push` 推送 / `all` 两者）。常改点：`INTERESTS`(兴趣画像)、`call_deepseek` 里的 `prompt`(输出模板)、`push_feishu`(飞书推送) |
| `check.py` | 健康检查：判断今天「生成 / 推送 / 网站」是否完成（`python3 check.py all`） |
| `requirements.txt` | 依赖（feedparser） |
| `.github/workflows/daily.yml` | 定时任务说明书（cron、环境变量、存档提交） |
| `reports/brief-日期.md` | 每日晨报存档（Markdown，供飞书与兼容渲染） |
| `reports/brief-日期.json` | 每日晨报**结构化数据**（板块/条目/来源/时间），网站卡片渲染来源 |
| `build_site.py` | 网站生成器（零依赖）：把 `reports/` 渲染成 `docs/` 静态网站 |
| `config/sources.json` | **信息源清单**（`brief.py` 采集与网站"资讯源"页共用） |
| `prompts/interests.md` | **兴趣画像**（决定什么算重要） |
| `prompts/brief.md` | **提示词模板**（占位符由 `brief.py` 运行时替换） |
| `prompts/config.json` | **AI 配置**：模型、温度、鲜度、各板块条数、摘要长度、emoji |
| `templates/style.css` | **网站样式**（前端改动入口） |
| `templates/page.html` | **页面骨架**（前端改动入口），占位符 `{{TITLE}} {{CSS_URL}} {{SITE}} {{SUB}} {{BODY}}` |
| `templates/app.js` | **前端交互脚本**（工作流拖动/连线/弹窗、资讯源历史弹窗） |
| `data/items.json` | 资讯累积数据（每条含来源/标题/链接/时间），供资讯源历史弹窗使用 |
| `data/sources_status.json` | 各源最近抓取状态（成功/失败、条数、时间） |
| `state/日期.json` | **幂等账本**：记录 `generated_at` / `pushed_at` / `attempts`，用于避免重复推送 |
| `docs/` | 生成的网站（首页 + 每日页面 + style.css，Actions 自动更新） |
| `wrangler.jsonc` | Cloudflare Worker 配置：入口 `worker.js`、静态资源目录 `./docs` |
| `worker.js` | Cloudflare Worker：HTTP Basic Auth + 提供静态网站 |
| `CHANGELOG.md` | 变更记录 |

## 可靠性与幂等（不漏推、不重复推）

- 触发：GitHub schedule（00:00 / 00:30 UTC）+ 外部定时（Cloudflare Worker Cron：ai-brief-cron）调用 `workflow_dispatch`，可重复触发。
- 幂等：`state/<日期>.json` 记录 `generated_at` / `pushed_at`；`python brief.py push` 若已有 `pushed_at` 则跳过。
- 校验：`python3 check.py all` 检查「生成 / 推送 / 网站」三项，任一缺失即任务失败。
- 告警：任务失败时通过飞书发送告警。
- 并发：`concurrency: daily-brief`，同一天串行执行，避免并发重复推送。
- 重跑：Actions → Daily AI Brief → Run workflow（重跑会先检查状态，不会重复推送）。

## 网站托管与鉴权

- 托管：**Cloudflare Workers（Git 集成）**。Cloudflare 新版已把 Pages 并入 Workers，
  新项目是 Worker。构建命令 `npx wrangler deploy`，通过 `wrangler.jsonc`
  部署 `worker.js` + 静态资源 `./docs`。
- 鉴权：`worker.js` 提供 HTTP Basic Auth；用户名/密码存在 Worker 的
  **环境变量/密钥** `BASIC_USER` / `BASIC_PASS`（ASCII 字符）。
- 网址：部署成功后，将 Worker 的 URL 填入 `brief.py` 的 `SITE_URL`。
- 每日 Actions 提交 `docs/` 后，Cloudflare 自动重新构建部署。

## 网站结构

- 顶部标签栏（`templates/page.html` 的 `.tabs`）：`AI日报`（index.html）、`工作流`（workflow.html）、`资讯源`（sources.html）、`提示词`（prompts.html）。
- `build_site.py` 生成：`index.html`（当前晨报 + 往期列表）、每日页 `<日期>.html`、`workflow.html`（可拖动节点+弹窗）、`sources.html`（状态+历史弹窗）、`prompts.html`（当前提示词与规则）。
- 交互脚本 `templates/app.js` 会被拷到 `docs/app.js`；资讯数据从 `docs/data/items.json` 读取（因此本地预览要用 HTTP 服务，不能用 file://）。
- 本地预览：`cd docs && python3 -m http.server 8123`，然后打开 http://localhost:8123/ 。

## 本地 / 线上边界（重要，别搞错）

- 每天运行时，GitHub Actions **只使用 GitHub 仓库里的代码，完全不使用本地文件**。
- 本地改动**必须 `git push` 到 GitHub 才生效**。
- Actions 每天会自动向 GitHub 提交 `reports/`，因此**本地改动前必须先 `git pull`**，否则 push 会冲突。
- 密钥（`DEEPSEEK_API_KEY`、`FEISHU_WEBHOOK_URL`）存在 **GitHub Secrets**，不要写进代码。

## 常见改动怎么做

| 想改什么 | 改哪里 |
|---|---|
| 加/删信息源 | `config/sources.json`（每项 `name` / `url` / `category` / `note`）；采集与"资讯源"页都会同步 |
| 调兴趣 / 筛选偏好 | `prompts/interests.md` |
| 改输出模板 / 板块规则 | `prompts/brief.md`（模板）+ `prompts/config.json`（条数/板块/emoji） |
| 换模型 / 温度 / 摘要长度 | `prompts/config.json` |
| **改网站样式** | `templates/style.css` |
| **改网站结构/页头页脚** | `templates/page.html`，再 `python3 build_site.py` 重新生成 |
| **改前端交互**（拖动/弹窗等） | `templates/app.js` |
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

- [x] 第 1 期：抓取 + DeepSeek 筛选 + 飞书推送 + 存档（每天 8:00 自动）
- [x] 第 3 期：网站（首页 / 历史 / 原文 / 工作流 / 资讯源），构建于 `docs/`
- [x] 可靠性与幂等：状态账本 + 校验 + 失败告警 + Cloudflare Worker Cron 外部触发
- [x] 网站托管：GitHub Pages（公开）https://zzzzzrt.github.io/ai-daily-brief/
- [x] 信息源：15 个（含中文媒体：量子位 / 雷锋网 / InfoQ / 爱范儿 / 开源中国）
- [ ] 第 2 期：接入 X / Reddit / 小红书 / B站 等社交源
- [ ] 第 4 期：知识库 + AI 问答
- [ ] 可选：Cloudflare Worker 托管 + 密码（`worker.js` / `wrangler.jsonc` 已就绪，因 workers.dev 国内被墙暂缓）

## 运维速查

- 站点：https://zzzzzrt.github.io/ai-daily-brief/ （GitHub Pages，随 push 自动更新）
- 仓库：https://github.com/ZZZZZRT/ai-daily-brief
- Actions：https://github.com/ZZZZZRT/ai-daily-brief/actions/workflows/daily.yml
- 外部定时：Cloudflare Worker `ai-brief-cron`（Cron：`5,35 0 * * *`、`5 1 * * *`）
- 手动补跑：Actions → Daily AI Brief → Run workflow（幂等，不会重复推送）
- 查看状态：`python3 check.py all`；查看账本：`cat state/<日期>.json`
- 失败排查：看 Actions 日志；连续失败会收到飞书告警

## 已知限制

- GitHub 自带定时器不可靠（曾延迟 2 小时以上），已用 Cloudflare Worker Cron 兜底。
- `*.workers.dev` 在国内被 DNS 污染，网站改用 GitHub Pages；Cloudflare 托管 + 密码方案保留备用。
- 信息源 15 个（英文官方/媒体 + 中文媒体），社交源（X / Reddit / 小红书 / B站）待第 2 期。
- AI 只看标题与 ≤180 字摘要，未读正文全文，摘要与观点可能不完整。
