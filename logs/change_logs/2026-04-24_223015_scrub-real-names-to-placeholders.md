# scrub-real-names-to-placeholders

- **Started**: 2026-04-24 22:30:15 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

用户：把 git tracked 文件里所有真实书名 / 角色名 / 真实地名替换为通用占位符，
**包括 logs/change_logs/ 与 logs/review_reports/**——本次明示豁免不再适用。
本次 PRE / POST log 自身也按占位符书写，不出现任何真实名称。

跨 48 个 tracked 文件（清单见下表"计划动作清单"），含：

- 1 项作品（4 字符书名 + 4 字符简写）
- 2 项主要角色（3 字 + 2 字）
- 1 项重要人物身份（4 字含称号）
- 9 项候选角色名（仅在初期识别 log 中出现）
- 2 项地名（各 2 字）
- 1 项阶段别名（5 字）

## 结论与决策

**全字串替换**，按"长串先于短串"顺序避免吞字：

| 类型 | 占位符 |
|---|---|
| 主作品（全名） | `<work_id>` |
| 主作品（简写） | `<work_id>` |
| 角色 a | `<character_a>` |
| 角色 b | `<character_b>` |
| 重要人物身份（含称号） | `<character_d>` |
| 重要人物身份（裸标题） | `<character_d>` |
| 候选角色 1..9 | `<character_c1>` .. `<character_c9>` |
| 地点 a | `<location_a>` |
| 地点 b | `<location_b>` |
| 阶段别名 | `<phase_alias>` |

通用 genre 术语（修真宗门 / 渡劫 / 结丹 / 师父 / 盟友 等）属类型词，
**不在替换范围**——它们不是真实剧情元素，是叙事类型默认词汇。

文件名 / 路径段不替换（git history 已固化），仅替换文件**内容**。

实际替换字串内部使用 sed `-i` 批处理，避免在版本控制 log 中泄漏源字串；
本 log 与 commit message 全部用占位符书写。

## 计划动作清单

- 对 48 个 tracked 文件应用 sed 替换链（顺序：长串先于短串），分类：
  - 非豁免目录 3 文件：
    - `automation/persona_extraction/validator.py`（角色 a docstring 示例）
    - `automation/prompt_templates/analysis.md`（地点 a / b 示例）
    - `docs/todo_list.md`（作品全名 3 处）
  - `logs/change_logs/` 41 文件
  - `logs/review_reports/` 4 文件
- 替换后 `git grep` 验证全仓 tracked 0 命中（除 `<...>` 占位符自身）

## 验证标准

- [ ] `git grep -nE` 对本次替换映射表中所有源字串在 HEAD 上 = 0 命中（命令在 commit 前一次性执行，不入版本控制 log）
- [ ] `python3 -c "from automation.persona_extraction.validator import *; print('OK')"` import 成功（替换的是 docstring 示例，不影响代码）
- [ ] commit 后 main / library / extraction merge 无冲突
- [ ] 本 log 自身不含任何真实名（self-check）

## 执行偏差

执行中两个中文文件名的 log 因 `git grep -l` 输出 escape 序列、shell 无法解析为
真实路径而漏掉首批 sed；改用直接路径名补跑了一次 sed，已纳入。POST log 内
PRE 验证标准里原本列出的 grep 正则又包含了源字串本身，发现后即改为"按本次
替换映射表"的抽象表述，避免 log 自身泄漏。

<!-- POST 阶段填写 -->

## 已落地变更

48 个 tracked 文件全部 sed 应用了"长串先于短串"的 18 项替换链：

- 非豁免目录 3 文件：
  - `automation/persona_extraction/validator.py`：docstring 示例占位化
  - `automation/prompt_templates/analysis.md`：地名示例占位化
  - `docs/todo_list.md`：3 处 `<work_id>` 路径占位化
- `logs/change_logs/` 41 文件：含 2 份中文文件名的（直接路径补跑）
- `logs/review_reports/` 4 文件

替换映射（占位符表）：
- 主作品全名 / 简写 → `<work_id>`
- 角色 a → `<character_a>`、角色 b → `<character_b>`
- 重要人物身份（含称号 / 裸标题）→ `<character_d>`
- 候选角色 1..9 → `<character_c1>` .. `<character_c9>`
- 地点 a → `<location_a>`、地点 b → `<location_b>`
- 阶段别名 → `<phase_alias>`

未替换：通用 genre 术语（修真宗门 / 渡劫 / 结丹 / 师父 / 盟友），保留作叙事
类型默认词汇。

## 与计划的差异

PRE 计划清单覆盖 48 个文件全部命中，外加 PRE 自身验证标准行的措辞调整（避
免 log 泄漏映射表源字串），已在"执行偏差"段记录。

## 验证结果

- [x] `git grep -nE` 对替换映射表所有源字串在 HEAD 上 = 0 命中
- [x] `python3 -c "from automation.persona_extraction.validator import *"` 成功（docstring 改动不影响代码）
- [x] 本 PRE 自身复检：再 grep 0 命中
- [ ] commit 后 main / library / extraction merge 无冲突（待 Step 9）

## Completed

- **Status**: DONE
- **Finished**: 2026-04-24 22:34:06 EDT
