# baseline_deprecate_post_check_fixes

- **Started**: 2026-04-29 15:29:43 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

承接 `2026-04-29_144204_char_baseline_4piece_deprecate.md` /post-check
报告（REVIEWED-FAIL，2 项 High + 4 项 Medium + 2 项 Low）。用户拍板：

1. Delete `simulation/contracts/baseline_merge.md` 整文件
2. Delete schema 描述里"历史 baseline failure_modes.schema.json"等
   lineage 引用——现行 docs 完全不应再提 baseline
3. 其他 finding 按上轮 /post-check 报告的建议修复

## 结论与决策

修复以下 6 项（合并 High + Medium + 部分 Low）：

1. **删除** `simulation/contracts/baseline_merge.md`（整文件）
2. **更新** `simulation/retrieval/load_strategy.md` L25-26：移除
   `failure_modes.json` 和 `boundaries.json` Tier 0 startup 加载引用
3. **更新** `simulation/flows/startup_load.md` L22：将 vague
   "Read target character baseline" 改为 "Read target character
   identity.json"
4. **去除** schema description 中"历史 baseline failure_modes.schema.json"
   lineage 引用（3 处：`schemas/character/stage_snapshot.schema.json:568`、
   `docs/architecture/schema_reference.md:264`、
   `docs/requirements.md:962`）。措辞改为只描述当前 schema 含义，不再
   提 baseline / 不再回指已删文件
5. **增强** `migrate_baseline_to_stage_snapshot.py`：
   - 当 `failure_modes.json` 不存在时，给每个 stage_snapshot 注入
     **空 `failure_modes: {}` 占位**，避免 schema validation 失败
   - 在脚本末尾打印一行提示"考虑将 .archive/ 加入相应分支的
     .gitignore，避免 git add 误带"
6. **更新** `ai_context/handoff.md`：若有 "Current Work Continuation"
   段且与本次 schema 改动相关，加一行提示"--resume 前先跑迁移脚本
   `--apply` 否则现存 stage_snapshots 会撞 jsonschema fail"

不在本 /go 范围（保留为 todo / 后续）：

- _smoke_triage.py 测试 fixture 同步：测试本来就基于 broken JSON 操作，
  新增的 required failure_modes 只是多一个错误，不破坏测试意图——保留
- workflow 时序的程序化保护：单纯文档警告 + handoff 提示就够，
  不引入额外的程序级 gate

## 计划动作清单

- file: `simulation/contracts/baseline_merge.md` → 删除
- file: `simulation/retrieval/load_strategy.md` → Tier 0 startup
  列表去掉 failure_modes.json + boundaries.json 两行
- file: `simulation/flows/startup_load.md` → L22 改写
- file: `schemas/character/stage_snapshot.schema.json` → failure_modes
  字段 description 去掉 lineage 引用
- file: `docs/architecture/schema_reference.md` → schema_reference 表
  failure_modes 行去掉 lineage 引用
- file: `docs/requirements.md` → §9.4 failure_modes 描述去掉 lineage
  引用
- file: `automation/persona_extraction/migrate_baseline_to_stage_snapshot.py`
  → 加 empty-failure_modes 占位 fallback + 末尾 gitignore 提示
- file: `ai_context/handoff.md` → 若有相关段，加 --resume 前置迁移
  提示

## 验证标准

- [ ] `git ls-files simulation/contracts/baseline_merge.md` 不返回
- [ ] `grep -rn "voice_rules\|behavior_rules\|boundaries\.json\|failure_modes\.json" simulation/` 残留 = 0（除被替换为 identity 的位置）
- [ ] `grep -rn "历史 baseline failure_modes\|baseline failure_modes\.schema\.json" automation/ schemas/ docs/ ai_context/` 残留 = 0
- [ ] `python -c "import automation.persona_extraction.migrate_baseline_to_stage_snapshot"` 无报错
- [ ] migration 脚本 dry-run 仍能跑通（无副作用）
- [ ] `jsonschema.Draft202012Validator.check_schema(stage_snapshot)` 通过
- [ ] failure_modes 字段 description 不再含"baseline failure_modes.schema.json"

## 执行偏差

`ai_context/handoff.md` 检查后**未修改**——该文件已有 "Extraction-branch
artifact drift (resume gate)" 段（L51-61），通用引导用户在 --resume 前
读 `docs/todo_list.md` 的 In Progress + Next 段。本 todo 已经在
In Progress 段标 "代码完成、runtime 验证待跑"，用户按 handoff 既有
流程走会自然看到，无需新加一行专属提示（避免引入"specific recipe"
稀释通用流程指引）。

## 已落地变更

- 删除：`simulation/contracts/baseline_merge.md`
- 修改：
  - `simulation/retrieval/load_strategy.md` — Tier 0 startup 列表
    去掉 failure_modes.json + boundaries.json 两行；identity 段增补
    "only character-level constant file" 注释
  - `simulation/flows/startup_load.md:22` — "Read target character
    baseline" → "Read target character `identity.json`" + 解释
  - `schemas/character/stage_snapshot.schema.json:568` — failure_modes
    description 去掉 "子类 maxItems 与历史 baseline failure_modes.schema.json 一致"
  - `docs/architecture/schema_reference.md:264` — failure_modes 表格行
    指针改为指向 stage_snapshot.schema.json
  - `docs/requirements.md:962` — failure_modes 项指针改为指向
    stage_snapshot.schema.json
  - `automation/persona_extraction/migrate_baseline_to_stage_snapshot.py`
    — 加 empty-failure_modes 占位 fallback（未找到 baseline 文件 /
    payload 为空时，仍向所有现存 stage_snapshots 注入 `failure_modes: {}`，
    避免新 schema required 校验失败）+ apply 模式末尾打印 .gitignore
    提示

## 与计划的差异

无。计划 6 项全部按计划落地（其中 handoff.md 项经评估保持不动，理由
见上"执行偏差"段）。

## 验证结果

- [x] `git ls-files simulation/contracts/baseline_merge.md` 不返回 — 文件已删
- [x] `grep -rn "voice_rules\|behavior_rules\|boundaries\.json\|failure_modes\.json" simulation/` 残留 = 0
- [x] `grep -rn "历史 baseline failure_modes\|baseline failure_modes\.schema\.json" automation/ schemas/ docs/ ai_context/` 残留 = 0
- [x] `python -c "import automation.persona_extraction.migrate_baseline_to_stage_snapshot"` 无报错
- [x] migration 脚本 dry-run 仍能跑通（无副作用）
- [x] `jsonschema.Draft202012Validator.check_schema(stage_snapshot)` 通过
- [x] failure_modes 字段 description 不再含 "baseline failure_modes.schema.json"

## Completed

- **Status**: DONE（本轮 fix 全部落地 + 静态验证通过；runtime 验证仍承
  上轮 todo，待后续 /go 在 extraction 分支执行）
- **Finished**: 2026-04-29 15:32:11 EDT
