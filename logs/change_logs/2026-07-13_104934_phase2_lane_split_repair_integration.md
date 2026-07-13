# phase2_lane_split_repair_integration

- **Started**: 2026-07-13 10:49:34 EDT
- **Branch**: main
- **Type**: GO
- **Status**: PRE

## Background / Trigger

T-PHASE2-REPAIR-AGENT（2026-05-11 从决策 #54 拆出）启动。触发链：

1. 2026-07-13 /plan 两轮讨论确认：phase 2 baseline production 当前形态 =
   裸单次 LLM 组合 call + jsonschema gate + length-tolerance gate 终点
   硬失败（`orchestrator.run_baseline_production`），不经 repair lifecycle；
   全仓 repair 接入点只有 phase 3。
2. 关键发现：phase 2 的 4 件产物互相之间**没有产出依赖**（共同依赖
   phase 1 三件 + chunk summaries 不可变输入，见 `build_baseline_prompt`
   read list），可像 phase 1 一样拆 lane 并行；拆 lane 后 per-file repair
   的 T3 语义自然变成"只重跑自己 lane"，原设计障碍消失。
3. 4 个待决策项 2026-07-13 全部收敛（见 todo 条目"已收敛决策"），
   In Progress 单槽已空，用户 /go 启动。

## Conclusion and decisions

方案定稿（docs/todo_list.md T-PHASE2-REPAIR-AGENT 条目为单源，此处摘要）：

- **拆 2+2N lane**：lane A = foundation `major_factions[].key_figures`
  替换（**先行**，避免对 foundation.json 同文件读写并发）；lane B =
  fixed_relationships；每目标角色 2 lane——identity lane（identity.json
  + manifest.json）+ target_baseline lane（target_baseline.json）。
  lane B 与全部 per-char lanes 并行。
- 每 lane 独立 prompt + 独立 schema gate；per-lane 输入按需裁剪
  （照搬 phase 1 projector 思路：read list 只列该 lane 需要的文件）。
- **repair 缩水版接入**：per-file lifecycle 只开 T0/T1 + 便宜程序
  checker（character_id 合法性 / target keys 集合，纯集合运算）；
  L3 语义 checker / T2 source_patch / triage 不开（无失败样本 +
  phase 2 输入契约是摘要而非原文，T2 语义不适用）；T3 = 重跑自己 lane
  （经 file_regen 回调路由，参照决策 #55 sub_lane_regen 模式）。
- **不做 merge 点跨产物 checker**：baseline_production.md 模板确认
  fixed_relationships ↔ target_baseline 分叉合法（无跨产物约束）。
- `run_repair` 的 `source_context=None`（本就 Optional），不改
  `protocol.py`。
- LLM 类 checker（target_baseline 准入判定）等真实失败样本再立项。

## Planned action list

- file: `extraction/persona_extraction/prompts/baseline_key_figures.md`（新增）→ lane A prompt：key_figures raw→character_id 替换（拆自 baseline_production.md 产出 1）
- file: `extraction/persona_extraction/prompts/baseline_fixed_relationships.md`（新增）→ lane B prompt（拆自产出 2）
- file: `extraction/persona_extraction/prompts/baseline_identity.md`（新增）→ per-char identity lane prompt：identity.json + manifest.json（拆自产出 3）
- file: `extraction/persona_extraction/prompts/baseline_target_baseline.md`（新增）→ per-char target_baseline lane prompt（拆自产出 4，含准入门槛全文）
- file: `extraction/persona_extraction/prompts/baseline_production.md`（删除）→ 被 4 件 lane prompt 取代
- file: `extraction/persona_extraction/prompt_builder.py` → 删 `build_baseline_prompt`，加 `build_key_figures_prompt` / `build_fixed_relationships_prompt` / `build_identity_prompt` / `build_target_baseline_prompt` 四入口，read list 按 lane 裁剪
- file: `extraction/repair/checkers/phase2_baseline_refs.py`（新增）→ 程序 checker：`foundation_factions_legal` + `fixed_relationships_legal` + `target_baseline_keys_set`（hint 驱动，经 `_repair_hints` 注入合法 id 集）
- file: `extraction/persona_extraction/orchestrator.py` `run_baseline_production` → 重写为 fan-out：lane A 先行 → lane B + per-char 2N lanes 并行（ThreadPoolExecutor）；每 lane 产物过 per-file repair（T0/T1，`source_context=None`）；`validate_baseline` 终点 gate 保留
- file: `extraction/repair/coordinator.py` / `extraction/repair/fixers/file_regen.py` → T3 对 phase 2 产物路由 lane 重跑回调（`lane_regen` kwarg，参照 sub_lane_regen 模式）
- file: `extraction/config.toml` + `extraction/persona_extraction/core/config.py` → `[phase2]` 节：lane_concurrency + repair 开关
- file: `ai_context/decisions.md` + `docs/decisions.md` → #25（repair 接入点扩 phase 2）/ #48（tolerance gate 接入点）就地更新 + 本轮新决策 append
- file: `ai_context/architecture.md` + `docs/architecture/extraction_workflow.md` + `docs/requirements.md` → phase 2 描述改 2+2N lane + repair
- file: `extraction/README.md` → prompts 树 + phase 2 段同步
- file: `docs/todo_list.md` + `docs/todo_list_archived.md` → 条目完成归档 + Index 刷新

