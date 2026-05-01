# phase01_followup_repair_agent

- **Started**: 2026-05-01 02:02:15 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

接续 phase01_chapter_id_unify（commits `4a65837` + `6d98fe1`）。
/post-check 复查（commit `c2d780a`，REVIEWED-FAIL）抓到 phase01 漏点：
PRE 验证标准里"4 形态多路径 grep" 只 grep 自己刚改的具体变量名
`{ch:04d}`，未跑 conventions.md checklist 推荐的**通用 `\{:04d\}`**
形态——结果同 family 不同变量名（`chapter_num`、`start`、`end`）的代码
全部漏检：

- `automation/persona_extraction/scene_archive.py::_collect_chapters`
  L843-846：函数体仍 `int(parts[0])` 不去 C 前缀，输出 `f"{ch:04d}"`
  bare numeric——与同文件 `_build_chapter_to_stage_map`（已修）成
  孪生函数；docstring L832 已是 `"C0001-C0011"` 与函数体直接矛盾。
  phase 4 启动会立即 ValueError。
- `automation/repair_agent/context_retriever.py::_load_chapter`
  L230-248：3 个 fallback pattern `{:04d}.txt` / `{}.txt` /
  `chapter_{:04d}.txt` 没一个匹配 `C0001.txt`。silent 全 miss。
- `automation/repair_agent/context_retriever.py::_read_chapter_summary`
  L197-227：(a) per-file pattern `{:04d}.json` 不匹配；(b) chunked
  fallback `entry.get("chapter") == chapter_num`（int 与新 schema
  强制 string `"C0001"` 比），永远 False。
- `automation/repair_agent/context_retriever.py::_get_stage_chapters`
  L143：regex `^(\d+)\s*-\s*(\d+)$` 不匹配 `C0001-C0010`，返回 []；
  list-form fallback `int(chapters[0])` 也会 ValueError。
- `automation/persona_extraction/orchestrator.py:747`：ChunkEntry
  chapters 字段写入 `f"{start:04d}-{end:04d}"` 是 bare numeric，与
  LLM 输出（schema-validated）`C0001-C0010` 形态分裂；6 处日志
  f-string（L527/780/790/803/858/862）也仍 bare numeric——一致性
  + 日志可读性问题。
- `ai_context/conventions.md` "Identifier rename multi-form scan
  checklist" 第 3 项当前列了 `\{ch:04d\}` / `\{:04d\}` 两种但没强调
  "必跑通用 regex `\{[a-z_]+:04d\}`、不能单独用具体变量名"——本轮
  Step 5 自己就栽在这。

用户拍板：**方案 A**——立刻补上述 5 处 missed updates，外加 checklist
模板硬化。works/ 当前空、无产物回填。

## 结论与决策

**做**：

1. **`automation/persona_extraction/scene_archive.py::_collect_chapters`**
   （L843-846）：补 `lstrip("C")` 解析、输出改 `f"C{ch:04d}"`，与同文件
   `_build_chapter_to_stage_map`（L494-498）逻辑完全对齐。
2. **`automation/repair_agent/context_retriever.py::_load_chapter`**
   （L230-248）：3 个 fallback pattern 头部插入 `f"C{chapter_num:04d}.txt"`
   作为优先匹配，旧 3 个 pattern 保留作 backward-compat fallback（旧
   产物兼容；works/ 当前空所以不会真的命中旧 pattern，但保留兜底）。
3. **`automation/repair_agent/context_retriever.py::_read_chapter_summary`**
   （L197-227）：
   (a) per-file pattern 头部插入 `f"C{chapter_num:04d}.json"`；
   (b) chunked fallback 比较改为：先用 `entry.get("chapter")` 拿 string，
       `lstrip("C")` 后 `int()` 再与 `chapter_num` int 比；同时支持
       `entry.get("chapter_number")` 旧字段（int 直比）作 backward-compat。
4. **`automation/repair_agent/context_retriever.py::_get_stage_chapters`**
   （L143）：regex 改 `^C?(\d+)\s*-\s*C?(\d+)$` 兼容旧新格式；
   list-form fallback `int(chapters[0])` 加 `lstrip("C")` 兜底。
5. **`automation/persona_extraction/orchestrator.py:747`**：ChunkEntry
   chapters 写入改 `f"C{start:04d}-C{end:04d}"`（与 LLM 输出 schema 对齐）。
   6 处日志 f-string（L527/780/790/803/858/862）同步加 C 前缀（一致性
   + 日志读起来与文档/数据一致）。
