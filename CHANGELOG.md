# 变更记录

## 2026-10-16 · 前端模板化 + 托管暂缓
- 把前端从 Python 中抽离：新增 `templates/style.css`（样式）与 `templates/page.html`（页面骨架，占位符）。
- `build_site.py` 改为读取 `templates/` 渲染，行为不变。
- 托管决定暂缓：`workers.dev` 在国内被 DNS 污染/封锁无法直连；`worker.js` / `wrangler.jsonc` 保留备用。


## 2026-10-16 · 改用 Cloudflare Workers 托管
- Cloudflare 新版把 Pages 并入 Workers，新项目即 Worker。据此调整：
- 新增 `wrangler.jsonc`（入口 `worker.js`，静态资源目录 `./docs`）与 `worker.js`（HTTP Basic Auth + 静态托管）。
- 移除 `functions/_middleware.js`（Pages 专用）。
- 账号密码存 Worker 环境变量/密钥 `BASIC_USER` / `BASIC_PASS`。
- `brief.py` 的 `SITE_URL` 暂置空，待部署成功后填入 Worker 的 URL。


## 2026-10-16 · 网站加密码 + 换托管
- 新增 `functions/_middleware.js`：Cloudflare Pages 鉴权中间件（HTTP Basic Auth），未登录返回 401。
- 托管从 GitHub Pages 迁移到 **Cloudflare Pages**（连接本仓库，输出目录 `docs`），账号密码存环境变量 `BASIC_USER` / `BASIC_PASS`。
- 仓库转为私有。飞书推送的网站链接更新为 https://ai-daily-brief.pages.dev/。
- 更新 `brief.py`、`AGENTS.md`、`README.md`。


## 2026-10-16 · 第 3 期（网站）
- 新增 `build_site.py`：零依赖，把 `reports/` 渲染成静态网站（首页 + 每日页面 + style.css），带原文链接、上/下一天导航。
- 网站输出目录定为 `docs/`（GitHub Pages "从分支发布"支持 `/docs`）。
- `.github/workflows/daily.yml` 增加"构建网站"步骤，网站随每日晨报自动更新并提交。
- 飞书推送末尾加入"在网站查看 / 浏览历史"链接。
- 仓库设为公开并用 GitHub Pages 发布：https://zzzzzrt.github.io/ai-daily-brief/
- 更新 `AGENTS.md` / `README.md`。

## 2026-10-16
- 初始化项目：`brief.py` 引擎 + 每日定时（`.github/workflows/daily.yml`）+ 飞书推送 + 每日存档。
- 上线第 1 期，GitHub Actions 每天北京时间 08:00 自动运行。
- 新增 `AGENTS.md`（给 AI 的交接文档）与 `CHANGELOG.md`。
