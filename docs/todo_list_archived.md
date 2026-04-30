# TODO List Archived（归档清单）

---

## File guide

### Purpose

接收从 `docs/todo_list.md` 移走的两类任务条目：

- **Completed**：包括完整完成、部分完成、改方案后完成
- **Abandoned**：包括方案被颠覆、外部前提消失、合并到其他任务等

`docs/todo_list.md` 是**正在做和将来做**的事，本文件是**已经做完和决定不做**的事。两者互不重叠，原 todo 条目移过来后从源文件删除。

### 为什么要瘦身存档

不是为了保留完整改动记录——那个职责由 `git log` + `logs/change_logs/{timestamp}_{slug}.md` 共同承担。本文件仅作 **快速浏览索引**：

- 看 ID / 标题 → 知道有这件事
- 看完成形式 → 知道走到哪一步收尾的
- 看 1 行摘要 → 知道大概改了什么
- 看 log 链接 → 想了解细节就跳过去

**绝不在本文件保留改动清单原文 / 验证步骤 / 待决策项 / 长篇上下文**——这些在原 todo 段落里有，原 todo 一并被瘦身。需要追溯历史时去 git history 看 todo_list.md 删除前的版本，或去 change_logs 看落地详情。

### 条目格式

#### Completed 段

```markdown
### [T-XXX] 中文标题 · 完成于 YYYY-MM-DD · {完整 / 部分 / 改方案后} 完成

- 1 行摘要：实际改了什么 / 走到哪一步
- 关联 log: [logs/change_logs/YYYY-MM-DD_HHMMSS_slug.md](../logs/change_logs/YYYY-MM-DD_HHMMSS_slug.md)
- 关联 commit:（可选）`<short-sha>`
```

完成形式三档：

- **完整完成**：按原 todo 的完成标准全部达成
- **部分完成**：核心达成、留下次要尾巴；尾巴**必须作为新 todo 条目**重新登记到 `todo_list.md`，本归档行的摘要里标"尾巴去 T-YYY"
- **改方案后完成**：方案与原 todo 不同（更优 / 受新约束影响 / 实测后调整），但目的达成；摘要里 1 句话说清"原方案 vs 实际方案"

#### Abandoned 段

```markdown
### [T-YYY] 中文标题 · 废弃于 YYYY-MM-DD

- 废弃原因：1–2 句话
- 关联 log: [logs/change_logs/YYYY-MM-DD_HHMMSS_slug.md](../logs/change_logs/YYYY-MM-DD_HHMMSS_slug.md)
```

### 排序

每段内部按"完成 / 废弃日期"**降序**（新的在上）。同一天有多条按 ID 字母序。

### 不记录什么

✗ 仍在进行的任务 → `docs/todo_list.md`
✗ 历史 design 决策 → `ai_context/decisions.md`
✗ 落地细节 / diff / 验证日志 → `logs/change_logs/`
✗ 改动清单原文 → 不要从源 todo 拷过来
✗ 完整 PRE / POST log 内容 → 引一个链接就够了

### 读取时机

- 用户问"X 这件事我们之前做过 / 讨论过吗？" → 先在本文件 grep ID / 关键词
- 用户问"为什么不做 Y？" → 在 Abandoned 段查 → 引到对应 change_log
- 默认不主动加载（不进入 session 启动序列）

---

## Completed

### [T-CONSISTENCY-TARGETS-SUBSET] phase 3 stage_snapshot 三结构 keys == baseline.targets 强校验 + map 切 character_id keying + targets_cap 路径回滚 · 完成于 2026-04-30 · 完整完成

