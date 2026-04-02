# 用户包

这个顶层目录用于存放所有用户侧状态。

真实用户数据默认只作本地状态，不进入 git。

## 推荐结构

```text
users/
  {user_id}/
    profile.json
    personas/
      {persona_id}.json
    conversation_library/
      manifest.json
      archive_index.jsonl
      scopes/
        {work_id}/
          {character_id}/
            archive_refs.json
      archives/
        {archive_id}/
          manifest.json
          context_summary.json
          session_index.json
          key_moments.jsonl
          sessions/
            {session_id}/
              manifest.json
              transcript.jsonl
              turn_summaries.jsonl
              memory_updates.jsonl
    works/
      {work_id}/
        manifest.json
        characters/
          {character_id}/
            role_binding.json
            long_term_profile.json
            relationship_core/
              manifest.json
              pinned_memories.jsonl
            contexts/
              {context_id}/
                manifest.json
                relationship_state.json
                shared_memory.jsonl
                session_index.json
                sessions/
                  {session_id}/
                    manifest.json
                    transcript.jsonl
                    turn_journal.jsonl
                    turn_summaries.jsonl
                    memory_updates.jsonl
```

## 设计分层

### 1. 账户层

- `profile.json`
  - 全局用户画像
- `personas/`
  - 可选的用户 persona
- `conversation_library/`
  - 账户级长期对话归档库

### 2. 关系运行层

- `works/{work_id}/characters/{character_id}/`
  - 当前作品、当前目标角色下的活跃关系状态
- `contexts/{context_id}/`
  - 可写的 branch context
- `sessions/{session_id}/`
  - 当前 context 下的一次具体会话

### 3. 长期关系层

- `long_term_profile.json`
  - work-character scoped 的长期自我画像变化
- `relationship_core/`
  - 该用户与该角色之间的长期关系核心

## 完整对话记录模型

### 活跃会话

活跃会话期间，完整对话首先保存在：

- `contexts/{context_id}/sessions/{session_id}/transcript.jsonl`

推荐同时维护：

- `turn_journal.jsonl`
  - 记录每次输入、输出、摘要、写回、失败或恢复事件
- `turn_summaries.jsonl`
  - 摘要层
- `memory_updates.jsonl`
  - 写回候选与记忆更新

### 账户归档库

当用户选择把某个 context 并入账户长期信息时，完整对话记录应进入：

- `conversation_library/archives/{archive_id}/`

推荐归档内容：

- `manifest.json`
  - 归档来源、`work_id`、`character_id`、`context_id`、包含的
    `session_id`、合并时间、stage、merge reason
- `context_summary.json`
  - 归档层摘要
- `session_index.json`
  - 本归档内部可检索的 session 索引
- `key_moments.jsonl`
  - 提炼后的重要节点
- `sessions/{session_id}/...`
  - 被提升进账户库的完整对话与摘要

推荐账户级索引：

- `conversation_library/archive_index.jsonl`
  - 全账户归档摘要索引
- `conversation_library/scopes/{work_id}/{character_id}/archive_refs.json`
  - 当前作品与角色作用域下的轻量归档引用

## 输入输出备份规则

每轮对话建议按这个顺序做：

1. 接收到用户输入后，先分配 `turn_id`
2. 先把用户输入追加写入 `transcript.jsonl`
3. 再在 `turn_journal.jsonl` 中记录：
   - `turn_opened`
   - `user_input_committed`
4. 生成角色回复
5. 在把回复返回给前端前，先把角色输出追加写入 `transcript.jsonl`
6. 再在 `turn_journal.jsonl` 中记录：
   - `assistant_output_committed`
7. 补写：
   - `turn_summaries.jsonl`
   - `memory_updates.jsonl`
   - `session_index.json`
   - context 摘要层状态
8. 最后在 `turn_journal.jsonl` 中记录：
   - `turn_closed`

如果在第 2 步之后、第 5 步之前异常中断，系统仍然应能从：

- `transcript.jsonl`
- `turn_journal.jsonl`

恢复到“用户已发言、回复未完成”的状态。

## 启动加载与按需加载

### 启动默认可加载的摘要层

