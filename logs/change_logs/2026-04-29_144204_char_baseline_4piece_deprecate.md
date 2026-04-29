# char_baseline_4piece_deprecate

- **Started**: 2026-04-29 14:42:04 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

会话从 `/todo 讨论T-BASELINE-DEPRECATE` 开始，对 todo_list 中既有
`T-BASELINE-DEPRECATE` 条目（标题原为「废弃 voice_rules /
behavior_rules / boundaries 三件套，重定位 identity / failure_modes
为 character-level 恒定+模拟时加载」）展开讨论。

讨论中识别出两个关键问题：
1. 原条目把 stage_delta 升级为结构化字段（changed/removed/added）耦合
   进 BASELINE-DEPRECATE，过度工程
2. 原方案 `active_failure_modes` 字段（"全量 active 子集"+ 仍保留
   character-level failure_modes 文件）是不必要的两层抽象

用户拍板的最终方案：4 件套（含 failure_modes）一并废弃，failure_modes
schema 整体内联进 stage_snapshot；stage_delta 不动；额外新增「所有带
maxItems 的字段触发上限时由 LLM 在抽取阶段按重要度先排序后截断」的
prompt 统一规则。

todo_list 顶部索引行 + 全文条目已在前一步会话中按新方案改写并 commit
（`77bb111 todo: 新增 T-BASELINE-DEPRECATE / T-CHAR-SNAPSHOT-PER-STAGE
+ SUB-LANES brief/body 同步`）。本 /go 实施代码 + schema + prompt +
docs + 迁移脚本，runtime 验证 + 真实 work 迁移留作后续 /go。

## 结论与决策

按 `docs/todo_list.md` `### [T-BASELINE-DEPRECATE]` 全文条目执行：

1. **废弃 4 件套**：voice_rules / behavior_rules / boundaries /
   failure_modes 4 个 baseline schema 文件 + 现行 works/ 下对应
   canon 文件迁移到 .archive/
2. **identity 重定位**：仍是 character-level 恒定文件，未来
   simulation runtime 加载（本 /go 不动 runtime）
3. **manifest 不读**：从 char_snapshot prompt 的 files_to_read
   清单移除（manifest 文件本身保留作为元数据）
4. **stage_snapshot 加 failure_modes 字段**：4 子类
   common_failures / knowledge_leaks / tone_traps /
   relationship_traps，子类上下限直接搬用现行
   failure_modes.schema.json
5. **stage_delta 不动**：保持现行自由文本方案
6. **prompt 加 maxItems-aware 裁剪规则**：character_snapshot_extraction.md
   新增段落，对所有带 maxItems 字段统一生效

**作用域分界**：本 /go 闭合到「代码 / schema / prompt / docs /
迁移脚本写完 + 静态验证（import + jsonschema）」。**不**跑实际
extraction、**不**迁移现有 works/ 数据、**不**移 todo 到 archived
（runtime 验证未跑前任务不算 Done）。

## 计划动作清单

**Schema**：

- file: `schemas/character/voice_rules.schema.json` → 删除
- file: `schemas/character/behavior_rules.schema.json` → 删除
- file: `schemas/character/boundaries.schema.json` → 删除
- file: `schemas/character/failure_modes.schema.json` → 删除（内容内联前先备份其 schema 子结构信息）
- file: `schemas/character/stage_snapshot.schema.json` → 加 `failure_modes`
  对象字段（4 子类），子类 schema 直接搬自原 failure_modes.schema.json

**Code**：

- file: `automation/persona_extraction/prompt_builder.py`
  `_build_char_snapshot_read_list`（行 ~436-480）→ 移除 voice_rules /
  behavior_rules / boundaries / failure_modes / manifest（5 文件）；
  保留 identity / 上阶段 snapshot / schema / 章节
- file: `automation/persona_extraction/migrate_baseline_to_stage_snapshot.py`
  → 新建迁移脚本（一次性、幂等、dry-run 模式默认）。**本 /go 仅写脚本
  不跑**，运行时迁移留后续

**Prompt**：

