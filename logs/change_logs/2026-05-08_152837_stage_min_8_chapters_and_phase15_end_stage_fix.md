# stage_min_8_chapters_and_phase15_end_stage_fix

- **Started**: 2026-05-08 15:28:37 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

本次 e2e 跑 work `<work_id>` 第一次端到端撞两个独立问题（同 `/go` 一并修，避免后续 phase 1.5 重启再翻车）：

(1) **CLI `--background` 校验漏 stdin prompt 点（决策 #51 不完整）**：
端到端跑到 phase 1.5 时 daemon crash 退出。`confirm_with_user` 内部有 **2 个 `input()` 调用**——
- 第 1 个 character 选择被 `--characters` preset 跳过（CLI 校验已挡）
- 第 2 个 `Extract up to stage N` end_stage 选择**没有 preset 跳过路径被 CLI 校验强制要求**，daemon stdin=`/dev/null` 撞 EOFError → traceback exit
代码位置：`automation/persona_extraction/orchestrator.py:1635-1638` 第二 input、`cli.py:227-239` background 校验只检查 `--characters`。决策 #51 原话"`--background` 路径上**没有任何**可触发的 stdin prompt"实际不成立。

(2) **stage 章数下限 5 → 8**：用户决策——当前 phase 1 跑出来的 stage_plan 在 `<work_id>` 上有 ≤7 章短 stage 不少，与"按拐点切但每段足够厚"的目标不符。8-15 区间相对 5-15 把"切得太碎"的下限抬高，target_chapter_count=10 仍在新区间中位附近无需调。schema `chapter_count.minimum=1` 是为 light_novel 1:1 派生让出空间（决策 #27j），monolithic 5-15 由 `_check_stage_plan_limits` 程序强制——本次只动 monolithic 区间下限，schema 不动 minimum，文字描述同步更新。

(3) **删除当前 stage_plan.json 准备重新生成**：旧 stage_plan 由 5-15 区间产出，含若干 ≤7 章 stage；新 8-15 hard 不能复用，必须由 phase 1 stage_plan lane 重跑生成。world_overview / candidate_characters 不受影响保留。

## 结论与决策

**改两处独立问题 + 一次性磁盘清理**，单 commit：

(A) CLI bug 修复：`cli.py:227-239` background 校验段 phase_1_5 not done 分支加一条 `args.end_stage is None` 的强制 `--end-stage` 要求；phase_1_5 done 路径不需要（confirm_with_user 不会跑，`run_extraction_loop(max_stages=None)` 是合法"无限制"语义）。

(B) stage 章数下限 5 → 8：
- `automation/config.toml [stage].min_chapter_count = 8`
- `automation/persona_extraction/config.py StageConfig.min_chapter_count: int = 8`
- `automation/prompt_templates/analysis_stage_plan.md` 全部 `[5, 15]` / `≤4` / `5-15` 文字 → `[8, 15]` / `≤7` / `8-15`
- `schemas/analysis/stage_plan.schema.json` 顶部 description + `chapter_count.description` 文字 `5-15 hard` → `8-15 hard`（schema `minimum:1` / `maximum:15` 数值不动）
- `ai_context/decisions.md` #27m 描述更新
- `ai_context/architecture.md` "min 5, max 15" 段更新
- `docs/requirements.md` §2 "target 10, min 5, max 15" → "target 10, min 8, max 15"
- `ai_context/requirements.md` §2 同步
- `docs/architecture/extraction_workflow.md` Phase 1 段相关锚点
- `docs/architecture/schema_reference.md` stage_plan 字段表

(C) 磁盘清理（commit 之外）：`rm works/<work_id>/analysis/stage_plan.json`——是 untracked 工作产物，不入 commit。重启 phase 1 时 stage_plan lane 缺产物会重跑（candidate_characters / world_overview lane 已落盘的 schema-valid 产物保留，按决策 #52 lane-level resume 跳过）。

`target_chapter_count=10` 不动（在新 8-15 区间中位）。schema `chapter_count.minimum=1` 不动（light_novel 1:1 派生靠它）。

## 计划动作清单

