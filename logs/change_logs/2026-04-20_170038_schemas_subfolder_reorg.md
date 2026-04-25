# schemas/ 按语义分层重组为子目录

## 动机

`schemas/` 扁平地放了 24 个 `*.schema.json`，浏览与审阅都靠文件名前缀
推测归属。按数据模型实际分层组织为子目录更符合 ai_context 架构表述，
也让 `docs/architecture/schema_reference.md` 与 `schemas/` 直接一一对应。
无 `$ref` 跨 schema 引用，没有结构性耦合，迁移仅是机械替换。

## 新布局

| 子目录 | 成员 |
|--------|------|
| `schemas/work/` | `work_manifest`、`stage_catalog` |
| `schemas/world/` | `world_stage_catalog`、`world_stage_snapshot`、`fixed_relationships`、`world_event_digest_entry` |
| `schemas/character/` | `identity`、`character_manifest`、`voice_rules`、`behavior_rules`、`boundaries`、`failure_modes`、`stage_snapshot`、`memory_timeline_entry`、`memory_digest_entry` |
| `schemas/user/` | `user_profile`、`role_binding`、`long_term_profile`、`relationship_core` |
| `schemas/runtime/` | `context_manifest`、`context_character_state`、`session_manifest`、`runtime_session_request` |
| `schemas/shared/` | `source_note` |

每个 schema 的 `$id` 从 `persona-engine/<name>.schema.json` 更新为
`persona-engine/<subdir>/<name>.schema.json`，与文件实际相对路径一致。

## 改动清单

### Schema（`git mv` + `$id` 更新）

- 24 个 `*.schema.json` 按上表分入 6 个子目录，历史保留
- 每个 schema 顶部 `$id` 字段同步加上子目录前缀

### Python 代码（硬编码文件名改成 `<subdir>/<name>`）

- [automation/persona_extraction/prompt_builder.py](../../automation/persona_extraction/prompt_builder.py) — baseline schema 列表、world/char 快照 / memory_timeline schema 读清单条目
- [automation/persona_extraction/validator.py](../../automation/persona_extraction/validator.py) — `fixed_relationships` / `identity` / `character_manifest` / 四份 baseline schema 的查找路径
- [automation/persona_extraction/orchestrator.py](../../automation/persona_extraction/orchestrator.py) — `_build_repair_file_list` 内 7 处 schema 名
- [automation/persona_extraction/post_processing.py](../../automation/persona_extraction/post_processing.py) — memory_digest / world_event_digest / stage_catalog 校验路径
- [automation/repair_agent/protocol.py](../../automation/repair_agent/protocol.py) — 注释指向 `schemas/shared/source_note.schema.json`

### Prompt 模板

- [automation/prompt_templates/baseline_production.md](../../automation/prompt_templates/baseline_production.md) — 9 处 `必须遵循 ...` / `遵循 ...`
- [automation/prompt_templates/character_snapshot_extraction.md](../../automation/prompt_templates/character_snapshot_extraction.md) — stage_snapshot schema 路径
- [automation/prompt_templates/character_support_extraction.md](../../automation/prompt_templates/character_support_extraction.md) — memory_timeline_entry schema 路径
- [automation/prompt_templates/world_extraction.md](../../automation/prompt_templates/world_extraction.md) — world_stage_snapshot schema 路径
- [prompts/shared/最小结构读取入口.md](../../prompts/shared/最小结构读取入口.md) — context_manifest / role_binding 路径

### 文档

- [docs/architecture/schema_reference.md](../architecture/schema_reference.md) — 全文重组：按新 6 层顺序重排章节（Work / World / Character / User / Runtime / Shared），顶部加子目录索引表，所有 schema 标题补路径前缀，新增 `shared/source_note.schema.json` 章节（此前未登记）
- [docs/architecture/data_model.md](../architecture/data_model.md) — 3 处
- [docs/architecture/system_overview.md](../architecture/system_overview.md) — 1 处
- [docs/architecture/extraction_workflow.md](../architecture/extraction_workflow.md) — 1 处
- [docs/requirements.md](../requirements.md) — 4 处
- [docs/todo_list.md](../todo_list.md) — 2 处（relationship_core 链接 + 占位路径）
- [works/README.md](../../works/README.md) — 7 处
- [users/README.md](../../users/README.md) — 1 处
- [simulation/retrieval/index_and_rag.md](../../simulation/retrieval/index_and_rag.md) — 1 处
- [schemas/README.md](../../schemas/README.md) — 替换概览为新的子目录索引表
- [ai_context/conventions.md](../../ai_context/conventions.md) — 对齐表 glob 从 `schemas/*.schema.json` 改为 `schemas/**/*.schema.json`，并把 `schemas/README.md` 加入连带更新清单

### 历史归档不动

- `docs/logs/**` 与 `docs/review_reports/**` 保留旧路径引用——按 conventions
  这些是时间戳冻结的历史快照，不重写；git 历史本身已经反映了迁移事实

## 验证

```bash
# 1. 所有 schema 加载且 $id 与路径一致
python3 -c "
import json, jsonschema, pathlib
root = pathlib.Path('schemas')
for p in sorted(root.rglob('*.schema.json')):
    s = json.loads(p.read_text())
    jsonschema.Draft202012Validator.check_schema(s)
    assert s['\$id'] == f'persona-engine/{p.relative_to(root)}'
print('24 schemas OK')
"

# 2. 关键模块 import
python3 -c "
from automation.persona_extraction import validator, prompt_builder, orchestrator, post_processing
from automation.repair_agent import protocol
print('imports OK')
"

# 3. validator 可以用子目录路径工作
python3 -c "
from pathlib import Path
from automation.persona_extraction import validator
res = validator._validate_schema({}, Path('schemas/character/identity.schema.json'), 'dummy')
assert res  # empty doc → issues
print('_validate_schema accepts subdir paths')
"

# 4. 全库无残留旧扁平路径
rg -n 'schemas/[a-z_]+\\.schema\\.json' -g '!docs/logs/**' -g '!docs/review_reports/**'
# 预期：无输出
```

全部通过。

## 注意事项

- 没有 `$ref` 跨 schema 引用（重组前已确认），未引入新的 `$ref` 以避免
  依赖 `$id` 解析
- `jsonschema.validate(instance, schema_dict)` 用的是 dict 直接传参，不
  依赖 `$id`/`$ref`，所以 `$id` 的字符串值对校验行为无影响——更新
  只是为了语义一致
- 做这次迁移的时间窗：Phase 3 抽取暂停中（master 无 extraction 进程、
  无 pid 锁），下一次 `--resume` 会看到新的 schema 子目录与新的
  prompt_builder 输出，两侧已同步
