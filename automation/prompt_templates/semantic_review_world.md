# 世界层语义审校

你现在接手本地项目 `persona-engine`，你没有任何额外背景知识。

## 目标

对 `{work_id}` 的 `{batch_id}`（阶段 `{stage_id}`，章节 `{chapters}`）的**世界层**提取产出做语义审校。

## 审校范围

仅审校世界层产物，角色层由独立通道审校。

## 必读文件

{review_files}

## 程序化校验结果（第一层已完成）

```
{programmatic_report}
```

## 审校检查清单

### A. 风格与详细度一致性

如果前一批有输出（`{prev_stage_id}`），对比：

1. stage_events 条目的粒度是否相近，每条是否为 ≤ 80 字的 1 句话摘要
2. current_world_state 描述风格是否一致
3. evidence_refs（章节号列表）是否完整
4. 如果任何维度出现明显退化（比前批减少 50% 以上），标记为 FAIL

### B. 数据边界正确性

5. 世界层是否只记录了大事件？是否有小场景、个人经历误入世界层？
6. 是否有 inference 被标为 canon？
7. stage_events 是否只包含本阶段事件，未重复前序阶段？（跨阶段时间线由 world_event_digest.jsonl 累积，不在 snapshot 内）

### C. 信息充分性

8. snapshot_summary 是否存在且有意义？
9. current_world_state 是否覆盖本批重大变化？
10. stage_events 是否完整覆盖本阶段重要事件？（移除了 key_events 字段，stage_events 是唯一事件清单来源）

### D. 时间性

11. 当前阶段的内容是否写成了"现在时"？
12. 历史事件是否正确标注为已发生？
13. 是否有"未来阶段"的信息提前泄漏？

## 输出格式

```
VERDICT: PASS 或 FAIL

FINDINGS:
1. [severity: error/warning] [file] 具体问题描述
2. ...

STYLE_CONSISTENCY:
- stage_events: OK/退化
- current_world_state: OK/退化
- evidence_refs: OK/退化

SUMMARY:
一句话总结。
```

如果 VERDICT 为 FAIL，必须在 FINDINGS 中说明具体哪些问题必须修复。
只有存在 severity=error 的 finding 时才应判定 FAIL。
