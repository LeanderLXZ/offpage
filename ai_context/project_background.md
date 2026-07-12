<!-- holo:section start -->
<!--
MAINTENANCE — 编辑本文件前请先阅读。
稳定的项目元规则。保持精简；仅在规则本身变化时更新。
Sentinel 纪律（参见 CLAUDE.md §plugin 管理段）：sentinel `<!-- holo:section start/end -->` 内的内容是 plugin canonical，`/holo:update` 会覆写；项目专属新增内容写在 sentinel 之外的 gap 里。
-->
<!-- holo:section end -->

# 项目背景 <!-- holo:heading -->

<!-- holo:section start -->
项目的"为什么" —— 它是什么、解决什么问题、指导原则是什么、
构建顺序是什么。未来的 AI 会话在动代码之前读这里，
理解项目的意图。

本文件保持简短稳定。易变细节（当前状态、路线图）属于
`handoff.md`（`§Current State` 表 + `§Next Steps` 表）。
<!-- holo:section end -->

长期演进的小说角色扮演系统。一个可跨会话更新与加载的
可复用角色资产系统 —— 而非一次性的 prompt 实验。

## 目标 <!-- holo:heading -->

对特定小说角色进行深度、稳定的角色扮演 —— 在长对话与
多次会话中保持一致的性格、记忆、知识边界与行为模式。

## 指导原则 <!-- holo:heading -->

- **深度扮演优先于表面模仿。** 行为 / 决策一致性是首要目标；语气其次。
- **原著小说 = 最高权威。** 所有角色数据均可追溯到原文。
- **增量式，而非从零重来。** 长篇小说分阶段处理；数据随时间积累。
- **分层，而非单个巨型 prompt。** 原文 / 世界 / 角色 / 用户 / 运行时 —— 每一层边界清晰。

## 构建顺序 <!-- holo:heading -->

1. 角色资产系统（schema、数据模型）
2. 提取工作流（阶段化处理、增量更新）
3. 运行时角色扮演引擎（加载、检索、会话管理）
4. 终端集成（agent、app、MCP）

## 权威指针 <!-- holo:heading -->

<!-- holo:section start -->
- 需求细节 → `requirements.md`
- 架构细节 → `architecture.md`
<!-- holo:section end -->
