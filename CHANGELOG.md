# 变更记录

## 2026-10-17 · 提示词解耦 + 前端展示
- 提示词从 `brief.py` 抽离到 `prompts/`：`interests.md`（兴趣画像）、`brief.md`（模板）、`config.json`（模型/温度/条数/emoji）。
- `brief.py` 新增 `build_prompt()` 与 `prompt` 子命令（预览最终提示词，不发请求）。
- 网站新增「提示词」tab（`prompts.html`）：展示当前兴趣画像、提示词模板、板块规则与模型参数。
- 修复页面渲染会把 `{{...}}` 占位符误删的问题（改为只清理系统占位符）。


## 2026-10-17 · 收尾：外部定时与运维文档
- 外部定时改用 **Cloudflare Worker Cron**（`ai-brief-cron`），含临时测试触发，验证后已删除。
- 实测确认：外部触发成功、幂等生效（`已生成=yes 已推送=yes`，`no changes`）、网站更新到今天。
- 记录 GitHub 自带定时器曾延迟 2 小时以上。
- 更新 `AGENTS.md` 的当前进展 / 运维速查 / 已知限制。


## 2026-10-17 · 可靠性改造（幂等 + 校验 + 告警）
- `brief.py` 拆分为子命令：`generate`（只生成）/ `push`（幂等推送）/ `all`。
- 新增 `state/<日期>.json` 幂等账本（`generated_at` / `pushed_at` / `attempts`），已推送则跳过，避免重复推送。
- 新增 `check.py`：校验「生成 / 推送 / 网站」三项。
- `daily.yml`：加入 `concurrency` 串行锁、按状态跳过、`Verify` 校验、失败自动飞书告警；保留 00:00/00:30 双定时。
- 支持外部定时（cron-job.org）重复调用 `workflow_dispatch`，因幂等而安全。


## 2026-10-16 · 工作流改版（横向连接 + AI 标注）
- 节点改为**横向排布**，连接点出现在卡片**左/右两侧**，左右依次相连（不再上下相连）；画布加高，超宽可横向滚动。
- **非 AI 节点白底**、**AI 节点浅蓝底**并带「AI」角标，节点内直接列出 **AI 做了哪些事**。
- 新增图例（白=非AI / 蓝=AI）与「AI 做了什么 / 能力边界」说明面板。


## 2026-10-16 · 信息密度改版（网格布局）
- 顶部信息条合并为**一行**（日期·每日更新·标题·说明）。
- 今日头条改为**网格**（宽屏 3 列 / 中屏 2 列 / 窄屏 1 列），每张为独立卡片，首屏即可看全。
- 其余四个板块改为**双栏**（左两块 / 右两块），充分利用横向空间、减少留白。
- 收紧了间距与字号节奏，整体更紧凑。


## 2026-10-16 · 结构化晨报（新闻卡片）
- `brief.py` 的 DeepSeek 输出改为**结构化 JSON**（sections → items，含 title/summary/why/url），并用 `enrich()` 按 URL 回填**来源与时间**。
- 同一份数据生成两种产物：`reports/<日期>.json`（网站用）与 `reports/<日期>.md`（飞书/存档用）。
- 网站改为**卡片渲染**：头条（来源标签+时间+摘要+"为什么重要"高亮）、其余板块为紧凑列表；旧的 Markdown 存档自动回退为文章渲染。
- CSS 新增卡片/标签/新闻列表样式。


## 2026-10-16 · 视觉精装修（提升高级感）
- 排版：确立字号层级、标题负字距、正文行距 1.75、阅读宽度约 72 字符。
- 配色：Slate 灰阶 + 靛蓝主色；半透明边框 + 柔和阴影替代硬边框，卡片有垂坠感。
- 结构：首页新增 Hero 开场（日期 + 一句话）；分区标题；往期列表加星期、头条预览与箭头。
- 细节：粘性毛玻璃导航、hover/focus 过渡、自定义滚动条、选中色、emoji SVG favicon、theme-color、meta 描述。
- 内容宽度改为 `min(100% - 2×边距, 1120px)`，兼顾"自适应容器"与"阅读舒适"。


## 2026-10-16 · 工作流/资讯源增强 + 中文源 + 数据持久化
- 工作流页：改为**可拖动节点画布**（节点间自动连线；点击节点弹窗看细节），交互脚本 `templates/app.js`。
- 资讯源页：显示每个源的**最近抓取状态/时间**；点**标题**跳转源站，点**整行**弹窗查看该源**历史资讯**（可向下滚动）。
- 数据持久化：`brief.py` 抓取后写入 `data/items.json`（按 URL 去重累积）与 `data/sources_status.json`（各源状态）。
- 新增中文源：量子位、雷锋网、InfoQ 中文、爱范儿、开源中国（共 15 个源）。
- `daily.yml` 一并提交 `data/`。


## 2026-10-16 · 新增「工作流」「资讯源」两个板块
- 顶部标签栏扩展为三个 tab：`AI日报` / `工作流` / `资讯源`（自动高亮当前页）。
- 新增 `workflow.html`：以 6 步流程展示智能体工作流，并附关键指标卡。
- 新增 `sources.html`：按类别分组展示当前采集的 11 个信息源（含链接与说明）。
- 信息源抽成配置文件 `config/sources.json`，`brief.py` 采集与网站"资讯源"页共用。


## 2026-10-16 · 前端改版（白色系 + 首页改版）
- 整体改为白色系主题。
- 顶部新增标签栏（首个 tab「AI日报」，`.topbar` / `.tab`）。
- 首页改为：顶部「当前晨报」全文 + 下方「往期晨报」列表（点击查看）。
- 容器宽度自适应，左右固定边距（`--side`），单列纵向排布。
- 样式与结构集中在 `templates/style.css`、`templates/page.html`。


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
