# offpage — Claude Entry Point <!-- holo:heading -->

<!-- holo:section start -->
本文件由 Claude 在会话开始时自动加载。保持简短 ——
详细上下文放在 `ai_context/`，不在此处。

> **plugin 管理段（sentinel 契约）。** 段头带 `<!-- holo:heading -->`
> + 段内被 `<!-- holo:section start --> ... <!-- holo:section end -->`
> 包裹的内容是 plugin canonical 内容。plugin 升级时（`/holo:update`），
> 这些区域通过 extract-and-reformat smart-merge 用新 plugin 模板重填 ——
> 用户内容（sentinel 之间的 gap）保留；plugin canonical 内容（sentinel
> 内）跟随新模板。**不可退出**：删除 marker 不会"分离"段所有权 ——
> 下一次 `/holo:update` 会通过 extract-and-reformat smart-merge
> 重新对齐 sentinel 结构（详见 `ai_context/decisions.md` §Skill
> Implementation #18）。需要永久自定义段内容的 consumer 请 fork 整个
> plugin。完整设计见 `docs/architecture/section-version-sentinel.md`。
>
> **sentinel `<!-- holo:section start/end -->` 内的编辑会在下一次
> `/holo:update` 时被覆写。** 项目专属新增内容必须写在
> `<!-- holo:section end -->` 到下一个 sentinel-start /
> heading-sentinel 之间的 gap 里。
<!-- holo:section end -->

## 语言 <!-- holo:heading -->

<!-- holo:section start -->
对**每一次**对话生效，不只是首轮。代码标识符与字段名保持英文。
<!-- holo:section end -->

- `content_language: zh` —— 落盘类输出（docs / logs / commits /
  skill 输出 / 新增代码注释）
- `conversation_language: zh` —— AI ↔ 用户对话

## 会话开始：通读 ai_context/ 一次 <!-- holo:heading -->

<!-- holo:section start -->
在**每个新会话**开始时，按 `ai_context/instructions.md` 指定的
顺序通读整个 `ai_context/` 目录：

1. `instructions.md`
2. `project_background.md`
3. `requirements.md`
4. `architecture.md`
5. `conventions.md`
6. `decisions.md`
7. `handoff.md`

读完后，**停下来等待用户指令。** 不要自行开始修改代码、schema 或
文档。
<!-- holo:section end -->

## 默认不加载的内容 <!-- holo:heading -->

<!-- holo:section start -->
参见 `ai_context/instructions.md` §阅读范围 中本项目专属的清单。

通用规则：除非任务明确要求，否则不要扫描大型原始输入、完整对话
历史、整个日志目录、生成产物、数据库、向量库及索引。
<!-- holo:section end -->

## 行动 vs. 加载 <!-- holo:heading -->

<!-- holo:section start -->
读 `ai_context/` 是上下文加载，不是任务说明。只在用户显式请求时
行动。如果在阅读过程中发现异常，记录下来并等待 —— 不要主动修复。
<!-- holo:section end -->

## 稀释自查 <!-- holo:heading -->

<!-- holo:section start -->
长会话会导致静默遗忘。在编辑代码、schema 或文档之前 —— 以及任何
任务类型切换之后 —— 暂停并回答：

1. **范围检查**：我做的是用户要求的那件事，还是扩展到了主动重构
   /"顺手改一下"？若扩展了 → 停下来先问。
2. **正确层级**：我即将编辑的文件是否位于此关注点所属的正确模块 /
   层？若不确定 → 重读 `ai_context/architecture.md`。
3. **对齐检查**：在收尾一组改动前，对照 `ai_context/conventions.md`
   中的 Cross-File Alignment 表 —— 是否更新了每一个下游文件？

如果任一答案是"我不记得了"或"我在猜" → 在继续之前重读相关的
`ai_context/` 文件。
<!-- holo:section end -->

## 与 AGENTS.md 保持同步 <!-- holo:heading -->

<!-- holo:section start -->
本文件与 `AGENTS.md` 保持**完全一致**，仅标题行不同（"Claude
Entry Point" vs. "Agent Entry Point"）。对其中之一的任何改动
必须在同一次 commit 中镜像到另一文件。
<!-- holo:section end -->
