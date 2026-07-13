# abandon T-PLUGIN-README

- **Started**: 2026-07-13 04:01 EDT
- **Branch**: main
- **Status**: ABANDONED

## 废弃原因

前提消失——任务被 holo 插件取代：

1. **原任务的场景已不存在**：T-PLUGIN-README（2026-04-28 立项）的背景是
   "新项目接 plugin 需手动复制 `.agents/skills/` + `.claude/commands/` +
   照散落的注释填一份 `skills_config.md`"，所以需要一份 README 当 setup
   入口文档。
2. **这套 skill plugin 已产品化为 holo 插件**（本仓库当前用 1.18.0）：
   新项目接入走 `/holo:init` 交互式初始化（收集语言轴 + 项目答案、落地
   CLAUDE.md / AGENTS.md / skills_config.md / `.agents/skills/` 镜像等
   全套骨架），后续升级走 `/holo:update`（模板盘点 + 漂移检测 +
   smart-merge）。原 README 要承载的"每节怎么填 / 缺失行为 / 模板"
   信息由插件模板与 init/update 流程自身承接，手写 README 不再需要。

## 后续如有需要

若 holo 插件本身需要面向新用户的 setup 文档，那属于插件仓库的职责，
在插件侧立项；本项目内不再跟踪。

## 关联

- 原 todo 条目：见本 commit 前 `docs/todo_list.md` ## Next 段（git 历史）
- holo 骨架落地 commit：`a2a3c11 holo_init_skeleton_zh`
