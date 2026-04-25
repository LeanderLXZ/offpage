# Manifest 架构整顿：schema 化 + 程序化生成

## 动机

之前的 manifest 体系是半成品：

- `sources/works/*/manifest.json` 没有 schema，字段随意
- `works/*/manifest.json` 被 startup_load 等多处引用，但从未被 orchestrator
  生成过
- `works/*/world/manifest.json` 文档提过但未实装
- 各 character `manifest.json` 的 `build_status` 字段需要在 Phase 2/2.5/3
  多处状态机里同步更新，容易漂移
- 三个 metadata 文件（`book_metadata.json` / `chapter_index.json`）也没有
  schema 约束

本次按 4 步重规划执行，把 manifest / metadata 全部 schema 化、并对可程序化
生成的部分切成确定性写入，把 prompt 从"描述 manifest 字段"的负担里解放出来。

## 设计决策

1. **移除 `build_status`**（works / world / character 三处）——状态机太散、
   容易与真实状态不一致。运行时需要的 "已做到哪一步" 已经在
   `works/*/analysis/progress/` 下的 JSON 里，manifest 里再存一份只是冗余
2. **`source_package_ref` 用相对路径字符串**，pattern
   `^sources/works/[^/]+$`；不做绝对路径 / URI / 反向引用
3. **world manifest 不带 tagline / description**——全程序化生成，0 LLM 调用
4. **Phase 归属**：works manifest 在 Phase 2 末（用户确认人物+阶段后）写；
   world manifest 在 Phase 2.5 baseline 末写

## 改动清单

### 新增 schema（5 份）

- [schemas/work/book_metadata.schema.json](../../schemas/work/book_metadata.schema.json) —
  必需：`work_id` / `title` / `language` / `source_format` / `chapter_count`
  / `created_at` / `updated_at`
- [schemas/work/chapter_index.schema.json](../../schemas/work/chapter_index.schema.json) —
  顶层数组，每项必需 `sequence` / `chapter_id` / `title` / `normalized_path`；
  `sequence` 必须从 1 起严格连续
- [schemas/work/works_manifest.schema.json](../../schemas/work/works_manifest.schema.json) —
  必需：`schema_version` / `work_id` / `title` / `language`
  / `source_package_ref` / `paths` / `chapter_count` / `stage_count`
  / `character_count` / `stage_ids` / `character_ids` / `created_at`
  / `updated_at`
- [schemas/world/world_manifest.schema.json](../../schemas/world/world_manifest.schema.json) —
  必需：`schema_version` / `work_id` / `world_id` / `paths` / `stage_ids`
  / `created_at` / `updated_at`
- [schemas/character/character_manifest.schema.json](../../schemas/character/character_manifest.schema.json) —
  删除 `build_status` 字段及其 `required` 条目

### 新增入库 validator（离线硬门）

- [automation/ingestion/__init__.py](../../automation/ingestion/__init__.py)
- [automation/ingestion/validator.py](../../automation/ingestion/validator.py) —
  `validate_source_package(project_root, work_id)` 检查 3 份必需文件、
  JSON 合法、schema 合法、`chapter_count` 与 `chapter_index` 长度一致、
  `sequence` 1..N 严格连续
  - CLI 入口：`python -m automation.ingestion.validator <work_id>`

### 新增程序化 manifest writer

- [automation/persona_extraction/manifests.py](../../automation/persona_extraction/manifests.py) —
  - `write_works_manifest(project_root, work_id, character_ids)`：读
    source manifest + chapter_index + stage_plan，写
    `works/{work_id}/manifest.json`
  - `write_world_manifest(project_root, work_id)`：读 stage_plan，写
    `works/{work_id}/world/manifest.json`
  - 两者 idempotent；`created_at` 在已存在文件上保留

### Orchestrator 接线

- [automation/persona_extraction/orchestrator.py](../../automation/persona_extraction/orchestrator.py) —
  - `confirm_with_user`：`pipeline.save(...)` 之后调 `write_works_manifest`
  - `run_baseline_production`：`missing_critical` 检查之后调 `write_world_manifest`
- [automation/persona_extraction/validator.py](../../automation/persona_extraction/validator.py) —
  `validate_baseline` 里把 `works/{work_id}/manifest.json` 与
  `works/{work_id}/world/manifest.json` 缺失作 error 级闸门

### Prompt 调整

- [prompts/ingestion/原始资料规范化.md](../../prompts/ingestion/原始资料规范化.md) —
  step 6 按 3 份 metadata 分列，并指向 schema；新增 step 8 调 validator CLI
  的硬自检；"回答里要明确" 补一条 schema 验证状态
