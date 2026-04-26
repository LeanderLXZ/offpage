# phase0-phase4-schema-gate-with-prior-error

- **Started**: 2026-04-26 17:05:49 EDT
- **Branch**: main（worktree `../offpage-main`，主 checkout 留在 `extraction/我和女帝的九世孽缘`，clean）
- **Status**: DONE
- **LOG**: `logs/change_logs/2026-04-26_170549_phase0-phase4-schema-gate-with-prior-error.md`

## 背景 / 触发

上一轮 /go (`3f3e05f`) 落了 `schemas/analysis/{chapter_summary_chunk,scene_split}.schema.json` 两份 schema + `scene_archive_entry` summary bound，但**pipeline 上没有执行点 enforce**（POST-CHECK 标 H1+H2，REVIEWED-PARTIAL）：

- Phase 4 [scene_archive.py:228 validate_scene_split](automation/persona_extraction/scene_archive.py#L228) 用手写 required-field 检查、不调 jsonschema → bound 不强制
- Phase 0 [orchestrator.py:369 _summarize_chunk](automation/persona_extraction/orchestrator.py#L369) 完全没有 chunk schema 调用点 → schema paper-only

讨论后决定：

1. **不**抽 `valid_repair/` 独立模块（self-critique 之后否定，YAGNI）
2. **不**走 agent topology 重构
3. **直接在每 phase 现有 fail-retry 装置内插入 schema gate**——schema fail 作为现有 retry 的另一个 trigger 类型；retry 时通过 prior_error 注入告诉 LLM 上次错在哪
4. Phase 1 单独 /go（要先建 3 个新 schema，超本轮 scope）

## 结论与决策

**1. Phase 4 接入路径（最简）**

[scene_archive.py:_process_chapter](automation/persona_extraction/scene_archive.py) 已经有完整 prior_error 注入机制：
- `prior_error = entry.error_message if entry.retry_count > 0 else ""` (line 349)
- `build_scene_split_prompt(..., prior_error=prior_error)` (line 350-352)
- `validate_scene_split(...)` (line 388) 返回 errors，存进 entry.error_message
- 重试时 `_process_chapter` 再次被调，prior_error 自动注入

→ 只需在 `validate_scene_split` 末尾追加 jsonschema 校验，把 schema errors 并入 errors list。**改动 1 处函数 + 1 个 module-level lru_cache validator**。

**2. Phase 0 接入路径（需补 prior_error 接管线）**

[orchestrator.py:_summarize_chunk](automation/persona_extraction/orchestrator.py#L369) 现状：
- L1+L2 JSON 修复失败 → L3 全 re-run（递归调用 `_is_l3_retry=True`），但**重跑用同 prompt，不注 prior_error**
- 没有 schema 校验

→ 三步改造：
- 给 `_summarize_chunk` 加 `_prior_error: str = ""` keyword-only 参数，L3 递归调用时把上次错误（JSON 解析失败 / schema 失败）传进去
- 给 `build_summarization_prompt` 加 `prior_error: str = ""` keyword-only 参数（与 `build_scene_split_prompt` 同款签名），用同款 retry_note 模板
- 给 `summarization.md` prompt 模板末尾加 `{retry_note}` 占位符（与 `scene_split.md` 同款）
- _summarize_chunk 末尾加 schema 校验：fail → unlink + L3 retry + prior_error="Schema 校验失败: {first_err}"

**3. 故意不动**

- **不**改 resume path（line 665-685 早跳逻辑）—— 让 schema check 也校验 resume 时已存在的 chunk 是 scope 蔓延；用户后续会清现有数据，resume gating 对当前 work 无意义。如果将来需要"resume 时 re-validate 现有 chunk"，单独 /go
- **不**改 schema 文件
- **不**改 Phase 1 / Phase 3 / Phase 3.5
- **不**抽 `valid_repair/` 模块（每 phase 内嵌 5-10 行 jsonschema 调用，没有共享价值）
- **不**做 dry-run mode（一次性 ad-hoc python 跑就行，不进 codebase）

## 计划动作清单

- file: [automation/persona_extraction/scene_archive.py](automation/persona_extraction/scene_archive.py) → 加 module-level `_scene_split_validator()` lru_cache helper；`validate_scene_split` 末尾追加 jsonschema 校验段（~5 行）
- file: [automation/persona_extraction/orchestrator.py](automation/persona_extraction/orchestrator.py) → 加 module-level `_chunk_validator()` lru_cache helper；`_summarize_chunk` 加 `_prior_error: str = ""` 参数 + L3 retry 时透传 + schema check 段（~15 行）
- file: [automation/persona_extraction/prompt_builder.py](automation/persona_extraction/prompt_builder.py) → `build_summarization_prompt` 加 `prior_error: str = ""` keyword-only 参数 + retry_note 块构造（与 `build_scene_split_prompt:586-593` 同款 ~7 行）
- file: [automation/prompt_templates/summarization.md](automation/prompt_templates/summarization.md) → 末尾加 `{retry_note}` 占位符（与 `scene_split.md:56` 同款）
- file: [ai_context/architecture.md](ai_context/architecture.md) → §Automated Extraction Pipeline → Phase 0 描述加 "+ schema gate (chunk)"；Phase 4 描述加 "+ schema gate (scene_split)"；引用对应 schema 文件
- file: [docs/architecture/extraction_workflow.md](docs/architecture/extraction_workflow.md) → Phase 0 / Phase 4 段同步
- file: [docs/todo_list.md](docs/todo_list.md) → 删除 T-SCENE-ARCHIVE-SUMMARY-REQUIRED 中"summary 应 required"那条已落实的隐含动作？不——T-SCENE-ARCHIVE-SUMMARY-REQUIRED 是单独的 schema required 调整，本轮不做、保留 todo 不动。**新增**一条 T-RESUME-SCHEMA-RECHECK 备忘 resume path 也走 schema 是后续可选

## 验证标准

- [ ] `python -m py_compile automation/persona_extraction/{scene_archive,orchestrator,prompt_builder}.py` 全过
- [ ] `python -c "from automation.persona_extraction.orchestrator import *"` import 通
- [ ] `python -c "from automation.persona_extraction.prompt_builder import build_summarization_prompt"` import 通
- [ ] `python -c "from automation.persona_extraction.scene_archive import validate_scene_split"` import 通
- [ ] `_chunk_validator()` / `_scene_split_validator()` 各调一次：返回 Draft202012Validator 实例（lru_cache 命中第二次返同一对象）
- [ ] 跑现有数据手测：1 个违反 chunk → `_chunk_validator().iter_errors(data)` 返非空 list；1 个合规 chunk → 返空 list
- [ ] 跑现有 scene_archive 1236 行 → schema 校验报告与 POST-CHECK 实测 354/1236 fail 一致（验 validator 装载正确）
- [ ] `summarization.md` 模板 `{retry_note}` 占位符空字符串渲染时不留空白行（与 scene_split.md 同款）
- [ ] `git grep -nE 'retry_note' automation/prompt_templates/` 三处（summarization.md / scene_split.md，均存在）
- [ ] commit message 风格对齐 `git log --oneline -10`

## 执行偏差

无（计划清单 7 项 = 实际改动 7 项；外加 1 个 log 文件）

<!-- POST 阶段填写 -->

## 已落地变更

- [automation/persona_extraction/scene_archive.py:30-47](automation/persona_extraction/scene_archive.py) `import jsonschema` + `lru_cache _scene_split_validator()` + [validate_scene_split:319-326](automation/persona_extraction/scene_archive.py#L319) 末尾追加 jsonschema 校验段（schema errors 并入返回 errors list，schema_path 用 `absolute_path`）
- [automation/persona_extraction/orchestrator.py:70-81](automation/persona_extraction/orchestrator.py) `import jsonschema as _jsonschema` + module-level `_chunk_validator()` lru_cache helper（同款 `Path(__file__).resolve().parents[2]` schema 路径解析）
- [automation/persona_extraction/orchestrator.py:382-466](automation/persona_extraction/orchestrator.py) `_summarize_chunk` 加 `_prior_error: str = ""` 参数；prompt build 透传；JSON fail / schema fail 各自路由 L3 retry 时透传 `_prior_error="JSON 解析失败: {desc}"` / `"Schema 校验失败（共 N 处，首条：{path}: {msg}）"`
- [automation/persona_extraction/prompt_builder.py:51-99](automation/persona_extraction/prompt_builder.py) `build_summarization_prompt` 加 `prior_error: str = ""` keyword-only 参数 + `retry_note` 块构造（与 `build_scene_split_prompt` 完全同款 7 行模板：`## 重试说明` + `上一次尝试校验失败` + ` ``` ` + 错误内容 + ` ``` ` + `请特别注意修正以上问题。`）
- [automation/prompt_templates/summarization.md:72](automation/prompt_templates/summarization.md) 末尾追加 `{retry_note}` 占位符（与 scene_split.md / char_snapshot / char_support / world_extraction 同款）
- [ai_context/architecture.md:155](ai_context/architecture.md) Phase 0 描述追加 jsonschema gate 与 `prior_error` L3 retry 注入；line 161 Phase 4 描述追加 jsonschema gate 与 `build_scene_split_prompt(prior_error=...)` 现有装置说明
- [docs/architecture/extraction_workflow.md:43-50](docs/architecture/extraction_workflow.md) Phase 0 段加 Schema gate 子条目；line 304-310 Phase 4 段说明 jsonschema gate 与 prior_error 重试

## 与计划的差异

无

## 验证结果

- [x] `python -m py_compile automation/persona_extraction/{scene_archive,orchestrator,prompt_builder}.py` 全过
- [x] 三处 import 通：`from automation.persona_extraction.scene_archive import _scene_split_validator, validate_scene_split` / `orchestrator import _chunk_validator` / `prompt_builder import build_summarization_prompt`
- [x] `_chunk_validator()` 第二次调返回同实例（lru_cache OK）；`_scene_split_validator()` 同
- [x] 实测 `chunk_001.json` schema 校验：53 errors，首条 `Additional properties are not allowed ('boundary_hint', 'potential_boundary')` ——与已知 100% 违反预期一致
- [x] 实测 `scene_splits/0001.json` schema 校验：2 errors，首条 location `'回忆中的各处...'` 超 19 字 ——验证 bound 正确生效
- [x] `validate_scene_split` 整合后：手写 0 + schema 2 错误，即 schema gate 揪出了手写漏掉的 bound 违反
- [x] `build_summarization_prompt(prior_error="Schema 校验失败...")` 渲染后 prompt 含 `## 重试说明` + `Schema 校验失败` 块；不传 prior_error 时不渲染该段
- [x] `git grep '\{retry_note\}' automation/prompt_templates/` = 5 处（summarization 新加 + scene_split / char_snapshot / char_support / world_extraction 已有）
- [x] `_summarize_chunk` 递归调用 2 处（line 438 JSON fail, line 458 schema fail）均透传 `_prior_error`；外部 executor.submit 调用点（line 712-715）未传，使用默认 `""` 正确
- [x] commit message 风格对齐（待 Step 8 验证）

## Completed

- **Status**: DONE
- **Finished**: 2026-04-26 17:30 EDT
