# ai_context 新增「读完等待指令」约束

## 变更

- `ai_context/instructions.md` 的 Entry Point 段新增一段:
  读完 `ai_context/` 后停下等下一步指示,不要自行改代码/schema/prompts/docs,
  即使发现可疑点也不擅动。`ai_context/` 是上下文加载,不是任务书。

## 原因

避免 agent 把"上下文阅读"误当作"任务执行",在用户未明确给出请求前就开始
修改仓库。

## 影响范围

- 仅 `ai_context/instructions.md` 文案增加,无代码/schema 改动。
- 与现有 `read_scope.md`「不主动深读」规则方向一致,形成更完整的边界。
