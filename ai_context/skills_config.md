# Skills 配置（项目实例）

由 `.agents/skills/*` 在运行时按需读取。session start **不**默认加载本
文件——只有具体 skill 跑到相关步骤时才读。

每节按本项目实际填写。**节标题（## 开头那一行）必须存在**，缺失整节
会被 skills 视为配置不完整、报错并停手。某节本项目没有此项时，内容
写 `（无）` 或留空，skills 会跳过该节相关步骤。某节列了具体路径但
路径不存在 → skills fail loudly 提示该节漂移。

跨项目移植时改这一份即可，不动 `.agents/skills/*` 正文。

## 后台进程

skills 用它判断"分支 / 工作树是否有运行中的后台工作"，避免误干扰
（如 `/commit` Step 4 forward、`/go` Step 0 自动锁定、`/monitor` 进程盘点）。

- pgrep 模式：
  - `persona_extraction`
- 进程产物：
  - `works/*/analysis/progress/*.pid`
  - `works/*/analysis/progress/*.json`
- 进程日志：
  - `works/*/analysis/logs/`

## 保护分支前缀

skills 用它判断"哪些分支不应被自动 forward / merge 干扰"
（如 `/commit` Step 4、`/go` Step 9 分支同步）。

- 前缀：
  - `extraction/`

## 主分支策略

变更如何流向主分支（`/go` 工作位置自动锁定 / Step 9 同步逻辑的依据）。

- 主分支：`main`
- 规则：代码 / schema / prompt / docs / ai_context / skill 变更先进 main，
  其他分支通过 `git merge main` 前向同步

## 禁提路径

commit 扫描时禁止入库的项目专属路径补充——`.gitignore` +
`ai_context/conventions.md` 之外的项目专属清单（`/commit` Step 2、
`/go` Step 8）。

- `sources/`（原文）
- `*.sqlite*`
- `embeddings/`
- `caches/`
- `works/`（产物）
- `users/`（真实 user packages）

## 源码目录

skills 用它做"实现线"扫描（`/full-review` 工作方式 / `/post-check`
轨 2 实现线）。

- `automation/`
- `simulation/`

## 示例产物目录

skills 用它做"产物 / 模板线"扫描（`/full-review` 工作方式 /
`/post-check` 轨 2 产物结构线）。如示例输出 / 用户模板 / fixture 数据等。

- `works/`
- `users/_template/`

## 核心组件关键词

skills 用它定位关键架构组件做对齐审计（`/full-review` 重点检查项
"orchestrator / validator / consistency checker / post-processing
是否真的兑现文档中的门控与校验承诺"）。

- `orchestrator`
- `validator`
- `consistency checker`
- `post-processing`

## 敏感内容占位规则

写 docs / prompts / ai_context 时禁止出现的真实内容；用占位符代替
（`/go` Step 2 / Step 6、`/post-check` 轨 2 残留检查）。

- 真实业务实体名（如：书名 / 人物 / 客户名 / 私域数据 / 真实用户邮箱）

## 时区

时间戳生成的时区设定（`/go` Step 1 PRE log / Step 7 POST log、
`/full-review` 归档文件名、`/monitor` 单轮 Timestamp）。

- 命令模板：`TZ='America/New_York' date '+%Y-%m-%d_%H%M%S'`
