# 2026-04-22 废弃 Phase 4 原地修复方案 + 清空产物准备整体重跑

## 背景

2026-04-21 晚 `2026-04-21_230811_master-works-cleanup-and-phase4-remerge.md`
记录了 Phase 4 产物的两类状态问题：

1. `scene_archive.jsonl`（1591 条）每条 `stage_id` 仍是旧中文
   `阶段NN_xxx`（`scene_id` 已是 `SC-S###-##`）——stage_id 英文化 refactor
   后的残留
2. `scene_splits/` 从 537 → 213、`phase4_scenes.json` pending 318 / passed
   206 / splitting 9 / failed 4——当晚漏带 `--resume` 误触 LLM 整套重跑、
   中途手动杀进程留下的半损坏中间态

针对这两类问题，上一条 log 末尾登记了两条"立即执行" todo：

- **[T-SCENE-ARCHIVE-STAGE-ID]** 10 行 Python 原地改写 `stage_id`
- **[T-PHASE4-RECONCILE]** 评估 intermediate 文件是否值得重建（选项 A/B/C）

## 决定废弃

用户决定 Phase 4 **整体重跑**（不走原地修复路径），所以：

- T-SCENE-ARCHIVE-STAGE-ID 变得多余：全新 Phase 4 会用 `stage_plan.json`
  作为唯一 stage_id 源，写出的 `scene_archive.jsonl` 天然全是 `S###`
- T-PHASE4-RECONCILE 自动消失：新 Phase 4 会从 pending 空 progress 跑
  完 537 章，scene_splits 也会一并重建，无需任何反向重建工具

## 已执行的清空操作

在 extraction 分支（主 worktree `/home/leander/Leander/persona-engine`）：

```
rm works/我和女帝的九世孽缘/retrieval/scene_archive.jsonl   # 4.3 MB
rm -rf works/我和女帝的九世孽缘/analysis/scene_splits/       # 213 个 .json
rm works/我和女帝的九世孽缘/analysis/progress/phase4_scenes.json  # 85 KB
rm works/我和女帝的九世孽缘/analysis/.scene_archive.lock     # 确保无残留锁
```

全部是 gitignore 文件，git 工作区无改动；下一次运行
`python -m automation.persona_extraction "我和女帝的九世孽缘" --start-phase 4`
（**不带** `--resume`）即走正确的"从空状态全量切场景"路径，并发 LLM
跑 537 章，merge 一次性写出正确 stage_id 的 `scene_archive.jsonl`。

## 后续待办

- **运行时机**：等用户主动发起。本次不自动触发——上次就是为了省事跳过
  了"先和用户对齐再跑"这一步，代价是一堆无效 claude -p。
- **前置检查**：运行前确认 `pgrep -af persona_extraction` 无残留
  orchestrator、无 claude -p 僵尸进程。
- **`[phase4] max_scenes_per_chapter` 上限**：[T-SCENE-CAP] 现已提升到"立即执行"。
  若在 Phase 4 重跑前落地，本次重跑就能直接享受新上限（粗粒度 scene、
  更高 retrieval 命中率）；否则第一次重跑仍可能产出超细场景，之后
  打 T-SCENE-CAP 补丁再跑一次。由用户选择执行顺序。

## todo_list 联动

按 todo_list.md 末尾"任务废弃"规则：

- 从"立即执行"删除 T-SCENE-ARCHIVE-STAGE-ID + T-PHASE4-RECONCILE 两条
- 触发 Step 4 提升（废弃 2 条 → 提升 2 条）：
  - T-CODEX-STDIN ←（原"下一步"首条）
  - T-SCENE-CAP ←（原"下一步"次条）
- "下一步"现暂无条目，不违反"pipeline 不空转"——"立即执行"已有 2 条

## 不需要的动作

- **不改代码**：`scene_archive.py` / `orchestrator.py` / `cli.py` 的 Phase 4
  入口本身无 bug，事故根因是当时我漏带 `--resume`。把强校验加进
  `--start-phase 4` 入口（原 T-PHASE4-RECONCILE 选项 C）作为防呆是独立
  的工程选项，但用户当前不选 A/B/C，直接重跑即可。若日后想做，单独开一条
  todo 即可。
- **不动 ai_context / architecture**：无架构变更。
- **不动 schema / prompt**：Phase 4 产物 schema 未变，prompt 未变。
