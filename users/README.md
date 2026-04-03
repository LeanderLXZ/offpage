# 用户包

这个顶层目录用于存放所有用户侧状态。

真实用户数据默认只作本地状态，不进入 git。

## 核心约束

一个 `user_id` 对应一个锁定的用户包。

这个锁定包在生成后固定承载：

- 一个 `work_id`
- 一个目标 `character_id`
- 一个当前用户侧身份 / counterpart 绑定

如果同一个人要切换到另一部作品、另一名目标角色，或另一套用户侧身份，
应新建一个新的 `user_id`，或走显式迁移流程；不要在同一个
`users/{user_id}/` 下面再挂多套 `works/{work_id}/characters/{character_id}/`
子树。

## 推荐结构

```text
users/
  {user_id}/
    profile.json
    role_binding.json
    long_term_profile.json
    conversation_library/
      manifest.json
      archive_refs.json
      archive_index.jsonl
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

### 1. 账户根层

- `profile.json`
  - 全局用户画像
- `role_binding.json`
  - 当前锁定绑定
  - 里面显式保存 `work_id`、目标 `character_id`、`stage_id`、
    counterpart mode、setup lock 等

### 2. 长期关系层

- `long_term_profile.json`
  - 当前这套锁定绑定下的长期自我画像变化
- `relationship_core/`
  - 该用户与当前目标角色之间的长期关系核心

### 3. 运行时分支层

- `contexts/{context_id}/`
  - 当前锁定绑定下的 branch context
- `sessions/{session_id}/`
  - 当前 context 下的一次具体会话

### 4. 账户归档层

- `conversation_library/`
  - 当前锁定绑定下的账户级长期对话归档库

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

当用户选择把某个 context 并入长期信息时，完整对话记录应进入：

- `conversation_library/archives/{archive_id}/`

推荐归档内容：

- `manifest.json`
  - 归档来源、`work_id`、`character_id`、`context_id`、包含的
    `session_id`、合并时间、`stage_id`、merge reason
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
- `conversation_library/archive_refs.json`
  - 当前锁定绑定下的轻量归档引用

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
- `conversation_library/archive_refs.json`

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
5. 把当前 context 的完整对话记录归档到
   `conversation_library/archives/{archive_id}/`
6. 更新：
   - `conversation_library/archive_index.jsonl`
   - `conversation_library/archive_refs.json`
7. 把原 context 标记为：
   - `merged`
   - 或 `merged_archived`
8. 在原 context 中记录：
   - `archive_ref`
   - 被归档的 `session_id`

推荐默认采用“归档后保留轻量 stub”的方式，而不是默默删除所有原上下文痕迹。

## 结构模板

`users/_template/` 提供的是单绑定用户包模板。

模板里保留的是核心清单文件与最小目录骨架；运行期 append-only 文件和
归档正文文件可以在真正创建 context、session、archive 时再按需生成。

新建用户包时，把模板中的 `{user_id}`、`{work_id}`、`{character_id}`、
`{context_id}`、`{session_id}`、`{stage_id}` 等占位符替换成真实值即可。

## 重要边界

- 由原文支撑的基础世界与角色数据应保留在 `works/{work_id}/`
- 所有用户专属变化、记忆、事件和对话历史都应保留在 `users/{user_id}/`
- 当前 user package 只承载一套锁定绑定，不再通过目录继续分叉
  `works/{work_id}/characters/{character_id}/`
- `work_id`、`character_id`、`stage_id` 等作用域信息应显式写在
  `role_binding.json`、`long_term_profile.json`、`relationship_core`、
  `contexts/{context_id}`、`sessions/{session_id}`、`archives/{archive_id}`
  的文件内容里，不要只依赖路径推断
- 当用户选择角色时，应先加载 `works/{work_id}/characters/{character_id}/`
  下的基础角色包，再叠加 `users/{user_id}/` 下的用户侧状态
- `role_binding.json` 应承接当前目标角色、当前用户侧身份模式，以及任何
  canon-backed 角色槽位对应的 stage 选择
- 运行时对话中，`sessions/` 与 `contexts/` 下的轻量状态更新应持续进行，
  而不是等用户手动再触发一次写回
- 只有明确保留、提升或合并的内容，才应进入 `relationship_core/` 或
  `pinned_memories.jsonl`
- `contexts/{context_id}/` 应支持 `ephemeral / persistent / merged /
  merged_archived` 等生命周期
- 当用户明确要求，或当前 merge policy 允许且证据足够时，context 中的
  内容可以被部分或整体提升进用户长期状态
- 对中文作品，文件内容中的 `work_id`、`character_id`、`stage_id` 可以直接
  使用中文，不需要为了用户包路径再额外做一层 pinyin 镜像
- `users/` 下的真实用户数据默认只作本地状态，不进入 git
- 仓库中默认只保留 `users/README.md` 与 `users/_template/`，其余真实用户包
  应由 `.gitignore` 排除
