# phase2_target_baseline

- **Started**: 2026-04-29 20:54:23 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

会话内讨论 + /todo-add 落盘的 T-PHASE2-TARGET-BASELINE。当前 phase 3
char_snapshot 由 LLM 在 stage-local 视角自主决定 target_voice_map /
target_behavior_map / relationships 的 keys，三个痛点：
(1) stage-local 看不到全书关系网络，可能漏判跨章节隐性重要关系；
(2) 单 lane 模式下三方 keys 是否真对齐尚未验证；
(3) sub-lane 拆 3 lane 后三方 keys 必须 ⊆ 同一基线才能合并。

新方案：phase 2 全书视野一次性拍每角色 `target_baseline.json`（含 tier
+ relationship_type），后续 phase 3 各 stage 严格 ⊆ baseline 写 keys。
三方一致 by-construction，跟 identity / fixed_relationships 同源思路
（结构性 + 跨 stage 不变 → phase 2 一次拍，后续 stage 只读不写）。

## 结论与决策

D1（schema 形态）：per-character；字段 `target_character_id`（用
identity.id，规避化名 / 隐藏身份歧义）+ `relationship_type`（多候选清单
覆盖亲密度 × 立场两维）+ `tier`（核心 / 重要 / 次要 / 路人）+
`description`（≤100 字）；不要 `origin_stage_hint`。

D2（active 子集判定）：纯 prompt-based。三态规则在 phase 3 char_snapshot
prompt 里描述（a 未登场空缺 / b 已登场以 prev 为基线增删 / c 曾登场未
出现继承 prev），让 LLM 自行判断；不做程序判定、不做 step 0。

D3（baseline immutable）：phase 2 一次拍后 stage 只读不写；漏判走人工
编辑 + stage 重抽。

D4（硬约束）：phase 3 各 stage 写入 target keys 必须 ⊆ baseline.targets[]，
即使漏判也不允许 stage 突破——hard fail（不引入 escape hatch）。

5（全流程改造）：本 todo 仅完成 phase 2 加产出 + schema + manifest 字段
+ validate_baseline 校验。phase 3 prompt 三态规则注入 + consistency_checker
跨文件 keys ⊆ baseline 校验属于 T-CHAR-SNAPSHOT-SUB-LANES 范围，不在本
todo 范围（这是它的硬前置）。

## 计划动作清单

- file: `schemas/character/target_baseline.schema.json`（新增）→ 顶层
  字段 `schema_version` / `work_id` / `character_id` / `targets[]`，
  每条 target 含 `target_character_id` / `relationship_type` / `tier`
  / `description`（≤100 字）
- file: `schemas/character/character_manifest.schema.json` → `paths`
  对象加 `target_baseline_path` 字段（角色级，相对 canon_root）
- file: `automation/prompt_templates/baseline_production.md` → 加产出
  4：target_baseline.json；input 同现行（全书摘要 + candidate_characters
  + identity）；说明 D1 字段 + tier / relationship_type 的语义；说明
  baseline 一旦产出后续 stage 只读不写；不在 phase 3 重新生成
- file: `automation/persona_extraction/prompt_builder.py` →
  `build_baseline_prompt` 把 `character/target_baseline.schema.json`
  加入 `files_to_read` 的 schema 读列表
- file: `automation/persona_extraction/validator.py` →
  `validate_baseline()` 加 target_baseline.json 校验：必须存在 + schema
  合规 + character_id 与目录名一致；缺失 / 违规 → error
- file: `ai_context/decisions.md` → "Character Depth" 段或新增条目：
  phase 2 产 per-character target_baseline + immutable + D4 硬约束
  （phase 3 keys ⊆ baseline，违规 hard fail）
- file: `ai_context/architecture.md` § Automated Extraction Pipeline →
  Phase 2 行补充 target_baseline.json 产出
- file: `ai_context/requirements.md` § §9 / §7 → 同步 character canon
  描述（identity 不再是唯一恒定文件，target_baseline 与之并列）
- file: `docs/architecture/extraction_workflow.md` § 5 Baseline 产出
  （Phase 2）→ 加 target_baseline 描述 + immutable 约束 + 出口验证补充
- file: `docs/requirements.md` § 角色层 baseline → 加 target_baseline
  条目 + immutable 约束

## 验证标准

- [ ] target_baseline.schema.json jsonschema 校验通过（语法合法，字段
  约束符合 D1）
- [ ] character_manifest.schema.json 改动后 jsonschema 校验通过
- [ ] `python -c "from automation.persona_extraction import validator,
  prompt_builder, manifests"` import 全部通过
- [ ] `python -c` 调 `validator.validate_baseline()` 在 fixture 下能识别
  target_baseline.json 缺失 → error
- [ ] grep 残留：`docs/` `ai_context/` 不再有"identity 是唯一恒定 baseline
  文件"或等价表述（应改为"identity + target_baseline 是 character-level
  恒定文件"）
- [ ] todo_list.md 更新 T-PHASE2-TARGET-BASELINE 状态：code 完成、phase 2
  runtime 验证待跑（与 BASELINE-DEPRECATE 同形态）

## 执行偏差

- character_manifest.schema.json 字段命名：原计划"加 `target_baseline_path`
  字段"未明确放在哪一层；最终放进 `paths` 对象（与 stage_catalog_path /
  stage_snapshot_root / evidence_root 同级），符合现有 manifest 路径字段
  组织方式
- prompt 模板章节编号：原 baseline_production.md 是「产出 1 / 2 / 3
  (stage_catalog)」三段；插入 target_baseline 时新建「产出 3：角色 Target
  Baseline」并将原 stage_catalog 顺移到「产出 4」。无内容删除
