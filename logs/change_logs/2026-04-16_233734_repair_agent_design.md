# Repair Agent 框架设计

日期: 2026-04-16
状态: 设计完成，待实现

## 背景

现有 validation/fix 系统的问题:
1. 修复 = 回滚重提取 (每次 20+ min)，但大部分问题不需要重跑提取
2. review_lanes / commit gate / lane retry / gate cascade 深度耦合在 orchestrator 中 (~550 行)
3. 语义审校标准模糊，误触发回滚
4. 各 phase 各用一套校验逻辑 (Phase 0 json_repair, Phase 2.5 validate_baseline, Phase 3 review_lanes, Phase 3.5 consistency_checker)

## 核心原则

**就地修复，逐层升级，永不回滚。**

- 修复粒度是字段级，不是文件级
- Fixer 从最低可用层开始尝试，每层有重试次数，用尽后升级到下一层
- 全文件重生成是最后手段，几乎不触发
- 语义检查只在首检和终检各调用一次 LLM，中间修复循环全部程序化

## 架构总览

```
automation/repair_agent/           ← 独立模块，所有 phase 统一调用
├── __init__.py                    # 统一入口: run(), validate_only()
├── coordinator.py                 # 编排: check → fix → recheck 循环
├── protocol.py                    # Issue, RoundReport, RepairAttempt 等数据类
├── tracker.py                     # 跨轮次 diff, 收敛/regression 检测
├── context_retriever.py           # chapter_summaries 定位 → 原始章节加载
├── field_patch.py                 # json_path 精准替换
├── checkers/
│   ├── __init__.py                # BaseChecker + CheckerPipeline
│   ├── json_syntax.py             # L0: JSON 解析 + 编码
│   ├── schema.py                  # L1: jsonschema 校验
│   ├── structural.py              # L2: 业务规则 (计数/长度/ID格式/深度)
│   └── semantic.py                # L3: LLM 语义审校 → 结构化 Issue list
└── fixers/
    ├── __init__.py                # BaseFixer + 注册
    ├── programmatic.py            # T0: json repair + schema autofix
    ├── local_patch.py             # T1: 字段级微修补 (不需原文)
    ├── source_patch.py            # T2: 字段级原文修补 (定位章节→加载→修)
    └── file_regen.py              # T3: 全文件重生成

prompt_templates (复用现有目录或新建):
    ├── semantic_review.md         # L3 语义审校 prompt (输出结构化 Issue)
    ├── local_patch_fix.md         # T1 微修补 prompt
    ├── source_patch_fix.md        # T2 原文修补 prompt
    └── file_regen.md              # T3 全文件重生成 prompt
```

## 统一调用接口

```python
from automation.repair_agent import run as repair, validate_only

# 任何 phase 都用同一个接口
result = repair(
    files=[
        FileEntry(
            path="characters/角色A/stage_snapshots/阶段03.json",
            schema=load_schema("stage_snapshot"),
        ),
        FileEntry(
            path="characters/角色A/canon/memory_timeline/阶段03.json",
            schema=load_schema("memory_timeline"),
        ),
    ],
    config=RepairConfig(
        max_rounds=5,
        block_on="error",           # "error" 或 "all" (含 warning)
        run_semantic=True,           # 是否启用 L3
        retry_policy=RetryPolicy(),  # 可覆盖默认重试次数
    ),
    # T2 需要的上下文 (可选)
    source_context=SourceContext(
        work_path="works/某作品",
        stage_id="阶段03_某事件",
        chapter_summaries_dir="analysis/chapter_summaries",
        chapters_dir="../../sources/works/某作品/chapters",
    ),
)

if result.passed:
    proceed()
else:
    log_report(result.report)

# 纯检查模式 (Phase 3.5, 或手动审查)
issues = validate_only(files=..., run_semantic=False)
```

## 数据协议

### Issue — 检查器的统一输出

```python
@dataclass
class Issue:
    file: str              # 文件路径
    json_path: str         # "$.voice_state.target_voice_map.角色B"
    category: str          # "json_syntax" | "schema" | "structural" | "semantic"
    severity: str          # "error" | "warning"
    rule: str              # 检查规则 ID, 如 "min_examples", "schema_required"
    message: str           # 人可读描述
    context: dict | None   # 给 fixer 的额外信息 (期望值/当前值/建议等)

    @property
    def fingerprint(self) -> str:
        """同一文件、同一位置、同一规则 = 同一问题"""
        return f"{self.file}::{self.json_path}::{self.rule}"
```

