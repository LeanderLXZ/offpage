# phase01_chapter_id_unify

- **Started**: 2026-05-01 01:03:31 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

接续 T-CHAPTER-MULTIVOL（已完成于 commit `3fc1629`，logs/change_logs/
2026-04-30_215840_chapter_id_multivol.md）。/post-check 复查（log 末段
REVIEWED-FAIL）暴露下游 phase 0/1 系列**整组未跟进**新 chapter_id
命名 `^C[0-9]{4}$`：

- `schemas/analysis/chapter_summary_chunk.schema.json` `chapter` /
  `chapters` 字段仍 pattern `^\d{4}$` / `^\d{4}-\d{4}$`
- `schemas/analysis/stage_plan.schema.json` `chapters` 字段仍
  pattern `^\d{4}-\d{4}$`
- `automation/prompt_templates/summarization.md` 描述 + JSON
  example 用 `0001`
- `automation/prompt_templates/analysis.md` example `chapters:
  "0001-0010"`
- `automation/persona_extraction/prompt_builder.py` 4 处
  `f"chapters/{ch:04d}.txt"`
- `automation/persona_extraction/scene_archive.py`
  `_build_chapter_to_stage_map` 用 `{ch:04d}` 作 dict key
- `docs/requirements.md:2396` 文档描述 `"0001-0011"` 字符串

**实际工程效果**：<character> `chapters/` 已迁移到 `C####.txt`、
`chapter_index.json` 的 `chapter_id` 已是 `C####`，但下游代码用
`f"chapters/{ch:04d}.txt"` 拼路径（找不到文件）+ `chapter_to_stage`
dict key 是裸数字（与 `C####` lookup 100% miss）。立即跑 phase 0/1/3/4
任意一个会 broken。

用户拍板 **选项 A：全部统一为 `C####`**（推荐方案）。

## 结论与决策

**做**（按用户拍板的选项 A + 验证标准模板改进）：

1. **schemas/analysis/chapter_summary_chunk.schema.json**：
   - `chapters` 字段（chunk 范围）pattern `^\d{4}-\d{4}$` →
     `^C[0-9]{4}-C[0-9]{4}$`，描述 `0001-0025` → `C0001-C0025`
   - `chapter` 字段（chunk 内每章）pattern `^\d{4}$` →
     `^C[0-9]{4}$`，描述 `0001` → `C0001`
2. **schemas/analysis/stage_plan.schema.json**：
   - `chapters` 字段 pattern `^\d{4}-\d{4}$` →
     `^C[0-9]{4}-C[0-9]{4}$`，描述同步
3. **automation/prompt_templates/summarization.md**：
   - 步骤 2 描述 `chapter: 章节编号（4 位零填充，如 "0001"）` →
     `C + 4 位零填充，如 "C0001"`
   - 步骤 3 JSON example `"chapters": "{start_chapter}-{end_chapter}"`
     与 `"chapter": "0001"` 同步改 C 前缀（看模板变量是否在
     prompt_builder 侧已是 `C####` 形式；如裸数字则 prompt_builder
     一并改）
4. **automation/prompt_templates/analysis.md**：
   - example `"chapters": "0001-0010"` → `"C0001-C0010"`
5. **automation/persona_extraction/prompt_builder.py**：
   - 4 处 `f"chapters/{ch:04d}.txt"` →
     `f"chapters/C{ch:04d}.txt"`（行号 77, 432, 473, 512）
   - `_parse_chapter_range(stage.chapters)` 让其支持 `C####-C####`
     格式输入（去前缀后转 int）
   - `format_chapter_range_for_prompt` / 给 LLM 传的 `start_chapter`
     / `end_chapter` 模板变量同步改 C 前缀字符串
6. **automation/persona_extraction/scene_archive.py**：
   - `_build_chapter_to_stage_map` 中 `mapping[f"{ch:04d}"]` →
     `mapping[f"C{ch:04d}"]`
   - 同函数中 `ch_range.split("-")` + `int(parts[0])` 改为支持
     `C####-C####`（剥前缀 `C` 后 int）