6. **`ai_context/conventions.md` Identifier rename checklist**：
   第 3 项 "Python f-string format spec" 强化措辞——
   - 必跑形态：通用 regex `\{[a-z_]+:04d\}`（覆盖任意变量名）
   - 禁止单独用具体变量名（如 `\{ch:04d\}` / `\{chapter_num:04d\}`）
     作为唯一 grep 形态——否则同 family 不同变量名的代码会漏

**不做**（push back）：

- ❌ 不动 `_chunk_covers_range`（prompt_builder.py:558-575）的 doc
  comment 与实际产物不一致问题——这是 phase01 之前就存在的死代码，
  当前 chunk 文件名是 `chunk_{chunk_index:03d}.json`（L81）不是
  doc 说的 `chunk_NNNN_NNNN.json`，与本次 chapter_id 命名无关，单独立项
- ❌ 不在 PRE 验证标准模板里加"property-based test"（用户 Open
  Question #1 提的可选项）——当前 checklist 文字硬化已经覆盖了
  根本原因（grep 形态过窄），property test 是 N+2 的事
- ❌ 不动 simulation/ 模块（grep 0 命中 chapter_id 使用）

## 计划动作清单

- file: `automation/persona_extraction/scene_archive.py:843-846` →
  `_collect_chapters` 函数体补 `lstrip("C")` + `f"C{ch:04d}"`
- file: `automation/repair_agent/context_retriever.py:230-248` →
  `_load_chapter` 头部加 `C{chapter_num:04d}.txt` 优先 pattern
- file: `automation/repair_agent/context_retriever.py:197-227` →
  `_read_chapter_summary` (a) 加 `C{chapter_num:04d}.json` 优先
  pattern；(b) chunked entry 比较去 C 前缀
- file: `automation/repair_agent/context_retriever.py:140-152` →
  `_get_stage_chapters` regex 改 `^C?(\d+)-C?(\d+)$`；list-form
  分支加 `lstrip("C")`
- file: `automation/persona_extraction/orchestrator.py:747` →
  ChunkEntry chapters 字段改 C 前缀；6 处日志 f-string 改 C 前缀
- file: `ai_context/conventions.md` § Identifier rename checklist →
  第 3 项强化通用形态 + 禁止具体变量名条款

## 验证标准

- [ ] code import 无错：`prompt_builder` / `scene_archive` /
  `context_retriever` / `triage` / `orchestrator` 全部 import OK
- [ ] **`_collect_chapters` mock test**：构造小 stage_plan
  `{stages: [{chapters: "C0001-C0003"}, {chapters: "C0004-C0006"}]}`
  → 返回 `["C0001", "C0002", "C0003", "C0004", "C0005", "C0006"]`
- [ ] **`_get_stage_chapters` 双向兼容**：构造 SourceContext +
  stage_plan.json 含 `chapters: "C0001-C0003"` → 返回 `[1,2,3]`；
  含旧 `chapters: "0001-0003"` → 同样返回 `[1,2,3]`（向后兼容）
- [ ] **`_load_chapter` 文件名匹配**：tmp dir 含 `C0001.txt` →
  `_load_chapter(dir, 1)` 返回文件内容；含旧 `0001.txt` →
  也能匹配（fallback pattern 命中）
- [ ] **`_read_chapter_summary` 双格式 chunked**：构造 chunk JSON
  含 `entry["chapter"] = "C0001"` → `_read_chapter_summary(dir, 1)`
  能找到该 entry；构造旧 `entry["chapter_number"] = 1` → 也能找到
- [ ] **通用 `\{[a-z_]+:04d\}` per-dir 残留扫描**：在 schemas /
  prompts / automation / docs / ai_context / simulation 各目录单独
  跑 `grep -rEn '\{[a-z_]+:04d\}\.txt'`、`\{[a-z_]+:04d\}\.json'`、
  `\{[a-z_]+:04d\}-\{[a-z_]+:04d\}'` 三种形态——所有 hit 必须以
  `C` 前缀开头（即 `f"C{ch:04d}.txt"` 形式），不允许 bare 数字
- [ ] schema 自检 + 边界 + ingestion validator regression 全过
  （regression）

## 执行偏差

- `_read_chapter_summary` 顺手修复了一个相关 bug：旧代码 chunked 路径
  迭代 `chunk.get("chapters", [])`，但 chunk schema 真正的字段是
  `summaries[]`（`chapters` 是字符串范围而非数组），所以旧代码即使没
  有 chapter_id 命名漂移也找不到 entry。改为
  `chunk.get("summaries", chunk.get("chapters", []))` 双 fallback，
  优先新字段名。本属"发现即修"小修补，不在 PRE 严格范围但同函数同
  事故，一并修了。