### FileEntry — 输入文件描述

```python
@dataclass
class FileEntry:
    path: str              # 文件路径 (相对于 work_path 或绝对)
    schema: dict | None    # JSON Schema (None = 跳过 schema 检查)
    content: dict | list | None = None  # 预加载内容 (None = 从 path 读取)
```

### RoundReport — 每轮修复后的 diff

```python
@dataclass
class RoundReport:
    resolved: list[Issue]      # 上轮有，这轮没了
    persisting: list[Issue]    # 上轮有，这轮还在
    introduced: list[Issue]    # 上轮没有，这轮新出现 (regression)
```

### RepairAttempt — 单次修复记录

```python
@dataclass
class RepairAttempt:
    issue_fingerprint: str
    tier: int                  # 0/1/2/3
    attempt_num: int           # 该层第几次
    strategy: str              # "standard" / "with_context" / "expanded_chapters"
    result: str                # "resolved" | "persisting" | "regression"
```

### RepairResult — 最终输出

```python
@dataclass
class RepairResult:
    passed: bool
    issues: list[Issue]                    # 剩余未解决的 issues
    history: dict[str, list[RepairAttempt]]  # fingerprint → 修复历史
    report: str                            # 人可读报告
```

## Checker 四层架构

### 依赖关系 (严格顺序)

```
L0 json_syntax → L1 schema → L2 structural → L3 semantic
     ↑ 前一层有 error 的文件，后续层跳过该文件
```

### L0 json_syntax (0 token)
- 文件存在
- JSON/JSONL 可解析
- UTF-8 编码

### L1 schema (0 token)
- jsonschema 全字段校验
- required / type / enum / additionalProperties / minLength / maxLength

