# ingest_structure_mode_confidence_gate

- **Started**: 2026-05-01 14:29:02 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

会话上游讨论：用户在 [prompts/ingestion/原始资料规范化.md:51](../../prompts/ingestion/原始资料规范化.md#L51) 选中 `monolithic` 那行，问"这个 prompt 是不是最好先问一下用户，要选择哪种格式（monolithic / light_novel）比较好"。

讨论收敛：

- 现有 prompt 已有 `structure_mode` 字段 + `判定要点`（line 54），但是单次拍板，没有置信度回路 — LLM 误判成本很高（monolithic 当 light_novel 跑会切假章节，反向丢结构信号）
- 不全量改成"每次必问"：单卷大白话网络小说之类置信度自然 ≥ 0.9，让 LLM 直接走；只在判定不确定时才回路问用户
- 折中：让 LLM 先输出 `判定 + 依据 + 置信度`，置信度 ≥ 0.8 直接进；< 0.8 停手等用户拍板
- 阈值 0.8、"任意识别信号 = 不确定 → 置信度上限 0.7"硬约束、light_novel "卷分隔 + 卷数 ≥ 2 + 章内 sub-section" 三条都满足 — 三条均确认保留

用户也给了两种格式的口径定义，供 prompt 内文使用：

- monolithic = 一本小说，多个章节，没有卷，没有子章节
- light_novel = 多个卷，每卷多个章节，每章多个子章节（典型日式轻小说）

## 结论与决策

只改一份 prompt 文件 — `prompts/ingestion/原始资料规范化.md`。两处改动：

1. **task 步骤 1 和原 step 2 之间，插入新 step 2「判定 structure_mode」**：含
   - monolithic / light_novel 两种格式的口径定义（"是什么 / 不是什么 / 层级结构 / 典型形态"）
   - 识别信号清单（对各自的目录结构、文件名、TOC、正文样本的信号）
   - 判定输出格式（强制先输出 `判定 + 依据 + 置信度` 再决定后续动作）
   - 决策规则：≥ 0.8 直接进；< 0.8 停手等用户；不确定信号 → 置信度上限 0.7
2. **原 step 6（manifest.json 的 structure_mode 段）的"判定要点"删除**（迁到新 step 2，不再两处分散维护），保留 mode 语义说明 + 与 chapter_index 的一致性约束

原 step 2-8 顺延为 step 3-9。

**不改**：

- schema（`schemas/work/work_manifest.schema.json` 的 structure_mode enum / default 不动）
- 代码（automation/ingestion/* 不动 — 判定流程发生在 LLM agent 在该 prompt 下执行时，不是 Python 侧）
- chapter_index profile / validator 跨文件断言（不变）
- ai_context / docs（这是 prompt 内部的执行流程改进，没有架构 / 决策级影响）
- todo_list（T-INGEST-STRUCTURE-MODE 的 schema/code/prompt/ai_context/docs 完成项不动；本次只是同 prompt 内的判定流程加固）

## 计划动作清单

- file: `prompts/ingestion/原始资料规范化.md`
  - 在 task 步骤 1（line 41）和原 step 2（line 42）之间插入新 step 2「判定 structure_mode」（约 35-40 行）
  - 原 step 2-8 重编号为 step 3-9
  - 原 step 6（manifest 段，现 step 7）的 `structure_mode` 子项里删掉判定要点那条 bullet（line 54），改为引用新 step 2

## 验证标准

- [ ] 文件内 task 步骤编号严格连续（1 → 2 → 3 → ... → 9，不漏不重）
- [ ] `grep -n "判定要点"` 在 prompt 文件里只出现 0 或 1 次（迁移后只能在新 step 2 内有"判定输出"相关字样，不应在原 step 6 manifest 段还残留旧"判定要点"）
- [ ] `grep -n "置信度"` 在新 step 2 内出现，并且决策规则段含 `≥ 0.8` 和 `< 0.8` 两条分支
- [ ] 新 step 2 内 monolithic / light_novel 两块格式定义都包含：口径定义 + 识别信号 + 层级结构描述
- [ ] light_novel 识别信号块明确写"三条都满足才判 light_novel"
- [ ] manifest.json 段（现 step 7）保留 mode 语义 + 与 chapter_index 一致性约束，**不再含**判定要点 bullet
- [ ] 文件首尾无 markdown 解析破坏（代码块未提前关闭、列表层级正常）

## 执行偏差

无（计划与落地一致；Step 7 review 期间发现 3 处规范线漂移文案——均为一行级小修，按 /go skill 规则就地补齐，未额外建 todo）

<!-- POST 阶段填写 -->

## 已落地变更

- **`prompts/ingestion/原始资料规范化.md`**（核心改动）
  - line 41 → 79（task 步骤 2 新插）：新增 step 2「判定 `structure_mode`」，含
    - `monolithic` 口径定义（单层 / 单卷 / 无子章节）+ 识别信号 3 条
    - `light_novel` 口径定义（三层 / 多卷 / 每章再切子章节）+ 识别信号 3 条
      （明确"三条都满足才判 light_novel"）
    - 判定输出格式（强制实质工作前先输出 `判定 + 依据 + 置信度`，按结构逐行写）
    - 决策规则：≥ 0.8 直接填、< 0.8 停手等用户、任意识别信号"不确定" → 置信度
      上限 0.7
  - 原 task 步骤 2-8 顺延 → 现 3-9（line 81-119）
  - 现 step 7 manifest 段（line 90-94）的 `structure_mode` 子项：删掉旧
    "判定要点" bullet（迁到新 step 2 单源），保留 mode 语义说明 + 与 chapter_index
    一致性约束
  - 现 step 9 自检段（line 119）"退回步骤 6" → "退回步骤 7"（同步顺延）
- **`docs/todo_list.md`**
  - line 15 Index 表：T-INGEST-STRUCTURE-MODE 行 Updated 列 `—` → `2026-05-01`
  - 条目 body（line 427+）：加 `**更新时间**：2026-05-01 14:29 EDT`；
    "已落地" prompt bullet 追加本次 14:29 update 描述
- **`ai_context/decisions.md`** §27j（Step 7 漂移修复）
  - "Identification of structure_mode ... deferred to a separate todo;
    for now normalization writes it manually" → 改写为"LLM-driven inside
    the normalization prompt, confidence-gate ≥ 0.8 / < 0.8 stops for
    human-confirm, 不确定 信号 caps at 0.7"
- **`ai_context/conventions.md`** Cross-File Alignment 表（Step 7 漂移修复）
  - `structure_mode` 行 prompt 描述 `(manual fill instructions + title
    derivation)` → 改为 `(task step 2 LLM judgment with confidence gate
    ≥ 0.8 directly fills / < 0.8 stops for human-confirm; manifest fill
    instructions + title derivation)`
- **`docs/architecture/schema_reference.md`** §`work_manifest.json`（Step 7 漂移修复）
  - `**生成时机**：... structure_mode 手填` → 改为"由 task 步骤 2 LLM 判定：
    先输出 判定 + 依据 + 置信度，置信度 ≥ 0.8 直接填、< 0.8 停手等用户确认"

不动：

- 所有 schema（structure_mode enum / default 不变）
- 所有 Python 代码（validator / orchestrator / manifests 在 manifest 已填后跑，与
  judgement 流程解耦）
- chapter_index profile / `oneOf` 跨文件断言 / phase 0/1 分支调度逻辑

## 与计划的差异

PRE 计划只列了 prompt 文件 + 一次性可能的 todo_list 维护。Step 7 review 期间
另外发现 3 处规范线旧措辞（decisions.md 27j 说"deferred / manually" /
conventions.md 表说"manual fill" / schema_reference.md 说"手填"）—— 都是
本次 prompt 改动的语义对齐尾巴，已就地修齐，未升级为新 todo（按 /go Step 7
"一行能修的小问题 → 发现即修"规则处理）。

## 验证结果

- [x] 文件内 task 步骤编号严格连续（1 → 2 → 3 → ... → 9，不漏不重）— 检查通过
      （`grep -nE '^[0-9]+\. '` 输出 line 41 `1` / 42 `2` / 81 `3` / 82 `4` /
      83 `5` / 84 `6` / 85 `7` / 118 `8` / 119 `9`）
- [x] `grep -n "判定要点"` 0 残留 — 通过
- [x] `grep -n "置信度"` 在新 step 2 内出现 + 决策规则 ≥ 0.8 / < 0.8 双分支齐全
      — 通过（line 42 / 70 / 75 / 78 / 79 / 80 / 93）
- [x] 新 step 2 内 monolithic / light_novel 两块格式定义都有口径 + 识别信号 +
      层级结构 — 通过（line 46-55 monolithic / line 57-66 light_novel）
- [x] light_novel 识别信号块明确"三条都满足才判 light_novel" — 通过（line 63）
- [x] manifest.json 段（现 step 7）保留 mode 语义 + chapter_index 一致性约束、
      不再含判定要点 — 通过（line 90-94，line 93 改为引用 step 2 判定流程）
- [x] 文件首尾 markdown 解析未破坏（外层 ```text fence open line 14 / close
      line 156 单对，无嵌套 fence；新 step 2 判定输出模板用 7-space 缩进块而非
      内嵌 fence，保完整性）

## Completed

- **Status**: DONE
- **Finished**: 2026-05-01 14:36:55 EDT