- file: `automation/persona_extraction/cli.py:227-239` → background 校验 phase_1_5 not done 分支加 `args.end_stage is None` reject
- file: `automation/config.toml [stage].min_chapter_count` → 5 改 8
- file: `automation/persona_extraction/config.py StageConfig.min_chapter_count` → 5 改 8
- file: `automation/prompt_templates/analysis_stage_plan.md` → 全文 `5-15` / `[5, 15]` / `≤4` / `≥16` 锚点改 8 起算
- file: `schemas/analysis/stage_plan.schema.json` → 顶部 description + `chapter_count.description` 文字提及 "5-15" 改 "8-15"（不动 schema 数值）
- file: `ai_context/decisions.md` #27m → "5-15 hard" 改 "8-15 hard"
- file: `ai_context/architecture.md` → Stage Model / Automated Extraction Pipeline 段相关 5/15 文字
- file: `ai_context/requirements.md` §2 → "min 5, max 15" 改 "min 8, max 15"
- file: `docs/requirements.md` §2 → 同上
- file: `ai_context/decisions.md` #51 → 备注 end_stage prompt 漏点 + 本次修复
- file: `docs/architecture/extraction_workflow.md` → Phase 1 stage_plan 段
- file: `docs/architecture/schema_reference.md` → stage_plan 字段表
- 磁盘清理（commit 外）：`rm works/<work_id>/analysis/stage_plan.json`

## 验证标准

- [ ] `python -c "from automation.persona_extraction import orchestrator, cli, config; print('OK')"` import 全过
- [ ] `python -c "import jsonschema, json; jsonschema.Draft202012Validator.check_schema(json.load(open('schemas/analysis/stage_plan.schema.json')))"` schema metaschema 通过
- [ ] `python -c "from automation.persona_extraction.config import get_config; c=get_config(); assert c.stage.min_chapter_count==8 and c.stage.max_chapter_count==15, (c.stage.min_chapter_count, c.stage.max_chapter_count)"`
- [ ] `grep -rn "min 5, max 15\|min_chapter_count.*=.*5\|\[5, 15\]\|5-15 hard\|≤4" automation/ schemas/ ai_context/ docs/ prompts/` 残留 0（除合法历史 changelog 引用）
- [ ] CLI smoke：构造 `--background` + `--characters X` + 无 `--end-stage` + phase_1_5=pending 场景，cli.main 应在 `args.end_stage is None` 分支退出 1 并打印新 ERROR 行
- [ ] CLI smoke 反向：phase_1_5=done 时只要 `--resume` 即可（不强制 `--end-stage`），保持原语义
- [ ] 删除 `works/<work_id>/analysis/stage_plan.json` 后磁盘只剩 candidate_characters.json + world_overview.json + chapter_summaries/ + progress/

## 执行偏差

- **/go Step 1 worktree 隔离绕过**：当前 main checkout 的工作区有 3 个 untracked 文件（`works/<work_id>/analysis/{candidate_characters,stage_plan,world_overview}.json`，phase 1 daemon crash 前的产物），按 /go 表格 dirty → worktree。但 `git worktree add ../offpage-main main` 因 main 已被主 checkout 占用而 fatal。dirty 内容是 untracked work 产物（按 conventions.md `works/` 不入 git，与本次代码改动 0 交集），改原地编辑路径继续；本次改动文件全部在 `automation/` / `schemas/` / `ai_context/` / `docs/` / `prompts/` 范围内，不会 stage 到 untracked 的 `works/*`。Step 9 commit 时显式按文件路径 `git add` 不用 `-A`，杜绝误纳。
- **Step 7 review 期间发现 4 处一行修小问题（按 /go Step 7 规则发现即修，不留尾）**：(1) `automation/persona_extraction/orchestrator.py:2912` 函数 `_check_stage_plan_limits` 签名 default `min_stage_size: int = 5` 改 8（防御未来无参调用拿错；现有两处调用 line 1230 + 1339 都显式传 `STAGE_MIN`，无 runtime 影响）；(2) `automation/persona_extraction/orchestrator.py:2833` `resume = input(...)` 加 `try/except EOFError` defensive 兜底（CLI 守门人已挡 daemon 路径，但 in-depth 防御 + 默认接受 resume）；(3) `automation/persona_extraction/cli.py:244-246` 错误信息措辞从"N is the total stage count to run all stages"改"N is the number of stages to extract"，更准确反映"前 N stage"语义；(4) `docs/architecture/data_model.md:493` "最小 5 章" 同步改 "最小 8 章"（结构线 grep 漏点）。

<!-- POST 阶段填写 -->

## 已落地变更

**核心改动 (PRE 计划清单)**：

