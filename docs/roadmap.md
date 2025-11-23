# Roadmap

- Ingest
  - [ ] 支持更多 PDF/HTML 格式清洗
  - [ ] 网页正文抽取（去导航/广告）
- Extract
  - [ ] 引入 LLM JSON mode + 函数调用对齐 Pydantic Schema
  - [ ] 强化日期/金额解析与 funder 提取
- RAG
  - [ ] 结构化字段 + 原文段落的联合索引
  - [ ] 更智能的 metadata filter 构造
- Matching
  - [ ] 学科/学段权重细化；引入学习到的回归权重
  - [ ] 批量去重与同源聚合
- Reasoning
  - [ ] 增加可验证引用（段落编号/链接）
  - [ ] 草拟邮件/申请大纲
- API/UI
  - [ ] 增加分页与缓存
  - [ ] 前端交互完善与指标展示
