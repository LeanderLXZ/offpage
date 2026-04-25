# Codex 跨审修复：commit gate / --end-stage / FIXING 移除 / jsonschema 必需

## 背景

一轮外部跨审（codex audit）对 Phase 3 编排器、提交门控、文档一致性做了
体检，列出了 4 项 High、4 项 Medium、1 项 Low、3 项 Residual Risk。逐项
复核后全部属实。本次一次性落地：代码修复 + 契约文档 + ai_context 对齐 +
run book 对齐。

## 核心代码变更

### H1：memory_digest gate 解析 stage 数字，不再依赖中文 stage_id 字符串

`review_lanes._validate_digest_has_stage`：旧实现对 `memory_id` 做
`stage_id in mem_id` 子串检查，中文 `阶段02_xxx` 必然无法匹配
`M-S002-##` 前缀。改为：

1. 通过 `_parse_stage_number(stage_id)` 从 `stage_id` 中抽取数字
2. 通过 `_stage_from_id(entry.memory_id)` 从 ID 前缀抽取
3. 两个数字相等才计入"本阶段命中"

无法解析 stage 号时报硬错，避免静默漏门控。

### H2：commit 顺序契约——SHA 真的写入后才迁移 COMMITTED

`orchestrator._commit_stage` 旧实现先 `transition(COMMITTED)` 再
`commit_stage()`，commit 返回空 SHA 时状态已写回硬盘，造成"状态 committed
但 git 里没有对应 object"漂移。新顺序：

```
sha = commit_stage(...)
if not sha:
    stage.transition(FAILED)  # 让 resume 重跑
    return
stage.committed_sha = sha
stage.transition(COMMITTED)
```

### H3：`--end-stage` 严格前缀语义

之前命中 `--end-stage` 停止时仍会触发 Phase 3.5 / squash-merge 提示 /
Phase 4。改为两个独立布尔 `stopped_by_limit` / `all_done`：只有
`all_done == True` 才进入收尾；前缀运行打印"re-run without --end-stage
to finalize"并退出。

### H4：commit gate 跨实体引用解析（warn-only）

新增 `_cross_entity_reference_warnings` + `_collect_alias_index` +
`_walk_names`：提交门控扫描 world snapshot `relationship_shifts` /
`character_status_changes` 中出现的人名，与 world cast + 当前阶段角色
aliases 做模糊匹配；未解析的 → `[WARN]` 前缀记录。所有 `[WARN]` 不进
硬失败集合，保持门控「结构 + 标识符」的边界；内容级冲突仍由角色通道
语义审校负责。

### M1：`jsonschema` 升级为硬依赖

- `automation/pyproject.toml` 增加 `dependencies = ["jsonschema>=4.0"]`
- `validator.py` / `post_processing.py` 改为 `import jsonschema`
  失败即 `ImportError`，不再悄悄降级门控
- 删除 `if jsonschema is None` 短路分支

### L1：`process_guard` work_id 解析深度

旧实现 `self.lock_path.parent.parent.parent.name` 会取到 `works/` 目录
本身作为 work_id。`lock_path` 实际形态是
`works/{work_id}/analysis/.extraction.lock`，正确深度是 `.parent.parent`。
修正并加一行注释说明路径层级。

### R2：`StageState.FIXING` 移除

`FIXING` 是 2026-04-08 加的中间状态，但现在走的是「reviewer → 直接
调 targeted-fix → re-validate → PASSED/FAILED」的线性流程，`FIXING`
状态没有持久化入口，只在内存里短暂存在。移除：

- `progress.StageState` 枚举删去 `FIXING`
- `_TRANSITIONS`：`REVIEWING → {PASSED, FAILED}`，新增
  `PASSED → FAILED`（极少见的提交前回滚路径）
- `next_pending_stage` in-progress 集合去掉 `FIXING`，加入 `PASSED`
  （resume 到 PASSED 的 stage 走再提交）
- `orchestrator` 对应 state handler：原 `FIXING` 分支替换为 `PASSED`
  resume handler

## 契约与 run book 对齐

