# full_review_findings_fixes

- **Started**: 2026-05-12 13:26:53 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

复审 `logs/review_reports/2026-05-12_112511_opus-4-7_full-review-findings.md`
（opus-4-7 `/full-review` 36 finding + 9 OQ）后，用户拍板：建议修的全做，
建议留 todo 的直接跳过（不写 todo），其他建议跳过的也跳过；简洁有效，不
过度工程。

复核结论中 M2 已被前置 commit `85a3cba` 修复（撤回），M4 严重度降到 Low
且建议跳过 merge 改动；其他建议修的 H1/H2/H3 + 多条 M/L 项执行本次落盘。

## 结论与决策

**本轮要修的 finding（按报告 ID）**：

- H1 — phase 3 主 pool n_workers 按 sub-lane 启用与否降量
- H2 — RateLimitHardStop 路径不删 partial、立即 raise（partial 保留供
  下次 resume）
- H3 — `final_path.write_text(...)` → 复用 `_atomic_write_json`
- M1 — `schema_reference.md` 子目录文件数列改 4 / 5 / 6 / 8 / 5 / 5 / 1
- M3 — scene_archive_entry chapter description 例改 `C0042`（pattern
  不加；range 形态 OQ2 跳过）
- M5 — recovery sweep raise 前 `executor.shutdown(wait=False,
  cancel_futures=True)`
- M6 — sub_lane_regen 回调加 `Path(file_path).is_relative_to(work_root)`
  + `_CHAR_SNAPSHOT_PATH_RE` 锚 `works/{wid}/` 段
- M8 — decisions.md 11d 标题改写为当前事实（去掉 deprecated 措辞）
- M9 — works/README.md character canon 树补 `memory_digest.jsonl` +
  `extraction_notes/`；world 侧补 `extraction_notes/`
- M10 — works/README.md `extraction.log` → `extraction_logs/extraction.log`
- M13 — snapshot_merge.py docstring 清理职责措辞修正
- M14 — works/README.md `indexes/` + `world/cast/character_index.json`
  加 "尚未启用" 注释
- L1 — ai_context/requirements.md 字面 `15` 改为 schema 指针
- L2 — prompts/review/手动补抽与修复.md 字面字数改 schema 指针
- L5 — 5 处 "renamed from / moved from" 注释清理
- L6 — consistency_checker.py `target_label` fallback 改 warning + skip
- L7 — snapshot_merge.py docstring 「5 道 merge hard gate」→ 「4 正向
  + 1 anti-rule」
- L10 — sub-lane error joiner 截断到 2000 字
- L12 — `_clear_snapshot_partials` OSError 改 raise（fail loudly）
- L15 — post_processing.py JSONL `open("w")` 改原子写

**本轮跳过**：M2（已修撤回）/ M4（schema 严格契约一致，不改）/ M7 / M11
/ M12 / L3 / L4 / L8 / L9 / L11 / L13 / L14 / L16 / L17 / L18 / L19 /
OQ1–OQ10（用户明示跳过留 todo 的不写 todo，其他跳过也直接跳过）。

**显式不做**：不引入 `[phase3].global_concurrency_cap` 新 toml（H1 用
"按 sub-lane 启用降量 outer n_workers" 最小路径修，不新增配置面）；不动
prompt template（M4 prompt 端 verify 跳过）；不动 light_novel
chapter_count=1 oneOf schema；不补 `ai_context/requirements.md` sub-lane
mention（OQ1 跳过）；不改 scene_archive_entry pattern（OQ2 跳过）。

## 计划动作清单

### 代码

- file: `automation/persona_extraction/orchestrator.py`
  - H3：line 1055-1057 直写 → `_atomic_write_json(final_path, merged)`
    + import 调整
  - H2：line 966-976 hard_stop 路径删除 `_clear_snapshot_partials`
    调用、立即 raise（partial 保留供 resume）
  - H1：line 2718 附近 `n_workers = max(1, len(lanes_to_run))` 改为
    `n_workers = max(1, len(lanes_to_run) // (3 if self.char_snapshot_sub_lanes else 1))`
    （sub-lane 启用时把 outer 并发缩到 1/3，与 inner sub-lane fan-out
    相消；保底 1）
  - M5：line 713 `except RateLimitHardStop: raise` 前加
    `executor.shutdown(wait=False, cancel_futures=True)`
  - M6：line 1100-1118 `_cb` 顶部加
    `Path(file_path).resolve().is_relative_to(work_root.resolve())`
    检查
  - L5：line 1667 + 其他 "renamed from / moved from" 注释清理（共 5 处
    含 prompt_builder.py，描述当前事实而非历史）
  - L6：consistency_checker.py:378-383 `target_label` fallback → warning
    + skip
  - L10：line 981-986 `joined = "; ".join(...)` 截断到 2000 字
  - L12：line 1078-1083 `_clear_snapshot_partials` OSError 改 raise
