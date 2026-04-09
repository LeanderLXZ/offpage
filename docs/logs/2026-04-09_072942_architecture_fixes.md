# 架构修复：生成-验证对齐、Schema 扩展、Phase 出口验证、Phase 4 Bug 修复

日期: 2026-04-09
触发: 首次全流程集成测试（Phase 0-4）暴露的四类架构问题

## 变更概述

本次修复解决了首次端到端测试中发现的四类架构级问题，涉及 14 个文件。

## 问题 1：生成-验证断层（P0）

**问题**：validator/consistency_checker 使用 importance-based 阈值检查
target_voice_map / target_behavior_map 的 examples 数量，但 extraction prompt
没有告知 LLM 对应的差异化要求。LLM 不知道哪些 target 需要更多 examples，
生成不足时只能回滚重来，浪费 token。

**修复**：
- `prompt_builder.py`：新增 `_build_quality_requirements()` 和
  `_IMPORTANCE_THRESHOLDS`，从 `candidate_characters.json` 读取 importance，
  构建 markdown 表格注入 prompt context
- `character_extraction.md`：新增 `{quality_requirements}` 模板变量，替换
  原来的固定 "3-5" 要求
- `validator.py`：新增 `_load_importance_map()` / `_min_examples_for_target()`
- `consistency_checker.py`：同步新增 `_min_examples_for_target()`
- 阈值：主角≥5, 重要配角≥3, 其他≥1

## 问题 2：Schema Enum 过窄 + 来源不统一（P1）

**问题**：identity.schema.json 的 alias type enum 缺少 '昵称' 和 '绰号'，
导致 LLM 生成的 alias type 校验失败 → batch 回滚。同时 Phase 1 分析 prompt
使用自由格式的 alias type（如"易容伪装"），与 schema enum 不一致。

**修复**：
- `identity.schema.json`：enum 扩展为 10 个值（+昵称, +绰号）
- `analysis.md`：要求 candidate_characters 的 alias type 使用 schema enum
- `baseline_production.md`：同步更新 alias type 列表
- `docs/requirements.md`：通用要求中更新别名类型枚举

## 问题 3：各 Phase 缺少出口验证（P1）

**问题**：Phase 2.5 产出 identity.json 时 `name: null`（别名的 name 字段
为空），直到 Phase 3 才发现。各 Phase 完成后缺少基本的验证步骤。

**修复**：
- `validator.py`：新增 `validate_baseline()` 函数，校验 identity.json /
  manifest.json / foundation.json 的 schema 合规性和 required 字段非空
- `orchestrator.py`：Phase 2.5 完成后调用 `validate_baseline()`，
  验证失败阻断 Phase 3
- `docs/requirements.md`：新增 §11.4.2 各 Phase 出口验证表

## 问题 4：Phase 4 集成 Bug（P2）

4 个 Bug 全部修复：

| Bug | 修复 |
|-----|------|
| PidLock 阻塞 Phase 4 | `cli.py`：Phase 4 路径移到锁检查之前，有独立的 background 启动路径 |
| `_collect_chapters` 字段名错误 | `scene_archive.py`：解析 `chapters: "0001-0011"` 字符串而非 `chapter_start`/`chapter_end` |
| `_build_chapter_to_stage_map` 字段名错误（新发现） | 同上，导致 scene_archive.jsonl 的 stage_id 为空 |
| character name validation 误杀 | `scene_archive.py`：scene archive 是 work-level，传 `None` 跳过角色名验证 |

## 修改文件清单

| 文件 | 变更类型 |
|------|---------|
| `schemas/identity.schema.json` | enum 扩展 |
| `automation/prompt_templates/analysis.md` | alias type 统一 |
| `automation/prompt_templates/baseline_production.md` | alias type 统一 |
| `automation/prompt_templates/character_extraction.md` | quality_requirements 注入 |
| `automation/persona_extraction/prompt_builder.py` | quality requirements 构建 |
| `automation/persona_extraction/validator.py` | importance-based 阈值 + validate_baseline |
| `automation/persona_extraction/consistency_checker.py` | importance-based 阈值 |
| `automation/persona_extraction/orchestrator.py` | Phase 2.5 出口验证 |
| `automation/persona_extraction/cli.py` | Phase 4 lock bypass |
| `automation/persona_extraction/scene_archive.py` | chapter 解析 + stage_id 映射 + character validation |
| `docs/requirements.md` | §11.4.1, §11.4.2, alias types, target_map |
| `docs/architecture/extraction_workflow.md` | Phase 2.5 验证, target_map 阈值 |
| `automation/README.md` | Phase 4 独立性, baseline 验证 |
| `ai_context/current_status.md` | 同步更新 |
