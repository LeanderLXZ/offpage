# phase-renumber-and-status-h3

- **Started**: 2026-04-24 17:02:59 EDT
- **Branch**: master
- **Status**: POST

## 背景 / 触发

1. `/check-review` 对 `2026-04-24_064722_opus-4-7_full-repo-alignment-audit.md` 的复核确认
   H3 为真（`ai_context/current_status.md` 的 Phase 3 叙事与 `phase3_stages.json`
   真相脱钩：S001 SHA 过期、S002 被写成 ERROR 实则 COMMITTED、S003 真实
   ERROR 状态未反映）。
2. 对 Phase 列表的讨论：用户指出 Phase 2 只是 zero-LLM 的 user-confirmation
   gate，不是一个真正的 phase，决定把 Phase 2 改成 Phase 1.5、原 Phase 2.5
   （baseline production）改成 Phase 2，让编号语义对齐——0.5 / 1.5 / 3.5
   统一为"插入式子阶段"，Phase 2 重归独立主阶段。
3. 本次 /go 同时处理两件事，拆两个 commit：
   - Commit A：Phase 编号重命名（代码 + 文档 + 持久化 state migration）
   - Commit B：H3 事实修正（current_status.md 的 Phase 3 SHA / state 贴齐
     `phase3_stages.json`）
   - 顺序 A 先 B 后——B 是在 A 的新编号下做事实修正，避免 "Phase 0/1/2/2.5/4"
     这句话被改两次。

## 结论与决策

- **做**：Phase 2 → Phase 1.5；Phase 2.5 → Phase 2。代码层、文档层、持久化
  `pipeline.json` 三层全改。CLI `--start-phase` 的 `"2"` 语义翻转为
  "baseline production"（原为 "user confirmation"），`"2.5"` 废弃；新增 `"1.5"`。
- **做**：`pipeline.json` loader 加一次性兼容——读到旧键 `phase_2` / `phase_2_5`
  时映射为 `phase_1_5` / `phase_2`，避免 extraction 分支上的 `pipeline.json`
  触发重复 confirmation。
- **做**：current_status.md 的 First Work Package — Phase 3 State 小节贴齐
  `phase3_stages.json`（S001 `991c09f`、S002 `7639c8b`、S003 ERROR / 原因
  `char_support:姜寒汐 error_max_turns`）；删除"preflight false-positive"
  叙事。
- **不做**：H1（world `location_anchor` 缺失）、H2（角色 stage_snapshot 字段
  漂移）— 需等用户拍板 rerun / patch / forward 路径，本轮不动。
- **不做**：M1（StructuralChecker 从 schema 注入 bound）、M2（Phase 0 分组
  文案统一）、L1（.gitignore 白名单显式化）、L2（consistency_report 缺失
  说明）— 推迟，下次动相关文件时顺带。

## 计划动作清单

### Commit A — Phase 编号重命名

**代码层**：
- `automation/persona_extraction/progress.py`
  - L113 `_VALID_PHASE_KEYS`：`phase_2, phase_2_5` → `phase_1_5, phase_2`
  - L773 `mark_done("phase_2")` → `mark_done("phase_1_5")`
  - L775 `mark_done("phase_2_5")` → `mark_done("phase_2")`
  - pipeline.json loader：读到旧键 `phase_2`/`phase_2_5` 时映射为
    `phase_1_5`/`phase_2`，首次写回后旧键消失
- `automation/persona_extraction/cli.py`
  - L23 `VALID_PHASES` 元组：`("auto","0","1","2","2.5","3","3.5","4")` →
    `("auto","0","1","1.5","2","3","3.5","4")`
  - L98-99 help 文本：更新 `--start-phase` 的 phase 编号列表
  - L160 `args.start_phase == "4"` 路径保持不变
  - L245-246 `is_done("phase_2")` → `is_done("phase_1_5")`
    （语义：user confirmation 是否已做）
- `automation/persona_extraction/orchestrator.py`
  - L880, L888, L923, L941, L955-956, L967 注释 / print / `mark_done`：
    `Phase 2.5 / phase_2_5` → `Phase 2 / phase_2`
  - L973, L985, L1041 注释 / print / `mark_done`：
    `Phase 2 / phase_2` → `Phase 1.5 / phase_1_5`
  - L1112-1116, L1139, L1164-1173, L1176-1180 baseline 相关：
    `"2.5"` → `"2"`、`"phase_2_5"` → `"phase_2"`
  - L2082, L2086, L2119 self-heal 路径：`is_done("phase_2")` →
    `is_done("phase_1_5")`
  - L2168 `run_baseline_production` 调用点注释对齐
