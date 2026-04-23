# extraction_workflow_align_and_structural_dedupe

- **Started**: 2026-04-23 18:22:59 EDT
- **Branch**: master
- **Status**: DONE

## 背景 / 触发

上一轮 `/after-check` 发现两件事需要收尾：

1. [M] `docs/architecture/extraction_workflow.md:269` / `:361`——Phase 3.5
   检查 #4 描述未与 `docs/requirements.md:2152` 新脚注对齐；验证清单里
   "evidence_refs 是否有效引用"没界定层级，读者会误以为 memory_timeline
   也被覆盖。
2. Open Question 2 — `automation/repair_agent/checkers/structural.py`
   里 `stage_events` 50–80 字长度校验是和 `stage_snapshot.schema.json`
   `items.minLength=50 / maxLength=80` 重复的业务规则；严格意义上和
   "字段约束只在 schema 声明"原则不一致。

本轮同时处理这两项。

## 结论与决策

### 修 M — 对齐 extraction_workflow.md

- `:269` Phase 3.5 检查 #4：把 `evidence_refs 覆盖率 — 空 evidence_refs
  比例` 改成和 `docs/requirements.md:2152` 同口径，明确只对
  `角色 / 世界 stage_snapshot` 检查空值比例，并加脚注"memory_timeline 不
  再持有 evidence_refs"。
- `:361` 阶段验证清单条目：把 `evidence_refs 是否有效引用` 改成
  `stage_snapshot 的 evidence_refs 是否有效引用（memory_timeline 不涉及）`
  的清晰表述。

### structural.py stage_events 长度去重

- `StructuralChecker._check_dict` 中 `stage_events` 的 50 / 80 字长度检查
  （[structural.py:89-109](automation/repair_agent/checkers/structural.py#L89-L109)）
  与 `schemas/character/stage_snapshot.schema.json` 里
  `"stage_events": { ..., "items": { "type": "string", "minLength": 50,
  "maxLength": 80 } }` 完全重复；L1 `SchemaChecker` 已经跑在
  `StructuralChecker` 之前（`coordinator._build_pipeline`），同 issue 会
  被两层报告。删掉 L2 这段。
- 同一审查顺便看了 `relationship_history_summary` 的 300 字校验
  ([structural.py:111-154](automation/repair_agent/checkers/structural.py#L111-L154))：
  该函数同时做 `driving_events 空值 warning` / `relationship_history_summary
  空值 warning` / 超长 error。前两项是 schema 表达不了的语义检查
  （schema 只能说 required，但这里是 warning 级，不阻塞 COMMITTED），
  **保留**。超长 error 这一支和 schema `maxLength: 300` 重复，但为了
  让 warning + error 走同一分支给出一致的 json_path，保留不动，避免
  过度拆分。若未来决定彻底去重，单独一轮。
- `common_triggers`：上一轮给 `failure_modes.schema.json` 的
  `common_failures[].common_triggers` 加了 `maxItems: 10`，当时 PRE
  有这一条；但原本这个字段并未有 L2 structural 校验，无需动
  `structural.py`。

### 连带更新

- 把"stage_events 50–80 字在 structural.py 去重"一事登到
  `ai_context/decisions.md` 27b 条后面，顺便把 27b 里原来说的"L2
  structural checker keeps defaults aligned with schema"改准一点：
  确认仅 `relationship_history_summary_max_chars` 仍在程序里保留
  fallback，避免读者误会 structural.py 还在做长度镜像。
- 检查 `docs/architecture/extraction_workflow.md` / `docs/requirements.md`
  是否有其他位置谈及"L2 对 stage_events 长度校验"；如有，连带更新。

## 计划动作清单

- file: `docs/architecture/extraction_workflow.md` →
  `:269` Phase 3.5 #4 文案对齐；`:361` 清单条目加层级界定
- file: `automation/repair_agent/checkers/structural.py` →
  删除 `_check_dict` 里 `stage_events` 的 50 / 80 字长度校验分支
  （含两条 `Issue(stage_events_min_length / max_length)`）；保留
  `_rel_history_max_chars` 相关逻辑
- file: `ai_context/decisions.md` → 27b 条目措辞收紧；
  追加"stage_events 50–80 由 schema 唯一门控"
- 全库 grep 扫描："stage_events_min_length / stage_events_max_length" 是
  否有别处的硬编码引用（repair prompt、L3、文档）；如有，同步

## 验证标准

- [ ] `grep -n "stage_events_min_length\|stage_events_max_length" automation/ docs/ ai_context/` 输出为空（除本次 log 以外）
- [ ] `python -c "from automation.repair_agent.checkers.structural import StructuralChecker; c=StructuralChecker(); issues=c._check_dict('x.json', {'stage_events': ['短']*3}, __import__('pathlib').Path('x.json')); print([i.rule for i in issues])"` 不出现 `stage_events_*` 规则
- [ ] `python -c "import jsonschema, json; s=json.load(open('schemas/character/stage_snapshot.schema.json')); jsonschema.Draft202012Validator.check_schema(s)"` 通过
- [ ] `grep "evidence_refs" docs/architecture/extraction_workflow.md` 剩下的两处表述和 `docs/requirements.md:2152` 同口径
- [ ] import smoke: `python -c "from automation.persona_extraction import orchestrator, consistency_checker; from automation.repair_agent import coordinator"` 不报错
- [ ] 27b 决策条目读起来没歧义（不会被误读为"structural 还在做长度镜像"）

## 执行偏差

全库 grep 扫描时多找到了 `docs/requirements.md:1558` 的 L2 checker 检查内容描述——本来写着 "L2 含 event_description / stage_events / digest_summary 长度校验"，与实际去除后的 L2 职责不再匹配。PRE 计划动作清单里没列这条，但属于同一轴的对齐遗漏。现场补了一项：把该行改写成"schema 表达不了的业务规则 + relationship_history_summary 超长保险"。

<!-- POST 阶段填写 -->

## 已落地变更

- `docs/architecture/extraction_workflow.md:269` — Phase 3.5 检查 #4 文案改成 `角色 / 世界 stage_snapshot 中 evidence_refs 为空的比例（memory_timeline 不再持有 evidence_refs）`，与 `docs/requirements.md:2152` 同口径。
- `docs/architecture/extraction_workflow.md:361` — 阶段验证清单条目改成 `角色 / 世界 stage_snapshot 的 evidence_refs 是否有效引用（memory_timeline 不涉及此字段）`，明确层级。
- `automation/repair_agent/checkers/structural.py` — 删除 `_check_dict` 里 `stage_events` 50–80 字长度检查分支（连同 `stage_events_min_length` / `stage_events_max_length` 两条 `Issue.rule`）。`relationship_history_summary` 空值 warning + 超长 error 的分支原样保留。
- `ai_context/decisions.md` — 27b 条目收紧措辞：把原来"L2 structural checker keeps defaults aligned with schema"改成"L2 只保留 schema 表达不了的检查（`driving_events` / `relationship_history_summary` 空值 warning），内部仅 `relationship_history_summary_max_chars = 300` 作为超长 error 保险"。
- `docs/requirements.md:1558` — L2 checker 功能描述从"含 `event_description` / `stage_events` / `digest_summary` / `knowledge_scope` 长度 / 条数"改成"schema 表达不了的业务规则：target_map importance 阈值、ID 格式、缺失/空串 warning、stage_id 对齐、catalog / digest 完整性、snapshot 存在性、跨实体引用解析"；L1 一栏补充 "所有字段级长度/条数上下限一律由 L1 承担"。

## 与计划的差异

多做了一处：`docs/requirements.md:1558` L2 检查表格描述的对齐（PRE 未列）。理由见"执行偏差"。其余条目与 PRE 计划动作清单一致。

## 验证结果

- [x] `grep stage_events_min_length / stage_events_max_length` 仓库内为空（除本 log）。
- [x] `python3 -c` 实例化 `StructuralChecker` 并跑 `_check_dict` 对 `stage_events` 样本，输出规则列表为空——L2 已不再报 `stage_events_*`。
- [x] `schemas/character/stage_snapshot.schema.json` 里 `stage_events.items.minLength=50 / maxLength=80` 保留；Draft 2020-12 schema 校验通过——L1 仍然把关。
- [x] `grep evidence_refs docs/architecture/extraction_workflow.md` — 只剩 `:269` / `:361` 两处，和 `docs/requirements.md:2152` 表述同步。
- [x] Import smoke：`automation.persona_extraction.orchestrator` / `consistency_checker` / `automation.repair_agent.coordinator` 全部 import 成功。
- [x] `ai_context/decisions.md` 27b 读起来明确：仅 `relationship_history_summary_max_chars = 300` 作为程序端的超长 error 保险，其余长度 / 条数由 schema 管。

## Completed

- **Status**: DONE
- **Finished**: 2026-04-23 18:36:00 EDT
