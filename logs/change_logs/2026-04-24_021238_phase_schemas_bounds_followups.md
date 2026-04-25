# phase_schemas_bounds_followups

- **Started**: 2026-04-24 02:12:38 EDT
- **Branch**: master
- **Status**: PRE

## 背景 / 触发

延续 `phase_schemas_bounds_cleanup`（docs/logs/2026-04-23_203404_*.md）
之后的 /after-check 复查报告。REVIEWED-PARTIAL，3 条 H/M/L finding 需要
补齐：

- **[H]** `schemas/README.md:9,11` — `stage_catalog` 还挂在 `work/` 行，
  `character/` 行未列入。Cross-File Alignment 表第 1 行明列此文件必须
  随 schema 改动同步，上一轮遗漏
- **[M]** `ai_context/handoff.md` — 未提示 world_stage_snapshot 新的
  `timeline_anchor` / `location_anchor` 两个 required 字段会让当前
  extraction 分支上的 S001/S002 产物整批 INVALID，下次 `--resume` 会
  被 repair gate 直接拦
- **[L]** `automation/persona_extraction/post_processing.py:189-195` —
  `_timeline_to_digest` 仍用 `if time_val: ... if location: ...` 条件
  写入 digest 的 time/location；同文件 `generate_world_event_digest`
  已改为无条件写入。两处风格不一致是小技术债

用户决策："修复 H M L"，未涉及 Open Questions（产物迁移策略 + memory_timeline
minLength）—— 那两条继续 open。

## 结论与决策

1. **schemas/README.md**：`work/` 行去掉 `stage_catalog`；`character/`
   行补上 `stage_catalog`。保持行内既有语序。
2. **ai_context/handoff.md**：在合适位置加一条（或短段）advisory，提示
   现有 world_stage_snapshot 实例在新 schema 下 INVALID，需要重跑或
   patch 后才能继续 extraction。写成面向下次接手者的一次性提示。
3. **_timeline_to_digest**：去掉条件守卫，直接 `digest["time"] = entry.get("time", "")` / `digest["location"] = entry.get("location", "")`，与 `generate_world_event_digest` 同风格。memory_timeline 的 time/location 已 required，正常数据不会空——即便空也让 digest schema 校验去拦，不在此处做第二次兜底。

## 计划动作清单

- file: `schemas/README.md` → 两行分类表调整（L9 去 stage_catalog，L11 加 stage_catalog）
- file: `ai_context/handoff.md` → 新增 advisory 段落，提醒 world snapshot 新 required 字段
- file: `automation/persona_extraction/post_processing.py` → `_timeline_to_digest` 的条件守卫改无条件写入

## 验证标准

- [ ] `schemas/README.md` grep `stage_catalog` 出现 2 次（character 行 1 次 + 顶层文字提及 1 次）或仅 character/ 行 1 次
- [ ] `ai_context/handoff.md` 包含 `location_anchor` / `timeline_anchor` 字样
- [ ] `python -c "from automation.persona_extraction import post_processing"` 通过
- [ ] `_timeline_to_digest` 源码内不再出现 `if time_val:` / `if location:` 条件包裹写入
- [ ] 既有 smoke test（合法 memory_timeline entry → 合法 digest）仍通过
- [ ] 全 schema `jsonschema` 自校验通过（未改 schema，理应无影响，但一并跑一次确认）

## 执行偏差

无

<!-- POST 阶段填写 -->

## 已落地变更

- `schemas/README.md` L9 / L11 — `work/` 行去掉 `stage_catalog` 并精简说明为"作品级入库、目录、per-work 加载配置"；`character/` 行加入 `stage_catalog`，说明改为"角色 baseline + 阶段目录 + 阶段快照 + 记忆"
- `ai_context/handoff.md` — Quick Start 之后、"What The User Cares About" 之前新增 **"Extraction-branch artifact drift (resume gate)"** 子段落，列出 2026-04 schema 收口系列造成既有 extraction 产物失效的四处具体点（world snapshot 两锚点、两份 stage_catalog 的 order、fixed_relationships 的 source_type+evidence_refs、memory_timeline 的 scene_refs + time/location），给出三选一的修复路径
- `automation/persona_extraction/post_processing.py` `_timeline_to_digest` — 去掉 `if time_val:` / `if location:` 两个条件守卫，改为与 `generate_world_event_digest` 同样的无条件写入：`"time": entry.get("time", "")` / `"location": entry.get("location", "")`；空值交给下游 digest schema 校验统一拦截

## 与计划的差异

无。3 项均按计划落地。

## 验证结果

- [x] `schemas/README.md` grep `stage_catalog` 出现 1 次（仅 character/ 行），work/ 行已清；顶层文字未单独提及
- [x] `ai_context/handoff.md` 含 `location_anchor` / `timeline_anchor` 字样（新 advisory 子段落内）
- [x] `python -c "from automation.persona_extraction import post_processing, orchestrator, prompt_builder, consistency_checker, validator"` 全部 import OK
- [x] `grep -n "if time_val\|if location" automation/persona_extraction/post_processing.py` 零匹配
- [x] memory_digest 烟雾测试：合法 memory_timeline entry → digest 条目含 time/location（均复制自 timeline），issues 零
- [x] 全 32 份 schema `Draft202012Validator.check_schema` 通过

## Completed

- **Status**: DONE
- **Finished**: 2026-04-24 02:20:00 EDT
