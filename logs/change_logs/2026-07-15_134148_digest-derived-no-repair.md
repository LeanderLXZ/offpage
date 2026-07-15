# digest-derived-no-repair

- **Started**: 2026-07-15 13:41:48 EDT
- **Branch**: main（worktree ../offpage-main，隔离自 extraction/<work_id>）
- **Type**: GO
- **Status**: PRE

## Background / Trigger

extraction 运行在 S002 收尾时进入 repair，最终 `T3_EXHAUSTED` 硬 error 停机。
排查发现 `world_event_digest.jsonl` 的 3 个 S001 事件被重复 13 次，且 13 份
副本的 `involved_characters` 各不相同——证明是 **LLM 重新生成**（repair T3
`file_regen` 整文件重写），而非代码投影所致。

根因：digest 是**派生文件**（snapshot / timeline 的 1:1 代码投影），但当前
架构把它放进了 repair 集，允许 L0–L3 checker + T0–T3 fixer（含 T3 整文件
LLM 重写）改写它。这与 `phase3_5_consistency` 的 §32/§33 一致性门直接矛盾
——后者断言 `digest.summary` 必须逐字等于源。两个子系统互相打架。

设计文档本就规定 digest = 1:1 派生（`world_extraction.md` §7、
`extraction/README.md` L514-515）；repair 触碰 digest 是对项目自身设计的越界。

## Conclusion and decisions

确立 **primary / derived 二分**：repair 只作用于 primary（LLM 产出的
snapshot / timeline）；derived（`world_event_digest.jsonl` /
`memory_digest.jsonl`）永不进 repair、永不 LLM 重写，只由代码从 primary
幂等重投影，正确性由现有 `phase3_5_consistency` §32/§33 纯代码门守。

本次 /go **只做共享代码根治**（落 main）。数据清理（清 S002 污染 digest +
修Character B S002.json schema）+ `--resume` 作为后续，在 extraction 分支上、待本
修复经 `/forward` 合入后进行。

不做：不移除 `field_patch` / `protocol` 中现已 dead 的 slice-merge 基础设施
（`_merge_jsonl_slice` / `current_stage_keys` / `is_jsonl_slice`）——它们随
`_jsonl_stage_entry` 删除后变 dead 但无害，单独作为一次有界清理，避免本次
diff 扩散到带测试的 protocol 层。

## Planned action list

- file: `extraction/persona_extraction/orchestrator.py` → `_collect_stage_files`
  删除 world_event_digest / memory_digest 两个 `_jsonl_stage_entry` 块；删除
  随之 dead 的嵌套函数 `_jsonl_stage_entry` 与 `stage_pat`。digest 不再进
  repair file set。
- file: `extraction/persona_extraction/phases/post_processing.py` →
  (a) 两个生成器 `generate_memory_digest` / `generate_world_event_digest` 的
  `final` 按主键（memory_id / event_id）**全量幂等去重**（含 `kept` 前序
  stage），使重投影自愈已污染文件；
  (b) `generate_world_event_digest` 的 `involved_characters` 归一到
  canonical_name（新增可选 alias→canonical 映射，缺省回退旧行为保测试兼容），
  匹配后按 canonical 去重。
- file: `extraction/persona_extraction/phases/post_processing.py`（caller
  `run_stage_post_processing`）→ 构造 alias→canonical 映射传入生成器。

## Validation criteria

- [ ] `python -c "import extraction.persona_extraction.orchestrator, extraction.persona_extraction.phases.post_processing"` 无 error
- [ ] `grep -n "_jsonl_stage_entry\|stage_pat" orchestrator.py` 残留 = 0
- [ ] smoke：构造含前序 stage 重复条目的 digest，跑 `generate_world_event_digest`，断言重复被去重、`involved_characters` 归一到 canonical
- [ ] 既有 smoke `_smoke_post_processing_replace_slice.py` 仍通过
- [ ] `phase3_5_consistency` 相关 smoke（若有）仍通过

## Execution deviations

- 计划移除 orchestrator 内 dead 的 `_json` / `_re` 局部 import（随
  `_jsonl_stage_entry` 一并 dead）——已随手清除，属计划内清理。
- `_collect_stage_files` 的 `stage_num` 参数现已不被函数体使用（原仅用于
  `stage_pat`）；保留签名不动以免波及调用方，未做移除。
- 验证发现 `extraction/repair/tests/_smoke_triage.py` 失败
  （`expected at least one accepted note`）——经 `git stash` 隔离确认为
  **改动前 baseline 既有失败**，与本次无关，不在本次修复范围，记录待查。
- Step 5 复审发现 #61 归档误含真实角色名，按
  `## Sensitive content placeholder rules` 就地替换为占位符「某角色」。

<!-- POST phase fills in -->

## Landed changes

确立 primary / derived 二分：`world_event_digest.jsonl` /
`memory_digest.jsonl` 移出 repair 文件集，改由 post_processing 确定性幂等
重投影（按主键全量去重自愈历史重复）+ `phase3_5_consistency` §32/§33 门
守正确性；`involved_characters` 归一到 canonical_name。代码 2 文件
（orchestrator / post_processing），文档 4 文件（decisions ×2 / requirements
/ handoff）。

## Diff from plan

无实质偏离。计划内附带清理：随 `_jsonl_stage_entry` 删除一并移除 dead 的
`_json` / `_re` 局部 import。`_collect_stage_files` 的 `stage_num` 参数变
unused 但保留签名（避免波及调用方）。

## Validation results

- [x] import orchestrator + post_processing 无 error
- [x] `grep _jsonl_stage_entry|stage_pat` 残留 = 0
- [x] 新行为 smoke：前序重复 3→1 自愈 + `involved_characters` 三别名归一为 canonical + 顺序正确
- [x] 既有 `_smoke_post_processing_replace_slice` 4/4 通过
- [x] `_smoke_l3_gate` 通过；`phase3_5_consistency` import + digest 检查存在；compileall OK
- [ ] `_smoke_triage` — 既有失败（baseline 即失败），非本次引入，记录待查

## Completed

- **Status**: DONE
- **Finished**: 2026-07-15 13:56:21 EDT
