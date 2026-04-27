# 模式定义

这个目录用于存放持久化文件与运行时请求的第一版 JSON Schema。

按语义分层组织为子目录：

| 子目录 | 作用 | 典型成员 |
|--------|------|---------|
| `analysis/` | Phase 0 / Phase 1 / Phase 4 LLM 产物（不入运行时；Phase 1 三件套入 git） | `chapter_summary_chunk`、`scene_split`、`world_overview`、`stage_plan`、`candidate_characters` |
| `work/` | 作品级入库、目录、per-work 加载配置 | `work_manifest`、`works_manifest`、`book_metadata`、`chapter_index`、`load_profiles` |
| `world/` | 世界基础设定、阶段快照、事件、固定关系、目录页 | `world_manifest`、`foundation`、`world_stage_snapshot`、`world_event_digest_entry`、`fixed_relationships`、`world_stage_catalog` |
| `character/` | 角色 baseline + 阶段目录 + 阶段快照 + 记忆 | `identity`、`character_manifest`、`voice_rules`、`behavior_rules`、`boundaries`、`failure_modes`、`stage_catalog`、`stage_snapshot`、`memory_timeline_entry`、`memory_digest_entry` |
| `user/` | 用户根画像、绑定、长期档案、关系核心、钉选记忆条目 | `user_profile`、`role_binding`、`long_term_profile`、`relationship_core`、`pinned_memory_entry` |
| `runtime/` | Context / Session / 请求载荷 / 场景归档条目 | `context_manifest`、`context_character_state`、`session_manifest`、`runtime_session_request`、`scene_archive_entry` |
| `shared/` | 跨域共享（extraction_notes 等） | `source_note` |

各 schema 的 `$id` 统一为 `offpage/<subdir>/<name>.schema.json`；功能说明与字段索引见
[../docs/architecture/schema_reference.md](../docs/architecture/schema_reference.md)。

这些 schema 当前采取保守设计，优先固定结构，再为后续更丰富的抽取细节预留空间。

命名规则提醒：

- `work_id` 是作品包命名空间键
- 对中文作品，`work_id` 本身可以直接使用原始中文书名或中文作品标识，`sources/works/` 与 `works/` 下的根目录应与其保持一致
- 对中文作品，`character_id` 等作品级基础标识也可以直接使用中文
- `stage_id` 始终使用紧凑英文代号 `S###`（三位数字零填充，如 `S001`），与 `M-S###-##` / `E-S###-##` / `SC-S###-##` / `SN-S###-##` ID 家族共享 stage 段；人类可读的阶段短标题由 `stage_title` 承载
- `user_id`、`context_id`、`session_id` 等用户侧 id 可以继续采用各自的运行时约定
- 对运行时请求以及 `users/` 下的持久化清单，`work_id` 也应在 JSON 文件内容中显式出现，不要只依赖目录路径表达作品作用域
- 全局 `users/{user_id}/profile.json` 应保持为用户根画像；作品或关系特有的长期变化应进入 work-scoped 的长期画像或关系核心，而不是直接污染根画像
