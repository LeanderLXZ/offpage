# knowledge_scope 条数/字数硬门控 + 裁剪策略

## 背景

`stage_snapshot.knowledge_scope` 过去只有结构约束（三个字符串数组），没有
条数或单条字数的上限。多阶段提取运行中观察到：

- 某角色在前 5 个阶段中 `knows` 条目数以约 +5/阶段的速度线性增长；按 49
  阶段外推会接近 260 条，startup prompt 预算不可控
- 单条条目偶尔超过 50 字，退化为"事件复述"而非认知断言，职责与
  `memory_timeline` 重叠
- schema 无硬门控 → 即便语义审校发现问题也没有机械化阻断路径

本次把 `knowledge_scope` 升级为**硬门控字段**：条数上限 + 单条字数上限 +
prompt 层裁剪策略 + 审校层语义检查。

## 改动范围

### Schema（真源）

- `schemas/stage_snapshot.schema.json` — `knowledge_scope` 新增：
  - `knows`：`maxItems: 50`，`items.maxLength: 50`
  - `does_not_know`：`maxItems: 30`，`items.maxLength: 50`
  - `uncertain`：`maxItems: 30`，`items.maxLength: 50`
  - 顶层 `description` 说明条数/字数上限与裁剪策略，供生成端参考

硬门控由 `jsonschema` 自动拾取，`validator.py` / `consistency_checker.py`
无需代码改动。

### 提取 prompt

- `automation/prompt_templates/character_extraction.md` — 在
  `knowledge_scope` 字段说明处补充：
  - 条数 50/30/30、每条 ≤ 50 字（schema 硬门控、超限直接 FAIL）
  - 裁剪策略：**优先保留**影响当前决策或关联 core_wounds /
    active_obsessions / 活跃 relationships 的条目；**优先丢弃**日常常识、
    早期无触发点的细节、已在 memory_timeline 中完整承载的条目
  - 禁止敷衍填充（贴近 50 字上限但语义稀薄、堆砌形容词）
- `automation/prompt_templates/coordinated_extraction.md` — 同步

### 审校 prompt

- `automation/prompt_templates/semantic_review_character.md` — 检查项 12
  扩展为四点：泄漏 / 冗余堆砌 / 敷衍填充 / 语义分类偏离。条数与字数由
  schema 硬门控，此处只审语义裁剪质量
- `automation/prompt_templates/semantic_review.md` — 兜底模板对齐
  （review_lanes.py 当前只会派发 world / character 两种 lane，此模板为
  fallback；仍保持一致以防未来通道扩展）

### 需求文档 + 上下文

- `docs/requirements.md` §11.3 角色包字段列表中 `knowledge_scope` 条目
  补齐条数上限、字数上限、裁剪策略
- `ai_context/conventions.md` **Data Separation — Hard Rules** 段新增
  条数/字数硬门控总结与裁剪优先级
- `works/README.md` stage_snapshot 字段说明列表中补齐约束

## 现有产物合规性

在修改前对 extraction 分支上已 committed 的 20 个 stage_snapshot 文件
（2 角色 × 5 阶段 × 3 字段 × 条数/字数两个维度）做全量合规性审计：

| 维度 | 上限 | 实测最大 | 违规数 |
|------|------|---------|-------|
| knows 条数 | 50 | 25 | 0 |
| does_not_know 条数 | 30 | 19 | 0 |
| uncertain 条数 | 30 | 11 | 0 |
| 单条字数 | 50 | 56 → 修复 | 2 → 0 |

发现并手动修复两条超长条目（已以独立 commit 落在 extraction 分支）：

- `<character_a>/阶段04/knows[1]`：56 → 26 字（被剥离的细节已在 `does_not_know[5]`
  中独立承载）
- `<character_a>/阶段05/uncertain[2]`：51 → 26 字（具体信号明细归
  `memory_timeline.subjective_experience`）

修复后对全部 10 个角色 stage_snapshot 跑新 schema 校验：**0 violations**。
新增硬门控不会误伤已有数据，可安全启用。

## 综合测试

在 master worktree 上：

1. Draft-7 schema 自检通过
2. 合成正/反例测试：边界值（50/30、50 字）通过，超限 1 条 / 超长 1 字均
   触发 jsonschema 错误
3. 现有 10 个角色 stage_snapshot 跑新 schema 通过
4. `validator.py` / `consistency_checker.py` / `orchestrator.py` /
   `review_lanes.py` 模块 import 无异常

## 合并流程

本次改动在 master 分支完成（架构级变更的统一落地点），随后 merge 回
`extraction/{work_id}` 提取分支，Phase 3 在下一阶段重启时即沿用新规则。
旧阶段产物已单独做过合规修正，无需回滚。

## 不在本次范围

- `knowledge_scope` 上限数值仍是人工定值（50/30/30、50 字）；未来如出现
  特殊作品类型（百科式 / 群像式）导致合理超限，可在 prompt 层先观察再调
  整 schema 上限
- world 快照暂未引入条数/字数硬门控；world 的 `stage_events` 已有 50–80
  字长度门控，`stage_events` 条数控制由"只记公共层事件"的语义规则承担
- runtime 侧（`simulation/`）无改动——运行时加载的 stage_snapshot 已由
  提取期保证合规