## Validation criteria

- [ ] `python -c` import 全过：prompt_builder / orchestrator / repair.checkers.phase2_baseline_refs / config
- [ ] smoke：4 个 build_*_prompt 入口渲染成功且 read list 精确（每 lane 只含该 lane 声明的输入文件；identity lane 不含 target_baseline schema，反之亦然）
- [ ] smoke：phase2 checker 3 条规则双向（合法 pass + 越界 fail）各至少 1 case
- [ ] smoke：`run_baseline_production` fan-out 结构 grep（lane A 先行、ThreadPoolExecutor、source_context=None、validate_baseline 保留）
- [ ] jsonschema metaschema：schemas 未改动（本轮零 schema 变更），跳过或抽查 1 件确认无意外 diff
- [ ] grep 残留 = 0：`build_baseline_prompt` / `baseline_production.md` 旧引用全仓（除 logs/ 与归档）清零
- [ ] `extraction/config.toml` 新增键 `load_config()` round-trip 读取成功

## Execution deviations

1. **顺手修 pre-existing 断链 import**：`orchestrator.py:1412`
   `_collect_stage_files` 内 `from .schema_loader import load_schema` ——
   T-EXTRACTION-PKG-RESTRUCTURE 把模块迁到 `core/` 后此处漏改，phase 3
   repair 下次运行必 ImportError。一行改为 `.core.schema_loader`。
2. **`fixed_relationships` parties 检查降级为 warning**：schema 契约
   （`parties` = "关系涉及的角色名"）允许非 candidate 的 raw 角色名，
   hard error 会对合法内容误报。checker 规则
   `fixed_relationships_party_unmatched` 定为 severity=warning
   （不阻塞，报告提示 runtime 绑定受限）；relationship_id 重复仍为 error。
3. **checker 规则超出计划清单的细化**：`target_baseline_keys_set` 拆为
   character_id 一致 / target ∈ 合法集 / 重复 / 自引用 4 条规则；
   `foundation_factions_legal` 落地为 势力集合稳定 / 条目溯源（合法 id
   ∪ pre-lane raw 名）/ 去重 3 条——"匹配不上保留 raw 名"合法，纯
   "∈ candidates" 检查会误报，故对照 pre-lane 状态做溯源检查。
4. `coordinator.validate_only` 一并加 `extra_checkers` kwarg（与 `run`
   对称，供 smoke / 未来独立校验用）——计划外微增。
5. **FileRegenFixer llm_call=None 早退守卫修正**（smoke 抓出）：原
   `fix()` 在 `llm_call is None` 时直接返回，`sub_lane_regen` /
   `lane_regen` 回调永远不会被调用。改为仅当"无 LLM 且无任何回调"才
   早退；默认 regen 路径内单独判 `llm_call is None` 跳过。
6. **schema description 文本同步**（PRE 写"零 schema 变更"，此处指结构
   零变更）：`chapter_summary_chunk.schema.json` + `foundation.schema.json`
   3 处 description 提到"build_baseline_prompt 单次 LLM call"，随 call
   拓扑改为 lane A 语义；metaschema 验证通过，字段 / bound 零改动。
7. **Step 5 review 修复（code shard 1 error + 3 warn + 2 nit）**：
   (a) error——resume skip 判据只查 schema，repair FAIL 留盘的"schema
   合法但引用非法"文件会被 `--resume` 跳过直通 phase 3；`_outputs_valid`
   补跑本 lane 程序 checker（skip 判据 ≥ lane 通过判据）。
   (b) warn——`RepairFileEntry` 的 schema 加载不再裸抛（`_safe_schema`
   降级 `None`，对齐 phase 3 姿态）+ lane 池补泛 `Exception` 兜底合成
   lane_failed（对齐 phase 3 repair 池）。
   (c) warn——`_lane_regen` 成功判据从恒真的 exists() 改为重跑后全输出
   JSON re-parse + `regen_state["ok"]` 记录（双文件 lane 第二次回调返回
   首次重跑的真实 verdict）。
   (d) warn——内置 `StructuralChecker` 顶层 `relationships` 检查按文件名
   跳过 `fixed_relationships.json`（entry 形状不同，纯误报面）。
   (e) nit——phase2 checker `key_figures` 两条规则 json_path 带条目下标
   （fingerprint 去碰撞）；`output_missing_max_retry` 负值 clamp 到 0；
   `PHASE2_LANES` 改名 `PHASE2_PROJECTED_LANES`（不含 lane A，防误枚举）。