- ai_context/decisions.md 改写位置：原计划"新增决策"，实际改写既有 #13
  使其涵盖 target_baseline 产出 + D4 硬约束 + immutable，避免在 Extraction
  Model 段堆叠并行决策
- 顺手修了 3 处与本次改动直接相关的 stale 引用（system_overview.md /
  data_model.md / extraction_workflow.md "identity 是唯一恒定文件" 类
  表述），改为"identity + target_baseline 都是 character-level 恒定
  文件"；这些是跨文件一致性的连带更新，未扩到 BASELINE-DEPRECATE 留下
  的 4 件套残余（4 件套残余属那个 todo 范围）

## 已落地变更

新增：
- `schemas/character/target_baseline.schema.json`（59 行）
- `logs/change_logs/2026-04-29_205423_phase2_target_baseline.md`（本文件）

修改：
- `schemas/character/character_manifest.schema.json` — `paths` 加
  `target_baseline_path`
- `automation/prompt_templates/baseline_production.md` — 新增「产出 3：
  角色 Target Baseline」+ manifest paths 段加 `target_baseline_path`
  填写指引；顶部 baseline 文件描述改为"identity + target_baseline 都是
  恒定文件"
- `automation/persona_extraction/prompt_builder.py` — `build_baseline_prompt`
  schemas 读列表加 `character/target_baseline.schema.json`
- `automation/persona_extraction/validator.py` — `validate_baseline()`
  加 target_baseline.json 校验：必须存在 + schema 合规 + character_id
  与目录名一致
- `ai_context/decisions.md` #13 — 改写为含 target_baseline 产出 + D4 硬
  约束（phase 3 keys ⊆ baseline，违规 hard fail）+ phase 3 不写 baseline
- `ai_context/decisions.md` #11d — "identity is the only character-level
  constant" 改为"identity + target_baseline 都是 character-level constants"
- `ai_context/architecture.md` § Automated Extraction Pipeline — Phase 2
  行补充 target_baseline 产出 + 硬约束
- `ai_context/requirements.md` § §7 Information Layering — immutable 层
  补 target_baseline
- `docs/architecture/extraction_workflow.md` § 5 Baseline 产出 + §
  Baseline 文件的角色 — 加 target_baseline 描述 + immutable 约束 + 出口
  验证补充
- `docs/requirements.md` § 角色层 baseline — 加 target_baseline 条目 +
  immutable 约束 + phase 2 宁可多列不可漏列原则
- `docs/architecture/system_overview.md` 启动加载段 + 角色资产包段 —
  identity 改为 identity + target_baseline
- `docs/architecture/data_model.md` 角色资产包列表 — 加 target_baseline
  条目
- `simulation/flows/startup_load.md` 第 8 步 — identity 改为 identity +
  target_baseline，加 phase 3 keys ⊆ baseline 约束注释
- `simulation/retrieval/load_strategy.md` Tier 0 — identity 改为
  identity + target_baseline，加 loader 可用 baseline 作为 target 预取
  上限的注释
- `docs/todo_list.md` — T-PHASE2-TARGET-BASELINE 从 Next 移到 In
  Progress（加开始时间 + 当前状态）；index 同步刷新（In Progress 1 → 2 /
  Next 4 → 3 / Total 不变 11）

## 与计划的差异

- 计划里没显式列 `system_overview.md` / `data_model.md` /
  `simulation/flows/startup_load.md` / `simulation/retrieval/load_strategy.md`
  的更新——Step 7 review 发现这些文件描述"identity 是 character-level
  唯一恒定文件"与本次改动直接冲突，顺手修了
- 计划里写"`automation/persona_extraction/manifests.py` 写 character_manifest
  时填 target_baseline_path"——实际 character manifest 不由 manifests.py
  写（manifests.py 只写 works manifest 和 world manifest）；character
  manifest 由 phase 2 LLM 直接产出（baseline_production.md prompt 指导）。
  所以本次只改了 prompt 指引让 LLM 填 target_baseline_path，没动
  manifests.py。这与现有 character manifest 的产出路径一致

## 验证结果

- [x] target_baseline.schema.json jsonschema 校验通过 — Draft 2020-12
  schema valid；样本 valid 通过；过长 description / 未知 relationship_type
  / 未知 tier 三种违规均按预期 reject
- [x] character_manifest.schema.json 改动后 jsonschema 校验通过 —
  Draft 2020-12 schema valid
- [x] `python -c` import `validator` / `prompt_builder` / `manifests` /
  `orchestrator` — 全部通过
- [x] `validator.validate_baseline()` 在 fixture 下识别 target_baseline.json
  缺失 → error；present + valid → 无 target_baseline error；character_id
  mismatch → error
- [x] grep 残留：`docs/` `ai_context/` `automation/` `simulation/` 中
  "唯一恒定" / "character-level 唯一" / "the only character-level constant"
  / "identity 是 Phase 2 唯一" 类描述全部消除
- [ ] phase 2 跑通至少一个 work：每个 candidate character 产出
  target_baseline.json，schema 合规 — 待 runtime（与 BASELINE-DEPRECATE
  同形态，可同批跑）
- [x] todo_list.md 更新：T-PHASE2-TARGET-BASELINE 从 Next 移到 In Progress
  + 加 开始时间 / 当前状态 字段；index 同步

## Completed

- **Status**: DONE（代码完成；runtime 验证待跑作为 In Progress 状态保留）
- **Finished**: 2026-04-29 21:06:35 EDT
