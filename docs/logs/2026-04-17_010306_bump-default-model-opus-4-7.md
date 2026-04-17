# 默认抽取模型升级 opus 4.6 → opus 4.7

## 变更

- `automation/persona_extraction/cli.py`
  `--model` 默认值: `claude-opus-4-6` → `claude-opus-4-7`
  help 文案同步。

## 原因

Opus 4.7 已发布,作为 Claude 4.x 家族最新最强模型,作为抽取默认更合适。
`--effort max` 与 `--max-turns 50` 保持不变。

## 影响范围

- 仅改默认值,未动 `llm_backend.py` 透传逻辑。
- Codex backend 不受影响(不透传 effort,仅接收 `--model`)。
- Reviewer backend 复用同一 model,自动跟随升级。
- 用户显式 `-m xxx` 覆盖行为不变。

## 验证

- `python -m automation.persona_extraction --help` 应显示新 default。
- Claude CLI `--model claude-opus-4-7` 由 CLI 侧解析,本仓库不做别名映射。