- file: `automation/persona_extraction/snapshot_merge.py`
  - M13：line 39-42 docstring 清理职责措辞修正
  - L7：line 16-37 docstring 「5 道 merge hard gate」→ 「4 正向 + 1
    anti-rule」
- file: `automation/persona_extraction/consistency_checker.py`
  - L6：380-381 `target_label` fallback
- file: `automation/persona_extraction/prompt_builder.py`
  - L5：line 122 / 124 / 349 / 350 "renamed from" / "moved from" 注释
    改写为描述当前状态
- file: `automation/persona_extraction/post_processing.py`
  - L15：line 165-168 + line 362-366 truncate write → 原子写（新增
    `_atomic_write_jsonl` helper 或就地 `tempfile + os.replace`）
- file: `automation/repair_agent/fixers/file_regen.py`
  - M6：line 52-53 `_CHAR_SNAPSHOT_PATH_RE` 加 `works/(?P<wid>[^/]+)/`
    前置锚

### Schema

- file: `schemas/runtime/scene_archive_entry.schema.json`
  - M3：line 29-32 description 例改 `C0042` / `C0042-C0043`

### Docs

- file: `docs/architecture/schema_reference.md`
  - M1：line 13-19 子目录文件数列改 4 / 5 / 6 / 8 / 5 / 5 / 1
- file: `works/README.md`
  - M9：character canon 树（line 41-49）补 `memory_digest.jsonl` +
    `extraction_notes/{stage_id}.jsonl`；world 侧（line 12-40 附近）补
    `extraction_notes/`
  - M10：line 60 + 183 `extraction.log` → `extraction_logs/extraction.log`
  - M14：line 69-74 + line 38-40（world/cast/character_index.json）加
    "（尚未启用）" 注释
- file: `ai_context/decisions.md`
  - M8：line 46 11d 标题 `**4-piece character baseline deprecated.**`
    → 描述当前事实

### Ai_context

- file: `ai_context/requirements.md`
  - L1：line 82 `15 via shared` → 删字面 `15`，改 schema 指针

### Prompts

- file: `prompts/review/手动补抽与修复.md`
  - L2：line 33-35 字面字数 → schema 指针

## 验证标准

- [ ] 三文件 import 不报错（orchestrator / snapshot_merge / post_processing）
- [ ] `python -c "from automation.persona_extraction import orchestrator,
  snapshot_merge, post_processing, consistency_checker, prompt_builder,
  scene_archive; from automation.repair_agent.fixers import file_regen"`
  通过
- [ ] 36 schema metaschema 全过：`python automation/scripts/schema_metaschema_check.py`
- [ ] `grep -rn "renamed from\|moved from" automation/persona_extraction/`
  剩余命中数 = 0
- [ ] `grep -n "4-piece character baseline deprecated" ai_context/decisions.md` = 0
- [ ] `grep -rn "extraction\.log\b" works/README.md` 全部带
  `extraction_logs/` 前缀
- [ ] `grep -n '"0042"' schemas/runtime/scene_archive_entry.schema.json` = 0
- [ ] `grep -n '15 via shared' ai_context/requirements.md` = 0
- [ ] `_atomic_write_json` import 在 orchestrator.py 可用，调用形态正确
- [ ] snapshot_merge.py docstring 不再含「5 道 merge hard gate」字面

## 执行偏差

- Step 3 内 works/README.md 顺手修 line 201 的 `原 world_overview.json
  路径已废弃` 措辞 → 改成纯当前事实描述（违反 conventions §3 "no legacy"，
  PRE 计划之外但属于 docs 对齐 batch 同源；不影响其他 finding）。
