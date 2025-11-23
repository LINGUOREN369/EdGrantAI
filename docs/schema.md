# GrantSchema

核心结构化字段：

- id: 稳定 ID（基于文本/URL 哈希）
- title: RFP 标题
- funder: 资助方
- url: 详情或来源链接
- summary: 简述
- eligibility: 资格条目（列表）
- deadline: 截止日期（可为空）
- amount: 资助金额或范围（文本）
- tags: 关键词，如 STEM/EdTech/K-12
- raw_ref: 追溯到原始文本的位置（可选）

生成流程：raw text → heuristics/LLM → GrantSchema JSON → data/structured/