7. **docs/requirements.md:2396**：
   - `"0001-0011"` → `"C0001-C0011"`
8. **PRE 验证标准模板改进**（结构性增强，写到 `ai_context/conventions.md`）：
   - 在 `## Cross-File Alignment` 后或 `## Naming and Identifiers`
     段加新小节 **"Identifier rename — multi-form scan checklist"**，
     列出 identifier 命名变更应同时 grep 的 4 种形态：
     1. 旧前缀字面（如 `chapter[0-9]{4}`）
     2. 裸数字 4 位 pattern（如 `^\\d{4}$` schema pattern）
     3. Python f-string 格式（如 `{:04d}` / `{ch:04d}`）
     4. 文件名格式（如 `0001.txt`）
   - 这样下次 identifier rename 的 PRE 验证标准能直接复用，避免本
     轮"grep 残留 0 实际不充分"的失败模式

**不做**（push back / 范围收敛）：

- ❌ 不改运行时 simulation 侧（chapter_id 不在 simulation 数据流，
  本轮无证据需要触及）
- ❌ 不动 sources/ 既有产物（<character> chapters/ 上轮 /go 已完成 C####
  迁移）
- ❌ 不写迁移脚本（works/ 当前空，无 phase 0/1 产物需回填；后续若
  有产物只需重跑）
- ❌ 不抽象出"identifier 通用迁移工具"（N+2，等下次真有第三种
  identifier rename 再做）

## 计划动作清单

- file: `schemas/analysis/chapter_summary_chunk.schema.json` →
  `chapters` + `chapter` 字段 pattern + 描述同步 C 前缀
- file: `schemas/analysis/stage_plan.schema.json` → `chapters` 字段
  pattern + 描述同步 C 前缀
- file: `automation/prompt_templates/summarization.md` → 描述
  `0001` 例子改 C0001；JSON example 同步
- file: `automation/prompt_templates/analysis.md` → example
  `0001-0010` → `C0001-C0010`
- file: `automation/persona_extraction/prompt_builder.py` → 4 处
  `f"chapters/{ch:04d}.txt"` 改 `C{ch:04d}.txt`；`_parse_chapter_range`
  支持 `C####-C####`；模板变量 `start_chapter` / `end_chapter` 改
  C 前缀字符串
- file: `automation/persona_extraction/scene_archive.py` →
  `_build_chapter_to_stage_map` mapping key 改 `C####`，
  `ch_range.split("-")` 后剥 C 前缀再 int
- file: `docs/requirements.md:2396` → `"0001-0011"` → `"C0001-C0011"`
- file: `ai_context/conventions.md` → 新增 "Identifier rename
  multi-form scan checklist" 小节
- file: `ai_context/decisions.md` → #10a 末尾追加一句指向新 checklist
  小节，标记本轮跟进

## 验证标准

- [ ] schema 自检：`jsonschema.Draft202012Validator.check_schema`
  对 chapter_summary_chunk + stage_plan 通过
- [ ] schema 边界：bad `chapter: "0001"`（裸数字）被新 pattern
  拒；good `chapter: "C0001"` 通过；bad `chapters: "0001-0010"` 被
  拒；good `chapters: "C0001-C0010"` 通过
- [ ] code import 无报错：`python3 -c "import
  automation.persona_extraction.prompt_builder,
  automation.persona_extraction.scene_archive"` exit 0
- [ ] `_parse_chapter_range("C0001-C0010")` 返回 `(1, 10)`；
  `_build_chapter_to_stage_map` 用 mock stage_plan
  `chapters="C0001-C0003"` 产 `{"C0001": "S001", "C0002": "S001",
  "C0003": "S001"}`
- [ ] 全库 **多形态** grep 残留为 0，覆盖 4 种形态：
  - 旧字面 `chapter[0-9]{4}` （/go Step 7 用过的）
  - 裸数字 schema pattern：`"\^\\\\d{4}\$"` / `"\^\\\\d{4}-\\\\d{4}\$"`
  - Python f-string：`f"chapters/{ch:04d}\.txt"` /
    `mapping\[f"\{ch:04d\}"\]`
  - 文件名 / example 字面：`chapters/0001\.txt` / `"0001-0010"`
  - 排除：sources/、users/、works/、logs/change_logs/、
    todo_list_archived（可包含历史快照）
