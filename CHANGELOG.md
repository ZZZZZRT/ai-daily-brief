# 变更记录

## 2026-10-16 · 第 3 期（网站）
- 新增 `build_site.py`：零依赖，把 `reports/` 渲染成 `site/` 静态网站（首页 + 每日页面 + style.css），带原文链接、上/下一天导航。
- `.github/workflows/daily.yml` 增加"构建网站"步骤，网站随每日晨报自动更新并提交。
- 更新 `AGENTS.md` / `README.md`。
- 待办：选择托管方案（GitHub Pages / Cloudflare Pages）并接入部署，把飞书推送链接指向网站。

## 2026-10-16
- 初始化项目：`brief.py` 引擎 + 每日定时（`.github/workflows/daily.yml`）+ 飞书推送 + 每日存档。
- 上线第 1 期，GitHub Actions 每天北京时间 08:00 自动运行。
- 新增 `AGENTS.md`（给 AI 的交接文档）与 `CHANGELOG.md`。
