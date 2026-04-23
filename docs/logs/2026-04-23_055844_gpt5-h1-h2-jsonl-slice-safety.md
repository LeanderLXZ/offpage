# 2026-04-23 05:58 — gpt-5 audit H1/H2：累积 JSONL 切片安全 + repair 后 PP 重跑

## 背景

`docs/review_reports/2026-04-23_020531_gpt-5_full-repo-alignment-audit.md`
H1：repair 对累积 JSONL（`memory_digest.jsonl` / `world_event_digest.jsonl`）
按当前 stage 切片后，write-back 路径会用切片子集覆盖整份累积文件，静默
丢失历史阶段条目。
H2：post-processing 在 repair 之前跑；repair 改写 `digest_summary` /
world `stage_events` 后，派生的 digest/catalog 没有被重新生成，Phase 3.5
仅按 ID 数量对应，不做 1:1 文本比对，漂移放行。

本轮一次性收敛两个问题，并额外补上 Phase 3.5 两条文本等值 gate 作为
defense-in-depth。

## H1 — 累积 JSONL 切片安全回写

### `FileEntry` 扩展（`automation/repair_agent/protocol.py`）

新增三个字段（都可选、默认等价于非切片）：
- `is_jsonl_slice: bool = False`
- `jsonl_full_content: list[dict] | None = None`
- `jsonl_key_field: str = ""`

### `write_file_entry()` 新助手（`automation/repair_agent/field_patch.py`）

- 非切片：等价 `write_patched_file(entry.path, entry.content)`
- 切片：按 `entry.jsonl_key_field` 把 `entry.content`（修补后的切片）
  merge 回 `entry.jsonl_full_content`（完整累积列表），然后写盘。合并
  语义 = replace-by-key + append-new，历史阶段条目原位保留；
  `entry.jsonl_full_content` in-place 更新，保证同一修复轮次内后续 patch
  看到最新状态。

### 四个 fixer 切换写路径

`programmatic.py` / `local_patch.py` / `source_patch.py` / `file_regen.py`
全部改为：`f.content = new_content` 后调 `write_file_entry(f)`，不再直接
`write_patched_file(f.path, new_content)`。

### `_jsonl_stage_entry` 扩展（`automation/persona_extraction/orchestrator.py`）

读取整份累积 jsonl 时同时保留 `full` 和 `kept`（当前阶段切片）；返回的
`FileEntry` 带 `is_jsonl_slice=True` + `jsonl_full_content=full` +
`jsonl_key_field=id_fields[0]`（`memory_id` / `event_id`）。

## H2 — repair 后程序化后处理重跑 + Phase 3.5 等值 gate

### 后处理重跑（`_process_stage` Step 4 末尾）

`stage.transition(StageState.PASSED)` 后、进入 Step 5 git commit 之前，
无条件再调一次 `run_stage_post_processing`。post-processing 幂等、0 token；
repair 若改过源字段，重跑让 `memory_digest.jsonl` /
`world_event_digest.jsonl` / `stage_catalog.json` 同步到新源字段。重跑
失败按首次失败同样降级：stage → FAILED → ERROR，`--resume` 重试。

### Phase 3.5 新增两条等值 gate（`automation/persona_extraction/consistency_checker.py`）

- `_check_memory_digest_summary_equality`：按 `memory_id` 配对 digest
  与 timeline，比 `digest.summary` 是否文本完全等于 `timeline.digest_summary`。
  违反 → `error`。
- `_check_world_event_digest_summary_equality`：按 `event_id` 的 stage
  + seq 解析回 world snapshot `stage_events[seq-1]`，比 `digest.summary`
  与 `event_text.strip()` 是否文本完全等。违反 → `error`。

两条 gate 接在 `run_consistency_check` 主序列里，拼成 10 条检查总盘。

## 跨文件对齐

- `docs/requirements.md` §11.4.5 新增"累积 JSONL 切片回写"和"repair 后
  PP 重跑"两段约束；§11.10 检查表从 8 条扩到 10 条，对应加两行；
  §11 主流程图 ASCII 对应段的"8 项"改为"10 项"，Phase 3 步骤列表
  插入 ④' post-repair PP 重跑行
- `ai_context/architecture.md` Phase 3 步骤列表加第 4 步（post-repair PP
  重跑），git commit 从第 4 变第 5；Phase 3.5 改 10 项并点名两条等值
  gate；末尾新增"累积 JSONL repair 安全"段
- `ai_context/current_status.md` 的 Phase 3.5 描述从 "8 programmatic
  checks" 改为 "10 programmatic checks"，列出两条等值 gate
- `docs/architecture/extraction_workflow.md` Phase 3.5 列表 8→10 条；
  Phase 3 ASCII 流程插入"程序化后处理重跑"节点

## 验证

- `python -c` import `FileEntry` / `write_file_entry` / 四个 fixer /
  `orchestrator` / `consistency_checker` 全部通过
- 单元 smoke：
  - `_merge_jsonl_slice(full=3 条含 S001+S002, sliced=S002 改写, key=memory_id)`
    → S001 两条原位保留，S002 替换成新版
  - `write_file_entry()` 在 tmp 文件上走切片路径，回读后结构与预期一致
  - 非切片路径对普通 `.json` 文件行为不变

## 未做 / 推迟

- 实际 stage 上端到端回归：需要切到 extraction 分支跑 `--resume` 观察
  S002（ERROR 状态）的 repair → PP 重跑路径；本轮只做单元级验证，
  端到端回归由用户下次 `--resume` 自然覆盖
- `json_repair._load_json` side-effect 写盘（H4 子问题）与 Phase 3.5
  产物 commit 契约拆到下一 commit（gpt-5 H4）

## 受影响文件清单

```
ai_context/architecture.md
ai_context/current_status.md
automation/persona_extraction/consistency_checker.py
automation/persona_extraction/orchestrator.py
automation/repair_agent/field_patch.py
automation/repair_agent/fixers/file_regen.py
automation/repair_agent/fixers/local_patch.py
automation/repair_agent/fixers/programmatic.py
automation/repair_agent/fixers/source_patch.py
automation/repair_agent/protocol.py
docs/architecture/extraction_workflow.md
docs/requirements.md
```
