**Review 模型**：Claude Opus 4.7（`claude-opus-4-7`）

# /check 全仓库对齐审计 — 2026-04-20

**审计范围**：`ai_context/` → `docs/`（requirements、architecture） →
`schemas/` → `automation/`（persona_extraction、repair_agent、prompt_templates） →
`simulation/`（contracts、flows、retrieval） → `prompts/` → `works/` 已提交样例 →
`users/_template/` → `README.md`、`AGENTS.md`、`CLAUDE.md`、`.gitignore`。

**工作目录 Git 状态**：`master` clean，HEAD = `664cb45 chore(agent-configs):
追踪团队共享的 Claude/Codex 入口配置`。

---

## Findings

### High

#### H1 — schema 与 docs 中仍散落具体书名/角色名/地名

**结论**：`schemas/` 与 `docs/requirements.md` 中至少 6 处 description
里写死了具体作品 `我和女帝的九世孽缘` 的角色与地名。这与
`feedback_no_specific_refs_in_docs.md`（memory 中明确写着
"never put real book/character/plot names in docs, prompts, or ai_context;
use generic placeholders"）直接冲突。

**证据**：

| 位置 | 内容 |
|------|------|
| [schemas/stage_snapshot.schema.json:620](schemas/stage_snapshot.schema.json#L620) | `"例如：受萧尘为她挡剑影响。"` |
| [schemas/stage_snapshot.schema.json:635](schemas/stage_snapshot.schema.json#L635) | `"例如：对萧尘从戒备转为信任。"` |
| [schemas/stage_snapshot.schema.json:639](schemas/stage_snapshot.schema.json#L639) | `"例如：萧尘放弃帝位陪她渡劫。"` |
| [schemas/stage_snapshot.schema.json:667](schemas/stage_snapshot.schema.json#L667) | `"从完全冰冷的前大帝，到被一个人的善意逐渐撬开冰层……"` |
| [schemas/identity.schema.json:106](schemas/identity.schema.json#L106) | `"例如：'五岁被亲生父母抛弃于冰宫门前'。"` |
| [docs/requirements.md:2314](docs/requirements.md#L2314) | `首次撞限的 lane 标识（如 \`char_snapshot:王枫\`）` |

前 5 处是 json schema 的 `description` 字段，后 1 处在 requirements §11.13.3
"暂停文件契约"的字段表里。

另外 [automation/persona_extraction/git_utils.py:134](automation/persona_extraction/git_utils.py#L134)
把 `阶段01_南林初遇` 写进 `commit_stage()` 的 docstring，作为 stage_id 的示例，
也复用了当前唯一在跑的作品的具体 stage 名——同类问题但属代码注释层，定性上
轻一档，与 schema/requirements 不同批处理。

**为什么是问题**：

- 规则层面：用户显式规则，memory 长期保留，审计必须把规则破坏视为 High。
- 可传播性：这些 schema 描述被模型在每次 lane 调用时**直接作为指令** reference，
  具体名会潜移默化影响其他作品的 extraction 输出（例："受萧尘为她挡剑
  影响"会被模型视为合法模式继续套用类似结构）。
- 可复现性：对任何不是"我和女帝的九世孽缘"的新作品，schema 里的例子都是
  misleading 甚至误导。
- 归档逻辑：docs/logs/ 与 docs/review_reports/ 里出现具体名是**允许的**
  （因为那是历史决策快照），但 docs/requirements.md、schemas/、ai_context/、
  prompts/ 是"当前规范/规则"，必须中性化。

**影响范围**：
  所有未来 extraction 调用使用 stage_snapshot.schema / identity.schema 作为
权威；docs/requirements.md §11.13.3 作为 token-pause 契约依据。

**建议落地顺序**：列为首批修正。把 6 处具体名批量改成占位符
（如 `角色A`、`角色B`、`某宗门所在地`、`char_snapshot:<character_id>`）。
不要 include 本次 review 报告的文件名里的具体书名——review 报告属历史
快照，不受此规则约束。

---

### Medium

#### M1 — consistency_checker 字段完整性清单遗漏 `character_arc` 与 `stage_events`

**结论**：Phase 3.5 的 `_check_field_completeness` 宣称校验"每个快照包含所有
必需维度"，实际 `required_fields` 只覆盖 12 个字段，遗漏了架构文档和
prompt 两侧都列为**必备维度**的 `character_arc` 与 `stage_events`。

**证据**：

- 检查器清单：
  [automation/persona_extraction/consistency_checker.py:244-249](automation/persona_extraction/consistency_checker.py#L244-L249)
  `required_fields = ["active_aliases", "voice_state", "behavior_state",
  "boundary_state", "relationships", "knowledge_scope", "misunderstandings",
  "concealments", "emotional_baseline", "current_personality",
  "current_mood", "current_status"]`
- schema 结构明确存在 `stage_events`（50-80 字硬门控，maxItems 10）：
  [schemas/stage_snapshot.schema.json:110-115](schemas/stage_snapshot.schema.json#L110-L115)
- schema 结构明确存在 `character_arc`（非首阶段应有弧线概览）：
  [schemas/stage_snapshot.schema.json:660](schemas/stage_snapshot.schema.json#L660)
- prompt 明示两者必填：
  [automation/prompt_templates/character_snapshot_extraction.md:44-46](automation/prompt_templates/character_snapshot_extraction.md#L44-L46)
  `stage_events` 与 `character_arc` 并列在"每个 stage_snapshot 必须包含以下
  全部维度"之内；缺失定性为"扮演缺陷"。
- 架构总览：
  [docs/architecture/schema_reference.md:170](docs/architecture/schema_reference.md#L170)
  把 `character_arc` / `stage_events` 描述为 stage_snapshot 的核心维度。

**为什么是问题**：

- 检查器字面语义承诺"每个快照包含所有必需维度"，但实际放过 `stage_events`
  为空、`character_arc` 缺失的 snapshot——即使 schema 的数值硬门控（50-80 字）
  会在 L1 schema check 层面拦住"写了但长度错"，它不拦"压根没写"
  （schema 顶层 `required` 只列 6 个键）。
- 结合 prompt 要求"缺任何一个维度 = 扮演缺陷"，这是一个
  **宣称会阻断但代码实际不会阻断**的缺口——直属 `/check` 重点检查项。

**影响范围**：Phase 3.5 consistency_report 会把遗漏 `character_arc` /
`stage_events` 的快照误判为"通过"；后续运行时角色扮演加载时才发现缺数据。

**建议**：把 `stage_events` 和 `character_arc` 加进 `required_fields`；
`character_arc` 对首阶段的处理参考 `stage_delta` 的分支（`idx > 0` 才强制）。
prompt 的 non-首阶段要求与此对齐。

---

#### M2 — `works/*/indexes/` 在规范中是 canonical 可提交目录，但首作实际不存在

**结论**：`indexes/` 目录与 `vocab_dict.txt` 在多处规范被写成"tracked /
committed"的 canonical 产物，`works/我和女帝的九世孽缘/indexes/` 目录却
不存在；git 里也没有任何 `indexes/` 下的文件。

**证据**：

- 规范宣称已提交：
  - [ai_context/current_status.md:157](ai_context/current_status.md#L157)
    `works/*/world/、works/*/characters/、works/*/indexes/ tracked`
  - [ai_context/requirements.md:229](ai_context/requirements.md#L229)
    `works/{work_id}/indexes/vocab_dict.txt（committed）`
  - [ai_context/decisions.md:174](ai_context/decisions.md#L174)、
    [ai_context/decisions.md:225](ai_context/decisions.md#L225)
  - [docs/architecture/data_model.md:160](docs/architecture/data_model.md#L160)、
    [docs/architecture/data_model.md:475](docs/architecture/data_model.md#L475)
  - [docs/architecture/system_overview.md:36](docs/architecture/system_overview.md#L36)、
    [docs/architecture/system_overview.md:326](docs/architecture/system_overview.md#L326)
- 仓库实际状态：`ls works/我和女帝的九世孽缘/indexes/` → `No such file`。
- `.gitignore` 未排除 `works/*/indexes/`——缺失是"还没产出"，不是"本地 only"。

**为什么是问题**：

- 当前状态叙述（`current_status.md`）与唯一的 committed work 不一致——
  "规范宣称 A，样例是 B"典型对齐断裂。
- retrieval 运行时约定 jieba 用 `vocab_dict.txt` 作自定义词典
  （system_overview.md:326），indexes/ 不存在意味着首作启动时要么 fallback
  要么报错；retrieval 还没落地所以当前运行时没触发，但**部署默认路径与产出
  路径不一致**是定时炸弹。

**影响范围**：影响 retrieval 实现启动、影响任何按 canonical 路径加载
vocab_dict 的代码、以及任何以"规范=事实"为前提做 handoff 的 agent。

**建议**：要么把 vocab_dict.txt 产出纳入 Phase 2.5 / Phase 3.5 的产物清单（目前
没有任何阶段承担"生成 indexes/"的责任）；要么降格规范描述——明确
"indexes/ 运行时或 retrieval 首次加载时生成"，把当前状态从"committed"改为
"pending 等 retrieval 实现"。

---

#### M3 — prompt 模板把"已移除"写进硬性指令表里，违反"describe current only"

**结论**：[automation/prompt_templates/character_snapshot_extraction.md:106](automation/prompt_templates/character_snapshot_extraction.md#L106)
在"字段命名严格对照"表里写：`| stage_snapshot | relationship_behavior_map |
已移除，用 target_behavior_map |`。

**证据**：user memory `feedback_docs_describe_current_only.md` 明确：
"describe current design only; no 'renamed from / 旧 / 已废弃 / legacy';
history lives in docs/logs/ + git"，且 prompts 被包含在此规则内
（见 `feedback_no_specific_refs_in_docs.md` 的 "docs, prompts, or ai_context"）。
schema 层面 `behavior_rules.schema.json:101` 里 `relationship_behavior_map`
仍然是 baseline 的有效字段（未被移除），只是 stage_snapshot 里用
`target_behavior_map`；此表的"已移除"表述也**技术上不准确**——是字段层职责
分离，不是字段被废弃。

**为什么是问题**：
- 表达上暗示该字段被废弃，但它在 baseline 仍然存在，会误导 LLM；
  反向也易引发 LLM 跨文件串字段。
- 规则层面：prompt 模板被要求只描述当前设计。

**建议**：改为
`| stage_snapshot.behavior_state | relationship_behavior_map | stage 快照
使用 target_behavior_map（relationship_behavior_map 仅存在于 baseline
behavior_rules.json） |`——既保留防坑意图，又不带"已移除"这种历史定语。

---

#### M4 — sample stage 01 的 progress 条目缺 `lane_states`，与 T-RESUME 约定的 in-disk 状态不一致

**结论**：[works/我和女帝的九世孽缘/analysis/progress/phase3_stages.json:9](works/我和女帝的九世孽缘/analysis/progress/phase3_stages.json#L9)
`阶段01_南林初遇` 的 StageEntry JSON **没有 `lane_states` 字段**，但 stage 02
存在且已进入 ERROR 流程。当前 `StageEntry.from_dict`（[automation/persona_extraction/progress.py:463](automation/persona_extraction/progress.py#L463)）
对缺失字段默认空 dict，orchestrator 对 `committed` 状态也不再依赖
`lane_states` 走任何分支——所以不会直接坏 flow。但**样例与 handoff
文档之间仍然不匹配**：`current_status.md:78-82` 把 lane_states 描述为
每个 StageEntry 的常驻字段；新手按文档看 sample 会困惑。

**为什么是问题**：
- 文档说"StageEntry tracks per-lane completion"，实际 committed 样例没这个
  字段——对齐审计视角下是"样例与叙述不一致"。
- 非高风险，因为 committed + non-empty SHA 足以让 resume 逻辑直接跳过
  stage 01——但 sample 作为"规范最权威的落地证明"不应弱于 doc。

**影响范围**：新上来的 agent / reviewer。

**建议**：在 orchestrator 的 committed 分支里，`commit_stage` 成功后回填
`lane_states`（把所有已跑的 lane 标 complete）；或在 `save()` 时对
committed stage 做一次性 backfill。后续 stage 全部按此执行即可，无需改
历史样例。

---

### Low

#### L1 — `git_utils.commit_stage` 连续两次 `git add works/`

**位置**：[automation/persona_extraction/git_utils.py:140-144](automation/persona_extraction/git_utils.py#L140-L144)

连续调用 `_git(["add", "works/"], ...)` 再 `_git(["add", "-A", "works/"], ...)`。
第二次 `-A` 覆盖第一次，第一次是冗余步骤。非 bug，但是一个浪费的 subprocess
调用，并且 `-A works/` 的作用等价于"works/ 下所有状态（含删除）入 index"——
若以后有人把第一次误删或改路径，行为会悄悄变化。

**建议**：删除 line 142 的单独 `add`，只保留 `-A`。不急。

---

#### L2 — `pipeline.json` 的 phase_4 完成顺序先于 phase_3

**位置**：[works/我和女帝的九世孽缘/analysis/progress/pipeline.json](works/我和女帝的九世孽缘/analysis/progress/pipeline.json)
显示 `phase_3: pending, phase_3_5: pending, phase_4: done`。

设计上 Phase 4（scene archive）是独立的 work-level 任务，可与 Phase 3 并行或
错开，这一点在 `scene_archive.py:642` 有独立 PID lock 支持。所以 phase_4
done 先于 phase_3 是**允许行为**，不是 bug。但作为 sample，未来 agent 看到
这个 pipeline.json 可能误解为"Phase 3 依赖 Phase 4"或反之。

**建议**：无需改样例；在 docs/architecture/extraction_workflow.md 明确
"Phase 4 可独立先完成"即可。当前 workflow doc 已零散提及，但不够显眼。

---

#### L3 — `prompts/review/手动补抽与修复.md:43` 仍是 prompts/ 的唯一被跟踪文件之一，保留用途 OK 但和 ai_context 的"已退场"描述存在轻微不一致

[ai_context/current_status.md:19-20](ai_context/current_status.md#L19-L20)
说 `prompts/` 已被精简为 4 个手动场景模板，实际目录结构匹配（ingestion /
review / shared + README），没问题；但 ai_context/read_scope.md 默认把
prompts/ 排除出默认加载。此项属于 Low 但**不构成冲突**，仅标注：
`prompts/review/手动补抽与修复.md` 中提到 `target_voice_map`/
`target_behavior_map` 属当前字段，不需要改。

---

## False Positives / 纳入但最后排除

- **`schemas/behavior_rules.schema.json:101` 的 `relationship_behavior_map`**：
  初筛时怀疑与 stage_snapshot 的 `target_behavior_map` 冲突；复核后确认这是
  baseline（跨阶段）字段，stage_snapshot（阶段性）用 `target_behavior_map`，
  两者属于不同职责层，未冲突。
- **`automation/persona_extraction/git_utils.py:144` 的 `-A works/`**：
  初筛时担心范围过宽，复核后确认限定在 `works/` 下，不会吞 `.env` 等敏感文件。
- **`AGENTS.md` 与 `CLAUDE.md` 同步状态**：diff 仅显示 title/mirror-note
  方向性差异（符合 CLAUDE.md 的 mirroring rule），正文一致，无问题。
- **`.agents/skills/check/SKILL.md` 与 `.claude/commands/check.md` 同步**：
  前者多 5 行 YAML frontmatter（name/description），正文与后者逐字一致，
  符合 mirror 约定。
- **`.gitignore` 与 tracked files 一致性**：
  git ls-files 显示 `chapter_summaries/`、`scene_splits/`、`progress/` 均未
  入库，`.gitignore` 条目与实际 tracked set 一致。
- **`users/_template/` 缺 `conversation_library/archives/` 子树**：
  README 明确说模板只保留"最小目录骨架"，运行时按需生成，非缺漏。

---

## Open Questions / Ambiguities

1. **`indexes/vocab_dict.txt` 的生成阶段归属未定**：规范说"committed"，但
   没有任何 Phase 明确承担生成职责（Phase 2.5 baseline_production 不涉及，
   Phase 3 per-stage 不涉及，Phase 3.5 是消费型）。需要产品决定："是 Phase
   2.5 的产物之一？" 还是"retrieval 首次启动时现生成？" 当前状态是
   undefined。
2. **`character_arc` 在首阶段的必要性**：prompt 模板（
   character_snapshot_extraction.md:46）写"第一个阶段可省略或仅写起点
   状态"，但 `_check_field_completeness` 如果以后要补加 `character_arc`，
   需要和 `stage_delta` 一样支持 `idx > 0` 条件。确认一下产品意图：**首
   阶段是否允许完全不写 `character_arc`？**
3. **schemas 中 example 是否允许"风格化"样例**：M3 / H1 都触及这个问题。
   schema description 的 example 必须中性化到什么程度？完全不写例子？只写
   结构不写内容？这是规则的边界问题。

---

## Alignment Summary

| 层 | 对齐度 | 备注 |
|----|--------|------|
| `ai_context/` vs `docs/requirements.md` / `docs/architecture/` | 高 | current_status.md 与架构文档互相支撑，未发现语义冲突 |
| `ai_context/` vs `docs/requirements.md` 的 specific refs | 低 | requirements §11.13.3 仍有具体名（H1） |
| `docs/architecture/schema_reference.md` vs `schemas/*.json` | 高 | schema 字段与架构对齐 |
| `schemas/` vs `automation/prompt_templates/` 字段名 | 中 | 字段名基本一致，但 M3 的"已移除"表述误导 |
| `schemas/` vs `automation/persona_extraction/consistency_checker.py` | **中低** | M2：checker 必填字段清单落后于 schema/prompt/架构三方共识 |
| `prompt_templates/` vs `schemas/` | 高 | 50-80 / 150-200 / 30-50 字等硬门控描述一致 |
| `docs/` / `ai_context/` vs `works/我和女帝的九世孽缘/` 样例 | **中低** | M2（consistency_checker）、M4（sample 缺 lane_states）、M2（indexes 缺失）三条叠加 |
| `users/_template/` vs `users/README.md` | 高 | 模板是"最小骨架"，README 明说运行时按需长出 archives/sessions |
| `AGENTS.md` vs `CLAUDE.md` / `.agents/skills/check/SKILL.md` vs `.claude/commands/check.md` | 高 | 自动对齐，diff 干净 |

**最不对齐的一层**：schemas / requirements 等 canonical 规范与"no specific refs"
规则——H1 的 6 处散布已是系统性的规则漂移，需要一次集中修正。

---

## Residual Risks

1. **retrieval 落地时会先踩 `indexes/` 缺失这个坑**：M2 未修之前任何真实
   retrieval 实现都要么降级 fallback，要么报错。
2. **consistency_checker 是"空检"的局部模式**：M2 揭示检查器实际覆盖
   面比字面承诺小；后续如果继续在 prompt / schema 加字段（如架构里
   还在讨论的"action_scenes"、"perception_state"之类），需要同步审视
   checker 的 `required_fields` 是否补加。这是一个**需要制度化的"加
   字段必改 checker"规则**，否则漂移会持续。
3. **repair_agent 的 SemanticChecker 不在本轮审计范围内**：`simulation/`
   里未实现运行时侧，`repair_agent` 的 L3 semantic prompt 需要单独一轮 prompt-
   centric review（本次未深入）。目前只覆盖到 coordinator 的三相位流程。
4. **`prompts/review/` 与 `prompts/ingestion/` / `prompts/shared/` 的具体
   内容未逐文件审**：本次仅 grep 了具体书名，未检测其他遗漏（如旧字段
   名）；属于残余风险。
5. **scene_archive 与 retrieval 的 stage_id 契约**：`scene_archive.py`
   强制 `SC-S###-##` 规范并硬限 99 scene/stage（[scene_archive.py:548](automation/persona_extraction/scene_archive.py#L548)）；
   超过会 fail merge。首作第一阶段 scene 数量目前未知，可能埋雷。

---

## 建议落地顺序

1. **H1**（schemas/requirements 中 6 处具体名去标识化）——规则级硬错，先修；
   可在同一 commit 里连带修 L3 风险提到的 `git_utils.py:134` docstring。
2. **M2**（consistency_checker 补 `character_arc` + `stage_events`）——影响
   phase 3.5 正确性，低风险一次性改；同步补单元或 sample 测试。
3. **M3**（prompt 模板把"已移除"换成职责分离表述）——小改动，顺路清理。
4. **M1 / M4**（`indexes/` 产出归属、`lane_states` 样例 backfill）——需要
   一次产品侧决定；可以等 Phase 3 继续跑、有新 committed stage 时一并处理。
5. **L1 / L2 / L3**——纯清理，不阻塞任何开发。

> **不建议在本修正里做的事**：
> - 不要改 `docs/logs/` 里带具体名的历史记录（logs 是 append-only 历史，
>   user memory 明确排除 logs/review_reports）。
> - 不要动 `works/我和女帝的九世孽缘/` 下任何产出文件（样例是真实 extraction
>   结果，修动会污染数据）。
> - 不要重命名 `relationship_behavior_map`；它在 baseline schema 里是有效
>   字段，更名会带动一批 baseline sample 重写。
