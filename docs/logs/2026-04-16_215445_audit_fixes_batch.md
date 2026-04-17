# Codex 审计修复批次

## 变更内容

根据 Codex 审计结果，修复 4 个已验证问题并清理遗留代码：

### 1. `--resume` 自愈缺失 (cli.py)

`--resume` 路径缺少 `run_full()` 中已有的两项自愈逻辑：
- Phase 3 progress 从 `stage_plan.json` 重建（当 `phase3_stages.json` 丢失但 pipeline 已完成 phase_2）
- `reconcile_with_disk()` 磁盘对账

修复：在 `cli.py` 的 `--resume` 分支中加入两项自愈，与 `run_full()` 行为一致。

### 2. world_event_digest 1:1 强制执行 (review_lanes.py)

定点修复可能缩减 `stage_events`，但 digest 仅在提取后生成一次，导致
条目数不一致。

修复：
- 提交门控 `_validate_world_event_digest_has_stage` 新增 `expected_event_count`
  参数，条目数 ≠ stage_events 数 → error（category=`world_event_digest_missing`，
  属于 `POST_PROCESSING_RECOVERABLE`）→ 自动触发免费 PP 重跑恢复 1:1。
- `consistency_checker.py` 同步将条目数不一致从 warning 升级为 error。

### 3. 门控恢复级联 warning 过滤 (orchestrator.py)

之前 warning（如 `reference_warning`）混入门控恢复级联，导致：
- Tier 1：PP-recoverable `all()` 检查被 warning 的 category 破坏，跳过免费 PP 重跑
- Tier 2：warning 被归入 lane 分组，消耗 retry 预算

修复：在级联入口提取 `gate_errors = [i for i in gate_issues if i.severity == "error"]`，
Tier 1/2/失败终止判断均使用 `gate_errors`，warning 仅记录日志。

### 4. 遗留清理

- 删除 `automation/prompt_templates/coordinated_extraction.md`（1+2N 架构后已无引用）
- 删除 `prompt_builder.py` 中的死代码 `build_extraction_prompt()` 和 `_build_read_list()`
- 更新 `automation/README.md` 文件树

## 修改文件

- `automation/persona_extraction/cli.py` — --resume 自愈
- `automation/persona_extraction/review_lanes.py` — digest 条目数校验
- `automation/persona_extraction/consistency_checker.py` — warning → error
- `automation/persona_extraction/orchestrator.py` — warning 过滤
- `automation/persona_extraction/prompt_builder.py` — 删除死代码
- `automation/prompt_templates/coordinated_extraction.md` — 已删除
- `automation/README.md` — 文件树更新
- `docs/requirements.md` — 门控失败表、1:1 强制说明、warning 过滤说明
- `ai_context/architecture.md` — 门控级联和 PP_RECOVERABLE 描述同步
- `docs/architecture/extraction_workflow.md` — 门控级联描述同步