- Step 6 跨文档对齐发现 decision #55 + extraction_workflow §6.2 描述了
  原 hard-stop 行为（"删 partial"），与本次 H2 修复后行为冲突——同步
  改写措辞描述当前设计；同时 #55 末段加 H1 outer pool 降量一句记录
  ("Outer pool 并发降量")。PRE 计划仅列代码 + schema + docs tree 改动，
  未列决策 / extraction_workflow 同步——Step 6 补齐。
- PRE 计划写"36 schema metaschema 全过"——实际仓库内 schema 总数 = 34，
  全过；估算偏差，不影响验证结论。

<!-- POST 阶段填写 -->

## 已落地变更

### 代码

- `automation/persona_extraction/orchestrator.py`
  - Import 加 `_atomic_write_json`（line 81）
  - H3：`_run_char_snapshot_sub_lanes` final_path 写入改用
    `_atomic_write_json(final_path, merged)`（line ~1054-1056，删原
    `parent.mkdir` + `write_text` 三行）
  - H2：hard_stop 路径删除 `_clear_snapshot_partials` 调用 + 立即 raise；
    partial 保留供下次启动前的 `_clear_snapshot_partials` (line 916)
    + reconcile_with_disk 兜底清理（line ~966-985）
  - L10：sub_lane_errors 路径 `joined = "; ".join(...)` 超 2000 字截断
  - H1：phase 3 主 ThreadPoolExecutor 启动前 `n_workers = max(1,
    len(lanes_to_run) // (3 if char_snapshot_sub_lanes else 1))`
    （line ~2727-2736）
  - M5：`_run_recovery_sweep` 在 `except RateLimitHardStop: raise` 前
    `executor.shutdown(wait=False, cancel_futures=True)`（line ~712-719）
  - M6：`_build_sub_lane_regen_callback._cb` 顶部加
    `Path(file_path).resolve().is_relative_to(work_root.resolve())`
    检查 + OSError 兜底
  - L12：`_clear_snapshot_partials` 删 OSError → warning 包装；只保留
    `p.unlink(missing_ok=True)` 让真异常 fail loudly
  - L5：`run_analysis` docstring 删 "world_overview lane renamed to /
    moved from" 描述
- `automation/persona_extraction/snapshot_merge.py`
  - M13 + L7：module docstring 改写——"5 道 merge hard gate" →
    "4 positive gates + 1 anti-rule"；MergeError 失败路径清理职责改为
    "由 orchestrator 显式 `_clear_snapshot_partials` 调用，
    `progress.reconcile_with_disk` 仅 sweep orphan partial"
- `automation/persona_extraction/consistency_checker.py`
  - L6：相关性检查 `target_label` fallback 删除；缺 `target_character_id`
    时 `logger.warning(...)` + continue（line 377-389）
- `automation/persona_extraction/prompt_builder.py`
  - L5：foundation lane 段顶部注释删 "lane renamed from world_overview /
    schema moved from" 文字（line 121-130）；
    `build_foundation_prompt` docstring 删 "renamed from
    build_world_overview_prompt" 文字（line 346-348）
- `automation/persona_extraction/post_processing.py`
  - L15：新增 module-level `_atomic_write_jsonl(path, entries)` helper
    （tempfile + fsync + os.replace），替换 memory_digest（line ~196）+
    world_event_digest（line ~390）两处 `open("w")` truncate write
- `automation/repair_agent/fixers/file_regen.py`
  - M6：`_CHAR_SNAPSHOT_PATH_RE` 加 `works/(?P<wid>[^/]+)/` 前置锚
    （兼容 `_parse_char_snapshot_path` 仍返回 `(cid, sid)`）

### Schema

- `schemas/runtime/scene_archive_entry.schema.json`
  - M3：`chapter` description 例 `0042` / `0042-0043` →
    `C0042` / `C0042-C0043`（OQ2 跳过 pattern 加入）

### Docs

- `docs/architecture/schema_reference.md`
  - M1：子目录文件数列 `analysis = 5 → 4` / `character = 7 → 8`
- `works/README.md`
  - M9：character canon 树补 `memory_digest.jsonl` +
    `extraction_notes/{stage_id}.jsonl`；world 侧补 `extraction_notes/`
  - M10：`extraction.log` → `extraction_logs/extraction.log{,.1,.2}`
    rolling 形态；analysis 段补 `repair_logs/`
  - M14：`indexes/` 子树加"整棵子树尚未启用"标注；
    `world/cast/character_index.json` 加同标注；analysis/ 节内
    `indexes/` 描述段重写
  - 执行偏差：line 201 "原 world_overview.json 路径已废弃" → 纯当前
    事实描述
