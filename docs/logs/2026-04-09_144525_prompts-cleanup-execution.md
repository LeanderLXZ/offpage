# prompts/ 清理执行

日期：2026-04-09

## 背景

2026-04-08 讨论并记录了 prompts/ 清理方案
（见 `2026-04-08_085905_prompts_cleanup_and_module_encapsulation.md`），
但文件删除和新建部分因 worktree 丢失未被提交。本次补做执行。

## 变更内容

### 删除 16 个废弃文件

**prompts/analysis/**（7 个，已被 `automation/prompt_templates/` 替代）：
- 世界信息抽取.md
- 候选角色识别.md
- 全书总体分析.md
- 全流程提取编排.md
- 批次修订与冲突合并.md
- 源文件分批规划.md
- 角色信息抽取.md

**prompts/runtime/**（6 个，已迁入 `simulation/prompt_templates/` 或被
`simulation/flows/` 覆盖）：
- 历史回忆处理规则.md
- 认知冲突处理规则.md
- 会话稀释保护检查清单.md
- users状态回写.md
- 写回前防污染检查清单.md
- 用户入口与上下文装载.md

**prompts/shared/**（3 个，已被 automation 代码化）：
- 批次执行检查清单.md
- 批次交接模板.md
- 自动批处理进度模板.md

### 新建

- `prompts/review/手动补抽与修复.md` — 自动化完成后的局部补充和修正

### 修复

- `prompts/README.md` — 全面重写，仅列出 4 个保留模板
- `prompts/review/数据包审校.md` — 移除对已删文件的引用，术语改为"防漂移机制"
- `prompts/ingestion/原始资料规范化.md` — 移除对已删文件的引用，术语改为"防漂移机制"
- `ai_context/handoff.md` — 新增文档脱敏规则

### prompts/ 最终结构

```
prompts/
  README.md
  ingestion/原始资料规范化.md
  review/数据包审校.md
  review/手动补抽与修复.md
  shared/最小结构读取入口.md
```

## 验证

- 全库 grep 确认无活跃代码或文档引用已删除文件
- 仅 docs/logs/ 历史记录中有旧路径引用（预期行为）