- [automation/prompt_templates/analysis.md](../../automation/prompt_templates/analysis.md) —
  末尾加 "## 不需要你产出的文件" 区块，说明 works/manifest.json 由 Phase 2
  末程序化写入
- [automation/prompt_templates/baseline_production.md](../../automation/prompt_templates/baseline_production.md) —
  删除 `build_status: "extracting"` 指示

### 文档对齐

- [schemas/README.md](../../schemas/README.md) — work 目录改 5 files、world 目录
  改 5 files，并把新 manifest / metadata 入表
- [docs/architecture/schema_reference.md](../../docs/architecture/schema_reference.md) —
  为 4 份新 schema 开节（附"生成时机"说明），character_manifest 节移除
  `build_status`
- [docs/architecture/data_model.md](../../docs/architecture/data_model.md) —
  三处 "推荐内容" 升级为 "必需内容" + schema 引用；step 6 入库规范化加 schema
  引用与硬门标注；新增 step 9 调 validator；startup load 加载清单里把
  `works/{work_id}/manifest.json` 放在 canon 首条
- [docs/architecture/extraction_workflow.md](../../docs/architecture/extraction_workflow.md) —
  step 1（入库）列出 schema-gated 文件 + validator 命令并指向 ingestion
  prompt；step 4（Phase 2）加 works manifest 程序化写入说明；step 5
  （Phase 2.5）加 world manifest 程序化写入 + 更新 validator gate 清单
- [simulation/flows/startup_load.md](../../simulation/flows/startup_load.md) —
  load order 在开头插入 works / source manifest 两步，world foundation 步
  序重新编号

### 首个 work 的实际数据

- [sources/works/<work_id>/manifest.json](../../sources/works/<work_id>/manifest.json) —
  按新 source manifest schema 手写
- [works/<work_id>/manifest.json](../../works/<work_id>/manifest.json) —
  `write_works_manifest` 程序化生成（537 章 / 49 stage / 2 character）
- [works/<work_id>/world/manifest.json](../../works/<work_id>/world/manifest.json) —
  `write_world_manifest` 程序化生成（49 stage_ids）
- `works/<work_id>/characters/{<character_a>,<character_b>}/manifest.json` —
  去掉 `build_status` 行，仍通过 schema

### ai_context/

- [ai_context/current_status.md](../../ai_context/current_status.md) —
  Project Stage / First Work Package 改为 "Phase 0/1/2/2.5/4 complete;
  Phase 3 reset to fresh start (all 49 stages pending after 2026-04-20
  rollback)"
- [ai_context/next_steps.md](../../ai_context/next_steps.md) — Phase 3 状态
  同步；删掉已不再相关的 content-language 继承条目

## 验证

```bash
# 1. 所有新 schema JSON 合法
python3 -c "
import json, pathlib
for p in pathlib.Path('schemas').rglob('*.schema.json'):
    json.loads(p.read_text())
print('schema OK')
"

# 2. source validator 对已有 work 通过
python3 -m automation.ingestion.validator <work_id>
# 预期 exit 0

# 3. 程序化 writer 可重入不破坏 created_at
python3 -c "
from automation.persona_extraction.manifests import (
    write_works_manifest, write_world_manifest
)
from pathlib import Path
root = Path('.')
write_works_manifest(root, '<work_id>', ['<character_a>', '<character_b>'])
write_world_manifest(root, '<work_id>')
print('writer OK')
"

# 4. character manifest 仍通过 schema（已无 build_status）
python3 -c "
import json, jsonschema
from pathlib import Path
schema = json.loads(
    Path('schemas/character/character_manifest.schema.json').read_text()
)
for p in Path('works/<work_id>/characters').glob('*/manifest.json'):
    jsonschema.validate(json.loads(p.read_text()), schema)
print('character manifest OK')
"
```

全部通过。

## 注意事项

- works / world manifest 是 **程序化** 产物，不要让 LLM 去生成——prompt 已
  显式说明。改字段时要同步 schema + writer + validator 三处
- source manifest 仍是 **手写**，由入库规范化 prompt 指导；validator 提供
  后置硬门
- `build_status` 彻底消失，不要再在新代码里回填这个字段
- `created_at` 在 writer 的 idempotent 路径里保留老值——之后若需强制刷新
  时间戳请用独立脚本，不要改 writer
- startup_load 的新顺序意味着 simulation 运行时**必须**先能读到
  `works/{work_id}/manifest.json`；老 work 若还没生成，需要手动调一次
  `write_works_manifest` 补上
