# Phase 4 scene_archive split 文件完整性保护

日期：2026-04-09

## 背景

scene_archive 的 split 文件在 Phase 4 运行过程中频繁消失。排查发现两个根因：

1. **split 文件被 git track**：`scene_archive/splits/` 不在 `.gitignore` 中，
   且 extraction 分支上已有 68 个 split 文件被 commit。当 Phase 3 执行
   `rollback_to_head()` 时，`git checkout -- .` 会将所有 tracked 文件恢复
   到上次 commit 的版本，导致 Phase 4 新生成的 split 被覆盖或还原。
   之前 `8b5dd86` 的修复（`git clean --exclude`）只保护了 untracked 文件，
   对 tracked 文件无效。

2. **resume 不验证 split 文件存在**：progress.json 中标记为 `passed` 的章节，
   如果对应的 split 文件已丢失，不会被重新生成。最终 merge 时才会报
   `Split file missing` 错误，但此时已无法恢复。

## 变更

### 核心修复

- **`scene_archive.py`**：新增 `verify_passed()` 方法，在 resume 时验证
  所有 `passed` 章节的 `splits/{chapter}.json` 是否实际存在于磁盘。
  缺失的重置为 `pending` 并重新生成。在 `_run_scene_archive_inner` 的
  resume 流程中，紧接 `reset_failed()` 之后调用。

### 根因阻断

- **`.gitignore`**：已包含 `works/*/analysis/incremental/scene_archive/`
  和 `.scene_archive.lock`（commit `8b5dd86` 已添加）
- **extraction 分支**：需执行 `git rm --cached` 移除已 tracked 的 split
  文件和 progress.json（本次未操作，需在切换到 extraction 分支后执行）

### 文档对齐

以下文件统一更新了两点信息：
1. scene_archive 中间产物**不得被 git track**
2. resume 时校验 split 文件存在性

- `docs/requirements.md` — §11.11 断点恢复
- `docs/architecture/extraction_workflow.md` — Phase 4 产出
- `automation/README.md` — Phase 4 说明
- `ai_context/requirements.md` — Phase 4 compressed ref
- `ai_context/architecture.md` — Phase 4 intermediate state
- `ai_context/current_status.md` — Phase 4 feature list
- `ai_context/decisions.md` — 40d 重写（untrack 要求）+ 40e 新增（verify_passed）

## 待执行

切到 extraction 分支后：
```bash
git rm --cached -r "works/我和女帝的九世孽缘/analysis/incremental/scene_archive/"
git commit -m "untrack scene_archive splits（已在 .gitignore 中）"
```
