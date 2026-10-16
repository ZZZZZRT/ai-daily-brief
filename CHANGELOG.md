# 变更记录

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