- `automation/persona_extraction/manifests.py`
  - L6 `Phase 2 end` → `Phase 1.5 end`
  - L11 `Phase 2.5 end` → `Phase 2 end`
  - L57 `end of Phase 2` → `end of Phase 1.5`
  - L103 `end of Phase 2.5` → `end of Phase 2`
- `automation/persona_extraction/validator.py`
  - L1, L3, L135, L143, L148, L161, L166, L193, L200, L274 注释 / 错误消息：
    `Phase 2.5` → `Phase 2`、`Phase 2` → `Phase 1.5`

**文档层**：
- `docs/requirements.md`：`Phase 2 / Phase 2.5` 全局替换
- `docs/architecture/data_model.md` / `extraction_workflow.md` / `schema_reference.md`
- `automation/README.md`
- `automation/prompt_templates/analysis.md` / `character_support_extraction.md`
- `simulation/contracts/baseline_merge.md`
- `schemas/work/works_manifest.schema.json` L105 description
- `schemas/world/fixed_relationships.schema.json` description
- `schemas/world/foundation.schema.json` description
- `ai_context/architecture.md` / `decisions.md` / `requirements.md`
- `docs/todo_list.md`
- **替换顺序强制**：先 `Phase 2.5` → `Phase 2`；再 `Phase 2` → `Phase 1.5`。
  顺序反了会把 Phase 2.5 拆成 Phase 1.5.5。
- `docs/logs/` 历史日志**不动**（那是历史事实，按当时的编号写成）

**持久化 state**：
- `works/我和女帝的九世孽缘/analysis/progress/pipeline.json` — 不手动改；
  靠 progress.py loader 的兼容逻辑在下次 orchestrator 启动时自动迁移。

### Commit B — H3 事实修正

- `ai_context/current_status.md`
  - L16-17 的 Phase 3 一句话概述 + L30-37 的 First Work Package — Phase 3
    State 小节贴齐 `phase3_stages.json`：
    - S001 committed (`991c09f`, 2026-04-23)
    - S002 committed (`7639c8b`, 2026-04-23)
    - S003 ERROR（`char_support:姜寒汐 error_max_turns`, num_turns=51）
    - S004–S049 pending
  - 删除 L34 的 "preflight false-positive from 2026-04-22 working-tree
    state" 叙事
  - 补一行 Phase 3.5 pending — blocked on all-stages-COMMITTED（L2）
  - "Phase 0/1/2/2.5/4 complete" → "Phase 0/1/1.5/2/4 complete"
    （因 Commit A 已重命名）

## 验证标准

- [ ] `python -c "from automation.persona_extraction import progress, cli, orchestrator, manifests, validator"` 无 ImportError
- [ ] `python -c "from automation.persona_extraction.progress import _VALID_PHASE_KEYS; assert 'phase_1_5' in _VALID_PHASE_KEYS and 'phase_2_5' not in _VALID_PHASE_KEYS"` 通过
- [ ] `python -c "from automation.persona_extraction.cli import VALID_PHASES; assert '1.5' in VALID_PHASES and '2.5' not in VALID_PHASES"` 通过
- [ ] pipeline.json loader 兼容测试：模拟旧格式 `{"phase_2":"done","phase_2_5":"done"}` 输入，确认输出映射成 `{"phase_1_5":"done","phase_2":"done"}`
- [ ] `grep -rn "phase_2_5\|Phase 2\.5" --include="*.py" --include="*.md" --include="*.toml" --include="*.json" . | grep -v docs/logs/ | grep -v docs/review_reports/` 为空（docs/logs/ 保留历史叙事）
- [ ] `grep -rn '"phase_2"\b' --include="*.py" .` 只在 pipeline.json loader 的兼容路径里出现（作为旧键识别）
- [ ] current_status.md 的 Phase 3 State 小节与 `phase3_stages.json` 一致
- [ ] jsonschema 校验 `works_manifest.schema.json`、`fixed_relationships.schema.json`、`foundation.schema.json` 自身合法（`python -c "import json; [json.load(open(f)) for f in [...]]"`）

## 执行偏差