- file: `automation/prompt_templates/character_snapshot_extraction.md` →
  major rewrite：
  - 加「baseline 文件的角色定位」段：identity 是角色基础事实层
    （权威），4 件套已废弃不读取
  - 「自包含快照」段（原 ~50-57 行）：明确 stage_snapshot 是角色状态
    唯一权威；模拟时**会加载** identity，**不**加载已废弃 4 件套
  - is_first_stage = true 分支：S001 必须基于本阶段原文 + identity
    直接推演出基线状态全字段（含 failure_modes）
  - 新增 `failure_modes` 字段说明
  - 新增「maxItems 裁剪规则」段（对所有带 maxItems 字段统一生效）
- files: phase 1/2 prompt 模板 → grep 定位后删除产出 4 件套指令；
  identity 仍然产出

**Docs / ai_context**：

- file: `ai_context/architecture.md` § Character canon → 更新文件清单
- file: `ai_context/decisions.md` → 新增决策（废弃 4 件套 +
  failure_modes 并入 stage_snapshot full-state + identity 重定位 +
  maxItems 裁剪统一规则）
- file: `ai_context/data_model.md`（若存在）→ 更新角色 canon 数据模型
- file: `ai_context/current_status.md` → 状态变更说明
- file: `ai_context/requirements.md` → 同步
- file: `docs/architecture/extraction_workflow.md` → phase 1/2/3
  产出更新
- file: `docs/requirements.md` → 同步 character canon 描述

**Todo 维护**：

- file: `docs/todo_list.md` → BASELINE-DEPRECATE 从 Next 移到 In
  Progress；追加「开始时间」「当前状态：代码完成、runtime 验证待跑」
  字段；同步刷新顶部 Index 段

## 验证标准

- [ ] `python -c "import automation.persona_extraction.prompt_builder"` 无报错
- [ ] `python -c "import automation.persona_extraction.migrate_baseline_to_stage_snapshot"` 无报错（新脚本）
- [ ] `jq empty schemas/character/stage_snapshot.schema.json` 通过（JSON 合法）
- [ ] `jsonschema -i <(echo '{}') schemas/character/stage_snapshot.schema.json` 至少能跑（不报 schema 自身错；instance 校验失败 OK）——验证 schema 自身合法
- [ ] `grep -rn "voice_rules\|behavior_rules\|boundaries\.json\|failure_modes\.json" automation/ docs/ ai_context/ schemas/` 残留 = 0（除 logs/change_logs/ 历史记录、本次 PRE log、迁移脚本 import 4 件套作迁移源、todo_list_archived.md 历史条目以外）
- [ ] `grep -rn "active_failure_modes" .` 残留 = 0（除本 PRE log）—— 旧设计名彻底清掉
- [ ] `git ls-files schemas/character/` 列表中 4 个废弃 schema 文件不存在
- [ ] todo_list.md 顶部 Index 与正文一致：BASELINE-DEPRECATE 在 In Progress 段
- [ ] 迁移脚本带 `--dry-run` 默认 + `--apply` 显式开关，未传 `--apply` 不动磁盘

## 执行偏差

执行中发现 PRE 计划清单遗漏的额外改动点，全部纳入本 /go：

1. **lane_output.py** `BASELINE_FILENAMES` 元组（5 文件）+ `baseline_paths()`
   docstring + `expected_lane_dirty_paths` docstring：缩为单元素
   `('identity.json',)`。partial-resume 行为保持不变（仅 reset
   identity.json 而非 5 文件）
2. **validator.py** `validate_baseline()` 移除 4 件套 warn 检查段
   （schema 已删，再检查会 NameError）
3. **orchestrator.py** Phase 2 baseline 完成后 4 件套存在性 print 块
   （L1037-1044）：删除
4. **prompt_builder.py** `build_baseline_prompt`（不在 PRE 清单上）：
   schemas 列表移除 voice_rules / behavior_rules / boundaries /
   failure_modes 4 个 schema 路径
5. **`_build_char_support_read_list`**（PRE 只列了 char_snapshot 同名
   函数）：同样需要清理 5 文件读取，否则 char_support lane 仍尝试
   读已删除文件
