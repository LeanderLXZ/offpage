# users 状态回写

适用场景：

- 在一次角色对话或一次 session 之后，把应该落到 `users/` 的状态变化写回去
- 或者在对话进行中的持续写回检查点，把本轮变化增量写回 `users/`
- 或者在会话结束并得到确认后，把一个 context 的内容提升或合并进长期用户状态

## 可直接使用的提示词

```text
你现在接手本地项目 `persona-engine`，你没有任何额外背景知识，请完全按本提示词执行。

目标：
根据本轮用户与角色的互动，把需要持久化的用户侧状态持续写入 `users/{user_id}/`，但不改写作品级 canon。

这份 prompt 有两种用法：

1. 作为 `用户入口与上下文装载` 的内置下游子流程，在对话中持续运行，用于维护 `session / context`。
2. 作为一个独立 prompt，在一次 session 结束后补写、修复、重算或执行显式 context 合并。

如果你当前处在运行中的对话里，不要等用户额外说一句“现在回写”才开始维护 `users/`。
你应把写回理解成运行时内部的持续维护逻辑，但要区分轻量层与长期层：

- 轻量层：`session / context`
- 长期层：`long_term_profile / relationship_core / pinned_memories`

开始实质工作前，先做一次最小结构读取：

1. 先读 `prompts/shared/最小结构读取入口.md`
2. 再读：
   - `README.md`
   - `users/README.md`
   - 如果本轮需要对照基础 canon：`works/README.md`
3. 如果存在：`users/{user_id}/role_binding.json`
4. 如果你准备读取或写入结构化 JSON / JSONL，再补读 `schemas/README.md` 与对应 schema
5. 如果你仍不确定哪些变化该留在 `context / session / relationship_core`，再补读 `docs/architecture/data_model.md`

你必须遵守这些边界：

1. 只更新 `users/{user_id}/...`
2. 不要把用户互动写回 `works/{work_id}/world/`
3. 不要把用户互动写回 `works/{work_id}/characters/{character_id}/`
4. 不要把某一部作品、某一个目标角色的关系漂移直接写进根级 `users/{user_id}/profile.json`

优先考虑更新这些内容：

1. `role_binding.json`
2. `long_term_profile.json`
3. `relationship_core/manifest.json`
4. `relationship_core/pinned_memories.jsonl`
5. `contexts/{context_id}/manifest.json`
6. `contexts/{context_id}/character_state.json`
7. `contexts/{context_id}/relationship_state.json`
8. `contexts/{context_id}/shared_memory.jsonl`
8. `contexts/{context_id}/session_index.json`
9. `sessions/{session_id}/transcript.jsonl`
10. `sessions/{session_id}/turn_journal.jsonl`
11. `sessions/{session_id}/turn_summaries.jsonl`
12. `sessions/{session_id}/memory_updates.jsonl`
13. `users/{user_id}/conversation_library/archive_index.jsonl`
14. 当前锁定绑定的 `users/{user_id}/conversation_library/archive_refs.json`

`role_binding.json` 至少应能承接这些信息：

- 当前目标角色与其 `stage_id`
- 当前用户侧身份模式
- 如果用户侧身份是 canon 角色：该用户侧角色与其阶段绑定模式
- 当前 context 的装载偏好、写回偏好或 merge 偏好
- 当前设定是否已经锁定

写回原则：

1. 只写“用户侧变化”：
   - 全局用户画像的稳定补充
   - work-scoped 长期画像变化
   - 用户与角色的关系变化
   - 用户侧角色漂移
   - 用户和角色之间的新事件
   - context / session / transcript / memory updates
2. 完整 `transcript.jsonl` 可以作为本地完整对话历史持续保存。
3. 但运行时启动默认应优先读取摘要层，而不是全量重读 transcript。
4. 每轮输入和输出都应先进入本地 transcript / turn journal，再考虑后续摘要与长期写回。
5. 区分：
   - 短期上下文状态
   - 应进入 `long_term_profile` 的长期变化
   - 应进入 `relationship_core` 的长期变化
6. 连续写回默认先做轻量层：
   - `sessions/{session_id}/...`
   - `contexts/{context_id}/...`
   - 特别是 `contexts/{context_id}/character_state.json`：
     - 每轮都应评估模拟角色的情绪、性格、口癖、与用户的约定是否发生了变化
     - 如果发生了变化，实时更新 `character_state.json`
     - 这些是 context 级的实时变化，不需要等合并
7. 在对话仍在进行时，不要把长期画像和长期关系核心当成每轮都要更新的默认落点。
8. 只有在以下条件成立时，才进入长期层：
   - 用户明确要求“记住这段关系变化”或“把这个 context 合并进去”
   - 会话已经结束，且用户明确同意并入长期历史
9. 执行长期合并时，优先采用追加而不是覆盖：
   - 事件历史追加
   - 记忆点追加
   - 画像变化记录追加
10. 如果执行 context 合并，应至少考虑：
   - 从 `character_state.json` 提炼模拟角色的累积变化，追加写入 `long_term_profile.json` 的 `character_drift_history`
   - 从 `character_state.json` 提炼持久的口癖/行为变化，更新 `relationship_core` 的 `personalized_voice_shift` 和 `personalized_behavior_shift`
   - 从 `character_state.json` 提炼持久有效的双方约定，追加写入 `relationship_core` 的 `mutual_agreements`
   - 更新 `long_term_profile.json` 的事件和记忆历史
   - 更新 `relationship_core` 的关系标签和数值
   - 更新 `merged_context_ids`
   - 提升必要的 `pinned_memories`
   - 更新当前 context 的 `lifecycle`
   - 生成 `archive_id`
   - 把完整对话记录归档进 `users/{user_id}/conversation_library/archives/{archive_id}/`
   - 更新 `users/{user_id}/conversation_library/archive_index.jsonl`
   - 更新当前锁定绑定的 `users/{user_id}/conversation_library/archive_refs.json`

输出要求：

1. 明确本轮新增了哪些用户侧状态。
2. 明确哪些内容只留在当前 context / session。
3. 明确哪些内容被提升成长期画像或长期记忆。
4. 如果执行了 context 提升或合并，明确说明：
   - 提升了哪些内容
   - 为什么这些内容值得进入长期状态
   - 这些记录是否按追加方式写入
   - 当前 context 是否已变为 `merged`
5. 如果证据不足以形成稳定变化，只做轻量更新，不要过度写入。
6. 如果你是作为运行时内部子流程执行，可以静默落盘，但仍应留下简短的结构化说明，供后续 agent 接力。
7. 如果用户拒绝并入长期历史，明确说明：
   - 只保留了哪些 `session / context` 级更新
   - 哪些长期层文件没有被改动

稀释保护机制：

1. 开始写回前，先写一张“当前任务卡”：
   - 当前目标
   - 当前阶段
   - 当前允许写入的目录
   - 当前禁止做的事
2. 不需要反复重读整份 prompt，但在以下时点必须回看本 prompt 的这些段落：
   - `目标`
   - `开始实质工作前，先做一次最小结构读取`
   - `边界`
   - `优先考虑更新这些内容`
   - `写回原则`
   - `输出要求`
   - `稀释保护机制`
3. 如果这次写回建立在正在进行的多轮会话之上，开始写回判断前，先回看 [会话稀释保护检查清单](./会话稀释保护检查清单.md)，确认当前 `work_id / character_id / context_id / session_id` 没有漂移。
4. 在以下时点，必须回看 [写回前防污染检查清单](./写回前防污染检查清单.md)：
   - 开始判断本轮是否需要写回前
   - 准备写入长期记忆前
   - 准备执行 context 提升或 full merge 前
   - 准备正式落盘前
5. 如果这是多轮 session 回写，也把“每一轮回写判断”视为单批次。
6. 每完成一轮回写后，都应按 `prompts/shared/批次交接模板.md` 产出简短交接摘要。
7. 一旦发现自己开始把用户事件、关系变化或记忆写回 `works/`，立即停止，先回看 `边界`、`写回原则` 与 [写回前防污染检查清单](./写回前防污染检查清单.md)。

我会补充给你：

- `user_id`
- `work_id`
- `character_id`
- `context_id`
- `session_id`
- 本轮对话摘要或关键片段
- 是否已经结束会话
- 用户是否同意并入长期历史
```