启动时应优先全量加载摘要层用户信息，例如：

- `profile.json`
- 当前激活 `persona`
- `role_binding.json`
- `long_term_profile.json`
- `relationship_core/manifest.json`
- `relationship_core/pinned_memories.jsonl`
- `contexts/{context_id}/manifest.json`
- `contexts/{context_id}/relationship_state.json`
- `contexts/{context_id}/shared_memory.jsonl`
- `contexts/{context_id}/session_index.json`
- 当前 context 下最近 session 的 `turn_summaries.jsonl`
- `conversation_library/manifest.json`
- 当前 work/character 作用域下的 `archive_refs.json`

### 按需检索的细节层

完整对话历史与更深层日志应通过索引按需打开：

- `transcript.jsonl`
- 更旧的 `turn_summaries.jsonl`
- `memory_updates.jsonl`
- `conversation_library/archive_index.jsonl`
- `conversation_library/archives/{archive_id}/...`

默认不要在启动阶段加载：

- 全量 `transcript.jsonl`
- 全账户历史归档正文
- 所有旧 session 的全部细节

## 并入账户时的推荐动作

当用户明确把当前 context 并入账户长期信息时，建议同时执行：

1. 更新 `long_term_profile.json`
2. 更新 `relationship_core`
3. 提升必要的 `pinned_memories`
4. 生成一个新的 `archive_id`
5. 把当前 context 的完整对话记录归档到 `conversation_library/archives/{archive_id}/`
6. 更新：
   - `conversation_library/archive_index.jsonl`
   - 当前 scope 的 `archive_refs.json`
7. 把原 context 标记为：
   - `merged`
   - 或 `merged_archived`
8. 在原 context 中记录：
   - `archive_ref`
   - 被归档的 `session_id`

推荐默认采用“归档后保留轻量 stub”的方式，而不是默默删除所有原上下文痕迹。

## 结构模板

`users/_template/` 下提供了完整的用户包目录结构模板，包含各级
manifest 和状态文件的占位格式。

新建用户包时，可以参考该模板的目录层级和字段结构。模板中的
`{user_id}`、`{work_id}`、`{character_id}`、`{context_id}`、
`{session_id}`、`{stage_id}` 等占位符应在实际创建时替换为真实值。

## 重要边界

- 由原文支撑的基础世界与角色数据应保留在 `works/{work_id}/`
- 所有用户专属变化、记忆、事件和对话历史都应保留在 `users/{user_id}/`
- 当中文作品使用中文 `work_id` 时，`users/{user_id}/works/{work_id}/` 这一层镜像路径也应使用同样的中文作品 id
- 对中文作品，这里的 `{character_id}` 路径段应跟随 `works/{work_id}/characters/{character_id}/` 中的基础角色 id，角色 id 可以是中文
- 这也意味着 `users/{user_id}/works/{work_id}/characters/{character_id}/` 这样的用户侧镜像目录，在基础角色 id 为中文时，也应使用同样的中文路径段
- 当用户选择角色时，应先加载 `works/{work_id}/characters/{character_id}/` 下的基础角色包，再叠加用户侧状态
- `role_binding.json` 应承接当前目标角色、当前用户侧身份模式，以及任何 canon-backed 角色槽位对应的 stage 选择
- 运行时对话中，`sessions/` 与 `contexts/` 下的轻量状态更新应持续进行，而不是等用户手动再触发一次写回
- 只有明确保留、提升或合并的内容，才应进入 `relationship_core/` 或 `pinned_memories.jsonl`
- `contexts/{context_id}/` 应支持 `ephemeral / persistent / merged / merged_archived` 等生命周期
- 当用户明确要求，或当前 merge policy 允许且证据足够时，context 中的内容可以被部分或整体提升进用户长期状态
- `relationship_core`、`contexts/{context_id}`、`sessions/{session_id}`、`archives/{archive_id}` 等持久化清单文件也应在文件内容中显式带上 `work_id`，不要只依赖路径推断作品作用域
- `users/` 下的真实用户数据默认只作本地状态，不进入 git
- 仓库中默认只保留 `users/README.md` 作为结构说明，其余用户包应由 `.gitignore` 排除