6. **character_support_extraction.md** prompt：rewrite "Baseline 修正"
   → "identity 修正"，删除 voice_rules / behavior_rules / boundaries
   / failure_modes 修正指令；字段命名对照表瘦身（4 件套字段名错误
   不再 relevant）；新增"不要重新创建已废弃文件"边界禁令
7. **docs/architecture/data_model.md** § 角色资产包 与
   **docs/architecture/system_overview.md** L137-138 / L319：未在 PRE
   清单中，含 4 件套文件清单 + 不变层描述，全部更新
8. **schemas/README.md** index 表：character/ 行原列出 9 个 schema
   名，移除 4 件套，stage_snapshot 标注内联字段
9. **docs/architecture/schema_reference.md**：character/ 子目录文件数
   从 9 改 5；移除 voice_rules / behavior_rules / boundaries /
   failure_modes 四节；stage_snapshot 节加 failure_modes 行；
   self-contained 契约段加 failure_modes required；底部 Baseline vs
   Runtime 加载规则表瘦身
10. **ai_context/conventions.md** § Data Separation：原"Baseline files
    = extraction anchors only"措辞过时——重写为"identity 是唯一
    character-level constant，其余内联进 stage_snapshot"；新增
    maxItems-aware truncation 规则项；删除 unified vocabulary 关于
    behavior_rules 的项（文件已删）
11. **ai_context/decisions.md**：在 11c 后追加 11d（4-piece deprecation
    详细决策）+ 11e（maxItems-aware truncation 规则）；27g 删除
    behavior_rules 重命名条款（文件已删）；13 改写不再提 character
    baseline drafts；11a 加 only-character-level-constant 注释
12. **ai_context/requirements.md** §3 Three Deep-Roleplay Goals：identity
    重定位为 character-level constant；§7 Information Layering：immutable
    层只剩 identity
13. **ai_context/current_status.md**：追加迁移说明段，提示 S001/S002
    现存快照需 migration 或重抽
14. **数据迁移脚本设计简化**：PRE 计划写"把 voice_rules /
    behavior_rules / boundaries 内容合并进 S001 stage_snapshot 种子"——
    实施时改为"仅迁移 failure_modes 内容到所有 stage_snapshots，其余
    3 件套直接 archive"。原因：voice / behavior / boundary 的内容已
    经存在于现有 stage_snapshot.{voice_state, behavior_state,
    boundary_state} 中，4 件套是冗余拷贝；只有 failure_modes 是真正
    需要迁移到新字段的数据。脚本默认 dry-run，`--apply` 显式开关
15. **todo_list.md In Progress 段位非空场景未在 PRE 计划**：本 todo
    移到 In Progress 槽位时，原段为空，所以走"直接放进单槽"路径，
    无需"先把当前那条 commit 完成或显式暂停回退到 Next 再启动新任务"

## 已落地变更

- 删除：4 个 schema 文件（voice_rules / behavior_rules / boundaries /
  failure_modes）
- 修改 schema：`schemas/character/stage_snapshot.schema.json`——
  description 重写、4 处 baseline 引用 description 修订、新增顶层
  `failure_modes` 字段（4 子类，子类 maxItems 与历史 schema 一致）、
  required 加入 failure_modes
- 修改 code：
  - `automation/persona_extraction/lane_output.py`（baseline 元组瘦身）
  - `automation/persona_extraction/validator.py`（去 4 件套 warn 段）
  - `automation/persona_extraction/orchestrator.py`（去 4 件套存在性
    检查 print）
  - `automation/persona_extraction/prompt_builder.py`（3 处：
    `build_baseline_prompt` schemas / `_build_char_snapshot_read_list`
    files / `_build_char_support_read_list` files；docstrings 同步）
- 新增 code：
  - `automation/persona_extraction/migrate_baseline_to_stage_snapshot.py`
    （一次性迁移，dry-run 默认）
- 修改 prompt：
  - `automation/prompt_templates/baseline_production.md`（删除 4 件套
    产出节，重写任务陈述）
  - `automation/prompt_templates/character_snapshot_extraction.md`
    （加文件角色定位段、自包含快照规则修订、failure_modes 字段说明、
    is_first_stage 推演指引、maxItems 裁剪规则统一段）
  - `automation/prompt_templates/character_support_extraction.md`
    （baseline 修正 → identity 修正，rewrite 多处）
