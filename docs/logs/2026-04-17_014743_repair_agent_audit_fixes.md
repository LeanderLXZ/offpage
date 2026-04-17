# Repair Agent 审计修复：H1–H5 + M/L 清理 + 全库对齐

## 背景

针对 repair_agent 架构落地后的专项审计（四轮并行），发现 5 项 High /
Medium 级问题与一批次要残留。本轮统一修复并完成全库对齐。

## 修复项

### High 级（阻断正确性）

| ID | 问题 | 修复 |
|----|------|------|
| H1 | `_llm_call(timeout=...)` 误传关键字参数 → 调用抛 `TypeError`，静默禁用所有 LLM 级修复（T1/T2/T3 + 语义审校） | `run_with_retry(..., timeout_seconds=timeout)`（`orchestrator.py:1401`） |
| H2 | `_collect_stage_files` 拉取形如 `world_event_digest/{stage_id}.json` 的非存在按阶段路径，导致 repair agent 永远看不到 digest 残留 | 改为累积型 JSONL 路径（`work/world_event_digest.jsonl`、`char/memory_digest.jsonl`），运行时按正则 `-S{stage_num:03d}-` 过滤当前阶段条目。签名新增 `stage_num: int` 参数；调用处根据阶段在 plan 中的 1-based 位置计算 |
| H3 | 结构检查器把 `relationships` / `target_voice_map` / `target_behavior_map` 当 dict 处理，与 schema 数组定义冲突 → 运行时 `.items()` 抛错 | 改为按数组遍历；`target_voice_map` / `target_behavior_map` 用 `entry.get("target_type")` 作目标名；`relationships` 用 `target_label` → `target_character_id` → `#{idx}` 顺序回退。`json_path` 用数组下标形式 `[{idx}]` |
| H4 | `stage_plan.json` 与 `phase3_stages.json` 阶段 id 漂移时，pipeline 无感知，直接按 phase3 状态执行，后续 commit 挂错 stage | `_ensure_stages_from_plan` 新增漂移检测：现有条目若非 plan 前缀子集，直接 `sys.exit` 提示手动处理 |
| H5 | `validator.py` 保留了 700+ 行 dead code（`validate_stage` / `validate_lane` / 多个 `_check_*` / `_min_examples_for_target` 等），`repair_agent` 架构落地后已无调用方 | 删除所有无引用函数；保留 `ValidationIssue` / `ValidationReport` / `validate_baseline` / `load_importance_map`（从 `_load_importance_map` 重命名为 public，供 orchestrator 调用） |

### Medium / Low 级

| ID | 问题 | 修复 |
|----|------|------|
| M1 | 语义 LLM 调用次数的文档表述不统一（"最多 2 次" 有歧义） | 所有文档统一为"**每文件最多 2 次**（Phase A 初检 + Phase C 终验）；总量随文件数线性增长"。更新 `docs/requirements.md §11.4.5`、`docs/architecture/extraction_workflow.md`、`automation/README.md`、`ai_context/architecture.md`、`ai_context/requirements.md`、`ai_context/decisions.md` |
| M2 | Phase 4 启动警告缺失（M3 trunc 日志） | 语义检查器触发 50k 字符截断时新增 `logger.warning`，记录原长与截断后长度 |
| M3 | `StageEntry.state = StageState.PENDING` 直接赋值有 3 处，无审计线索 | 新增 `force_reset_to_pending(reason: str)` 方法（`reason` 非空强约束），替换 3 处直接赋值：resume 自愈（REVIEWING/EXTRACTING 中断）、reconcile 降级（COMMITTED → PENDING / 中间态 → PENDING） |
| M4 | `fixed_relationships.json` 缺失仅报 warning，导致 Phase 2.5 基线门控可通过 | 升级为 error（"not produced (Phase 2.5 must create)"） |
| M5 | 步骤计数器 `Step X/6` 与实际 5 步流程不匹配 | 全部统一为 `/5` |
| M6 | `StageEntry.lane_retries` / `lane_max_retries` 字段已无语义，仍占据 dataclass + 序列化 | 从 dataclass 定义、`to_dict`、`from_dict` 中移除；`from_dict` 对未识别键静默忽略（前向兼容） |
| L1 | `StructuralChecker` 未接收 `importance_map` → 重要度分级阈值（主角≥5、重要配角≥3、其他≥1）全部降级为默认 | orchestrator 调用 `load_importance_map(...)` 传入 `run_repair`，经 `coordinator._build_pipeline` 透传至 checker |
| L2 | schema checker 仅对 `.jsonl` 后缀做按行校验，但 `memory_timeline/{stage_id}.json` 也是数组体 | 改为判断 `isinstance(content, list)`，与后缀解耦；同步删除 `structural.py` 中相同的耦合判断 |
| L3 | `schema.py` 残留无用的 `import json` / `from pathlib import Path` | 删除 |

