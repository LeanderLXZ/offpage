# type_check_cleanup

- **Started**: 2026-04-30 12:15:49 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

用户在 IDE（VS Code + Pylance）里看到一批 Python 类型检查器报错，例子：
- `Cannot access attribute "get" for class "list[Unknown]"` ×2
- `No parameter named "target_characters"` ×2
- `Argument of type "str | None" cannot be assigned to parameter "key" of type "str" in function "get"`

并要求在改之前先做一轮全仓库扫描，把所有同类问题一并修掉。

会话前期还顺带定位到一处真 bug（与类型问题无关，但同源于上一轮 codex
follow-up 的扫尾不全）：`f577641 commit M3` 项声称 "orchestrator 五处
caller 传 work_id"，实际只 4 处传，`_commit_consistency_report` 漏一处。

## 结论与决策

一次清理两类东西：

1. **真 bug**（不修会出错）
   - `automation/persona_extraction/orchestrator.py:2133` —
     `commit_stage()` 漏传 `work_id`，破坏 git scope guard
     ([git_utils.py:207](../../automation/persona_extraction/git_utils.py#L207))。
   - `automation/repair_agent/protocol.py:175` — `Issue.category`
     的 `Literal` 没把 `"cross_file"` 列进去，导致新加的
     D4 cross-file checker（`targets_keys_eq_baseline.py`）
     构造 Issue 时 dataclass 类型不一致。同步在
     `START_TIER` mapping 里给 `"cross_file"` 配一个起始 tier。
   - `automation/repair_agent/coordinator.py:763-770` — `t3_files`
     集合元素是 `str | None`（`fingerprint_to_file.get(fp)` 返回值），
     之后传给 `record_tier_use_on_file(str)` 和 `set[str].add()`
     会过 None。改成显式 walrus 过滤。
   - `automation/repair_agent/coordinator.py:786` — `RepairAttempt.result`
     是 `Literal["resolved","persisting","regression"]`，传 `str` 不窄化。

2. **类型噪音 + 易误读为 bug**（不修也跑得动，但 IDE 一片红）
   - `validator.py` / `consistency_checker.py` —— `_load_json` 返回
     `dict | list | None`，但调用方都按 dict 用 `.get(...)`。这些位置
     按 schema 一定是 dict；显式 narrow 一下。
   - `prompt_builder.py:258 / 317 / 365` — `bool(stages) and stages[0]...`
     运行时安全，但 Pyright 不会通过 `bool()` 窄化 Optional。改写法。
   - `scene_archive.py:896 + 923` — `futures: dict = {}` 类型太松，
     第二段 except 里 `cid = chapter_id` 触发 `str | None → str`。
     改成 `dict[Future, str]`。
   - `orchestrator.py:1930-1936` — repair-agent 那段把 `futures` 重新
     当 dict 用，但同名变量在前面 phase3 提取段被推为 list，
     mypy 误以为是再赋值。给 repair 段单独命名（`repair_futures`）。
   - `orchestrator.py:2333-2335` — `pipeline / phase3` 从 `.load()`
     拿到 `Optional`，赋给非可选变量。改成 `: T | None`
     或显式分支处理（实际下一段 `if pipeline and ...` 已 narrow，
     仅修类型注解）。
   - `repair_agent/triage.py:173` — `verdicts.get(fp)` 返回 Optional
     直接赋给非可选。
   - `repair_agent/checkers/semantic.py:101 _review_file` —
     `self._llm_call` 是 `Callable | None`，跨方法窄化失败。
     方法首行加 `assert self._llm_call is not None`（调用方
     `check()` 已经 None-guard）。
   - `repair_agent/_smoke_triage.py:340-341` — 局部变量缺类型
     注解（仅 smoke 测试，但顺手补）。

3. **pyflakes 噪音**（删掉就没事）
   - 4 个 unused import：
     `triage.py:22,23` (`re`, `Path`) /
     `repair_agent/checkers/structural.py:11` (`json`) /
     `orchestrator.py:53,109,117` (3 处 unused) /
     `config.py:21` (`is_dataclass`)。
   - 9 处 `f""` 但无占位符（`scene_archive.py` 2 / `orchestrator.py`
     6 / `consistency_checker.py` 2 / `prompt_builder.py` 0）。
   - 1 处 unused 局部变量 `chunk_idx` (orchestrator.py:850)。

文档：本次只动代码 + 配套 log，不改 schema、prompt、ai_context、requirements。
但 `protocol.py` 的 `Issue.category` Literal 算 protocol 改动，`/post-check`
会扫到，需要在 POST 段说明。

## 计划动作清单

按文件聚合，避免反复改同一文件：

- file: `automation/persona_extraction/orchestrator.py`
  → 2133: `commit_stage(... work_id=self.pipeline.work_id ...)`
  → 1930: 改名为 `repair_futures`（避免与上方 list 类型冲突）
  → 2333-2335: 加 `Optional` 类型注解
  → 53/109/117: 删 unused import
  → 850: 删 unused `chunk_idx`
  → 284/392/394/1258/1399/2186/2247: 去掉无占位符 `f""` 的 `f` 前缀
- file: `automation/repair_agent/protocol.py`
  → 175: `Literal["json_syntax","schema","structural","semantic","cross_file"]`
  → 190: `START_TIER["cross_file"] = 2` （定位到 L2 fixer；L1 json_repair
     无法跨文件，T3 file-regen 开销过大）
- file: `automation/repair_agent/coordinator.py`
  → 763-770: 用 walrus / 显式分支过滤 None
  → 786: 给 `status` 加 Literal 注解
- file: `automation/repair_agent/triage.py`
  → 22/23: 删 unused import
  → 173: 处理 `verdicts.get(fp)` 的 Optional
- file: `automation/repair_agent/checkers/semantic.py`
  → 101 `_review_file`: 函数体首行 `assert self._llm_call is not None`
- file: `automation/repair_agent/checkers/structural.py`
  → 11: 删 unused `json` import
- file: `automation/repair_agent/_smoke_triage.py`
  → 340-341: 加类型注解
- file: `automation/persona_extraction/validator.py`
  → 161/179/213/235/262/285: 调用 `_validate_schema` 前 narrow 到 dict
  → 193/238/243/288/291: `data.get(...)` 前 narrow 到 dict
- file: `automation/persona_extraction/consistency_checker.py`
  → 254/259/267/311/339/488/512/547/571/636/696: 同上 narrow
  → 551/561: 去掉无占位符 `f""` 的 `f` 前缀
- file: `automation/persona_extraction/scene_archive.py`
  → 896: `futures: dict[Future, str] = {}`
  → 674/676: 去掉无占位符 `f""` 的 `f` 前缀
- file: `automation/persona_extraction/prompt_builder.py`
  → 258/317/365: 改 `stages and stages[0].stage_id == stage.stage_id`
- file: `automation/persona_extraction/config.py`
  → 21: 删 unused `is_dataclass`

## 验证标准

- [ ] `python -m compileall -q automation/` 退出码 0（语法 / import 干净）
- [ ] `python -m pyflakes automation/` 输出条数从 19 降到 0
- [ ] `mypy --strict-optional --ignore-missing-imports automation/persona_extraction automation/repair_agent`（在 `automation/` cwd 下跑）
      "list/union has no attribute 'get'" 类条目降为 0；
      "Incompatible types in assignment" 类条目降为 0；
      允许保留 "Library stubs not installed" / "Skipping analyzing" 这种环境侧 note
- [ ] `python -c "from automation.persona_extraction import orchestrator, validator, consistency_checker, scene_archive, prompt_builder, progress; from automation.repair_agent import coordinator, protocol, triage; from automation.repair_agent.checkers import semantic, targets_keys_eq_baseline, structural" ` import smoke
- [ ] `grep -rn 'category="cross_file"' automation/` 仍能找到 4 处（不被误删）；
      并且 `protocol.py` Literal 已含 `"cross_file"`
- [ ] `commit_stage(` 5 个 caller 全部带 `work_id=`：
      `grep -n 'commit_stage(' automation/persona_extraction/orchestrator.py` 共 5 处，
      `grep -A2 'commit_stage(' automation/persona_extraction/orchestrator.py | grep -c 'work_id='` = 5

## 执行偏差

无。计划清单逐条落地，未发现需要中途变更范围的情况。

<!-- POST 阶段填写 -->

## 已落地变更

12 个文件，+102 / -53 行。

- `automation/persona_extraction/orchestrator.py`
  - import 表删 `PHASE_DONE` / `get_active as get_active_rl` /
    `validate_only as repair_validate_only`（3 个 unused）
  - 顶部 `from concurrent.futures` 加入 `Future`（供 1929 行类型注解）
  - 850: `chunk_idx` 从 try/except 的 tuple 解包中删除（替成 `_`）
  - 284 / 392 / 394 / 1258 / 1399 / 2186 / 2247: 7 处无占位符 `f""` 改普通字串
  - **2133 (真 bug)**: `commit_stage(... work_id=self.pipeline.work_id ...)`，
    与其他 4 个 caller 对齐；恢复 `git_utils.py:207-220` 的 scope guard
  - 1929-1934: `futures` → `repair_futures: dict[Future, RepairFileEntry]`
  - 2316-2334: `pipeline / phase3` 显式标 `Optional`；2363
    新增 `pipeline is not None` guard（保险，避免 phase3 自愈分支带来的
    单边 None 情形 down-stream 解引用）
- `automation/repair_agent/protocol.py`
  - 175: `Issue.category` Literal 增 `"cross_file"`
  - 191-200: `START_TIER["cross_file"] = 2` + 注释解释为何选 L2
- `automation/repair_agent/coordinator.py`
  - 39: import 加 `Literal`
  - 763-770: `t3_files` 改显式 walrus + 类型注解 `set[str]`
  - 786-790: `status` 标 `Literal["resolved","persisting"]`
- `automation/repair_agent/triage.py`
  - 19-24: 删 `re` / `pathlib.Path`（unused）
  - 173-176: 跨循环作用域的 `v` 改名 `v_or_none`（不与 line 161/165
    的 non-Optional 同名变量冲突）；narrow 后再赋回 `v`
- `automation/repair_agent/checkers/semantic.py`
  - 102: `_review_file` 函数体首行 `assert self._llm_call is not None`
- `automation/repair_agent/checkers/structural.py`
  - 11: 删 unused `import json`
- `automation/repair_agent/_smoke_triage.py`
  - 31-37: 加 `SourceNote` import
  - 340-341: `accepted_notes: list[SourceNote] = []`、
    `notes_per_file: dict[str, int] = {}`
- `automation/persona_extraction/validator.py`
  - 302-336: `_load_json` 收返回为 `dict | None`，添加 `isinstance(raw, dict)` 出口
    + 详细 docstring 说明对 list/scalar 一律按"无效 JSON"处理
- `automation/persona_extraction/consistency_checker.py`
  - 163-187: `_load_json` 同样收返回为 `dict | None`，docstring 同步
  - 562 / 572: 2 处无占位符 `f""` 改普通字串
- `automation/persona_extraction/scene_archive.py`
  - 24-26: `from concurrent.futures` 加入 `Future`
  - 674-677: 2 处无占位符 `f""` 改普通字串
  - 896: `futures: dict[Future, str] = {}`
- `automation/persona_extraction/prompt_builder.py`
  - 258-260 / 318-320 / 367-369: 3 处 `is_first_stage` 表达式从
    `bool(stages) and stages[0]....` 改为
    `stages is not None and len(stages) > 0 and stage.stage_id == stages[0].stage_id`
- `automation/persona_extraction/config.py`
  - 21: 删 unused `is_dataclass`

## 与计划的差异

新增（PRE 未列，但属于同一类问题，顺手补）：

- orchestrator.py 2363 `pipeline is not None` 二段 guard。原本仅打算
  把 `pipeline / phase3` 注解成 Optional；注解之后 mypy 立刻在 2364
  解引用 `pipeline.target_characters` 处冒出新错（之前未注解时被忽略），
  顺手把 guard 从 `phase3 is not None` 加宽到双判定。这是 type 收紧
  的正向连带效果，不是 scope 蔓延。

未触发：

- PRE 中"prompt_builder.py: 0 处 f-string"是正确的（该文件没有问题
  f-string，验证通过）。

## 验证结果

- [x] `python -m compileall -q automation/` — 退出 0，无输出
- [x] `python -m pyflakes automation/` — 输出空（之前 19 条）
- [x] `mypy --strict-optional --ignore-missing-imports persona_extraction/ repair_agent/`
      （cwd=`automation/`） — `Success: no issues found in 43 source files`
- [x] Import smoke — 18 个模块全部导入成功，打印 `IMPORT_SMOKE_OK`
- [x] `grep -c 'category="cross_file"' automation/repair_agent/checkers/targets_keys_eq_baseline.py` = 4；
      `protocol.py` Literal 含 `"cross_file"`；`START_TIER["cross_file"] = 2`
- [x] `commit_stage(` 5 个 caller 全部带 `work_id=` —
      `grep -c 'commit_stage(' orchestrator.py` = 5；
      `grep -A4 'commit_stage(' orchestrator.py | grep -c 'work_id='` = 5
- [x] 35 个 schema 仍 meta-validate 通过（变更未触及 schemas/，但顺验未回归）

## Completed

- **Status**: DONE
- **Finished**: 2026-04-30 12:30:44 EDT
