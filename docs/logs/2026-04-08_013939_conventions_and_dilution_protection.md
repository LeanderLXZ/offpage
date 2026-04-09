# 操作规范文件新增 & 稀释保护强化

**日期**: 2026-04-08 01:39
**触发**: 用户指出 log 文件缺少时间戳，ai_context 的稀释保护不够强

## 问题

1. 两个 log 文件创建时未按 `YYYY-MM-DD_HHMMSS` 格式命名，尽管
   `instructions.md` 中已有此规范
2. ai_context 的稀释保护规则分散在长文件中，对话推进后被推出注意力

## 变更

### 新增 `ai_context/conventions.md`

短而尖锐的操作 checklist，专门设计为对话中途可以快速重读。内容包括：
- Log 文件命名规范（含时间戳获取命令）
- 跨文件对齐表（变更 X 时也需更新 Y、Z）
- 命名和标识符规则
- 数据分离硬规则
- Git 规则
- Post-Change Checklist（5 项）

### 更新 `ai_context/instructions.md`

- 阅读顺序：`conventions.md` 提升为第 1 项
- 稀释保护新增：
  - 规则 5：完成任务后重读 conventions.md 并执行 Post-Change Checklist
  - 规则 6：长会话中每 3-4 个任务重读一次 conventions.md
  - 规则 7：创建 log 文件前必须运行 date 命令获取准确时间戳

### 更新 `ai_context/README.md`

- 阅读顺序：`conventions.md` 加入第 2 位

### 修正 log 文件名

- `2026-04-08_memory_digest_tiered_loading.md` → `2026-04-08_012400_...`
- `2026-04-08_requirements_flowcharts.md` → `2026-04-08_013400_...`

## 修改文件

- `ai_context/conventions.md`（新增）
- `ai_context/instructions.md`
- `ai_context/README.md`
- 两个 log 文件重命名
