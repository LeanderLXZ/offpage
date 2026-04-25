# 2026-04-14 21:01:21 — batch → stage 术语统一

## 背景
schema v4 refactor 之后，代码中仍保留了大量 `batch` / `Batch` / `批次`
以及 `batch_id` 字段。这些概念与 `stage` / `stage_id` 在语义上完全重合
（5–15 章一段的抽取切片），并行存在导致：
- 概念冗余：同一对象在不同文件里有两个名字。
- 命名不一致：`source_batch_plan.json` vs `阶段01_<location_a>初遇` 的 stage_id。
- 历史包袱：早期设计区分 "batch（技术切片）" 与 "stage（业务阶段）"，
  v4 之后 batch ≡ stage，但字段仍然并列。

本次统一彻底删除 `batch` 概念，全部改用 `stage`。

## 变更范围

### 1. 文件重命名
- `works/<work>/analysis/source_batch_plan.json`
  → `works/<work>/analysis/stage_plan.json`
- 进度文件 `phase3_batches.json` → `phase3_stages.json`

### 2. 字段重命名
- `batch_id` → 删除。stage_id 作为唯一身份标识。
- `batches` → `stages`
- `default_batch_size` → `default_stage_size`
- `stage_is_cumulative` 保留
- work_manifest schema 的 `batch_to_stage` 布尔旗标删除
  （v4 之后 batch=stage 恒成立，旗标无意义）

### 3. 代码符号
- `BatchEntry` → `StageEntry`
- `BatchState` → `StageState`
- `Phase3Progress.batches` → `Phase3Progress.stages`
- `commit_batch()` → `commit_stage()`，签名简化为
  `commit_stage(project_root, stage_id, *, message=None, files=None)`
  （原先 batch_id/stage_id 双参数歧义解除）
- `validate_batch` → `validate_stage`
- `print_batch_header` → `print_stage_header`
- `total_batches` / `full_batches` / `is_first_batch` / `max_batch_size`
  / `min_batch_size` / `batches_data` 等全部改 stage 前缀
- `_check_batch_plan_limits` → `_check_stage_plan_limits`
- `_ensure_batches_from_plan` → `_ensure_stages_from_plan`

### 4. CLI
- `--end-batch` → `--end-stage`
- 其他 batch 相关 flag 全部迁移

### 5. Prompt 模板
- 9 份 `automation/prompt_templates/*.md` 中的 `{batch_*}`
  占位符统一 → `{stage_*}`
- `{is_first_batch}` → `{is_first_stage}`

### 6. 文档
- `docs/requirements.md`：2.1 节术语定义重写，移除 "batch 即 stage"
  式同义反复；ASCII 流程图的 `(source_batch_plan.json)` 改
  `(stage_plan.json)`；全部 "stage 1 / 第一 batch" 改 "第一个 stage"
- `docs/architecture/*.md`：data_model / extraction_workflow /
  schema_reference / system_overview 对齐
- `ai_context/*.md`：7 份背景文件全部对齐
- `prompts/**/*.md` 与 `simulation/**/*.md`：术语统一

## 执行方式
三轮 regex rename：
1. Pass 1（`/tmp/rename_batch_to_stage.py`，44 files, 1061 subs）—
   精确标识符、CLI flag、中文术语。
2. Pass 2（14 files, 145 subs）— 复合词：`BatchEntry`, `commit_batch`,
   `total_batches`, `is_first_batch`, 样例字符串 `"batch_001"` 等。
3. Pass 3（6 files, 28 subs）— 词中模式：`_batch_` 通配、
   `print_batch_header`、`max_batch_size` 等。

排除路径：`docs/logs/`（历史记录不改写）、`sources/`（原始素材）。

## 修复的并发 bug
rename 过程中发现并修复：
1. `commit_batch(project_root, batch_id, stage_id, ...)` 在只存在
   stage 概念后退化成 `commit_stage(project_root, stage_id, stage_id, ...)`
   重名参数 → 改为关键字参数 `message=None` 接收 baseline commit 的
   自定义消息，默认模板用于抽取 commit。
2. `StageEntry` dataclass 有两个 `stage_id: str` 字段（Python 允许但
   语义错）— 去重。
3. `to_dict()` / `from_dict()` / `expand_stages()` 中 5 处
   `stage_id=...` kwargs 重复 — 去重。
4. `prompt_builder.py` context dict 有 5 处 `"stage_id": stage.stage_id`
   重复 entry — 去重。
5. `is_first_stage` 判断逻辑错误：pass 2 将样例 `"batch_001"` 改成
   `"阶段01_示例"`，但真实 stage_id 永远不等于字面量 `"阶段01_示例"` —
   改为 `bool(stages) and stage.stage_id == stages[0].stage_id`。

## 验证
- `python -c "import automation.persona_extraction"` 全部模块成功
  import。
- 4 份关键 schema（work_manifest / stage_catalog / stage_snapshot /
  world_stage_catalog）jsonschema 解析通过。
- `stage_plan.json` 可加载，49 stages，`default_stage_size=10`，首条
  keys = `['stage_id', 'chapters', 'chapter_count', 'boundary_reason',
  'key_events_expected']`，无 `batch_id`。
- 全库 grep `batch|Batch|BATCH|批次` 仅命中 `docs/logs/` 历史记录，
  活代码 / 文档 / schema / prompt 全部清空。
- `stage_plan.json` 与 `stages` 的 25 处引用（orchestrator,
  scene_archive, progress, consistency_checker, validator,
  post_processing, review_lanes, prompt_builder）全部使用正确。

## 影响面
47 files changed, 912 insertions(+), 973 deletions(-)（含文件 rename）。

## 后续
- extraction 分支 merge 本次 master 改动时，`stage_plan.json` 的
  stage 名称会冲突（extraction 分支的 stage 名称更新），冲突解决
  规则：保留 extraction 分支的 stage 名称，只采纳 master 的结构字段
  变更（去 `batch_id`、`batches` → `stages` 等）。
- 历史日志不做回溯修改，继续保留 `batch` 字样作为历史上下文。