### 全库对齐（术语 + 文档）

- `orchestrator.py`：替换 lane-scoped / per-lane 相关注释与局部变量（`lane_type`/`lane_id` → `proc_type`/`proc_id`；docstring 同步）
- `progress.py:370`：把"legacy lane_retries / lane_max_retries"注释改为通用的"未识别键静默丢弃（前向兼容）"，避免文档残留已删字段名
- `docs/architecture/schema_reference.md`：StageEntry 小节移除"旧版"措辞，改述为当前行为的 forward-compatible load；`force_reset_to_pending` 作为唯一合法回 PENDING 路径文档化
- `ai_context/architecture.md`、`ai_context/requirements.md`：repair agent 描述移除"replaces per-lane review, commit gate, and fix cascade"的历史引用，改述为当前系统角色

## 冒烟测试

```python
from automation.persona_extraction.validator import load_importance_map
from automation.persona_extraction.progress import StageEntry, StageState
from automation.repair_agent.coordinator import run as run_repair
from automation.repair_agent.checkers.structural import StructuralChecker

# force_reset_to_pending
e = StageEntry(stage_id='s1', chapters='0001-0005', chapter_count=5,
               state=StageState.FAILED)
e.force_reset_to_pending('test')
assert e.state == StageState.PENDING
assert e.error_message == 'test'

# StructuralChecker 接收 importance_map
StructuralChecker(importance_map={'主角A': '主角'})
```

所有模块 `py_compile` 干净通过。

## 全库审计结论

并行扫描 `ai_context/`、`automation/`、`docs/`（排除 `logs/`）、
`schemas/`、`simulation/`、`prompts/`、`automation/prompt_templates/`：

- 已删符号（`validate_stage` / `validate_lane` / `_check_world` 等）除
  `docs/logs/` 历史文件外无残留引用
- `/6` 步骤计数器除 `docs/logs/` 外无残留
- `lane_retries` / `lane_max_retries` / "per-lane review" / "lane gate" /
  "lane-independent retry" 除 `docs/logs/` 外无残留
- `consistency_checker.py` 中的 `_min_examples_for_target` 与
  `_check_world_event_digest` 是 Phase 3.5 独立实现，与 validator 删除
  的同名函数无关，保留正确

## 变更统计

```
 ai_context/architecture.md                     |  10 +-
 ai_context/decisions.md                        |   4 +-
 ai_context/requirements.md                     |  13 +-
 automation/README.md                           |   3 +-
 automation/persona_extraction/orchestrator.py  | 178 ++++-
 automation/persona_extraction/progress.py      |  37 +-
 automation/persona_extraction/validator.py     | 639 +-----------
 automation/repair_agent/checkers/schema.py     |  10 +-
 automation/repair_agent/checkers/semantic.py   |  14 +-
 automation/repair_agent/checkers/structural.py |  52 +-
 automation/repair_agent/coordinator.py         |  19 +-
 docs/architecture/extraction_workflow.md       |   2 +-
 docs/architecture/schema_reference.md          |  23 +-
 docs/requirements.md                           |  13 +-
 14 files changed, 281 insertions(+), 736 deletions(-)
```

净减 ~455 行（validator dead code 删除为主）。
