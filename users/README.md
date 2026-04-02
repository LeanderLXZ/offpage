# 用户包

这个顶层目录用于存放所有用户侧状态。

推荐结构：

```text
users/
  {user_id}/
      profile.json
      personas/
        {persona_id}.json
      works/
        {work_id}/
          manifest.json
          characters/
            {character_id}/
              role_binding.json
              relationship_core/
                manifest.json
                pinned_memories.jsonl
              contexts/
                {context_id}/
                  manifest.json
                  relationship_state.json
                  shared_memory.jsonl
                  sessions/
                    {session_id}/
                      manifest.json
                      transcript.jsonl
                      turn_summaries.jsonl
                      memory_updates.jsonl
```

重要边界：

- 由原文支撑的基础世界与角色数据应保留在 `works/{work_id}/`
- 所有用户专属变化、记忆、事件和对话历史都应保留在 `users/{user_id}/`
- 当中文作品使用中文 `work_id` 时，`users/{user_id}/works/{work_id}/` 这一层镜像路径也应使用同样的中文作品 id
- 对中文作品，这里的 `{character_id}` 路径段应跟随 `works/{work_id}/characters/{character_id}/` 中的基础角色 id，角色 id 可以是中文
- 这也意味着 `users/{user_id}/works/{work_id}/characters/{character_id}/` 这样的用户侧镜像目录，在基础角色 id 为中文时，也应使用同样的中文路径段
- 当用户选择角色时，应先加载 `works/{work_id}/characters/{character_id}/` 下的基础角色包，再叠加用户侧状态
- `role_binding.json` 应承接当前目标角色、当前用户侧身份模式，以及任何 canon-backed 角色槽位对应的 stage 选择
- 运行时对话中，`sessions/` 与 `contexts/` 下的轻量状态更新应持续进行，而不是等用户手动再触发一次写回
- 只有明确保留、提升或合并的内容，才应进入 `relationship_core/` 或 `pinned_memories.jsonl`
- `contexts/{context_id}/` 应支持 `ephemeral / persistent / merged` 等生命周期
- 当用户明确要求，或当前 merge policy 允许且证据足够时，context 中的内容可以被部分或整体提升进用户长期状态
- `relationship_core`、`contexts/{context_id}`、`sessions/{session_id}` 等持久化清单文件也应在文件内容中显式带上 `work_id`，不要只依赖路径推断作品作用域
