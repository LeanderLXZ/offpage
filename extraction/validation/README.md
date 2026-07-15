# `extraction/validation/` — 数据正确性框架

`extraction.repair` 是项目内统一的 L0–L3 checker + T0–T2 fixer 框架，
`extraction.validation` 是它的**共享层 + 过渡层**：

- `gates/` — **相位边界 validator**。由 orchestrator 在 phase 完成时调一次，
  返回 `ValidationReport`，pass/fail 即终点；**不触发 repair 循环**。
  目前住户：
  - `phase2_baseline.py` — Phase 2 终点校验（baseline 4 件产物 +
    works / world manifest + foundation）
  - `phase3_5_consistency.py` — Phase 3.5 跨 stage 一致性校验
- `shared/` — **纯函数原语**。`gates/` 内的 validator 与
  `extraction.repair.checkers.*` 都直接 import。这一层不依赖任何具体相位
  也不依赖 repair framework，只暴露与 schema / target importance 相关的
  helper：
  - `importance.py` — `importance_for_target` / `importance_min_examples`
    （重要性 → 例子数下界）
  - `schema_tolerance.py` — `validate_with_length_tolerance` /
    `relaxed_schema_for_length` / `_is_length_bound_error`
    （length-bound tolerance gate，决策 #48）

## 与 `extraction.repair` 的关系

`extraction.repair.checkers/*` 是已经接进 framework 的 `BaseChecker` 子类
（L0=json_syntax / L1=schema / L2=structural + targets_keys_eq_baseline +
phase2_baseline_refs / L3=semantic）；`extraction.repair.coordinator.run`
在 L×T 循环里调用它们（`extra_checkers` 参数支持按调用注册附加 checker，
决策 #59——phase 2 引用 checker 经此注入，hint 走构造函数）。

本目录下的 `gates/` 是**终点 validator**——它们与 checkers 的 `Issue`
数据契约几乎一致，但被 orchestrator 直接调用、不喂 fixer 循环。Phase 2
自决策 #59 起是**双层**形态：per-lane repair lifecycle（framework 内，
T0/T1 缩水版）先修，全部 lane 完成后 `gates/phase2_baseline.py` 的
`validate_baseline`（strict → ±10% tolerance）作最后安全阀。

## 未来去向

- `gates/phase2_baseline.py` **保留为终点安全阀**（决策 #59 落地形态：
  phase 2 修复职责已由 `repair/checkers/phase2_baseline_refs.py` +
  per-lane lifecycle 承担；本文件不再计划整体迁移）
- `gates/phase3_5_consistency.py` 如未来接 framework，拆 phase-3.5
  checker 移入 `repair/checkers/`（尚无立项）
- `shared/` 保留——这一层与 framework 状态无关，无论 gate 还是 checker
  都会继续 import
