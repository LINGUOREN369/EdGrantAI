# Matching Logic

- 检索：SmartRetriever
  - 优先 metadata 过滤（如 tags），若无结果回退到语义检索
- 打分：weighted_score(similarity, meta, project)
  - 语义相似度（距离 → 相似度）
  - 领域权重（STEM/EdTech/curriculum/PD）
  - eligibility 规则乘子（501c3/地理）
- 输出：grant_id, title, snippet, score, meta
