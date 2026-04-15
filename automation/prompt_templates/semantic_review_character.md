# 角色层语义审校

你现在接手本地项目 `persona-engine`，你没有任何额外背景知识。

## 目标

对 `{work_id}` 的 `{stage_id}`（阶段 `{stage_id}`，章节 `{chapters}`）中 **`{character_id}`** 的提取产出做语义审校。

## 审校范围

仅审校该角色的产物 + 与世界快照的交叉一致性。其他角色由独立通道审校。

## 必读文件

{review_files}

## 程序化校验结果（第一层已完成）

```
{programmatic_report}
```

## 审校检查清单

### A. 风格与详细度一致性

如果前一批有输出（`{prev_stage_id}`），对比：

1. emotional_voice_map 条目数是否相近（允许±2）
2. relationships 条目的 driving_events 是否同等详细
3. evidence_refs 引用密度是否相近
4. dialogue_examples 数量和质量是否相近
5. memory_timeline 条目的 `subjective_experience` 长度和深度是否一致
6. memory_timeline 每条的 `event_description`（150–200 字）和
   `digest_summary`（30–50 字）是否在范围内且非空泛。长度下限是 schema
   硬门控，但贴近下限的"擦边"填充仍应记为退化
7. `stage_events` 每条是否为 50–80 字的一句话（schema 硬门控；是否有
   贴近下限的敷衍填充）
8. target_voice_map 每个 target 的 dialogue_examples 数量和质量是否充分（至少 3-5 条）
9. target_behavior_map 每个 target 的 action_examples 数量和质量是否充分（至少 3-5 条）
10. 如果任何维度出现明显退化（比前阶段减少 50% 以上），标记为 FAIL

### B. 数据边界正确性

11. 角色包是否有世界层的大事件直接复制？
12. 角色的 knowledge_scope 是否合理？① 是否泄漏了角色不该知道的信息？
    ② 条目是否冗余堆砌（重复、泛泛、与当前决策无关）？
    ③ 是否有敷衍填充（贴近 50 字上限但语义稀薄、堆砌形容词）？
    ④ 条目是否偏离 `knows/does_not_know/uncertain` 的语义分类？
    （条数与字数上限由 schema 硬门控，此处只审语义裁剪质量）
13. `digest_summary` 是否是从 `event_description` 机械截断而非独立撰写
    （应当聚焦可检索关键词，而不是"前 50 字截断"）

### C. 信息充分性（stage_snapshot 完整度）

stage_snapshot 是运行时角色扮演的唯一状态来源。以下维度缺少任何一个 = 扮演缺陷：

14. `active_aliases` 是否存在？primary_name 是否正确？
15. `voice_state` 是否有足够的 emotional_voice_map（至少 3 种情绪）？target_voice_map 每个 target 是否有至少 3-5 条 dialogue_examples？
16. `behavior_state` 是否有足够的 emotional_reaction_map（至少 3 种情绪）？target_behavior_map 每个 target 是否有至少 3-5 条 action_examples？
17. `boundary_state` 是否存在？
18. `relationships` 是否覆盖了本阶段出现的所有重要角色？每条是否有 driving_events？
19. `knowledge_scope` 是否存在？
20. `misunderstandings` 和 `concealments` 是否已填写（即使为空数组）？
21. `emotional_baseline`、`current_personality`、`current_mood`、`current_status` 是否存在？
22. `stage_delta` 是否存在（非首阶段时应有实质内容）？
23. `memory_timeline` 是否覆盖了本阶段的关键事件？
24. 有没有明显的重大遗漏？

### C2. 别名一致性

25. identity.json 的 aliases 是否包含本阶段新发现的别名？
26. stage_snapshot 的 active_aliases 与 identity.json 的 aliases 是否一致？

### D. 世界-角色交叉一致性

27. 世界快照和角色快照使用的 stage_id 是否一致？
28. 世界快照中的重大事件是否在相关角色的 stage_events（仅本阶段）中有体现？
29. 角色 relationships 中引用的事件是否合理？

### E. 时间性

30. 当前阶段的内容是否写成了"现在时"？
31. 历史事件是否正确标注为已发生？
32. 是否有"未来阶段"的信息提前泄漏？

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
