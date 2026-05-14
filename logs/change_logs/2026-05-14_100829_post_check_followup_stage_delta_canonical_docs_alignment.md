# post_check_followup_stage_delta_canonical_docs_alignment

- **Started**: 2026-05-14 10:08:29 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

上一轮 [/post-check (commit 8f17057 REVIEWED-PARTIAL)](2026-05-14_004411_check_review_followup_cancel_futures_and_doc_alignment.md) 报出 2 M + 1 L + 2 OQ。user 指令"按照你的建议修复"，即按 /post-check Recommendations 段执行：M1 + M2 修（OQ1 候选 a 立刻一行小 commit）；L1 + OQ2 候选 (b)（把 ai_context/decisions.md 列入 §Generic Placeholders Exempt，对齐 M6 处理形态）。

## 结论与决策

**修**（3 条 + 1 policy）：

- **M1**：[docs/architecture/extraction_workflow.md:301-302](../../docs/architecture/extraction_workflow.md#L301-L302) "entry 数变化由 `stage_delta` 自由文本承载" → 改为"由 `stage_delta` 顶层 6-key structured object 内对应 sub-field 的叙述性 text 承载"，与 line 405 已修措辞对齐、与 #55 schema 真值对齐。
- **M2**：[docs/requirements.md:1081](../../docs/requirements.md#L1081) "`stage_delta`：从上一阶段的变化摘要（自由文本）" → 改为"`stage_delta` 顶层是 6-key 结构化对象（`trigger_events` / `personality_changes` / `relationship_changes` / `status_changes` / `mood_shift` / `voice_shift`），每个 sub-field 的内容是叙述性 text"。
- **OQ2 (b)**：[ai_context/conventions.md:104-115](../../ai_context/conventions.md#L104-L115) §Generic Placeholders 第 4 条 "No history narration" 加 decisions.md 豁免——decision log 本质承载历史 / 决策可追溯性需要 provenance 句；与 M6 处理形态对齐（把 archived 加豁免）。落地形态：在 §Generic Placeholders Exempt 行加 `ai_context/decisions.md`。这条 policy 决定同步释放 L1 漂移（[decisions.md:180](../../ai_context/decisions.md#L180) "原 schemas/analysis/world_overview.schema.json 已删除"无需修改）。

**不在本轮 scope**：
- 不全仓扫 decisions.md 其他 provenance 句的"strict 应用 §4 条"路径——OQ2 候选 (a) 被 (b) 否决，本轮一次性确认 decisions.md 豁免地位。

## 计划动作清单

### Docs (M1)
1. [docs/architecture/extraction_workflow.md:301-302](../../docs/architecture/extraction_workflow.md#L301-L302) "entry 数变化由 `stage_delta` 自由文本承载" 一句 → 改为 "由 `stage_delta` 顶层 6-key structured object 对应 sub-field 的叙述性 text 承载"。

### Docs (M2)
2. [docs/requirements.md:1081-1085](../../docs/requirements.md#L1081-L1085) `stage_delta` 字段说明改写为 6-key 结构化对象 + 叙述性 sub-field text；保留 (B) / (D) 捕捉 + "无明显变化"禁令 + 三态规则 ref 不变。

### ai_context (OQ2 policy)
3. [ai_context/conventions.md:114-115](../../ai_context/conventions.md#L114-L115) §Generic Placeholders Exempt 行加 `ai_context/decisions.md`——理由（注释）：decision log 承载历史，provenance 是其原生属性。

## 验证标准

- [ ] M1 + M2：`grep -rn "stage_delta.*自由文本\|stage_delta.*free-text\|stage_delta.*stays free" docs/ extraction/persona_extraction/prompts/ ai_context/` 命中 = 0（与上一轮 /go 同一 grep 标准）。
- [ ] OQ2 (b)：`grep -n "ai_context/decisions.md\b" ai_context/conventions.md` 命中 ≥ 1（Exempt 行）。
- [ ] 文档 markdown 链接锚点未失效（M1 / M2 改的是字段说明，不动 anchor）。

## 执行偏差

无。

## 已落地变更

### Docs (M1)
- [docs/architecture/extraction_workflow.md:301-303](../../docs/architecture/extraction_workflow.md#L301-L303) "entry 数变化由 `stage_delta` 自由文本承载" → "由 `stage_delta` 顶层 6-key structured object 对应 sub-field 的叙述性 text 承载"（保留 phase 3.5 consistency_checker 兜底句不变）。

### Docs (M2)
- [docs/requirements.md:1081-1089](../../docs/requirements.md#L1081-L1089) `stage_delta` 字段说明从"从上一阶段的变化摘要（自由文本）" → 重写为"**顶层是 6-key 结构化对象**（枚举 6 个 subkey 名）+ schema 真值 ref + 每个 sub-field 内容是叙述性 text"，保留 (B) / (D) 捕捉 + "无明显变化"禁令 + 三态规则 ref 不变。

### ai_context (OQ2 (b))
- [ai_context/conventions.md:114-116](../../ai_context/conventions.md#L114-L116) §Generic Placeholders Exempt 行加 `ai_context/decisions.md`。同步释放 [decisions.md:180](../../ai_context/decisions.md#L180) #27i "原 schemas/analysis/world_overview.schema.json 已删除" 漂移（policy 性确认决策日志承载历史，无需逐条剥离）。

## 与计划的差异

无。3 条计划动作 1:1 落地，无新增 / 删除 / 修改。

## 验证结果

- [x] M1 + M2：`grep -rn "stage_delta.*自由文本\|stage_delta.*free-text\|stage_delta.*stays free" docs/ extraction/persona_extraction/prompts/ ai_context/` 仅剩 [docs/requirements.md:1678](../../docs/requirements.md#L1678) L3 semantic validator output 描述（"输出为结构化 Issue list ... 不是自由文本"）+ [docs/todo_list_archived.md:143](../../docs/todo_list_archived.md#L143) archived todo——前者语义是 validator 输出格式（非 stage_delta 描述），后者已纳入 M6 Exempt 列表，两者均非漂移。
- [x] OQ2 (b)：`grep -n "ai_context/decisions.md" ai_context/conventions.md` 命中 line 115 Exempt 行 + 既有 Cross-File Alignment table 引用，合计 4 处，新增 1 处（line 115）。
- [x] 文档 markdown 链接锚点未失效：未动 anchor，链接结构无变化。

## Completed

- **Status**: DONE
- **Finished**: 2026-05-14 10:11:02 EDT