- `docs/requirements.md`
  - §11.4 首段：jsonschema 是硬依赖（ImportError 即失败）
  - §11.4b：提交门控范围表 + commit 顺序表 + 门控 vs 语义审校分工
  - §11.5：`--end-stage` 严格前缀语义（stopped_by_limit vs all_done）
  - 第三层 scene_archive 加载：默认 10 条 full_text + 摘要不进启动

- `automation/README.md`：新增 `--end-stage 严格前缀语义` 与
  `提交顺序契约` 两条说明；jsonschema 由「可选」改「必需」

## ai_context 对齐

- `architecture.md`：Phase 3 步骤 4/5 改写；Key design 更新
- `decisions.md`：25b 改为「结构 + 标识符范围」；新增 25b.1（commit
  顺序）、25b.2（`--end-stage` 前缀）、25b.3（jsonschema 硬依赖）
- `current_status.md`：review lanes / commit gate 段落重写；git
  integration 加入 commit-ordering + `--end-stage` 前缀；删除已完成的
  「relationships.json / bible.md 尚无 schema」Gap
- `instructions.md`：`works/*/analysis/` git-track 规则按 `.gitignore`
  现状拉齐

## 过期目录 / 字段清理

`users/_template/` 和 `schemas/context_manifest.schema.json` 是当前
真源：

- 单一 `character_state.json`（吸收原 `relationship_state.json` +
  `shared_memory.jsonl` 的职责）
- `lifecycle` 枚举为 `ephemeral / persistent / merged / archived`
  （没有 `merged_archived`）

据此修正：

- `users/README.md`：推荐结构删掉 `relationship_state.json` 与
  `shared_memory.jsonl`；启动加载段同步清理；`merged_archived` →
  `archived`
- `docs/architecture/data_model.md`：两处 context 加载清单同步清理
- `ai_context/architecture.md`：Runtime Load 第 7 步改为「单一
  character_state（含 relationship_delta + context_memories）」
- `simulation/flows/close_and_merge.md`、`simulation/flows/
  conversation_records.md`：`merged_archived` → `archived`（附
  semantics 注释）
- `works/README.md`：
  - 角色目录树删掉从未产出的 `bible.md`、`relationships.json`
  - world `stage_snapshots` 描述：`累积历史事件` → `仅本阶段
    stage_events`（跨阶段由 world_event_digest 承载）
  - 角色 `stage_snapshots` 描述：显式声明 `stage_events` 仅本阶段
  - `identity.json` 描述补充 `core_wounds` / `key_relationships`

## 加载拆分一致性

scene_archive 启动加载模型已统一为：

- 最近 `scene_fulltext_window` 条 full_text（默认 10，
  `load_profiles.json` 可覆盖）
- **摘要不进启动**——只存在于 FTS5 索引，按需检索命中

扫出的残留「默认 N=5」或「启动加载 summaries」表述已全部改齐：

- `simulation/retrieval/index_and_rag.md`
- `docs/requirements.md`（正文 + ASCII 加载拆分图）
- `docs/architecture/system_overview.md`（加载公式 + 推荐拆分）

## `prompts/shared/最小结构读取入口.md`

`users/` 相关章节把 schema + `_template/` 提到 `users/README.md` 前面，
避免 README 与真源出现分歧时新 agent 先信了文档。

## 测试

- `python -c` 导入三个改过的核心模块：通过
- `StageState` 枚举断言：`FIXING` 不存在、`PASSED→{COMMITTED,FAILED}`
  都合法
- `_parse_stage_number('阶段02_转折') == 2` / `_stage_from_id('M-S003-05')
  == 3`：通过
- digest gate 模拟：`stage='阶段02_转折'` 有匹配的 `M-S002-##` 条目 →
  空 issues；`stage='阶段05_无此段'` 无条目 → `memory_digest 缺少阶段
  S005 的条目`

## 未动

- codex audit 其余 Medium / Residual Risk（M2/M3/M4、R1/R3）——本次先
  落地能明确收敛的高风险项与文档漂移；其余条目需要更大的实现面（例如
  loader 的真实实现），留待后续单独行动
- 当前 extraction 分支数据不动，所有改动都在 master worktree，稍后
  merge 回分支
