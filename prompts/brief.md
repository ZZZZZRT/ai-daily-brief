{{INTERESTS}}

下面是最近 {{MAX_AGE_DAYS}} 天抓到的候选资讯（{{COUNT}} 条）。请生成一份中文《AI 晨报》，只输出 JSON，不要任何额外说明。

JSON 结构：
{
  "sections": [
    {"name": "今日头条", "items": [
        {"title": "中文标题", "summary": "一句话摘要", "why": "为什么重要（一句话）", "url": "原文链接"}
    ]},
    {"name": "模型与产品", "items": [
        {"title": "中文标题", "summary": "一句话摘要", "url": "原文链接"}
    ]}
  ]
}

要求：
- 只保留与上面兴趣相关的，无关的丢弃
- 第一节固定为 "今日头条"，{{HEADLINE_MIN}}-{{HEADLINE_MAX}} 条，每条都必须有 summary 和 why
- 其余节从这几个里选：{{SECTIONS}}，每节 {{SECTION_MIN}}-{{SECTION_MAX}} 条，每条含 summary 和 url，不需要 why
- title 用简洁中文；url 必须是候选资讯里给出的原始链接，不要编造
- 全文中文

候选资讯：
{{LISTING}}
