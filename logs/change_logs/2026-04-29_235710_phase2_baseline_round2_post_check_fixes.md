# phase2_baseline_round2_post_check_fixes

- **Started**: 2026-04-29 23:57:10 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

`/post-check` 第 2 轮（含修补轮）复查 T-PHASE2-TARGET-BASELINE 完整工作流，
返回 REVIEWED-FAIL，4 处发现：

- [H] `docs/architecture/system_overview.md:311-314` 同节内三处自相矛盾
  （旧 4 件套表达 vs line 321 已更新表达）
- [M] `automation/prompt_templates/character_snapshot_extraction.md`
  全文 0 处提及 target_baseline / D4 keys ⊆ baseline 约束
- [M] D4 enforcement 三层皆空（consistency_checker / repair_agent /
  phase 3 prompt），代码侧零 TODO 标注
- [M] `simulation/contracts/baseline_merge.md` 4 处悬挂引用（文件不存在）

本轮 /go 闭合这些发现。

## 结论与决策

按"不过度工程"原则，最小动作：

- system_overview.md:311 + 313-314 改写：删除 4 件套字段名（voice_rules /
  behavior_rules / boundaries soft / failure_modes / hard_boundaries 的
  baseline 措辞），统一为 identity + target_baseline 两件套
- character_snapshot_extraction.md：在 target_voice_map / target_behavior_map
  / relationships 描述附近加 1 段 D4 brief reference（指向 decisions.md
  #13），不动结构、不加 schema 校验
- consistency_checker.py 模块 docstring 加一行 TODO 标注 D4 ⊆ baseline 检查
  归属 T-CHAR-SNAPSHOT-SUB-LANES，避免被遗忘
- baseline_merge.md 4 处悬挂引用：删除引用（文件不存在，引用语义已被新
  方案覆盖：自包含 stage_snapshot 不需 baseline merge）

不动：
- validator.py 模块 docstring stale（属 BASELINE-DEPRECATE 范围，不扩）
- character_manifest.schema.json target_baseline_path 是否 required
  （与 identity / canon_root 等同 schema 路径字段一致 optional，是项目
  既有约定）
- 不引入新代码 / 不改 schema / 不动 D4 enforcement 实际实现（属
  T-CHAR-SNAPSHOT-SUB-LANES 范围）

## 计划动作清单

- file: `docs/architecture/system_overview.md` line 311 → 「角色不变层
  （identity + failure_modes + hard_boundaries）」改为「角色不变层
  （identity + target_baseline）」+ 删除 line 313-314 的 4 件套残余注释
- file: `automation/prompt_templates/character_snapshot_extraction.md`
  → 加 1 段 D4 brief（target_voice_map / target_behavior_map /
  relationships 的 keys 必须 ⊆ target_baseline.targets[].target_character_id），
  指向 decisions.md #13；约 5-10 行
- file: `automation/persona_extraction/consistency_checker.py` 模块
  docstring → 加一行 `TODO(T-CHAR-SNAPSHOT-SUB-LANES): 加 phase 3
  stage_snapshot.{target_voice_map,target_behavior_map,relationships}
  keys ⊆ target_baseline.targets[].target_character_id 检查（D4 硬约束，
  decisions.md #13）`