- 修改 docs：
  - `docs/requirements.md`（§7 信息分层 ASCII / §7.1 不变层 / §9.2
    Baseline 描述 / §9.3 1+2N 表 lane 读列 / §9.4 生成规则 / §9.5
    产出物 / §11.3 输入裁剪 / §11.5 partial-resume 描述 / §12.9
    storage layout / Phase 2 ASCII 等 ~12 处）
  - `docs/architecture/extraction_workflow.md`（Phase 2 产出 / §6.2 char_snapshot 产出 / §6.3 char_support / 自包含规则 / partial-resume 描述 / Baseline 文件的角色 整段重写 / 阶段间增量规则）
  - `docs/architecture/schema_reference.md`（schema 计数 / 4 节删除 /
    stage_snapshot 描述 + sections 表加 failure_modes 行 + required
    列表加 failure_modes / Baseline vs Runtime 加载规则表瘦身）
  - `docs/architecture/data_model.md`（§角色资产包 文件清单瘦身 +
    stage_snapshot 描述加 failure_modes）
  - `docs/architecture/system_overview.md`（Phase 3 产出描述 / 启动加载层）
  - `schemas/README.md`（index 表 character/ 行）
- 修改 ai_context：
  - `architecture.md`（Runtime Load Formula step 2 / Self-Contained
    Stage Snapshots 段）
  - `conventions.md`（Data Separation 段重写）
  - `decisions.md`（11a 注释 / 新增 11d + 11e / 13 改写 / 27g 修订）
  - `requirements.md`（§3 / §7）
  - `current_status.md`（追加迁移说明）
- 修改 docs/todo_list.md：T-BASELINE-DEPRECATE 整条从 Next 移到
  In Progress 段，加开始时间 + 当前状态字段；索引段相应同步刷新
  （In Progress 0→1, Next 5→4, totals 不变）

## 与计划的差异

见 "执行偏差" 段——主要是 PRE 漏掉的代码 / 文档触点（lane_output、
validator、orchestrator、char_support 提示词、data_model、system_overview、
schema_reference、schemas/README、conventions、ai_context/requirements 等
~10 个文件），实施时全部纳入。迁移脚本范围简化（只迁 failure_modes
的内容）。

## 验证结果

- [x] `python -c "import automation.persona_extraction.prompt_builder"` 无报错 — 所有相关模块 import OK
- [x] `python -c "import automation.persona_extraction.migrate_baseline_to_stage_snapshot"` 无报错
- [x] `jq empty schemas/character/stage_snapshot.schema.json` 通过 — JSON 合法
- [x] `jsonschema.Draft202012Validator.check_schema(stage_snapshot)` 通过 — schema 自身合法
- [x] `grep -rn "voice_rules\|behavior_rules\|boundaries\.json\|failure_modes\.json" automation/ docs/ ai_context/ schemas/` 残留 = 0（除 logs/change_logs/、迁移脚本、todo_list.md In Progress 条目"上下文"段对原 4 件套的描述、ai_context/decisions.md 11d 决策正文中对废弃文件名的引用、stage_snapshot.schema.json 描述中对历史 schema 的来源标注）
- [x] `grep -rn "active_failure_modes" .` 残留 = 0（除本 PRE log）— 旧设计名彻底清掉
- [x] `git ls-files schemas/character/` 列表中 4 个废弃 schema 文件不存在
- [x] todo_list.md 顶部 Index 与正文一致：BASELINE-DEPRECATE 在 In Progress 段，Next 4 / In Progress 1
- [x] 迁移脚本带 `--dry-run` 默认 + `--apply` 显式开关，未传 `--apply` 不动磁盘（dry-run 实测 OK）

## Completed

- **Status**: DONE（仅就本 /go 的代码 / schema / prompt / docs / 迁移脚本写完 +
  静态验证作用域；runtime 验证 + 真实 work 迁移留作后续 /go 在
  extraction 分支执行）
- **Finished**: 2026-04-29 15:08:17 EDT
