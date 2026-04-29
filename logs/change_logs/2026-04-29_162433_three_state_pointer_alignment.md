# three_state_pointer_alignment

- **Started**: 2026-04-29 16:24:33 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

承接 [2026-04-29_155949_char_snapshot_per_stage_three_state.md](2026-04-29_155949_char_snapshot_per_stage_three_state.md)
/post-check 报告（REVIEWED-PARTIAL，2 项 Medium + 1 项 Low）。用户拍板
"按你建议修正"，对应 fix 三项 finding。

## 结论与决策

按 /post-check 报告：

1. **[M-1]** `docs/requirements.md:980` stage_delta 字段说明
   "信息性，便于理解演变弧线" 过松——升级为反映 prompt 新约束
   "必须捕捉 (B) 关键变化 + (D) 消除原因 / 禁'无明显变化'敷衍"，
   并指针到 prompt 权威定义
2. **[M-2]** `docs/architecture/extraction_workflow.md` §6.2 自包含
   快照的生成规则 + `docs/requirements.md` §9.4 生成规则——加 1 行
   pointer 指向 prompt 内 (B/C/D) 三态规则的权威定义。**不复述
   完整规则**（按项目反 anti-pattern 既有清理模式：复述 schema /
   prompt 内容是反 pattern，pointer 即可）
3. **[L]** `character_snapshot_extraction.md:107` stage_delta 描述
   前向引用 (B)/(D) 标签——把 (B/C/D) 三态规则块从 L114 之后挪到
   字段列表之前（即 L94 那个字段子列表之前），消除前向引用

## 计划动作清单

- file: `docs/requirements.md` §9.4 生成规则段（[L1003-1010](../../docs/requirements.md#L1003-L1010)）
  → 末尾加 1 行 pointer 指向 character_snapshot_extraction.md 三态规则
- file: `docs/requirements.md` stage_delta 描述（[L980](../../docs/requirements.md#L980)）
  → 升级措辞 + 指针
- file: `docs/architecture/extraction_workflow.md` §6.2 自包含快照生成
  规则段（[L176-180](../../docs/architecture/extraction_workflow.md#L176-L180)）→ 末尾加 1 行 pointer
- file: `automation/prompt_templates/character_snapshot_extraction.md`
  → 把「未出场角色的继承规则 (A 类)」+「出场角色字段三态规则 (B/C/D 类)」
  +「per-stage 推演原则」+「首阶段特殊指引」整体上移到字段子列表
  **之前**（即 L87 "**自包含快照（最关键的规则）**" 之后、字段子列表
  L94 之前），让 stage_delta 描述提及 (B)/(D) 时它们已被定义；调整后
  L107 的 (B)/(D) 标签变后向引用，消除前向引用问题

## 验证标准

- [ ] `grep -n "B/C/D\|三态\|character_snapshot_extraction" docs/requirements.md docs/architecture/extraction_workflow.md` 各命中至少 1 行 pointer
- [ ] `grep -n "信息性，便于理解演变弧线" docs/requirements.md` = 0（旧措辞已替换）
- [ ] character_snapshot_extraction.md 中 B/C/D 定义行号 < stage_delta 字段说明行号（消除前向引用）
- [ ] 没有任何代码 / schema 改动（仅 docs + prompt 文字调整）
- [ ] todo_list 不需要新增 / 移段（本次属 /post-check 的小修补，不是新 todo）

## 执行偏差

无。

## 已落地变更

- `automation/prompt_templates/character_snapshot_extraction.md`：
  - 把「prev_stage 处理规则块」（A/B/C/D 三态 + per-stage 推演 +
    首阶段特殊指引）整体上移到字段子列表 **之前**（[L96-114](../../automation/prompt_templates/character_snapshot_extraction.md#L96-L114)）；
    字段子列表中 stage_delta 的描述（[L127](../../automation/prompt_templates/character_snapshot_extraction.md#L127)）现已是
    后向引用 (B)/(D) 标签——前向引用问题消除
  - (A) 类继承规则措辞改为 "(A) 未出场角色的继承规则" 与 (B/C/D) 同
    格式并列，方便阅读
- `docs/requirements.md`：
  - §9.4 字段维度列表的 `stage_delta` 项（[L980-985](../../docs/requirements.md#L980-L985)）
    措辞从 "信息性，便于理解演变弧线" 升级为 "必须捕捉 (B) 关键变化 +
    (D) 消除原因 / 禁'无明显变化'敷衍" + pointer 到 prompt 权威定义
  - §9.4 「生成规则」段（[L1022-1027](../../docs/requirements.md#L1022-L1027)）末尾
    加 1 行 pointer 指向 prompt §核心规则 #2
- `docs/architecture/extraction_workflow.md` §6.2 「自包含快照的生成
  规则」段（[L181-182](../../docs/architecture/extraction_workflow.md#L181-L182)）：
  stage_delta 描述从 "信息性，便于理解演变弧线" 升级为 "必须捕捉
  (B) 关键变化 + (D) 消除原因 / 禁'无明显变化'敷衍"；末尾加 1 行
  pointer 指向 prompt §核心规则 #2

## 与计划的差异

无。3 项 finding 全部按 PRE 计划落地。

## 验证结果

- [x] `grep -n "B/C/D\|三态\|character_snapshot_extraction" docs/requirements.md docs/architecture/extraction_workflow.md` requirements.md 命中 4 行（含 pointer），extraction_workflow.md 命中 3 行（含 pointer）
- [x] `grep -n "信息性，便于理解演变弧线" docs/requirements.md docs/architecture/extraction_workflow.md` 残留 = 0
- [x] B/C/D 定义在 prompt L99-101，stage_delta 字段说明在 L127——前者 < 后者，前向引用消除
- [x] git status 仅 3 markdown + 1 新 log，无代码 / schema 改动
- [x] todo_list 不需变（本次属 /post-check fix，未引入新 todo）

## Completed

- **Status**: DONE
- **Finished**: 2026-04-29 16:27:48 EDT