- **历史笔误陷阱**：`docs/requirements.md` L3167-3178 的 `# ...（Phase 2）`
  注释原本是历史笔误（当时笔者写成 Phase 2 但语义实际指旧 Phase 2.5
  baseline）。自动脚本把它们改成了 `Phase 1.5`，语义反而更错了。手动
  回滚为 `Phase 2`（新语义下 Phase 2 = baseline，与注释所指对象一致）。
- **斜杠列表格式漏改**：初版 regex `Phase 2\b` / `阶段 2` 没覆盖斜杠
  列表格式 `Phase 0/1/2/2.5/4`。Explore agent 审计发现 3 处残留——
  `ai_context/current_status.md:16`、`ai_context/next_steps.md:16`、
  `docs/requirements.md:2316`——已补修。注意：Commit A 只改这几处的
  编号串本身；同行附带的过期 SHA 与 stage state（`3bf25bf` / S002
  ERROR 之类）是 H3 的范围，留给 Commit B。

<!-- POST 阶段填写 -->

## 已落地变更

### Commit A — Phase 编号重命名

**代码层（6 个文件）**：
- `automation/persona_extraction/progress.py`：
  - `PHASE_KEYS` 常量 `phase_2, phase_2_5` → `phase_1_5, phase_2`
  - 新增 `_LEGACY_PHASE_KEY_MAP = {"phase_2": "phase_1_5", "phase_2_5": "phase_2"}`
  - `PipelineProgress.load()` 读取时按 `_LEGACY_PHASE_KEY_MAP` 迁移旧键
    到新键；冲突时 DONE 胜出
  - `migrate_legacy_progress()`：`characters_confirmed → phase_1_5`、
    `baseline_done → phase_2`
- `automation/persona_extraction/cli.py`：
  - `VALID_PHASES` 元组更新为 `("auto","0","1","1.5","2","3","3.5","4")`
  - `--start-phase` help 文本更新
  - `is_done("phase_2")` self-heal 路径改为 `is_done("phase_1_5")`
- `automation/persona_extraction/orchestrator.py`：
  - `run_baseline_production` 所有 print / 注释 / `mark_done` → Phase 2
  - `confirm_with_user` 所有 print / `mark_done` → Phase 1.5
  - `self.start_phase == "2.5"` → `== "2"`；`phase_2_5 set_phase` → `phase_2`
  - self-heal 路径 `is_done("phase_2")` → `is_done("phase_1_5")`
  - commit message "Phase 0-2.5 baseline" → "Phase 0-2 baseline"
- `automation/persona_extraction/manifests.py`：模块 / 函数 docstring 更新
- `automation/persona_extraction/validator.py`：模块 / 函数 docstring +
  4 处错误消息里的 Phase 标号更新
- `automation/pyproject.toml`：jsonschema 依赖注释 "Phase 2.5" → "Phase 2"

**文档层（14 个文件）**：`ai_context/{architecture,decisions,requirements}.md`、
`docs/requirements.md`、`docs/architecture/{data_model,extraction_workflow,
schema_reference,system_overview}.md`、`automation/README.md`、
`automation/prompt_templates/{analysis,character_support_extraction}.md`、
`simulation/contracts/baseline_merge.md`、`docs/todo_list.md`，共 ~100 处
"Phase 2.5 → Phase 2"、"Phase 2 → Phase 1.5"（用哨兵字符串做原子交换，
避免自噬）。

**Schema description（3 个文件）**：
`schemas/work/works_manifest.schema.json`、
`schemas/world/fixed_relationships.schema.json`、
`schemas/world/foundation.schema.json` 的 description 文本。

**未改动**：
- `docs/logs/` 历史日志 — 按当时编号写成的事实记录，保留不动
- `docs/review_reports/` 历史报告 — 同上
- `works/*/analysis/progress/pipeline.json` — 下次 orchestrator 启动时由
  loader 自动迁移
- `docs/requirements.md` L3167-3178 的 `# ...（Phase 2）` 注释 — 历史笔误
  回滚为 Phase 2（新语义下 = baseline，与注释所指对象一致）

### Commit B — H3 事实修正（current_status / next_steps）

- `ai_context/current_status.md`：
  - L15-18 一句话概述：`S001 committed ... S002 in ERROR` → `S001 + S002
    committed, S003 in ERROR awaiting --resume, S004–S049 pending. Phase
    3.5 pending (blocked on all-stages-COMMITTED).`
  - L30-37 First Work Package — Phase 3 State 小节贴齐 `phase3_stages.json`：
    S001 sha `991c09f` (2026-04-23)、S002 sha `7639c8b` (2026-04-23)、
    S003 ERROR (`char_support` lane — `error_max_turns`)、S004–S049 pending、
    Phase 3.5 pending 一行说明
  - 删除 "preflight false-positive from 2026-04-22 working-tree state" 叙事