- `docs/architecture/extraction_workflow.md`
  - Step 6 同步：sub-lane hard-stop 段（line 296-302）描述当前行为
    "partial 保留供下次启动前兜底清理"
- `ai_context/decisions.md`
  - M8：决策 #11d 标题改写——`**4-piece character baseline deprecated.**`
    → `**Character voice / behavior / boundary / failure_modes inlined
    in stage_snapshot.**`
  - Step 6 同步：决策 #55 R2 行措辞 + 新加 "Outer pool 并发降量" 句
- `ai_context/requirements.md`
  - L1：§7 信息分层段 `15 via shared schemas/...` → 删字面 15，仅留
    schema $ref 指针

### Prompts

- `prompts/review/手动补抽与修复.md`
  - L2：6 道长度硬门控字面字数 → 指向具体 schema 文件路径

### Logs

- `logs/change_logs/2026-05-12_132653_full_review_findings_fixes.md`
  本 PRE/POST log 文件

## 与计划的差异

PRE 计划全部落地；额外 3 处偏差均记录在「执行偏差」段：
1. works/README.md:201 "已废弃" 措辞顺手修
2. decisions.md #55 + extraction_workflow.md §6.2 hard-stop 段描述
   同步（PRE 漏列）
3. decisions.md #55 末段新加 "Outer pool 并发降量" 一句（H1 同步）

## 验证结果

- [x] **import 不报错** — `python -c "from automation.persona_extraction
  import orchestrator, snapshot_merge, post_processing,
  consistency_checker, prompt_builder, scene_archive, progress,
  lane_output, config, rate_limit, cli; from automation.repair_agent.fixers
  import file_regen; from automation.persona_extraction.progress import
  _atomic_write_json; from automation.persona_extraction.post_processing
  import _atomic_write_jsonl"` 全过
- [x] **schema metaschema** — 34 schemas pass Draft 2020-12（PRE 写 36
  为估算偏差，全过）
- [x] **grep "renamed from\|moved from"** — automation/ 残留 = 0
- [x] **grep "4-piece character baseline deprecated"** — ai_context/
  残留 = 0
- [x] **works/README extraction.log** — 仅出现 `extraction_logs/`
  路径前缀，无裸 `extraction.log` 字面
- [x] **scene_archive_entry "0042"** — schema 残留 = 0（已改 `C0042`）
- [x] **ai_context "15 via shared"** — 残留 = 0
- [x] **_atomic_write_json import 可用** — 验证 import +
  `_atomic_write_jsonl` smoke test（tempfile + replace 路径正确，无
  leftover .tmp）
- [x] **snapshot_merge 「5 道 merge hard gate」字面** — 残留 = 0
  （改为 "4 positive gates + 1 anti-rule"）
- [x] **file_regen 正则锚 wid** — smoke test 通过：含 `works/wid/`
  前缀的路径匹配并提取 wid；不含前缀的路径被拒绝；
  `_parse_char_snapshot_path` 仍返回 `(cid, sid)`
- [x] **_atomic_write_jsonl** — JSONL 写盘 atomic helper 测试：
  写入后无 leftover `.tmp`，文件可逐行 JSON parse

## Completed

- **Status**: DONE
- **Finished**: 2026-05-12 13:57:27 EDT

<!-- /post-check 填写 -->

## 复查结论（对话里有完整报告）

### 轨 1 — 需求落实
- 落实率：21/21 项计划动作 + 12/12 项验证标准（含 PRE 漏列由 Step 6
  补齐的 2 项跨文档对齐 + 1 项 H1 决策 #55 末段注记）
- Missed updates: 2 条（`docs/architecture/data_model.md` 与 M9 / M14
  同源的连带漂移；详见对话）

### 轨 2 — 影响扩散
- Findings: High=0 / Medium=2 / Low=1
- Open Questions: 1 条（详见对话）

## 复查时状态

- **Reviewed**: 2026-05-12 16:14:33 EDT
- **Status**: REVIEWED-PARTIAL
  - 轨 1 全落实；轨 2 有 2 个 Medium（data_model.md 与 works/README
    + works/README M14 同源的 pre-existing 漂移）+ 1 个 Low（L12
    成功路径 cleanup OSError raise 边界）
- **Conversation ref**: 同会话内 /post-check 输出