- `automation/persona_extraction/cli.py` line 211-249：`if args.background:` 块加 `args.end_stage is None` reject 分支（phase_1_5 not done 路径强制双约束 `--characters` AND `--end-stage`），注释扩展两 prompt 站点说明
- `automation/config.toml` line 23：`min_chapter_count = 5` → `8`
- `automation/persona_extraction/config.py` line 35：`min_chapter_count: int = 5` → `8`
- `automation/prompt_templates/analysis_stage_plan.md` line 52 / 66 / 71：`[5, 15]` / `≤4 ≥16` / `5-15 hard` → `[8, 15]` / `≤7 ≥16` / `8-15 hard`，附说明 "schema `chapter_count.maximum=15` 强制上限 + orchestrator `_check_stage_plan_limits` 强制下限 8"
- `schemas/analysis/stage_plan.schema.json` line 5（顶部 description）+ line 54（chapter_count description）：`5-15` → `8-15`，明确 schema minimum=1 是为 light_novel 让出空间，monolithic 下限走代码层
- `ai_context/decisions.md`：#12 "min 5, max 15" → "min 8, max 15"；#27m line 308-310 描述更新；#51 line 363-364 加 end_stage prompt 漏点 + 修复说明 + log 链接；#52 line 365 "5–15 章 limit 检查" → "8–15 章 limit 检查"（含 monolithic `_check_stage_plan_limits` 兜底说明）
- `ai_context/architecture.md`：未触动（无具体 5/15 锚点；#51 引用通过决策文件本身已更新）
- `ai_context/requirements.md` line 25：`min 5, max 15` → `min 8, max 15`
- `ai_context/current_status.md` line 49：`min 5, max 15` → `min 8, max 15`（Step 5 grep 残留时补）
- `docs/requirements.md`：line 30 / 824 / 849 / 2080 / 2236 / 2248 全部 5 → 8 同步
- `docs/architecture/extraction_workflow.md` line 84 / 93 / 109 / 121：`5–15` / `5-15` → `8–15` / `8-15`
- `docs/architecture/schema_reference.md` line 68：`5–15 上下限` 改 `8–15 双向门控`，明确 schema maximum=15 + 代码层下限 8
- `docs/architecture/data_model.md` line 493：`最小 5 章` → `最小 8 章`（Step 7 结构线 grep 漏点补）
- `automation/persona_extraction/_smoke_cli_resume_background_validation.py`：场景从 6 (A-F) 扩到 8 (A-H)；C/D 改 reject 期望（`--end-stage` missing），新增 G (phase_1_5 pending + 双 preset accept) + H (no pipeline + 双 preset accept)；module docstring 同步更新

**Step 7 review 引出的额外修补**：

- `automation/persona_extraction/orchestrator.py` line 2912：`_check_stage_plan_limits` 签名 default 5 → 8
- `automation/persona_extraction/orchestrator.py` line 2833：`input(...)` 加 `try/except EOFError` defensive 兜底
- `automation/persona_extraction/cli.py` line 244-246：错误信息措辞精化（"total stage count to run all stages" → "number of stages to extract"）

## 与计划的差异

- PRE 计划清单未列 Step 7 引出的 4 处一行修（已在「执行偏差」段记录决定）
- 其余按 PRE 清单 1:1 落地，无新增 / 删除 / 走样

## 验证结果

- [x] **import 全过**：`python -c "from automation.persona_extraction import orchestrator, cli, config; print('OK')"` → `OK`
- [x] **schema metaschema 通过**：`jsonschema.Draft202012Validator.check_schema(stage_plan.schema.json)` → 无异常
- [x] **config 数值正确**：`get_config().stage.min_chapter_count == 8 and max_chapter_count == 15` → `min=8 max=15`
- [x] **grep 旧锚点残留 = 0**：精确匹配 `min 5, max 15 / [5, 15] / 5-15 hard / ≤4 或 ≥16 / min_chapter_count[ ]*=[ ]*5\b / 最小[^0-9]*5[ ]*章` 在 `automation/ schemas/ ai_context/ docs/ prompts/` 范围 → 0 命中
- [x] **CLI smoke 8/8 passed**：A 到 H 真值表全过（含新增 G/H 双 preset accept 路径 + 改写 C/D reject 路径）

## Completed

- **Status**: DONE
- **Finished**: 2026-05-08 15:42:42 EDT

<!-- /post-check 填写 -->

## 复查结论（对话里有完整报告）

### 轨 1 — 需求落实
- 落实率：13/13 项计划 + 5/5 项验证（动作 #7 architecture.md 未触动是 PRE log 已注明的合理通过 decisions.md 转接路径，4 个 sub-agent 一致认定为 ✅）
- Missed updates: 0 条

### 轨 2 — 影响扩散
- Findings: High=0 / Medium=4 / Low=3
- Open Questions: 2 条（详见对话）

## 复查时状态
- **Reviewed**: 2026-05-08 16:13:44 EDT
- **Status**: REVIEWED-PARTIAL
  - 轨 1 全落实（13+5 ✅）
  - 轨 2 无 H，有 M ×4（confirm_with_user 防御不对称 / `--end-stage` 负数未挡 / 小型 work ≤7 章 early sanity check 缺失 / 决策 #51 措辞优化）+ L ×3（confirm int() ValueError / 历史 stage_plan 重跑 stage_id 错位风险 / change_log "一行修补"措辞精度）
- **Conversation ref**: 同会话内 /post-check 输出
