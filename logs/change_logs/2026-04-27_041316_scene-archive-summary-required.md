# scene-archive-summary-required

- **Started**: 2026-04-27 04:13:16 EDT
- **Branch**: main (worktree at /home/leander/Leander/offpage-main; primary checkout stays on `extraction/我和女帝的九世孽缘`)
- **Status**: PRE

## 背景 / 触发

落地 todo `T-SCENE-ARCHIVE-SUMMARY-REQUIRED`（立即执行段）。用户与 Claude 讨论后明确：仅加 required，不动 bound（minLength / maxLength / pattern 是否瘦身另案讨论）。

事实链（已验证）：

- `schemas/runtime/scene_archive_entry.schema.json` 当前 `required` 仅 `[scene_id, stage_id, chapter, characters_present, full_text]` —— **summary / time / location 缺席**
- 上游 `schemas/analysis/scene_split.schema.json` 已 require 这三个字段；summary 还有 minLength: 50 强约束，time / location 允许空字符串但键必出现
- 中间环节 `automation/persona_extraction/scene_archive.py:583-592` 是程序级 1:1 直拷（零 LLM）
- 结论：上游已 require + 程序保证不丢字段 → 下游升 required 100% 安全

## 结论与决策

### 改动范围

- **加 required**：`summary` / `time` / `location` 三个字段进 `required` 数组
- **bound 不动**：保留 summary 的 minLength/maxLength、scene_id/stage_id 的 pattern；瘦身另案讨论
- 不改其他 schema、prompt、代码

### Cross-File Alignment 评估

按 `ai_context/conventions.md` 表，`schemas/**/*.schema.json` 改动对应：

- `docs/architecture/schema_reference.md` —— 已声明"具体数字以 schema 为准"，且现有描述文本（runtime/scene_archive_entry 段）已经在描述当前契约。required 列表升级是契约硬化，描述无需变。**verify-only**
- `schemas/README.md` —— 不复述具体字段，无需改
- prompt templates —— scene_archive 不由 LLM 产出，prompt 无相关引用
- `automation/persona_extraction/validator.py` —— 动态读 schema，无硬编码

无下游联动文件需要改。

## 计划动作清单

1. `schemas/runtime/scene_archive_entry.schema.json:7-13` `required` 数组追加 `"summary"` / `"time"` / `"location"`
2. `docs/todo_list.md` 删除 `T-SCENE-ARCHIVE-SUMMARY-REQUIRED` 整条；按规则从「下一步」首条提升一条到「立即执行」
3. （Step 5）确认 schema_reference.md / schemas/README.md 无需联动改

## 验证标准

- [ ] `schemas/runtime/scene_archive_entry.schema.json` 通过 `Draft202012Validator.check_schema`
- [ ] `required` 数组实际含 8 个字段（5 旧 + 3 新）
- [ ] `docs/todo_list.md` 不再含 `T-SCENE-ARCHIVE-SUMMARY-REQUIRED` 字样
- [ ] 立即执行段非空（提升首条 from 下一步）

## 执行偏差

1. **发现 main worktree todo_list 仍是清理前版本**：上一轮 `/post-check` (`def093e`) 与 `/go todo-list-cleanup` (`3615f2a`) 都只 commit 在 extraction 分支，未同步进 main，违反"先进 main"硬规则。本轮先 cherry-pick 这两个 commit 到 main worktree（结果 commit `cb7c98d` + `9a97a22`），再做本任务编辑。
2. **删 T-SCENE-ARCHIVE-SUMMARY-REQUIRED 时误删 `## 下一步` 段标题**：补回 `## 下一步` 标题以保持三段结构。最终 T-CHAR-SNAPSHOT-13-DIM-VERIFY 提升到「立即执行」（按规则首条提升）；T-PHASE35-IMPORTANCE-AWARE 留在「下一步」首条。

<!-- POST 阶段填写 -->

## 已落地变更

1. [schemas/runtime/scene_archive_entry.schema.json:7-15](schemas/runtime/scene_archive_entry.schema.json#L7-L15) `required` 数组从 5 字段升到 8 字段（新增 `time` / `location` / `summary`）
2. [docs/todo_list.md](docs/todo_list.md)：
   - 删除「立即执行」段的 `T-SCENE-ARCHIVE-SUMMARY-REQUIRED` 整条
   - 提升 `T-CHAR-SNAPSHOT-13-DIM-VERIFY` 从「下一步」到「立即执行」首条
   - 维持 `T-PHASE35-IMPORTANCE-AWARE` 为「下一步」首条
3. cherry-pick 到 main：`cb7c98d`（todo-list cleanup）+ `9a97a22`（lt-le-bound-fix /post-check 回写）—— 修补先前漏同步

## 与计划的差异

- PRE 计划清单 2 条全数完成
- 新增 cherry-pick 步骤（执行偏差 1）
- 新增 `## 下一步` 标题恢复（执行偏差 2，纯结构修复）

## 验证结果

- [x] `schemas/runtime/scene_archive_entry.schema.json` 通过 `Draft202012Validator.check_schema`
- [x] `required` 数组实际含 8 个字段（`scene_id` / `stage_id` / `chapter` / `time` / `location` / `characters_present` / `summary` / `full_text`）
- [x] smoke test：缺 `time` 的 entry 触发 `'time' is a required property`；完整有效 entry（summary 60 字）0 errors
- [x] `docs/todo_list.md` 不再含 `T-SCENE-ARCHIVE-SUMMARY-REQUIRED` 字样（grep 0 命中）
- [x] 立即执行段非空：`T-CHAR-SNAPSHOT-13-DIM-VERIFY`

## Completed

- **Status**: DONE
- **Finished**: 2026-04-27 04:16:51 EDT