8. **Step 5 review 修复（surface shard 4 warn + 5 nit，全部就地修）**：
   `docs/architecture/system_overview.md` 阶段 2 bullet 补 lane fan-out；
   `docs/requirements.md` 第一张 ASCII 图同步 2+2N（两图口径统一）+
   §世界层 baseline 措辞改 lane A + §11.4.8 表头与 Phase 0 行修正
   （pre-existing 矛盾：Phase 0 走 #40 原生 JSON 修复阶梯，不经 repair
   framework）；`docs/decisions.md` #27l 指针改指 `baseline_key_figures.md`
   + #58 "T-PHASE2-REPAIR-AGENT 跟踪"补"已由 #59 落地"回指；
   `schema_reference.md` fixed_relationships / identity 条目补「生成时机」
   行；`extraction/validation/README.md` 终点校验口径放宽为全清单；
   `chapter_summary_chunk.schema.json` core_rules description 清除历史
   叙事（pre-existing 违反"只描述当前设计"）。
9. **勘误（/post-check M4，2026-07-13 补记）**：上条 #8 与 commit
   `577722f` message 所称「#27l 指针改指 baseline_key_figures.md」编号
   有误——实际被改的指针行位于当时归档中**第一条 "27m."**（chunk 级
   二级字段）条目内；#27l（title 派生）与该改动无关。误因是归档彼时
   存在重复编号 "27m." ×2（已由后续 fix 轮改号：stage_plan 条目 →
   "27n."，见 2026-07-13_152847_fix_from_postcheck_phase2_lane_split.md）。
   commit message 不可改，勘误以本条为准。

<!-- POST phase fills in -->

## Landed changes

Phase 2 baseline 由单次组合 LLM call 重构为 2+2N lane fan-out（lane A
key_figures 先行串行 + fixed_relationships / per-char identity /
target_baseline lanes 并行，per-lane 输入投影裁剪）+ per-lane repair
缩水版接入（T0/T1 + schema/程序 checker，T3 = lane_regen 重跑本 lane，
source_context=None），repair 框架获通用 extra_checkers / lane_regen
hook，`[phase2]` config 节新增，决策 #59 落档 + #25/#48/#54 就地
supersede，docs / ai_context / README / schema description 全链同步，
todo T-PHASE2-REPAIR-AGENT 归档。文件级明细即本 commit diff。

## Diff from plan

- 新增（计划外）：`FileRegenFixer` llm_call=None 早退守卫修正、
  `orchestrator.py:1412` restructure 遗留断链 import 修复、
  `StructuralChecker` 对 fixed_relationships.json 的误报豁免、
  resume skip 判据补程序 checker（review error 修复）、lane 池泛异常
  兜底、`_lane_regen` 成功判据收紧、`validate_only` extra_checkers、
  schema description 文本同步、`PHASE2_PROJECTED_LANES` 命名、
  docs 面 9 处 review 补漏（详见 Execution deviations #5-#8）。
- 删减（对计划）：`extraction/repair/coordinator.py` 无需扩 fixer 适配
  （通用 hook 已覆盖）；`fixed_relationships_legal` checker 降级
  warning（schema 契约允许 raw 角色名，hard error 会误报）。
- 其余按 PRE Planned action list 逐项落地，无遗漏。

## Validation results

- [x] import 全过（prompt_builder / orchestrator / repair.checkers.phase2_baseline_refs / config）+ CLI `--help` — smoke 输出 PASS
- [x] 4 个 build_*_prompt 渲染成功且 read list 精确隔离 — smoke 8 项断言全过（含占位符双向核对，review agent 机械脚本二次验证双射）
- [x] phase2 checker 3 条规则双向 — smoke 10 case 全过（合法 pass + 8 类越界 fail）
- [x] `run_baseline_production` fan-out 结构 grep — 7 项 token + lane A 先行于池 全过
- [x] jsonschema metaschema — 2 件被改 description 的 schema check_schema 通过；字段 / bound 零改动（git diff 确认）
- [x] grep 残留 = 0 — `build_baseline_prompt` / `baseline_production.md` 全仓（除 logs/ 与 decisions/todo 归档历史叙事）清零；"单次 call / 不接 repair"类断言归档外为零（surface agent 复核）
- [x] `[phase2]` config round-trip — load_config 实测 (5, 1, True)
- [x] 既有回归 smoke 7/7（l3_gate / recovery_sweep / stage_plan_min8 / 4_lane_merge / post_processing / memory_digest / cli_resume）+ review 修复后重跑 l3_gate / stage_plan / 全量 phase2 smoke 仍全过

## Completed

- **Status**: DONE
- **Finished**: 2026-07-13 12:28:52 EDT

<!-- /post-check writes -->

## Review conclusion (full report in conversation)

### Track 1 — requirement fulfillment
- Fulfillment rate: 14/14 plan items + 7/7 validations（sub-agent 复跑抽验通过）
- Missed updates: 0 items (see conversation)

### Track 2 — impact spread
- Findings: High=0 / Medium=4 / Low=6
- Open Questions: 1 items (see conversation)

## Review state
- **Reviewed**: 2026-07-13 13:44:21 EDT
- **Status**: REVIEWED-PARTIAL
  - track 1 全落地；track 2 有 Medium（lane A 溯源基线 resume 洗白窗口 /
    lane_regen 兄弟文件缓存陈旧 / decisions 归档 pre-existing "27m." 重复
    编号 + 本轮 log/commit 将改动点误引为 "#27l"），无 High
- **Conversation ref**: /post-check output in this session
