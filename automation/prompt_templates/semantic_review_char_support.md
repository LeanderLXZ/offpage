# 角色支持层语义审校

你现在接手本地项目 `persona-engine`，你没有任何额外背景知识。

## 目标

对 `{work_id}` 的 `{stage_id}`（章节 `{chapters}`）中 **`{character_id}`** 的 **memory_timeline 和 baseline 修正** 做语义审校。

## 审校范围

仅审校该角色的 memory_timeline 产物和 baseline 文件修正。stage_snapshot 由独立通道审校。

## 必读文件

{review_files}

## 程序化校验结果（第一层已完成）

```
{programmatic_report}
```

## 审校检查清单

### A. memory_timeline 详细度与一致性

如果前一阶段有输出（`{prev_stage_id}`），对比：

1. memory_timeline 条目的 `subjective_experience` 长度和深度是否一致
2. memory_timeline 每条的 `event_description`（150–200 字）和
   `digest_summary`（30–50 字）是否在范围内且非空泛。长度下限是 schema
   硬门控，但贴近下限的"擦边"填充仍应记为退化
3. `digest_summary` 是否是从 `event_description` 机械截断而非独立撰写
   （应当聚焦可检索关键词，而不是"前 50 字截断"）
4. memory_importance 分级是否合理？
5. 如果任何维度出现明显退化（比前阶段减少 50% 以上），标记为 FAIL

### B. memory_timeline 完整性

6. memory_timeline 是否覆盖了本阶段的关键事件？
7. 每条记忆的 emotional_impact 是否具体（而非泛泛的"很难过"）？
8. knowledge_gained 是否列出了角色从此事件获得的具体认知？
9. relationship_impact 是否详细描述关系变化的方向和原因？
10. misunderstanding / concealment 字段是否按需填写？
11. memory_id 是否符合 `M-S###-##` 格式？

### C. Baseline 修正合理性

12. identity.json 的 aliases 是否包含本阶段新发现的别名？
13. baseline 修正是否只涉及跨阶段稳定的角色基底？阶段性变化不应写入 baseline
14. baseline 修正是否与原文一致（不是推测/创造性添加）？
15. 是否有不当的激进修改（大幅重写稳定字段）？

### D. 数据边界正确性

16. memory_timeline 是否包含不属于本角色视角的事件？
17. memory_timeline 是否有明显的虚构（原文中未发生的事件）？
18. baseline 修正是否引入了角色不该知道的信息？

### E. 时间性

19. 记忆是否以事件发生时的视角书写？
20. 是否有"未来阶段"的信息提前泄漏？

## 输出格式

```
VERDICT: PASS 或 FAIL

FINDINGS:
1. [severity: error/warning] [file] 具体问题描述
2. ...

STYLE_CONSISTENCY:
- memory_timeline depth: 前阶段 vs 本阶段 → OK/退化
- event_description length: OK/过短/过长
- digest_summary quality: OK/退化/截断
- subjective_experience: OK/退化

SUMMARY:
一句话总结。
```

如果 VERDICT 为 FAIL，必须在 FINDINGS 中说明具体哪些问题必须修复。
只有存在 severity=error 的 finding 时才应判定 FAIL。
Warning 级别的问题不导致 FAIL，但应记录供参考。