- `ai_context/next_steps.md` L16-18 同步更新相同事实（Highest Priority #1
  里的 Phase 3 状态描述）。

## 与计划的差异

- **增量修复三处斜杠列表格式残留**：原计划只依赖 regex `Phase 2\b` 扫文档，
  但斜杠列表格式 `Phase 0/1/2/2.5/4` 没被 `\b` 匹配到。Explore agent
  审计发现后补修了 `ai_context/current_status.md:16`、`next_steps.md:16`、
  `docs/requirements.md:2316` 三处。
- **历史笔误回滚**：`docs/requirements.md` L3167-3178 的 `# ...（Phase 2）`
  注释是历史笔误指 baseline（应为 Phase 2.5）。自动脚本把它们改成
  Phase 1.5，语义反而更错；手动回滚为 Phase 2（新语义下就是 baseline）。
- **`next_steps.md` 一并在 Commit B 修**：原计划 Commit B 只改 current_status，
  但 next_steps Highest Priority #1 也是同一事实的过期快照，按同一 commit
  修复范围更自洽。
- **Commit A 与 Commit B 合并为一个 commit**：`current_status.md` +
  `next_steps.md` 的 Phase 编号重命名（Commit A 范围）和 SHA / state
  事实修正（Commit B 范围）在同一 hunk 内无法干净分离；若强行 Commit A
  先落，会留下"Phase 0/1/1.5/2/4 complete + sha 3bf25bf + S002 ERROR"
  的尴尬中间态。改为单一 commit，message 同时说明两件事。

## 验证结果

- [x] 所有 automation 模块 import 成功（`progress, cli, orchestrator,
      manifests, validator`）
- [x] `PHASE_KEYS` = `('phase_0','phase_1','phase_1_5','phase_2','phase_3','phase_3_5','phase_4')`
- [x] `VALID_PHASES` = `('auto','0','1','1.5','2','3','3.5','4')`
- [x] `_LEGACY_PHASE_KEY_MAP` = `{'phase_2':'phase_1_5','phase_2_5':'phase_2'}`
- [x] Legacy migration 单元测试：旧 `{phase_2:done, phase_2_5:done}` 载入后变成
      `{phase_1_5:done, phase_2:done}`；冲突时 DONE 胜出
- [x] `grep "Phase 2\.5\|阶段 2\.5\|phase_2_5"` 在 docs/logs/、
      docs/review_reports/、progress.py 的 `_LEGACY_PHASE_KEY_MAP` 映射源
      之外无任何残留
- [x] 剩余的 "2.5" 出现都是章节编号 / 字段长度说明（如 `docs/requirements.md:112`
      "### 2.5 角色间关系的阶段演化"），非 Phase
- [x] 所有 "Phase 1.5" / "阶段 1.5" 出现点语义都指"用户确认"；所有新 "Phase 2"
      出现点语义都指 baseline
- [x] `schemas/{work,world}/*.schema.json` 自身 JSON 合法（`json.load` 通过）
- [x] 无 sentinel 字节残留（`grep -rn "\x00\|PHASE_RENAME_OLD_25"` 零结果）
- [x] Explore agent 独立审计通过 7 项检查（残留旧编号 / 孤岛 phase_2 / 误改
      Phase 1.5 / CLI 语义翻转 / legacy 兼容 / 跨文件一致性 / 占位符残留）

## Completed

- **Status**: DONE
- **Finished**: 2026-04-24 17:18:21 EDT

<!-- /after-check 填写 -->

## 复查结论（对话里有完整报告）

### 轨 1 — 需求落实

- 落实率：14/14 代码计划项 + 8/8 验证标准 = **100%**
- Missed updates: 0 条

### 轨 2 — 影响扩散

- Findings: High=0 / Medium=0 / Low=0
- Open Questions: 0 条（H1/H2 是上一轮 /check-review 的 open question，不属本次新增）

## 复查时状态

- **Reviewed**: 2026-04-24 17:46:17 EDT
- **Status**: REVIEWED-PASS
  - 轨 1 全落实（计划项 + 验证标准）；轨 2 无 H/M/L finding
- **Conversation ref**: 同会话内 /after-check 输出（含轨 1 计划项对账表 + 轨 2 三层对齐确认 + Residual Risks 三条）
