# three-branch-model-library

- **Started**: 2026-04-24 21:38:57 EDT
- **Branch**: master
- **Status**: PRE

## 背景 / 触发

用户当前 workflow 痛点：master 分支跟踪了 `sources/works/<work_id>/manifest.json`，泄漏真实作品 ID。沿伸讨论后用户提出三分支模型：

1. **master** —— 永远干净的框架仓库，对外 push；不含任何作品 ID 命名的目录、源文件、产物文件、真实书名出现在代码 / schema / 文档中
2. **extraction/{work_id}** —— 每部作品独立的提取分支，本地工作流，永不 push
3. **{library}**（新建）—— 完成后的归档分支，本地保存所有 extraction 完成产出，永不 push

用户已确认采用 `library` 作为第三个分支名（在 10 个候选里选了它，与目录名 `works/`/`sources/works/` 形成"单部 → 全集"自然层级）。

原项目规则 "Squash-merge to master on completion"（`ai_context/conventions.md:91`、`decisions.md:81`、`architecture.md:134`、`docs/architecture/extraction_workflow.md`、`automation/persona_extraction/orchestrator.py:1984`）使作品产物注定回流 master，与"master 永远干净"目标冲突，必须改为 squash 到 `library`。

## 结论与决策

- **manifest.json 彻底 ignore**：用 `sources/works/[!_]*/manifest.json` pattern 在 .gitignore 添加，泛化以覆盖未来作品；`_template/` 不受影响
- **现存泄漏文件下架**：`git rm --cached sources/works/<work_id>/manifest.json`
- **squash 目标改为 `library`**：所有 ai_context / docs / 代码 / config 中"squash-merge to master"统一替换；新增 `GitConfig.squash_merge_target` 字段，默认 `"library"`
- **创建 `library` 分支**：从本次 master commit 切出，作为日后所有 extraction 完成时的 squash 归档目标
- **不强制让 library 立即 squash 进当前 in-progress extraction 内容**：当前 `extraction/<work_id>` 仍在进行中，按规则只在完成后 squash；本次仅创建空架构

`library` 分支的同步规则（写入 conventions / architecture）：
- 单向：`master → library`（吸收框架更新，定期 `git merge master`）
- 单向：`extraction/{work_id} → library`（每部完成后 squash-merge）
- **永不**：`library → master`（保持 master 框架洁净）
- **永不**：push 到远程（GitHub 上只有 master）

## 计划动作清单

- file: `.gitignore` → 在 sources 节追加 `sources/works/[!_]*/manifest.json`（保留 `_template/` 豁免）
- file: `sources/works/<work_id>/manifest.json` → `git rm --cached`（保留 working tree 文件，extraction 分支仍能用）
- file: `ai_context/conventions.md` Git 节 → `Squash-merge to master on completion` → `Squash-merge to library on completion (master 不回流)`；补一段 library 分支说明
- file: `ai_context/decisions.md` §26 → 同上"squash to master" → "squash to library"；新增一条决策捕捉三分支模型
- file: `ai_context/architecture.md` Git Branch Model 节 → 引入 library 分支描述
- file: `docs/architecture/extraction_workflow.md` 第 281 / 486 行附近 → squash 目标说明改为 library
- file: `automation/persona_extraction/config.py` `GitConfig` → 新增 `squash_merge_target: str = "library"`
- file: `automation/config.toml` `[git]` 节 → 加注释行（默认走 library，不设值即用代码默认）
- file: `automation/persona_extraction/orchestrator.py` `_offer_squash_merge` → 用 `get_config().git.squash_merge_target` 替换硬编码 `"master"`；docstring 与 print 文案更新
- file: `automation/README.md` § squash-merge 段 → 描述更新
- 分支：`git branch library master`（commit 完成后）

## 验证标准

- [ ] `git ls-files | grep 我和<character_d>` 在 master 上结果为空
- [ ] `grep -rn "squash.*master\|master.*squash" ai_context/ docs/ automation/` 无 stale 引用
- [ ] `python3 -c "from automation.persona_extraction.config import get_config; print(get_config().git.squash_merge_target)"` 输出 `library`
- [ ] `python3 -c "from automation.persona_extraction.orchestrator import Orchestrator"` import 不报错
- [ ] `git branch --list library` 存在
- [ ] master → extraction merge 无冲突；extraction 上 manifest.json 仍 tracked（先于 ignore 提交）