- [ ] <character> `chapter_index.json` 经 chapter_index schema 仍校验通过
  （本轮不动 ingestion schema，只是回归确认）
- [ ] mock 跑 `_build_chapter_to_stage_map`：构造一份小型
  stage_plan.json fixture（in-memory dict 即可），传入 chapter_id
  `C0001` 能正确 lookup 到 stage_id
- [ ] `python3 -m automation.ingestion.validator <work_id>`
  仍通过（regression）

## 执行偏差

- **Step 5 grep 多路径静默失败的诊断**：本轮 PRE 验证标准里"4
  形态多路径 grep" 在 Step 5 输出"全 clean"，但 Step 7 风险线
  缩到单路径再扫时抓到 5 处遗漏。复现：相同 grep `--exclude-dir`
  + alternation pattern + 6 路径 `$SCAN_PATHS` → 0 hit；
  缩到 2 路径 → 5 hits。原因疑似 6 路径之一（`simulation/` 或
  `prompts/`）遇到符号链接 / 权限问题让 grep 整体静默退出。
  **教训写进 conventions §Cross-File Alignment**："Identifier
  rename multi-form scan checklist" 应该 per-dir per-pattern 跑，
  不要把 6 路径塞成一个 grep 调用。本次复扫已用 per-dir 形式
  确认 0 残留。
- **Step 7 补修 6 处 PRE 计划清单未列出的连带文件**（同 phase 1
  / phase 0 family，按 "发现即修" 原则当场修）：
  - `automation/repair_agent/_smoke_triage.py:77,515`：smoke
    fixture `"chapters": "0001-0001"` → `"C0001-C0001"`
  - `automation/persona_extraction/progress.py:210,406`：dataclass
    doc comment `# e.g. "0001-0025"` / `"0001-0010"` → C 前缀
  - `automation/persona_extraction/scene_archive.py:832`：函数
    docstring `format: "0001-0011"` → `"C0001-C0011"`
  - `schemas/analysis/world_overview.schema.json:97`：
    `world_lines[].chapter_range` pattern `^\\d{4}-\\d{4}$` →
    `^C[0-9]{4}-C[0-9]{4}$`，描述同步（PRE 漏列的 phase 1 schema，
    与 stage_plan 同 LLM 调用产出，命名应同步）

## 已落地变更

- `schemas/analysis/chapter_summary_chunk.schema.json`：
  - `chapters`（chunk 范围）pattern `^\d{4}-\d{4}$` →
    `^C[0-9]{4}-C[0-9]{4}$`，描述 `0001-0025` → `C0001-C0025`
  - `chapter`（chunk 内每章）pattern `^\d{4}$` → `^C[0-9]{4}$`，
    描述 `0001` → `C0001`，加注"与 chapter_id 一致"
- `schemas/analysis/stage_plan.schema.json`：
  - `chapters` pattern `^\d{4}-\d{4}$` → `^C[0-9]{4}-C[0-9]{4}$`，
    描述同步
- `schemas/analysis/world_overview.schema.json`（Step 7 补修）：
  - `world_lines[].chapter_range` pattern → `^C[0-9]{4}-C[0-9]{4}$`，
    描述同步
- `automation/prompt_templates/summarization.md`：
  - 步骤 2 `chapter` 描述 `0001` → `C0001`，加注"与 chapter_id 一致"
  - 步骤 3 JSON example `"chapter": "0001"` → `"C0001"`
  - 顶部 prose 第 7 行去掉冗余 "第..章" 包裹（C 前缀 ID 自身已
    清晰），第 14 行同
- `automation/prompt_templates/analysis.md`：
  - example `"chapters": "0001-0010"` → `"C0001-C0010"`