- 新增模块级辅助 `_entry_matches_chapter` 函数（context_retriever.py
  顶部），把 chunked entry 的 chapter 字段比较封装：支持 string
  `"C0001"`（lstrip C 后 int 比）+ legacy int `chapter_number` 字段。
  PRE 计划里没单独列这个 helper 名字，但属于"chunked 比较改为支持
  string 形态" 的实现选择，性质一致。

## 已落地变更

- `automation/persona_extraction/scene_archive.py` `_collect_chapters`
  （L843-846）：`int(parts[0])` → `int(parts[0].lstrip("C"))`；
  `f"{ch:04d}"` → `f"C{ch:04d}"`。与同文件 `_build_chapter_to_stage_map`
  逻辑完全对齐（孪生函数两端一致）。
- `automation/repair_agent/context_retriever.py`：
  - 文件顶部新增模块级 helper `_entry_matches_chapter(entry, chapter_num)`
    支持 string `"C####"` (lstrip C 后 int 比) + legacy int `chapter_number`
  - `_get_stage_chapters`（L142-156）：regex `^(\d+)\s*-\s*(\d+)$` →
    `^C?(\d+)\s*-\s*C?(\d+)$` 兼容旧新两种格式；list-form fallback
    `int(chapters[0])` → `int(str(chapters[0]).lstrip("C"))`
  - `_read_chapter_summary`（L219-249）：(a) per-file pattern 头部
    新增 `f"C{chapter_num:04d}.json"` 优先；(b) chunked 路径用
    `_entry_matches_chapter` 替换原 `entry.get("chapter") == chapter_num`；
    顺带修了 chunk dict 形态从 `chunk.get("chapters", [])` →
    `chunk.get("summaries", chunk.get("chapters", []))` 对齐真实
    schema 字段名（执行偏差段提及）
  - `_load_chapter`（L255-266）：3 个 fallback pattern 头部新增
    `f"C{chapter_num:04d}.txt"` 优先；旧 3 个 pattern 保留作 backward-compat
- `automation/persona_extraction/orchestrator.py`：7 处
  `f"{start:04d}-{end:04d}"`（L527/747/780/790/803/858/862）全部
  改为 `f"C{start:04d}-C{end:04d}"`。包括 1 处数据写入（L747
  ChunkEntry.chapters）+ 6 处日志 / 错误信息 f-string
- `ai_context/conventions.md` § Identifier rename multi-form scan
  checklist 第 3 项强化：明确"必跑通用 regex `\{[a-z_]+:04d\}`、
  禁止单独用具体变量名作为唯一 grep 形态"；列出适用场景（路径拼接
  / dict-key 构造 / 日志 print f-string / 任意 `f"...{var:04d}..."` 站点）

## 与计划的差异

- `_read_chapter_summary` 多修了一个 chunked dict 字段名 bug
  （`chapters` → `summaries`），见执行偏差段
- 新增了模块级 helper `_entry_matches_chapter`（PRE 计划只描述了行为，
  实现成 helper 函数是工程选择），见执行偏差段
- 其余动作与 PRE 计划完全一致

## 验证结果

- [x] code import 全部 OK：prompt_builder / scene_archive / progress /
  orchestrator / context_retriever / triage / _smoke_triage
- [x] `_collect_chapters` mock test：双 stage `C0001-C0003` +
  `C0004-C0006` 输入返回 `["C0001", ..., "C0006"]` 6 项 ✓
- [x] `_get_stage_chapters` 双向兼容：
  - 新格式 `chapters: "C0001-C0003"` → `[1, 2, 3]` ✓
  - 旧格式 `chapters: "0004-0006"` → `[4, 5, 6]` ✓
- [x] `_load_chapter` 文件名匹配：
  - tmp 含 `C0001.txt` → `_load_chapter(dir, 1)` 返回内容 ✓
  - tmp 含 `0002.txt`（旧格式）→ `_load_chapter(dir, 2)` fallback 命中 ✓
- [x] `_read_chapter_summary` 双格式 chunked：
  - new `entry["chapter"]="C0001"` → `_read_chapter_summary(dir, 1)`
    返回 `"new ch1 sum"` ✓
  - legacy `entry["chapter_number"]=5` → 返回 `"legacy ch5 sum"` ✓
- [x] 通用 `\{[a-z_]+:04d\}` per-dir 残留扫描：6 dirs × 4 形态
  全扫，唯一 hit 在 `context_retriever.py:224/259/260` 的 backward-compat
  fallback pattern（前置 `C{chapter_num:04d}` 优先 pattern 已就位），
  PRE 决策"旧 pattern 保留兜底"明确允许；其余 0 残留
- [x] schema 自检：4 个 schema 全过
- [x] ingestion validator regression：<character> PASSED 0 errors / 0 warnings

## Completed

- **Status**: DONE
- **Finished**: 2026-05-01 02:07:30 EDT
