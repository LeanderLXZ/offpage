# requirements-three-branch-followup

- **Started**: 2026-04-24 21:55:35 EDT
- **Branch**: master
- **Status**: PRE

## 背景 / 触发

上一轮 /go（commit `ce70ccf` 三分支模型）跳过了 Step 2，遗漏了
`docs/requirements.md` 的同步。/post-check 时被发现并打断，本轮 /go 专门补
这一拨。

`docs/requirements.md` 中三处仍然描述旧的"squash to master"流程：

- **L2050-2051**：`全部提取完成后，squash merge 回主分支——main 上只出现一个干净的提取 commit`
- **L2167**：`接受 squash-merge 时，报告必须是 extraction 分支的已提交对象才能进入最终 master commit`
- **L2383**：`[git]` 配置表只列了 `extraction 分支前缀、是否自动 squash-merge`，缺新增的 `squash_merge_target` 字段

## 结论与决策

把这三处统一改成三分支模型描述：squash 目标改为 `library`，明确"不回流 master"，配置表加 `squash_merge_target` 字段。`ai_context/requirements.md` 经查无相关内容，无需改。

## 计划动作清单

- file: `docs/requirements.md:2050-2051` → "squash merge 回主分支——main 上只出现..." → "squash merge 到 `library` 分支（默认目标，可由 `[git].squash_merge_target` 配置）；library 是本地归档分支，作品 artefact 不回流 master"
- file: `docs/requirements.md:2167` → "进入最终 master commit" → "进入最终 squash-merge 的 commit（默认到 `library`）"
- file: `docs/requirements.md:2383` → `[git]` 行新增 `squash_merge_target`

## 验证标准

- [ ] `grep -nE "squash.*master|master.*squash" docs/requirements.md` 无 stale 引用
- [ ] `grep -n "library" docs/requirements.md` 包含 squash 上下文出现
- [ ] master → extraction / library merge 无冲突

## 执行偏差

执行中 Step 6 全仓 grep 时发现 PRE 漏列的第 4 处：`docs/requirements.md:1270`
ASCII 流程图里的 `Squash merge → main`，连带改为 `Squash merge → library`。
不扩大语义范围，属同主题补漏。

<!-- POST 阶段填写 -->

## 已落地变更

`docs/requirements.md` 4 处对齐到三分支模型：

- L2050-2053：squash 目标 `主分支/main` → `library`，明确"不回流 master"，提
  及 `[git].squash_merge_target` 配置出口
- L2169-2171：`进入最终 master commit` → `进入最终 squash-merge 的 commit
  （默认目标 library）`
- L2386：`[git]` 配置表行新增 `squash-merge 目标分支（默认 library）`
- L1270：ASCII 流程图 `Squash merge → main` → `Squash merge → library`（PRE
  漏列，Step 6 grep 时补）

## 与计划的差异

PRE 列了 3 处；POST 增加 1 处（流程图），已在"执行偏差"段记录。

## 验证结果

- [x] `grep -nE "squash.*master|squash.*main|squash.*主分支"` 在 docs/ 与
  ai_context/ 中无 stale 引用（仅 ai_context/architecture.md:142 的 "never
  to master" 是新文案，正确）
- [x] `grep -n "library" docs/requirements.md` 在 squash 上下文中出现（4 个新
  位置）
- [ ] master → extraction / library merge 无冲突（待 Step 9）

## Completed

- **Status**: DONE
- **Finished**: 2026-04-24 21:56:49 EDT

<!-- /post-check 填写（与同主题前置 log `2026-04-24_213857_three-branch-model-library.md` 合并复审） -->

## 复查结论（对话里有完整报告）

### 轨 1 — 需求落实

- 落实率：本 log 4/4 计划项（含执行偏差补的流程图） + 3/3 验证标准全部 ✅
- Missed updates：0 条

### 轨 2 — 影响扩散

- Findings：合并到前置 log（同主题）
- 详见 `2026-04-24_213857_three-branch-model-library.md` 的复查结论段

## 复查时状态

- **Reviewed**: 2026-04-24 22:01:51 EDT
- **Status**: REVIEWED-PARTIAL
  - 本 log 自身轨 1 全落实
  - 轨 2 的 Medium 命中（library 分支自检 + README 初始化指引缺失）属于上一次 commit 的扩散，未在本次补漏 commit 中处理
- **Conversation ref**: 同会话内 /post-check 输出（双 log 合并复审）
