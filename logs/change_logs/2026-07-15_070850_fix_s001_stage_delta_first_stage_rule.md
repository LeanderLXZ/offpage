# fix(char_snapshot prompt): S001 首阶段 stage_delta 加确定性"两边都省略"硬规则

**时间**: 2026-07-15 07:08 EDT
**类型**: prompt 内容缺陷修复（阻断 Phase 3 首个 stage）
**分支**: main（prompt 是提取行为定义，落 main → merge 进 extraction 分支）

## 症状

Phase 3（import 修复后）首次跑到 S001，两个角色的 char_snapshot lane
**都** merge 失败，且方向相反：

- Character B：`char_decision` 写了 `stage_delta`，`char_social` 没写 → MergeError
- Character A：`char_social` 写了 `stage_delta`，`char_decision` 没写 → MergeError

报错：`'stage_delta' written by some but not all contributing sub-lanes;
either every contributing lane writes it or none do`。S001 落 ERROR，
Phase 3 无法越过首个 stage。

## 根因

决策 #55 把 char_snapshot 拆成 4 个独立 sub-lane 并行，其中 `stage_delta`
顶层键被切成两半：`char_decision` 负责 3 子键、`char_social` 负责另 3 子键。
merge 契约（`snapshot_merge._check_shared_key_coverage`，
`allow_absent_both=True`）要求该字段**要么两条 lane 都写、要么都不写**，
一半写一半不写即 MergeError。

S001 是首阶段、没有前一阶段可对比，`stage_delta`（"从上一阶段的变化"）
本应两边都省略——merge docstring 也明确写了 "the S001 case — no prev,
no delta"。但 prompt 只有面向 S002+ 的通用要求（"即使无变化也必须在
stage_delta 中说明对照了哪些维度"），**没给 S001 开确定性豁免**。两个独立
LLM 各自拿不准首阶段该不该写自己那半，做出不一致决定 → 必然触发 merge 冲突。
两角色都挂且方向相反，证实是系统性契约歧义而非偶发。

Phase 3 系首次端到端运行（4-sub-lane 拆分从未在真实 LLM 输出上跑过 S001），
故此前未暴露。

## 改动

`extraction/persona_extraction/prompts/character_snapshot_extraction.md` 三处：

1. 首阶段特殊指引块内新增 **`stage_delta` 首阶段硬规则**：`is_first_stage
   = true` 时整个 `stage_delta` 必须省略，char_decision / char_social 两个
   sub-lane 都不得写入自己那半；显式说明"两边同时留空是唯一合法形态"并点明
   merge 契约的"要么都写要么都不写"。
2. 情境维度段（原"必须在 stage_delta 中显式说明"）追加 S001 例外指针。
3. `stage_delta` 字段说明行头部标注"S002+ 适用；S001 整个省略"。

merge 代码 + docstring + schema（stage_delta 非 required）本就支持"两边都空"
（`allow_absent_both=True` → 返回 None 省略字段），无需改动；本次仅补 prompt
的确定性指令。

## 验证

- merge：`_check_shared_key_coverage("stage_delta", allow_absent_both=True)`
  两边都空 → 返回 None、字段省略、不报错。✓
- schema：`stage_snapshot.schema.json` 顶层 required 不含 `stage_delta`，
  省略合规。✓
- 运行时验证：重跑 Phase 3，观察 S001 两角色 char_snapshot merge 是否通过。
