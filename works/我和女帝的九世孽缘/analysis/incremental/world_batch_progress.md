# 世界批次进度

执行模式：
- 自动连续模式

当前阶段：
- 世界抽取

当前对象：
- `work_id`: `我和女帝的九世孽缘`
- 总状态文件：`analysis/incremental/extraction_status.md`

最近完成：
- `last_completed_batch_id`: `batch_001`
- `last_completed_range`: `0001-0010`
- `last_completed_stage_id`: `阶段1_南林初遇`

下一批：
- `next_batch_id`: `batch_002`
- `next_batch_range`: `0011-0020`
- `next_batch_goal`: 在累计读取 `0001-0020` 的前提下，确认柳村 / 南林危机是否形成稳定收束，并把阶段 `2` 的当前世界状态与历史事件分开落盘。
- `next_stage_id`: `阶段2`

批次状态：
- `pending`: `batch_002` 至 `batch_054`（详见 `source_batch_plan.md`）
- `in_progress`: 无
- `completed`: `batch_001`
- `blocked`: 无
- `skipped`: 无

阶段状态：
- 当前阶段是否完成：`阶段1_南林初遇` 已完成并已写入 world 包
- 是否允许进入下一阶段：是

阻塞点：
- 当前需要人工决策的事项：无
- 当前缺失的数据：世界层细分 schema 仍未完整定义，当前沿用首批实例格式继续递增

备注：
- 自动选择下一批时采用的规则：先恢复 `in_progress`，否则选择第一个 `pending`
- `batch_id -> stage_id` 的映射规则：`batch_N` 对应 `阶段N`
- 当前阶段是否采用“累计到 1..N”的抽取方式：是
- 本轮修订过哪些旧结论：无；本轮为首个 world batch 落盘
- 同步要求：每次 world 进度变化后，同步更新 `extraction_status.md`
- 当前 world 精简边界：
  - 不再新增 `mysteries/`
  - 不再新增 `knowledge/character_event_awareness/`
  - 关系文件按 `social/stage_relationships/{stage_id}.json` 存储