- file: `ai_context/decisions.md:129` (#24) → 删除 `simulation/contracts/baseline_merge.md`
  引用（其它三项保留：memory_digest.jsonl / world_event_digest.jsonl /
  stage_catalog.json 仍有效）
- file: `ai_context/architecture.md:94` → 删除 `Contract → simulation/contracts/baseline_merge.md.` 整行
- file: `ai_context/architecture.md:160` → 删除 `Extraction prompts do
  NOT read baseline_merge.md, ...` 的 baseline_merge.md 引用（其它项保留）
- file: `docs/requirements.md:1385` → 删除「`simulation/contracts/baseline_merge.md`
  — 自包含快照的语义契约已内嵌在 extraction prompt 中」整条

## 验证标准

- [ ] grep `voice_rules\|behavior_rules\|boundaries\.json\|failure_modes\.json\|hard_boundaries`
  在 `docs/architecture/system_overview.md` → 0 命中（确认 stale 4 件套
  名清出该文件；其它文件如 ai_context/decisions.md #11d / current_status
  / todo_list / migrate_baseline_to_stage_snapshot.py 是合法历史描述，
  不变）
- [ ] grep `baseline_merge` 在 ai_context/ docs/ → 0 命中
- [ ] grep `target_baseline` 在 character_snapshot_extraction.md → ≥ 1 命中
- [ ] grep `T-CHAR-SNAPSHOT-SUB-LANES` 在 consistency_checker.py → ≥ 1 命中
- [ ] python -c "from automation.persona_extraction import consistency_checker"
  仍能 import
- [ ] git diff 仅触及计划清单内的 7 个文件，无其它 dirty

## 执行偏差

无（按计划清单 1:1 执行）。

<!-- POST 阶段填写 -->

## 已落地变更

修改（6 文件）：
- `docs/architecture/system_overview.md` line 311 — 运行时加载公式
  「角色不变层（identity + failure_modes + hard_boundaries）」改为
  「角色不变层（identity + target_baseline）」；line 313 注释删除
  「voice_rules、behavior_rules、boundaries 的 soft 部分」措辞，改为
  「voice / behavior / boundary / failure_modes 全部内联进 stage_snapshot，
  没有独立 baseline 文件」
- `automation/prompt_templates/character_snapshot_extraction.md` —
  「核心字段全量记录」段尾、「标识命名」段前插入 1 段「D4 硬约束
  （target keys ⊆ baseline）」brief（约 6 行），明确三方 keys 必须
  ⊆ target_baseline.targets[].target_character_id + 越界处理走
  stage_delta + 指向 decisions.md #13
- `automation/persona_extraction/consistency_checker.py` 模块 docstring
  尾部加 6 行 `TODO(T-CHAR-SNAPSHOT-SUB-LANES)` 块，标明 D4 ⊆ 检查归属、
  当前 enforcement 仅靠 prompt
- `ai_context/architecture.md` line 94 — 删除 `Contract → simulation/contracts/baseline_merge.md.` 整行
- `ai_context/architecture.md` line 158（原 160）— 「Extraction prompts
  do NOT read `baseline_merge.md`, digests, or catalog」改为「do NOT read
  digests or catalog」（保留 char extraction does NOT read world snapshot
  半句）
- `ai_context/decisions.md` #24 (line 129) — 删除 `simulation/contracts/baseline_merge.md`
  引用项，保留其它三项（memory_digest / world_event_digest / stage_catalog）
- `docs/requirements.md` 「显式排除」段 (line 1384–1387) — 删除
  baseline_merge.md 条目；该段头部加注「自包含快照的语义契约已内嵌在
  extraction prompt 中，无独立 baseline merge 文件」吸收原句义

新增（1 文件）：
- `logs/change_logs/2026-04-29_235710_phase2_baseline_round2_post_check_fixes.md`
  （本文件）

## 与计划的差异

无。计划 7 项动作全部执行，零偏差。

## 验证结果

- [x] grep `voice_rules|behavior_rules|boundaries\.json|failure_modes\.json|hard_boundaries`
  在 `docs/architecture/system_overview.md` → 0 命中
- [x] grep `baseline_merge` 在 ai_context/ docs/ → 0 命中
- [x] grep `target_baseline` 在 character_snapshot_extraction.md → 1 命中
  （插入的 D4 brief 段）
- [x] grep `T-CHAR-SNAPSHOT-SUB-LANES` 在 consistency_checker.py → 1 命中
- [x] python -c "from automation.persona_extraction import consistency_checker"
  → import OK
- [x] git diff 触及 6 doc/code 文件 + 1 新 log，无其它 dirty

## Completed

- **Status**: DONE
- **Finished**: 2026-04-29 23:59:32 EDT
