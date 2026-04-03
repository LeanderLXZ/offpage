# Runtime Packets

## Goal

The simulation engine should assemble a few predictable packet types instead
of dumping arbitrary files into the model context.

## 1. Bootstrap Request

Purpose:

- resolve or create the scoped setup before runtime starts

Recommended fields:

- `user_id`
- `work_id`
- target `character_id`
- `stage_id`
- `user_role_mode`
- optional `user_canon_character_id`
- optional `context_id`
- `setup_locked`

## 2. Startup Packet

Purpose:

- support the first in-character reply with the minimum stable context

Recommended sections:

- `scope`
  - `user_id`
  - `work_id`
  - target `character_id`
  - `stage_id`
  - `context_id`
- `identity`
  - target baseline summary
  - selected-stage target snapshot
  - user-side role binding
  - active persona summary when used
- `world`
  - work summary
  - selected-stage world snapshot
  - selected-stage relationship snapshot
  - minimal foundation rules
- `relationship`
  - long-term relationship core summary
  - pinned-memory summary
  - current context relationship state
- `session`
  - current context summary
  - current context shared-memory summary
  - current session index summary
  - current scope archive-ref summary
  - recent session summaries
  - full transcript excluded from startup by default
- `retrieval_policy`
  - startup-required files used
  - on-demand buckets available

## 3. Retrieval Request

Purpose:

- ask for deeper context only when the turn actually needs it

Recommended fields:

- `need_type`
  - `world_fact`
  - `historical_recall`
  - `relationship_history`
  - `location_lookup`
  - `faction_lookup`
  - `event_verification`
  - `past_stage_snapshot`
  - `character_memory`
  - `user_memory`
  - `context_history`
  - `archive_history`
  - `session_transcript`
  - `raw_source_check`
- `work_id`
- `stage_id`
- optional `context_id`
- optional `session_id`
- optional `character_id`
- optional `past_stage_id`
- optional `event_id`
- optional `location_id`
- optional `faction_id`
- optional `chapter_refs`
- optional `output_mode`

## 4. Turn Packet

Purpose:

- provide the model the exact packet needed for one response

Recommended sections:

- `character_anchor` — **每轮注入**的压缩角色锚点（≤300 字），防止角色
  信息在长对话中稀释。从 stage_snapshot 提取，包含：
  - 语气签名：2-3 个关键说话特征 + 对当前对话者的语气偏移
  - 硬边界提醒：最核心的 2-3 条
  - 当前关系姿态：对对话者的态度、信任度、警惕度
  - 知识边界：角色此刻知道/不知道什么的关键边界线
  - 当前情绪状态：当前情绪 + 本次对话中因事件产生的情绪变化
- `rolling_session_state` — 每 5-8 轮更新的滚动对话状态摘要，包含：
  - 情绪轨迹：本次会话中双方的情绪变化弧线
  - 已揭露信息：本次会话中新揭露的秘密、身份、过去的事
  - 承诺与约定：双方做出的承诺、约定、威胁
  - 关系微变化：本次对话中态度、信任、亲密度的微调
  - 未解决话题：尚未回答的问题、悬而未决的冲突
- `active_identity`
- `current_world_situation`
- `current_relationship_state`
- `user_turn_intent`
- `retrieved_supporting_evidence`
- `response_constraints`
  - cognitive conflict rules (see `prompts/runtime/认知冲突处理规则.md`)
  - historical recall rules (see `prompts/runtime/历史回忆处理规则.md`)
  - dilution protection rules (see `prompts/runtime/会话稀释保护检查清单.md`)

## 5. Writeback Patch

Purpose:

- describe what should be persisted after this turn

Recommended sections:

- `backup_events`
- `session_updates`
- `context_updates`
- `relationship_change_candidates`
- `memory_promotion_candidates`
- `archive_candidates`
- `notes`

## 6. Close Packet

Purpose:

- support explicit close and optional merge

Recommended fields:

- `context_id`
- `close_reason`
- `merge_prompt_required`
- `merge_decision`
- `long_term_updates`

## Reference Style

Within runtime packets, evidence should prefer compact refs.

Examples:

- `0001`
- `0008-0010`
- `阶段1_南林初遇`
- `王枫第九世复生与姜寒汐南林重逢`

Do not repeat full chapter paths inside every packet unless the path itself is
the meaningful distinction.