- 1 行摘要：D4 由"prompt 软约束 + 文档承诺"升级到代码强校验：(1) snapshot `voice_state.target_voice_map` / `behavior_state.target_behavior_map` 切 `target_character_id` keying（保留 `target_type` 作 sibling 元数据），与顶层 `relationships` 统一；(2) 三结构 keys 必须**双向相等**于 `baseline.targets[].target_character_id`（多/少都 fail），三态由内容是否填充承载，fixed_relationship 例外可预填关系字段，"fixed = 全书贯穿不变"严控（故事中才建立 / 改变 / 解除的师承 / 门派 / 婚姻 / 收养 / 决裂 等都不算）；(3) 校验从 phase 3.5 末端搬到 phase 3 单 stage validate 层，新增 L2 cross-file checker `repair_agent/checkers/targets_keys_eq_baseline.py`，越界走 file-level repair lifecycle (L1/L2/L3)；(4) `targets_cap.schema.json` 从 `schemas/_shared/` 回滚到 `schemas/character/`（共享面只在 character 域内），$ref + decision #27b + README 同步。docs / ai_context / prompt 全链 ⊆ → == 同步刷新。
- 关联 log: [logs/change_logs/2026-04-30_034614_targets_keys_eq_baseline.md](../logs/change_logs/2026-04-30_034614_targets_keys_eq_baseline.md)

### [T-CHAR-SNAPSHOT-PER-STAGE] character_snapshot prompt 补 prev_stage 出场字段三态规则 · 完成于 2026-04-29 · 改方案后完成

- 1 行摘要：原方案 = prompt 三态 + schema stage_delta 结构化（changed/removed/added），但被 T-BASELINE-DEPRECATE 拍板的"stage_delta 维持自由文本"否决；改方案 = 仅 prompt 改动。`character_snapshot_extraction.md` 在已有 (A) 未出场继承 后追加：(B) 出场且有变化 → 重写 + stage_delta 点出 / (C) 出场且无变化 → 保留 prev 但 required 必填 / (D) resolved-revealed-消除 → 在 stage_delta 写明消除原因（与 maxItems 裁剪两件事）；per-stage 推演原则；stage_delta 字段说明禁"无明显变化"敷衍。`ai_context/decisions.md` 加 11f。
- 关联 log: [logs/change_logs/2026-04-29_155949_char_snapshot_per_stage_three_state.md](../logs/change_logs/2026-04-29_155949_char_snapshot_per_stage_three_state.md)

### [T-REPAIR-T3-LIFECYCLE-RESET] T3 触发后开新 repair lifecycle，单文件最多 2 个 lifecycle · 完成于 2026-04-29 · 完整完成

- 1 行摘要：`max_lifecycles_per_file=2`（取代旧 `t3_max_per_file=1`）；coordinator 抽 `_run_one_lifecycle`，外层 lifecycle 循环；lifecycle 1 触发 T3 即返回（无 Post-T3 corruption 检查 / 无当轮 L3 gate / 无 Phase C），状态机重置后进入 lifecycle 2，禁用 T3 + 升 T3 即 `T3_EXHAUSTED`；T3 prompt 携带 `prior_attempt_context`（resolved+remaining 摘要 ≤600 char）；triage cap 改为 per-lifecycle，磁盘 jsonl append-only，lifecycle 2 启动前读已 accept fingerprint 过滤；recorder 事件加 `cycle` 字段；`T3_CORRUPTED` 路径完整删除。Smoke 三场景（A 单 lifecycle PASS / B lifecycle 1 T3→lifecycle 2 PASS / C 持续失败→T3_EXHAUSTED）+ 6 triage 场景全过。
- 关联 log: [logs/change_logs/2026-04-29_030118_repair-t3-lifecycle-reset.md](../logs/change_logs/2026-04-29_030118_repair-t3-lifecycle-reset.md)

### [T-LOAD-STRATEGY-WORLD-EVENTS-BOUND] load_strategy.md 删除复述 schema 的具体 bound · 完成于 2026-04-28 · 改方案后完成

