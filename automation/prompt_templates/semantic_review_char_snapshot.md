# 角色快照语义审校

你现在接手本地项目 `persona-engine`，你没有任何额外背景知识。

## 目标

对 `{work_id}` 的 `{stage_id}`（章节 `{chapters}`）中 **`{character_id}`** 的 **stage_snapshot** 做语义审校。

## 审校范围

仅审校该角色的 stage_snapshot 产物。memory_timeline 和 baseline 由独立通道审校。

## 必读文件

{review_files}

## 程序化校验结果（第一层已完成）

```
{programmatic_report}
```

## 审校检查清单

### A. 风格与详细度一致性

如果前一阶段有输出（`{prev_stage_id}`），对比：

1. emotional_voice_map 条目数是否相近（允许±2）
2. relationships 条目的 driving_events 是否同等详细
3. evidence_refs 引用密度是否相近
4. dialogue_examples 数量和质量是否相近
5. `stage_events` 每条是否为 50–80 字的一句话（schema 硬门控；是否有
   贴近下限的敷衍填充）
6. target_voice_map 每个 target 的 dialogue_examples 数量和质量是否充分（至少 3-5 条）
7. target_behavior_map 每个 target 的 action_examples 数量和质量是否充分（至少 3-5 条）
8. 如果任何维度出现明显退化（比前阶段减少 50% 以上），标记为 FAIL

### B. 数据边界正确性

9. 角色快照是否有世界层的大事件直接复制？
10. 角色的 knowledge_scope 是否合理？① 是否泄漏了角色不该知道的信息？
    ② 条目是否冗余堆砌（重复、泛泛、与当前决策无关）？
    ③ 是否有敷衍填充（贴近 50 字上限但语义稀薄、堆砌形容词）？
    ④ 条目是否偏离 `knows/does_not_know/uncertain` 的语义分类？

### C. 信息充分性（stage_snapshot 完整度）

stage_snapshot 是运行时角色扮演的唯一状态来源。以下维度缺少任何一个 = 扮演缺陷：

11. `active_aliases` 是否存在？primary_name 是否正确？
12. `voice_state` 是否有足够的 emotional_voice_map（至少 3 种情绪）？target_voice_map 每个 target 是否有至少 3-5 条 dialogue_examples？
13. `behavior_state` 是否有足够的 emotional_reaction_map（至少 3 种情绪）？target_behavior_map 每个 target 是否有至少 3-5 条 action_examples？
14. `boundary_state` 是否存在？
15. `relationships` 是否覆盖了本阶段出现的所有重要角色？每条是否有 driving_events？
16. `knowledge_scope` 是否存在？
17. `misunderstandings` 和 `concealments` 是否已填写（即使为空数组）？
18. `emotional_baseline`、`current_personality`、`current_mood`、`current_status` 是否存在？
19. `stage_delta` 是否存在（非首阶段时应有实质内容）？
20. `character_arc` 是否存在（非首阶段时应有弧线概览）？
21. 有没有明显的重大遗漏？

### D. 时间性

22. 当前阶段的内容是否写成了"现在时"？
23. 历史事件是否正确标注为已发生？
24. 是否有"未来阶段"的信息提前泄漏？

## 输出格式

```
VERDICT: PASS 或 FAIL

FINDINGS:
1. [severity: error/warning] [file] 具体问题描述
2. ...

STYLE_CONSISTENCY:
- emotional_voice_map: 前阶段 N 条 vs 本阶段 M 条 → OK/退化
- target_voice_map examples per target: OK/不足
- target_behavior_map examples per target: OK/不足/缺失
- relationships detail: OK/退化
- evidence_refs density: OK/退化
- dialogue_examples: OK/退化

SUMMARY:
一句话总结。
```

如果 VERDICT 为 FAIL，必须在 FINDINGS 中说明具体哪些问题必须修复。
只有存在 severity=error 的 finding 时才应判定 FAIL。
Warning 级别的问题不导致 FAIL，但应记录供参考。
