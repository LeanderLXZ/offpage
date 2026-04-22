# 2026-04-22 scene_split prompt：每章场景数软上限 + 反锚定

## 背景

Phase 4 scene 切分偶尔产出极细粒度结果（曾观测某章 30+ 个场景）。
T-SCENE-CAP 原计划通过 `config.toml` 加硬 cap + 程序 merge/flag 来兜底，
经讨论否决——核心诉求只是"不要失控"，不是"精确压到 N 个"，不值得引入
config 维度 + 二次切分代码。

## 决定采用 prompt-only 路径

在 `automation/prompt_templates/scene_split.md` 里同时加两处措辞：

1. **开场白加软提示**：`"按自然场景边界切分"` 后追加 `"（通常每章
   1-5 个场景，不强求多切）"`——给 LLM 一个心理预期的范围。
2. **切分规则追加 Rule 6**：

   > 场景数量按实际内容决定：如果本章自然只有 1 个场景就是 1 个、2 个
   > 就是 2 个——不要为了结构整齐或凑数而切分。硬约束：每章不超过 5 个
   > 场景；如果你数到 6 个以上，说明切得过细，请重新审视相邻场景
   > （小的对话转换、情绪起伏、视角微移都不构成场景边界）

Rule 6 三个子句各司其职：
- "按实际内容决定 + 1 就 1、2 就 2" → 反锚定，防止 LLM 把 5 当目标
- "硬约束 ≤ 5" → 上限线，LLM 对"硬约束"的权重显著高于"建议"
- "6 个以上说明过细" + 具体反例（对话转换 / 情绪起伏 / 视角微移） → 把
  Rule 1 里偏激进的"视角切换"在括号里显式降级，不动 Rule 1 本体

## 不做的事

- 不加 `[phase4].max_scenes_per_chapter` config 项——只有一个取值点，不需
  runtime 可变
- 不在 `_process_chapter` 加数量 validator——validator 拒绝后重试会让
  LLM 调用数膨胀，部分章节可能永远卡在 retry 上限
- 不加 merge / flag 程序兜底——合并语义边界代价大，flag 模式 537 章规模
  不可能人工复核
- 不动 Rule 1 的"视角切换"措辞——改它会动场景定义本身，只在 Rule 6 括号
  里软化

## 验证

模板渲染 smoke：

```python
from pathlib import Path
from automation.persona_extraction.prompt_builder import build_scene_split_prompt
p = build_scene_split_prompt(
    project_root=Path('.'), work_id='TEST',
    chapter_id='chapter_001', lines=['第一句', '第二句'],
)
assert '通常每章 1-5 个场景' in p
assert '硬约束：每章不超过 5 个场景' in p
assert '视角微移' in p
# prompt len = 953
```

真实分布验证要等 Phase 4 重跑后看 `scene_archive.jsonl` 的 per-chapter
场景数直方图。预期：≥95% 章节 ≤ 5，5% 上下浮动到 6-8（复杂章节 LLM
突破软约束是可接受的）。

## 副作用提醒

- "场景变粗"会让 `scene_fulltext_window = 10` 在 Tier 0 加载的 token 预算
  上涨——原本 10 scene 可能 3 章量，保守切后可能 7-10 章量。目前 runtime
  尚未实装，先不调 window；实装时按真实 token 统计再定。
- memory_timeline 的 `scene_refs` 精度会下降（一个 scene 可能跨多个
  memory event）。不影响语义，只是引用粒度变粗。

## 关联

- T-SCENE-CAP：从"立即执行"删除。原 config + 硬 cap 方案被本次讨论否决；
  本 prompt 改动是该任务的最终落地形式，不再保留 todo 条目。
- 下一步（promotion）：`todo_list.md` 规则第 4 步——废弃 1 条则从"下一步"
  提 1 条。"下一步"本身空，跳过。"立即执行"本次归零（正常，不违反规则）。