- `automation/persona_extraction/prompt_builder.py`：
  - L77 + L432/473/513 4 处 `f"chapters/{ch:04d}.txt"` →
    `f"chapters/C{ch:04d}.txt"`
  - L98-99 summarization context vars `start_chapter` / `end_chapter`
    从 `f"{ch:04d}"` 改 `f"C{ch:04d}"`
  - `_parse_chapter_range` 兼容 `C####-C####` 与 `C####` 单值，
    通过 `lstrip("C")` 后 `int()`
- `automation/persona_extraction/scene_archive.py`：
  - `_build_chapter_to_stage_map` 解析 `ch_range.split("-")`
    后 `lstrip("C")`；mapping key `f"{ch:04d}"` → `f"C{ch:04d}"`
  - `_collect_chapter_ids` (L832) docstring `"0001-0011"` →
    `"C0001-C0011"`（Step 7 补修）
- `automation/persona_extraction/progress.py`（Step 7 补修）：
  - `ChunkEntry.chapters` doc comment 改 C 前缀
  - `StageEntry.chapters` doc comment 改 C 前缀
- `automation/repair_agent/_smoke_triage.py`（Step 7 补修）：
  - 2 处 smoke fixture `"chapters": "0001-0001"` → `"C0001-C0001"`
- `docs/requirements.md:2396`：
  - `"0001-0011"` → `"C0001-C0011"`，"chapter → stage_id" 改
    "chapter_id → stage_id"
- `docs/architecture/schema_reference.md`：
  - `chapter_summary_chunk` 关键字段加 chapter / chapters 新 pattern
  - `stage_plan` 关键字段 `chapters` 改 `^C[0-9]{4}-C[0-9]{4}$`
- `ai_context/conventions.md`：
  - 在 §Cross-File Alignment 后新增小节 "Identifier rename —
    multi-form scan checklist"，列出 4 形态（旧前缀字面 / 裸数字
    schema pattern / Python f-string / 文件名 example）+ 排除目录
    + 写法约束（应当 per-dir per-pattern 而非塞成一个 grep）
- `ai_context/decisions.md` #10a：
  - 末尾追加 phase 0/1 schema + prompt + code 端到端使用 C 前缀
    的承诺，以及 4 形态 checklist 引用
  - 文末 → 行加 schemas/analysis/{chapter_summary_chunk,stage_plan}
    指针

## 与计划的差异

- PRE 计划清单未列出 4 个文件 + 1 个 schema，Step 7 review 期补修
  （详见"执行偏差"段）。补修动作均按"发现即修"原则就地完成，
  不超出 PRE 决策的"phase 0/1 全部统一为 C####"范围。
- PRE 验证标准里"4 形态多路径 grep" 在 Step 5 因 shell 多路径
  展开 bug 静默失败；后续在 conventions.md 新 checklist 小节加
  了"per-dir per-pattern"约束，避免本次模式被复用。

## 验证结果

- [x] schema 自检 OK：4 个 schema（chapter_summary_chunk +
  stage_plan + world_overview + chapter_index）通过
  `Draft202012Validator.check_schema`
- [x] schema 边界用例：good `C0001` / `C0001-C0010` 通过；bad
  `0001` / `0001-0010` 被拒（带 pattern 不匹配错误）
- [x] code import OK：`prompt_builder` / `scene_archive` /
  `progress` / `_smoke_triage` 全部 import 无错
- [x] `_parse_chapter_range("C0001-C0010")` → `(1, 10)` ✓；
  `("C0007")` → `(7, 7)` ✓
- [x] `_build_chapter_to_stage_map` mock fixture：
  `chapters="C0001-C0003"` 产 `{"C0001": "S001", "C0002": "S001",
  "C0003": "S001"}` ✓；旧格式 `0001` lookup MISS（正确）
- [x] 4 形态全库残留 0（per-dir per-pattern 复扫；唯一"hit" 是
  conventions.md 的 checklist 描述自身，合规）
- [x] <character> `chapter_index.json` 经 chapter_index schema 仍通过
  （regression）
- [x] `python3 -m automation.ingestion.validator
  <work_id>`：PASSED, 0 errors / 0 warnings

## Completed

- **Status**: DONE
- **Finished**: 2026-05-01 01:13:20 EDT
