# Phase 4 中间产物回滚保护

日期：2026-04-09

## 背景

排查发现 `works/{work_id}/analysis/incremental/scene_archive/` 与
`.scene_archive.lock` 既不受 git 跟踪，也未被 `.gitignore` 保护。
而 Phase 3 的 `rollback_to_head()` 会执行 repo-wide `git clean -fd`，
导致 Phase 4 断点恢复状态和已生成的 split 文件可能被误删。

## 变更内容

### 实现层防护

- `.gitignore` 新增：
  - `works/*/analysis/incremental/.scene_archive.lock`
  - `works/*/analysis/incremental/scene_archive/`
- `automation/persona_extraction/git_utils.py`
  的 `rollback_to_head()` 新增显式排除项：
  - `works/*/analysis/incremental/.scene_archive.lock`
  - `works/*/analysis/incremental/scene_archive/`
- rollback 日志文案更新为明确说明会保留 `scene_archive` 中间状态

### 文档对齐

- `docs/requirements.md`
- `docs/architecture/extraction_workflow.md`
- `automation/README.md`
- `ai_context/requirements.md`
- `ai_context/architecture.md`
- `ai_context/current_status.md`
- `ai_context/decisions.md`

统一补充以下事实：

- Phase 4 使用独立 PID 锁 `.scene_archive.lock`
- `analysis/incremental/scene_archive/` 为本地忽略的中间目录
- Phase 3 rollback 不会再清掉 Phase 4 的中间产物

## 验证

- `python3 -m py_compile automation/persona_extraction/git_utils.py automation/persona_extraction/scene_archive.py automation/persona_extraction/process_guard.py`
- `git check-ignore -v` 验证 split 文件与 `.scene_archive.lock` 已被忽略
- `git status --short -- works/.../analysis/incremental/scene_archive .../.scene_archive.lock`
  返回空结果，确认已退出工作区噪音