### L2 structural (0 token)
- 业务深度规则，从规则配置读取，不硬编码:
  - target_voice_map / target_behavior_map 示例数阈值
  - memory_id / event_id 格式 (M-S###-##, E-S###-##)
  - event_description 150-200 字, stage_events 50-80 字
  - digest_summary 30-50 字
  - knowledge_scope 条目上限
  - stage_id 与预期一致
  - relationships 必须有 driving_events
  - character_arc 与 stage_delta 共存
  - catalog / digest 完整性 (现有 commit gate 的结构检查并入此层)

### L3 semantic (LLM)
- 内容事实正确性
- 阶段间连贯性 (数值跳变、关系突变)
- 关系描述与行为描述一致性
- stage_delta 与实际变化一致性
- 输出: 结构化 Issue list (JSON array), 不是自由文本

## Fixer 四层架构

### 层级与起始 tier

每个 issue 从其 category 决定的最低可用 tier 开始尝试:

```python
START_TIER = {
    "json_syntax":  0,   # T0 能修
    "schema":       0,   # T0 能修
    "structural":   0,   # T0 可能能修, 不行升 T1
    "semantic":     1,   # T0 程序化修不了语义, 从 T1 开始
}
```

### T0 programmatic (0 token)
合并现有 json_repair.py L1 + schema_autofix.py:
- JSON 语法修复 (转义、尾逗号、截断闭合)
- schema 违规修复 (截断/填充/类型转换/enum 模糊匹配/补空字段)
- ID 格式正则替换
- 尝试次数: 1 (要么行要么不行)

### T1 local_patch (少量 token)
字段级微修补，不需要原文:
- 补写示例 (根据同文件上下文)
- 调整数值 (根据 issue 描述)
- 补充缺失子字段 (根据 schema + 现有数据推断)
- 尝试次数: 3, 每次换策略:
  - 尝试 1: 标准 prompt + issue 描述
  - 尝试 2: 加同文件其他相关字段作为参考
  - 尝试 3: 加前一阶段同字段值作为连续性参考

### T2 source_patch (中等 token)
字段级原文修补，需要回到原始章节:
- 事实性错误修正
- 遗漏事件补充
- 关系偏差修正
- 尝试次数: 3, 每次扩大上下文:
  - 尝试 1: chapter_summaries 定位 → top-3 相关章节原文
  - 尝试 2: 扩大到 top-5 章节, 含相邻章节
  - 尝试 3: 该阶段全部章节原文

### T3 file_regen (大量 token)
全文件重生成，极少触发:
- 只在 >50% 字段有 error 级 issue 时才走此路
- 整个文件 + 完整上下文 → LLM 重新生成
- 尝试次数: 1

### 重试策略配置

```python
@dataclass
class RetryPolicy:
    t0_max: int = 1
    t1_max: int = 3
    t2_max: int = 3
    t3_max: int = 1
    max_total_rounds: int = 5   # 整个 validate→fix 循环上限
```

## 修复流程

### 总体三阶段

```
阶段 A: 首次全量检查 (1 次)
  L0 → L1 → L2 → L3(semantic)
  产出完整 issue list
  semantic checker: LLM 第 1 次

阶段 B: 修复循环 (多轮)
  按 issue 分组处理, 从最低可用 tier 开始逐层升级
  每次 fix 后: scoped recheck (只 L0+L1+L2, 只检查被 patch 的字段)
  semantic checker: 不调用

阶段 C: 最终语义复核 (至多 1 次)
  只在阶段 A 发现过 semantic issue 时才跑
  只复核有过 semantic issue 的字段
  semantic checker: LLM 第 2 次 (范围缩小)
```

### 阶段 B 内部: 单个 issue 的修复历程

```
issue X (category=structural)

  从 START_TIER[structural] = 0 开始:
  ├─ T0 尝试 1 → scoped recheck → persisting (程序化修不了)
  │   → T0 用尽 (max=1), 升级到 T1
  ├─ T1 尝试 1 (标准 prompt) → scoped recheck → persisting
  ├─ T1 尝试 2 (加同文件上下文) → scoped recheck → persisting
  ├─ T1 尝试 3 (加前阶段参考) → scoped recheck → persisting
  │   → T1 用尽 (max=3), 升级到 T2
  ├─ T2 尝试 1 (top-3 章节) → scoped recheck → resolved ✓
  └─ 完成
```

### 阶段 B 内部: 批量处理策略

同一 tier 的 issues 可以批量处理:
- T0: 全部一次性程序化修复
- T1: 同一文件的多个 T1 issues 可合并成一次 LLM 调用 (发多个 issue + 多个子树)
- T2: 每个 issue 独立 (因为需要不同的章节上下文)

### Scoped Recheck

fix 一个字段后, 不重跑全部 checker:

```python
def scoped_recheck(file, patched_paths: list[str]) -> list[Issue]:
    new_issues = []
    for path in patched_paths:
        subtree = extract_subtree(file.content, path)
        sub_schema = extract_sub_schema(file.schema, path)
        new_issues += schema_checker.check_subtree(subtree, sub_schema, path)
        new_issues += structural_checker.check_subtree(subtree, path)
    # 跨字段全局一致性 (少量规则)
    new_issues += structural_checker.check_cross_field(file.content)
    return new_issues
```

只跑 L0 + L1 + L2, 不跑 L3 semantic (留到终检)。

### Issue 追踪与安全阀

每轮 fix 后, tracker 做 diff:

```python
def diff_rounds(prev, curr) -> RoundReport:
    prev_fps = {i.fingerprint: i for i in prev}
    curr_fps = {i.fingerprint: i for i in curr}
    return RoundReport(
        resolved   = [prev_fps[fp] for fp in prev_fps if fp not in curr_fps],
        persisting = [curr_fps[fp] for fp in curr_fps if fp in prev_fps],
        introduced = [curr_fps[fp] for fp in curr_fps if fp not in prev_fps],
    )
```

安全阀:
- regression 保护: 一轮修复的 introduced ≥ resolved → 停止该 tier, 升级
- 收敛检测: 连续两轮 persisting 指纹完全一致 → 该 tier 修不动, 升级
- 总轮次上限: max_total_rounds (default 5) 到了直接停机出报告

## Context Retriever (T2 用)

```python
class ContextRetriever:
    """两步定位: chapter_summaries 搜索 → 原始章节加载"""

    def retrieve(self, issue, stage_id, work_path, source_path,
                 attempt_num, max_attempts) -> str:
        # Step 1: 在 chapter_summaries 中搜索关键词 (0 token)
        #   关键词来源: issue.json_path 中的角色名, issue.message
        #   定位到相关章节编号
        #
        # Step 2: 加载原始章节文本
        #   attempt 1: top-3 章节
        #   attempt 2: top-5 章节 + 相邻章节
        #   attempt 3: 该阶段全部章节
        #
        # 返回: 拼接的原文片段
```

chapter_summaries 仅用于定位 (索引), 不作为修复上下文。
修复上下文 = 原始章节文本 (sources/works/{work_id}/chapters/)。

## Field Patch

```python
def apply_field_patch(original: dict, json_path: str, new_value: Any) -> dict:
    """只替换指定 json_path 的值, 其他字段完全不动"""
    # 保持原始 key 顺序
    # 不修改其他字段
    # 返回修改后的完整 dict
```

所有 fixer (T0-T3, T3 除外) 都通过 field_patch 写回, 保证手术式精准修改。

## 现有代码的替代关系

| 现有文件 | 新框架 | 处理方式 |
|---|---|---|
| `validator.py` | `checkers/schema.py` + `checkers/structural.py` | 重写, 拆分 |
| `schema_autofix.py` | `fixers/programmatic.py` | 合入 T0 |
| `json_repair.py` | `fixers/programmatic.py` (L1 部分) + `checkers/json_syntax.py` | 合入 |
| `review_lanes.py` | **删除** | 全部职责被 coordinator + checkers + fixers 替代 |
| `consistency_checker.py` | `checkers/structural.py` (cross_stage 模式) | 合入 |
| `post_processing.py` | **保留不动** | 不属于 repair_agent, orchestrator 继续直接调用 |
| `prompt_builder.py` 中 review/fix 相关 | `repair_agent/` 内的 prompt 构建 | 迁移 |
| orchestrator.py Step 4 (~550行) | ~10 行 `repair(files, config)` 调用 | 大幅简化 |

## 各 Phase 的调用方式

### Phase 0 (章节摘要)
```python
result = repair(
    files=[FileEntry(path=summary_path, schema=summary_schema)],
    config=RepairConfig(run_semantic=False),  # 摘要不需要语义审校
)
```

### Phase 2.5 (baseline)
```python
result = repair(
    files=[
        FileEntry(path=identity_path, schema=identity_schema),
        FileEntry(path=voice_rules_path, schema=voice_rules_schema),
        ...
    ],
    config=RepairConfig(run_semantic=True),
    source_context=SourceContext(work_path=..., chapters_dir=...),
)
```

### Phase 3 (stage extraction, 替代现有 review_lanes + commit gate)
```python
# 提取完成 + post_processing 完成后:
result = repair(
    files=[
        FileEntry(path=world_snapshot, schema=world_schema),
        FileEntry(path=char_snapshot, schema=snapshot_schema),
        FileEntry(path=memory_timeline, schema=timeline_schema),
        FileEntry(path=stage_catalog, schema=catalog_schema),
        FileEntry(path=memory_digest, schema=digest_schema),
        FileEntry(path=world_event_digest, schema=event_digest_schema),
    ],
    config=RepairConfig(run_semantic=True, block_on="error"),
    source_context=SourceContext(...),
)
if result.passed:
    commit_stage(...)
```

### Phase 3.5 (跨阶段一致性)
```python
# 纯检查, 不修复
issues = validate_only(
    files=all_stage_files,
    checkers=["structural"],  # 只跑 cross_stage 规则
    run_semantic=False,
)
```

## 与 orchestrator 的集成

orchestrator.py 的 _process_stage 方法中, 现有 Step 4 (review lanes, ~550 行)
+ Step 5 (commit gate) 替换为:

```python
# Step 4: Validate + Repair
result = repair(
    files=collect_stage_files(pipeline, stage),
    config=RepairConfig(run_semantic=True),
    source_context=SourceContext(
        work_path=work_dir,
        stage_id=stage.stage_id,
        chapter_summaries_dir=analysis_dir / "chapter_summaries",
        chapters_dir=source_dir / "chapters",
    ),
)

if not result.passed:
    stage.transition(StageState.ERROR)
    stage.error_message = result.report
    phase3.save(self.project_root)
    return

# Step 5: Git commit (不变)
```

不再需要: lane retry, rollback_lane_files, commit gate, gate cascade,
lane_retries dict, lane_max_retries, POST_PROCESSING_RECOVERABLE,
_re_extract_and_post_process, review_filter, outer_round 等。
