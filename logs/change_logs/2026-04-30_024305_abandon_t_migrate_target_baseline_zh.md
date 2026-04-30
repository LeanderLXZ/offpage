# Abandon T-MIGRATE-TARGET-BASELINE-ZH

**Time**: 2026-04-30 024305 EDT
**Action**: 废弃，从 `docs/todo_list.md` ## Next 移到
`docs/todo_list_archived.md` ## Abandoned

## 废弃原因

**前提失效：没有可迁移的对象。**

原 todo 上下文写"现有 phase 2 已 commit baseline 全是英文值，新 schema
校验 fail"。复盘时发现该前提双重错位：

1. **从未入库**：`works/` 目录在 `ai_context/skills_config.md` 的
   `## Do-not-commit paths` 列表内，phase 2 产物 `target_baseline.json`
   从未 commit 到 git。`git log --all --diff-filter=D --name-only --
   '**/target_baseline*'` 无任何匹配；只有 schema/code 改动两次
   （17dd290 加 schema、4939101 中文化）
2. **本地已清空**：当前 work（`works/我和女帝的九世孽缘/`）下
   `analysis/` 只剩 `progress/` 空目录 + 一个 0 字节的
   `rate_limit_pause.json.lock`，没有任何 `target_baseline.json`，也没有
   `characters/` 子树

也就是说既没有"已 commit 的英文 baseline"，本地实际产物也已被清空。
迁移脚本无对象可迁移。

下次 phase 2 重跑时会直接用新中文 schema（4939101 commit）生成 baseline
——relationship_type 走 14 候选中文柔性 string，tier 走"主/重/次/普通"，
不存在英文 → 中文转换问题。

## 替代任务

无。由 phase 2 重跑自然覆盖（属于 `T-PHASE2-TARGET-BASELINE` 的 runtime
验证范围，不需要单独迁移工具）。

## 关联

- 触发 schema 改的 commit：4939101 `schema+code+doc: target_baseline 中文化
  + tier 普通 + targets cap 共享 $ref`
- 同期 followup change log：[logs/change_logs/2026-04-30_014942_target_baseline_zh_and_cap.md](2026-04-30_014942_target_baseline_zh_and_cap.md)