- 1 行摘要：原方案"L17 把 50–80 改成 50–100"；实际方案升级为通用清理——`simulation/retrieval/load_strategy.md` 三处复述 schema 数值（L17 world event_digest summary `50–80 chars, hard schema gate`、L22-23 identity `≤ 200 chars` / `≤ 10 entries`、L41 memory_digest summary `30–50 chars, hard schema gate`）全部删除，只留"length capped at extraction time by … schema"指针；loader 自身行为参数（recent 2 stages 窗口、stage 1..N filter、token 预算估算）原样保留。判定准则："数字改了之后跟谁走"——跟 schema 走 → 删；跟 loader 代码走 → 留。
- 关联 log: [logs/change_logs/2026-04-28_234002_load-strategy-drop-schema-bounds.md](../logs/change_logs/2026-04-28_234002_load-strategy-drop-schema-bounds.md)

### [T-CHAR-SNAPSHOT-13-DIM-VERIFY] 角色 stage_snapshot "13 必填维度" 表述核对 · 完成于 2026-04-27 · 改方案后完成

- 1 行摘要：原方案候选"字面 17 条" vs 实际方案"指针式"；`docs/architecture/extraction_workflow.md:277` 与 `docs/requirements.md:2139` 改为"以 `schemas/character/stage_snapshot.schema.json` 的 `required` 列表为准"，去掉具体数字与字段示例，避免下次 schema 增减字段时再次漂移。
- 关联 log: [logs/change_logs/2026-04-27_185531_char-snapshot-required-fields-pointer.md](../logs/change_logs/2026-04-27_185531_char-snapshot-required-fields-pointer.md)

---

## Abandoned

### [T-PHASE35-IMPORTANCE-AWARE] Phase 3.5 一致性检查按 importance 调门槛 · 废弃于 2026-04-30

- 废弃原因：核心痛点（`_check_target_map_counts` 对从未登场 / tier=次要/普通 角色 over-error）已在 T-CONSISTENCY-TARGETS-SUBSET commit `620be09` 顺手用"空 examples 跳过"守卫等价解决；剩余 7 个 `_check_*` 的 over-error 风险被 D4 == + schema-required 字段双重稀释，且 T-PHASE2-TARGET-BASELINE / T-BASELINE-DEPRECATE runtime 未跑前调阈值是过早优化。后续如确有需要，按"D4-state + tier 双锚点"重新立项即可。
- 关联 log: [logs/change_logs/2026-04-30_045522_abandon_t_phase35_importance_aware.md](../logs/change_logs/2026-04-30_045522_abandon_t_phase35_importance_aware.md)

### [T-MIGRATE-TARGET-BASELINE-ZH] 迁移现有 target_baseline.json：英文 enum → 中文柔性 string + tier 路人→普通 · 废弃于 2026-04-30

- 废弃原因：前提失效，无可迁移对象。原 todo 假设"phase 2 已 commit baseline 全是英文值，新 schema 校验 fail"，但 `works/` 在 `## Do-not-commit paths` 内，target_baseline.json 从未入库（`git log --diff-filter=D` 全空）；本地当前 work 的 `analysis/` 也只剩空 progress/，无 baseline 文件。下次 phase 2 重跑直接用新中文 schema 生成，无需迁移工具。
- 关联 log: [logs/change_logs/2026-04-30_024305_abandon_t_migrate_target_baseline_zh.md](../logs/change_logs/2026-04-30_024305_abandon_t_migrate_target_baseline_zh.md)

---

### [T-CHAR-SNAPSHOT-TARGET-LIST] target_char_list 生成策略 + fallback 模式是否需要 · 废弃于 2026-04-29

- 废弃原因：被 T-PHASE2-TARGET-BASELINE 方案吞掉。原 todo 围绕 sub-lane step 0 三选一策略（program-only / llm-light / hybrid）+ fallback 是否跑 step 0；新方案 phase 2 全书视野一次拍 per-character target_baseline.json，后续各 stage ⊆ baseline 写 keys，step 0 整个删除，两个决策项都不再需要。
- 关联 log: [logs/change_logs/2026-04-29_203800_abandon_char_snapshot_target_list.md](../logs/change_logs/2026-04-29_203800_abandon_char_snapshot_target_list.md)