## 执行偏差

无。PRE 计划清单逐条落实。

<!-- POST 阶段填写 -->

## 已落地变更

`.gitignore` (1 处)：sources 节追加 `sources/works/[!_]*/manifest.json` + 注释（保 `_template/` 豁免）。

`git rm --cached`：`sources/works/<work_id>/manifest.json`（master 上下架；working tree 文件保留，extraction 分支 tracked 不变）。

`ai_context/conventions.md` Git 节：单段列表改为三分支表 + flow rules，新增 library 分支语义、squash 目标改 library、`master` 永不接收 artefact。

`ai_context/decisions.md` §26：squash 目标改 library，附三分支模型说明 + `[git].squash_merge_target` 配置出口。

`ai_context/architecture.md` §Git Branch Model：单段改三分支表 + flow rules，与 conventions.md 对齐。

`docs/architecture/extraction_workflow.md:486`：squash 目标 `master` → `library`，明确"不回流 master"。

`automation/persona_extraction/config.py`：`GitConfig` 新增 `squash_merge_target: str = "library"` 字段 + 注释。

`automation/persona_extraction/orchestrator.py:1950-1995`：`_offer_squash_merge` 用 `get_config().git.squash_merge_target` 替换硬编码 `"master"`，docstring 与 print 文案 / 手动指引同步更新。

`automation/config.toml` `[git]` 节：新增 `squash_merge_target = "library"` 配置项 + 三分支模型注释。

`automation/README.md` § squash-merge 段：描述同步更新。

## 与计划的差异

无。

## 验证结果

- [x] `git ls-files master | grep 我和` 为空
- [x] `grep -rnE "squash[^a-z]*master"` 在 ai_context / docs / automation 中无 stale 引用（仅 1 处文法偶合 `checkout_master 函数名` + `squash-merge 漏掉` 不是同一句意，CLEAN）
- [x] `python3 -c "from automation.persona_extraction.config import get_config; ..."` 输出 `squash_merge_target = 'library'`，配置链路通
- [x] `python3 -c "from automation.persona_extraction.orchestrator import ExtractionOrchestrator"` import OK（PRE 误写 `Orchestrator`，实际类名 `ExtractionOrchestrator`，已澄清）
- [ ] `git branch --list library` 存在（待 Step 8 commit 后创建）
- [ ] master → extraction merge 无冲突（待 Step 9）

## Completed

- **Status**: DONE
- **Finished**: 2026-04-24 21:43:10 EDT

<!-- /post-check 填写（与同主题后续补改 log `2026-04-24_215535_requirements-three-branch-followup.md` 合并复审） -->

## 复查结论（对话里有完整报告）

### 轨 1 — 需求落实

- 落实率：本 log 11/11 计划项 + 6/6 验证标准全部 ✅
- Missed updates：0 条

### 轨 2 — 影响扩散

- Findings：High=0 / Medium=2 / Low=2
  - [M] orchestrator 缺 library 分支存在性自检，新环境首次 squash 会静默失败
  - [M] automation/README.md 缺"首次 `git branch library master`"初始化指引
  - [L] session_branch_check.sh 未把 library 列入合法分支白名单（可能误警告）
  - [L] prompts/ingestion / prompts/shared 提及 manifest.json 未标注"已 .gitignore"
- Open Questions：2 条（library 自检策略、hook 白名单；详见对话）

## 复查时状态

- **Reviewed**: 2026-04-24 22:01:51 EDT
- **Status**: REVIEWED-PARTIAL
  - 轨 1 全落实，但轨 2 有 2 条 Medium，按 PASS/PARTIAL/FAIL 标准归 PARTIAL
  - 两条 Medium 都是"未来在新环境跑会卡"性质，当前 session 已手工建 library，运行无阻
- **Conversation ref**: 同会话内 /post-check 输出（含完整双轨报告）
