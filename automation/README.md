# 自动化提取编排器

用脚本驱动 Claude Code CLI（或 Codex CLI）自动完成多批次的世界+角色协同提取。

## 架构

```
orchestrator.py    ← 主循环：分析 → 用户确认 → 提取循环
                      │
  ┌─────────────────┼──────────────────┐
  │                 │                  │
  ▼                 ▼                  ▼
提取 agent      reviewer agent     程序化校验
(claude -p)     (claude -p)        (Python/jsonschema)
```

每个 batch 的流程：

1. Git preflight check（工作区干净、分支正确）
2. 构建 prompt（含文件清单、前批参照、schema 引用）
3. 运行提取 agent（`claude -p`，无人值守）
4. 程序化校验（JSON schema + 结构完整性，不花 token）
5. 语义审校（独立 agent 检查质量和一致性）
6. 通过 → git commit；失败 → rollback + 注入反馈重试

## 依赖

- Python >= 3.11
- `jsonschema`（可选，用于程序化校验。不装也能跑，只是跳过 schema 校验）

```bash
pip install jsonschema   # 一次性，可选
```

## 使用

所有命令从 `automation/` 目录运行：

```bash
cd automation
```

### 完整流程（从分析到提取）

```bash
# work_id 即 sources/works/ 下的目录名
python -m persona_extraction "<work_id>" -r ..

# 指定 backend 和 model
python -m persona_extraction "<work_id>" -r .. -b claude -m opus

# 预设参数（跳过交互选角色）
python -m persona_extraction "<work_id>" -r .. \
    -c 角色A 角色B \
    --end-batch 5
```

### 断点续跑

```bash
python -m persona_extraction "<work_id>" -r .. --resume
```

### 使用 Codex

```bash
python -m persona_extraction "<work_id>" -r .. -b codex
```

### 混合（Claude 提取 + Codex 审校）

```bash
python -m persona_extraction "<work_id>" -r .. -b claude --reviewer-backend codex
```

## 目录结构

```
automation/
├── pyproject.toml
├── README.md
├── prompt_templates/          ← 提取和审校的 prompt 模板
│   ├── analysis.md
│   ├── coordinated_extraction.md
│   └── semantic_review.md
└── persona_extraction/        ← Python 包
    ├── __init__.py
    ├── cli.py                 ← CLI 入口
    ├── orchestrator.py        ← 主循环
    ├── llm_backend.py         ← Claude/Codex 后端抽象
    ├── progress.py            ← 进度追踪和状态机
    ├── validator.py           ← 程序化校验（不花 token）
    ├── prompt_builder.py      ← 上下文感知的 prompt 组装
    └── git_utils.py           ← Git 安全操作
```

## 进度文件

自动生成在 `works/{work_id}/analysis/incremental/extraction_progress.json`。

状态机：

```
pending → extracting → extracted → reviewing → passed → committed
              │                       │
              └→ error                └→ failed → retrying → extracting
```

## 断点恢复

脚本可以在任何状态安全中断：

- `Ctrl+C` → 保存当前进度后退出
- Rate limit → 自动等待后重试
- 脚本崩溃 → 重启后加 `--resume` 从最后一个 committed batch 继续
- 提取失败 → 自动回滚未提交的文件变更
