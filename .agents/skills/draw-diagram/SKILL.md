---
name: draw-diagram
description: Draw polished diagrams — flowcharts, pipeline / process, agentic-loop, state-machine — as SVG / PNG / HTML in three themes (dark / light / mono-print). Triggers: flowchart / flow / pipeline / process diagram / agentic-loop / state-machine / workflow visualization.
---

> **Language**: per `ai_context/skills_config.md §Language` — disk-bound output (text labels / captions / notes written into the generated `.svg` / `.html` / `.png` diagram files) uses `content_language` unless the user's source material dictates otherwise; user-facing surface (chat prose / `AskUserQuestion` prompts and option labels / status lines) uses `conversation_language`. Diagram structural keywords, CSS class / role names, file paths, and code identifiers stay English regardless.

# Diagram Skill

Draw polished, minimalist diagrams — flowcharts, pipeline / process, agentic-loop, state-machine — as standalone SVG (PNG / HTML on request). The visual language is locked — every constant below is mandatory. Improvising is what causes diagram drift across iterations.

The skill writes an HTML intermediate (CSS-in-`<head>` + inline `<svg>` in `<body>` — easier to edit), then **extracts a standalone `.svg`** as the deliverable. The user receives the `.svg`; the `.html` is a temp source that may be kept for re-editing. PNG is **only** used as a temporary raster for subagent visual review (Read tool needs raster) and is deleted after review.

## Design System

### Color Palette

There are **8 node roles** plus **2 spare color slots**, and **3 edge styles**. Keep it sparse: most steps collapse into `action` — reach for another role only when it adds real meaning, so the diagram doesn't fragment into a rainbow. **Every role, in every theme, is a colored border (its hue) + a pale fill of the same hue.** The roles are the SAME in every theme — only the color values (below) change.

| Role | What it is | Examples |
|---|---|---|
| **action** | Process step / command / function — the verb | "Validate input", "Send email", "Transform" |
| **agent** | External actor / user / runtime / service — in the flow, not of it | "User", "Payment API", "CI runner", "LLM" |
| **data** | Persisted store — file / DB / log / queue / cache | "users table", "S3 bucket", "event queue" |
| **decision** | Branch / gate / conditional route | "if valid?", "route by type", "quota left?" |
| **event** | Trigger / signal / webhook / timer — something that fires | "order placed", "cron tick", "file uploaded" |
| **state** | Outcome / status marker — success / fail / paused | "Approved", "Failed", "Timed out" |
| **terminal** | Entry / exit point | "Start", "Done", "Request in" |
| **callout** | Out-of-band note / user-interrupt | "User can cancel", "Manual override" |
| **accent1** | spare color slot — no fixed meaning (use when the 8 aren't enough) | — |
| **accent2** | spare color slot — no fixed meaning (use when the 8 aren't enough) | — |

**Naming:** each role `R` defines `--R-fill` + `--R-stroke` (and `callout` adds `--callout-text`); apply via the role's CSS class. Exact classes live in each preset's `<style>`, copied verbatim in Step 5.

#### Colors — `light` (warm bg `#F0EEE6`; SOLID fill, NO border — only data / state / callout get a 2px border)

| Role | Fill | Border |
|---|---|---|
| action | `#C3DCB7` | — |
| agent | `#C2D6E5` | — |
| data | `#EAF0F4` | `#6E8CAF` |
| decision | `#C2C5D9` | — |
| event | `#EFC6BA` | — |
| state | `#F7F4E4` | `#C6A24F` |
| terminal | `#E5DCBE` | — |
| callout | `#FBF8EE` | `#D89270` · text `#B26C3F` |
| accent1 | `#C4DDD1` | — |
| accent2 | `#DBD4C1` | — |

#### Colors — `dark` (slate-950 bg; bright border + dark translucent fill)

| Role | Fill | Stroke |
|---|---|---|
| action | `rgba(19,78,74,0.4)` | `#2DD4BF` teal |
| agent | `rgba(14,116,144,0.35)` | `#22D3EE` cyan |
| data | `rgba(76,29,149,0.4)` | `#A78BFA` violet |
| decision | `rgba(30,58,138,0.4)` | `#60A5FA` blue |
| event | `rgba(136,19,55,0.35)` | `#FB7185` rose |
| state | `rgba(120,53,15,0.4)` | `#FBBF24` amber |
| terminal | `rgba(30,41,59,0.5)` | `#94A3B8` slate |
| callout | `rgba(251,146,60,0.25)` | `#FB923C` orange · text `#FDBA74` |
| accent1 | `rgba(6,78,59,0.4)` | `#34D399` emerald |
| accent2 | `rgba(112,26,117,0.4)` | `#E879F9` fuchsia |

#### Colors — `mono-print` (B&W; SOLID grey fill, NO border — only data / state / callout get a 2px border)

Mono can't carry 10 hues — boxes differ only by grey SHADE, so **rely on the node label, not color**, and use only a few roles per mono diagram.

| Role | Fill | Border |
|---|---|---|
| action | `#D8D8D8` | — |
| agent | `#ECECEC` | — |
| data | `#F2F2F2` | `#888888` |
| decision | `#E0E0E0` | — |
| event | `#EAEAEA` | — |
| state | `#DCDCDC` | `#555555` |
| terminal | `#E5E5E5` | — |
| callout | `#FFFFFF` | `#1A1A1A` · text `#1A1A1A` |
| accent1 | `#EEEEEE` | — |
| accent2 | `#F5F5F5` | — |

#### Base colors (theme chrome — not per-node)

| Element | light | dark | mono |
|---|---|---|---|
| Background `--bg` | `#F0EEE6` | `#020617` | `#FFFFFF` |
| Primary text `--text` | `#404442` | `#E2E8F0` | `#1A1A1A` |
| Secondary text `--label-text` | `#6B6E64` | `#94A3B8` | `#555555` |
| Flow line `--flow-line` | `#6A6F66` | `#94A3B8` | `#3A3A3A` |
| Loop-back `--flow-loopback` | `#8FB585` | `#2DD4BF` | `#999999` |
| Container `--container` | `#B5B2A8` | `#475569` | `#888888` |

Font (all themes): `"Inter", "Söhne", -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif`.

#### Group / region box tints (optional enclosure — NOT a node role)

A **group box** brackets a SUBSET of nodes that form one phase / region / sub-system. It is a dashed rounded rect with a colored border + a VERY transparent fill of the same hue; the color is a neutral grouping signal, never a role. The plain grey `--container` (`fill:none`) still works for a single plain group; reach for a tint when a region should stand out, or to tell MULTIPLE regions apart. `mono` has no tints — use the grey `--container`. See §Container / group box for when & how.

**`dark`** (fill alpha ~0.07 — a faint wash that never competes with the ~0.4 node fills):

| Tint | Border | Fill |
|---|---|---|
| sky | `#38BDF8` | `rgba(56,189,248,0.07)` |
| blue | `#3B82F6` | `rgba(59,130,246,0.07)` |
| green | `#34D399` | `rgba(52,211,153,0.07)` |
| yellow | `#FBBF24` | `rgba(251,191,36,0.07)` |
| gray | `#94A3B8` | `rgba(148,163,184,0.07)` |
| purple | `#A78BFA` | `rgba(167,139,250,0.07)` |
| red | `#FB7185` | `rgba(251,113,133,0.07)` |

**`light`** (warm, muted; fill alpha ~0.07 — a faint wash so the solid node boxes inside stay legible):

| Tint | Border | Fill |
|---|---|---|
| sky | `#84B6D9` | `rgba(132,182,217,0.07)` |
| blue | `#6E8CAF` | `rgba(110,140,175,0.07)` |
| green (sage) | `#8AB07F` | `rgba(138,176,127,0.07)` |
| yellow (ochre) | `#C6A24F` | `rgba(198,162,79,0.07)` |
| gray (warm) | `#B0ADA2` | `rgba(176,173,162,0.07)` |
| purple (mauve) | `#9E8AB8` | `rgba(158,138,184,0.07)` |
| red (terracotta) | `#C97E62` | `rgba(201,126,98,0.07)` |

### Typography

```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
```

Stack: `"Inter", "Söhne", -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif`

| Role | Size | Weight | Fill |
|---|---|---|---|
| **Node label** (main) | **18px** | **700** | `--text` |
| **Node sublabel** (optional, when context disambiguation adds value) | **12px** | **500** | `--label-text` |
| **Node detail line** (content card; one per line) | **14px** | 500 | `--label-text` |
| **Node port / accent line** (content card; optional) | **14px** | 600 | accent (e.g. `--agent-stroke`) |
| Container label (e.g., "agentic loop") | 16px | 500 | `--container-lbl` |
| Edge label | **18px** | 500 | `--label-text` |
| Callout label (user-interrupt) | **18px** | 500 | `--callout-text` |
| Legend item label | **18px** | 500 | `--label-text` |

**CRITICAL — Node labels are uniformly 18px.** If text overflows the box, **widen the box**, NEVER shrink the font.

**No in-SVG title.** Do NOT bake the diagram / section heading into the SVG — it holds only nodes, edges, labels, and the legend. The heading belongs in the surrounding document (markdown / slide / doc), not the image.

**One in-diagram text size: 18px.** Node labels, edge labels, and legend labels are ALL **18px** — the same size as the text inside the boxes (only the optional node sublabel at 12px, the container label at 16px, and content-card detail / port lines at 14px differ). Never shrink edge or legend text to a smaller tier; if an 18px edge label won't fit its gap, widen the gap (see §Horizontal space pressure), don't shrink the font.

**Text-width estimate (shared constant).** Estimate a label's rendered width at 18px from a **character-class sum**, NOT a flat per-char value — Inter is proportional, so a flat `chars × 10` over-reserves narrow / space-heavy labels (e.g. "entry / exit", with a slash + two spaces) and then renders an oversized trailing gap:

| Class | Characters | Width @18px |
|---|---|---|
| narrow | `i l I j t f r . , ' ! \| / : ;` + space | **5px** |
| wide | `m w M W @` | **15px** |
| default | everything else | **10px** |

`text_px ≈ Σ class_width(char)`. This single estimate feeds BOTH the node box-width formula (§Node shapes) and the legend item layout (§Pattern — In-SVG Legend) — same model in both places. Node boxes carry ≥30px padding slack that absorbs estimate error; the legend's inter-item gap is **exact**, so the class-weighted sum matters most there (a flat `chars × 10` is the visible cause of uneven legend gaps).

### Visual Elements

#### Background

Solid `var(--bg)`. No grid. No gradient.

#### Node shapes — rounded rect ONLY

Every role uses the same shape: rounded rectangle with `rx="12"`. NEVER use circles, cylinders, ellipses, pills, diamonds, hexagons.

**Height fits the content** (width stays text-driven — see sizing formula below):
- **60px** — single-line node (default)
- **80px** — node with a main label + one sublabel line (title+description)
- **content card (taller)** — a bold title + one or more 14px detail lines + an optional accent / port line; the box height GROWS to fit. See §Pattern — Multi-line content card.

**Border policy** (which roles are bordered differs by theme; the border WIDTH is a **uniform 2px** everywhere):
- **dark** — EVERY role is bordered: a bright accent border (**2px**) over a dark translucent fill (the semi-transparent fills need the edge). All roles share the same 2px width — data / state / callout are NOT thicker than the rest.
- **light / mono** — action / agent / terminal / decision / event / accent are **SOLID fill, NO border**; only **data / state / callout** carry a border, also **2px**.

Width = enough to fit text at 18px with **≥30px padding each side**: `max(120, ceil((text_pixels + 60) / 20) * 20)`, where `text_pixels` is the §Typography — Text-width estimate (character-class sum).

#### Same-role alignment (CRITICAL)

When two or more nodes of the **same role** appear in the diagram (e.g., 3 data stores; 2 agents), they MUST visually align:

- **Same width** when their labels permit. If `data1` has a 5-char label and `data2` has a 20-char label, you can't force same width — but if both labels fit in 200px, use 200px for both, NOT 140 and 200.
- **Same center-x** when stacked in a column.
- **Same y** when on the same row.

**Wrong:** `todo_list` at x=40 w=180 next to `todo_list_archived` at x=20 w=260 — different widths AND different left edges → reads as misaligned.
**Right:** Both at width 260, both with center-x=150 → visually aligned column. → see `examples/fan-in-out.svg` (A / B / C: same width, same center-x).

#### Container fit (CRITICAL)

When a `container` wraps a subset of nodes (e.g., "agentic loop" enclosure), the container's bounding rect MUST fully enclose every contained node with ≥30px padding on each side. A container whose right edge cuts through a contained node is a **glaring visual bug** that subagents have missed in past iterations.

**Wrong:** Container at `x=240 width=800` (right edge x=1040) when contained nodes extend to x=1070 — container right edge cuts through the last node.
**Right:** Container at `x=240 width=880` (right edge x=1120) — fully encloses nodes ending at x=1070 with 50px padding. → see `examples/dark.svg` (the `agentic loop` container: 50px side, 60/70 top/bottom inner padding).

#### Loopback origin alignment (CRITICAL)

A loop-back arrow's start point and end point MUST be at the EXACT geometric center of the source node's bottom edge and the destination node's bottom edge respectively. Off-center origins (even by 5-25px) look amateurish — they're the result of misreading box coordinates.

**Wrong:** Loopback exits `Verify results` (x=850, w=220, center=960) at `x=935` — that's 25px off-center. Subtle, but visible.
**Right:** Loopback exits at `x=960` exactly. → see `examples/dark.svg` (loop-back leaves `Verify results` bottom-center, returns to `Gather context` bottom-center).

#### Arrows — fixed-size markers + line-ends-at-triangle-TAIL

The `<marker>` defs (all 3) are in §Pattern — Marker defs. The rules that matter:

**CRITICAL — `markerUnits="userSpaceOnUse"` is mandatory.**

**CRITICAL — `refX=0` is mandatory** (NOT refX=11 or refX=9 or any other). With refX=0, the triangle's BASE sits exactly at the line endpoint, and the triangle extends 14 units past the endpoint to the apex. The line CONNECTS to the triangle's tail; line does NOT pass through the triangle interior.

**Wrong:** `refX="9"` (or "11", "13") — the line endpoint lands deep inside the triangle, so the line OVERLAPS the triangle interior, making the arrowhead look like a tiny spike on top of the line. Square/fat triangles compound this into a "bulge".
**Right:** `refX="0"` — the line stops AT the triangle base; the triangle is a clearly distinct visual element that EXTENDS FORWARD from the line.

**Triangle size:** 14 wide × 12 tall (fixed, `userSpaceOnUse` — does NOT scale with stroke) — ≈2.4× the 5px forward-flow stroke height. Big enough to read as a discrete arrow, NOT a tiny spike.

**Stroke widths:**

| Arrow type | Stroke | Color | Pattern |
|---|---|---|---|
| Default forward flow | **5px** | `--flow-line` (soft grey) | solid |
| Loop-back / return | **5px** | `--flow-loopback` (sage) | solid |
| Conditional / optional / skip | **3px** | `--flow-line` | dashed `7 5` |
| Callout (user-interrupt) | **3px** | `--callout-stroke` (orange) | dashed `7 5` |

**Arrow tip placement** (with `refX=0`). The triangle extends **14 user units past the line endpoint** in the path direction. For the tip to land EXACTLY on the destination box edge:

- **Rightward arrow → box left edge x=A:** `line_endpoint_x = A − 14`
- **Leftward arrow → box right edge x=A:** `line_endpoint_x = A + 14`
- **Downward arrow → box top edge y=A:** `line_endpoint_y = A − 14`
- **Upward arrow → box bottom edge y=A:** `line_endpoint_y = A + 14`

The visible line stops 14 units short of the destination edge; the triangle fills that gap; the apex touches the edge cleanly.

**Wrong:** `<line x2="319" />` for a rightward arrow into a box left edge x=320 — with the refX=0 marker, the triangle extends from x=319 to x=333, **tip 13px PAST the destination edge** (overshoots into the box).
**Right:** `<line x2="306" />` — line stops at 306; triangle fills 306–320; tip lands exactly on x=320 (box's left edge).

#### Line origin, fan-out & fan-in (CRITICAL)

A SINGLE arrow originates from the **geometric center** of the source box's edge — `(x_center, y_bottom)` for a downward arrow — never from a corner or arbitrary offset.

**Fan-OUT (one source → several targets) → SYMMETRIC shared "Y" trunk.** Both arrows start at `(x_center, y_bottom)` and share a 30-40px vertical stem, then diverge. Keep the Y **symmetric**: position the targets so they straddle the source center evenly (`target_left` and `target_right` equidistant from `x_center`) and split the stem into mirror-image branches. A lopsided split — one branch dropping straight down while the other elbows far to one side — reads as a crooked ⌐, not a Y; **reposition the targets** to make the two branches mirror each other.

**The split ARCS out — it is not a hard T.** Segments stay strictly orthogonal, but at the fork the stem stops 12px short of the split channel and each branch peels off with a quarter-arc (the same rounded `Q` transition used at every corner). A hard right-angle T at the split looks unfinished beside the rounded corners everywhere else. The same rule covers a single branch peeling off a continuing line (a tee). See §Pattern — Shared trunk fan-out and §Pattern — Branch arcing off a through-line.

- Two arrows from corners (`x=left+10` / `x=right−10`) is **WRONG** — both branches share the ONE centered stem, they do not start at the corners.

**Fan-IN (several sources → one target) → INDEPENDENT arrows, NOT a Y.** Each source routes its OWN complete arrow into the target; do NOT merge them into a shared trunk before the target. Two agents feeding one step each get a separate line that lands on the target's edge.

**Wrong (lopsided fan-out):** the source drops one branch straight into a box directly below and elbows the other far to one side — asymmetric ⌐.
**Right (symmetric fan-out):** the two targets sit at `cx−D` and `cx+D`; the stem splits into mirror branches of equal length.
**Wrong (fan-in merged):** two sources merged into one stem that then enters the target — reads as a single edge.
**Right (fan-in independent):** each source draws its own arrow into the target.

#### Edge labels — consistent placement (CRITICAL)

All edge labels follow the **same rule**: centered on the **midpoint of the longest segment** of the edge, **OFFSET from the line** — above for horizontals, right for verticals. NEVER on the line itself.

**No background fill — edge labels are transparent.** The label is offset off the line and sits on the solid `var(--bg)` card, so it is already legible with **no `<rect>` background**. A `var(--bg)` cutout behind the text is not just redundant — it punches an opaque hole in any stroke that passes near the label, including the very loop-back / flow line the label annotates, leaving a visible break in the line. So edge labels carry no background; legibility comes from the offset alone. (This replaces the older bg-cutout approach: a cutout was only ever needed for an ON-line label, but the mandatory offset already keeps text clear of the line, so the cutout — which silently consumes short arrows AND covers neighbouring lines — is dropped.)

**Computing position**:
- **Horizontal segment** `(x1,y) → (x2,y)`: text-anchor = `middle`, position = `(midpoint_x, y - 14)`.
- **Vertical segment** `(x,y1) → (x,y2)`: text-anchor = `start`, position = `(x + 6, midpoint_y)`. Critical: `text-anchor="start"` (NOT middle) so the text extends RIGHT, away from the arrow line.
- **L-shaped path**: pick the LONGEST of the two segments and use its offset midpoint.

**Arrow-length sanity check**: before placing a horizontal label, ensure `label_width < arrow_length`. If not, EXTEND the arrow (push target node further away) — do not shrink the label.

**Wrong:** "loop · next batch" with a `var(--bg)` cutout sitting beside the loop-back's vertical return — the opaque box covers a slice of the line, breaking it visually.
**Right:** "loop · next batch" offset 6px right of the line, no background — the return line stays continuous and the text reads cleanly off the solid card.

#### Container / group box (optional — bracket a sub-flow or region)

A dashed rounded rect (`rx=20`) enclosing a SUBSET of nodes that form a loop / phase / region (e.g. "agentic loop", "cross-model review"). Two looks: the **plain** grey `--container` (`fill:none`), or a **tinted** group box (a §Group / region box tint — faint hue fill + matching dashed border).

```svg
<!-- plain (grey, no fill) -->
<g class="container">
  <rect class="container-box" x="..." y="..." rx="20" />
  <rect class="container-gap" x="..." y="..." />          <!-- breaks the dashed border behind the label -->
  <text class="container-label" ...>agentic loop</text>
</g>

<!-- tinted region (pick a §Group / region box tint; here dark "blue") -->
<g class="container">
  <rect x="X" y="Y" width="W" height="H" rx="20"
        fill="rgba(59,130,246,0.07)" stroke="#3B82F6" stroke-width="2" stroke-dasharray="6 6" />
  <rect class="container-gap" x="..." y="..." />
  <text class="container-label" x="cx" y="..." text-anchor="middle" fill="#3B82F6">cross-model review</text>
</g>
```

CSS (plain variant):
```css
.container-box   { fill: none; stroke: var(--container); stroke-width: 2; stroke-dasharray: 6 6; }
.container-gap   { fill: var(--bg); }
.container-label { font-weight: 500; font-size: 16px; fill: var(--container-lbl); }
```

**When & how to use:**
- **Sparingly** — 1-3 groups per diagram; a box around every other node is noise. Nest at most 2 deep.
- **Color = grouping, not role.** Pick a tint for aesthetics, or to DISTINGUISH multiple regions; never to imply a node role. One region → any tint (often `blue` / `gray`); several → DISTINCT tints. Match the label fill to the border on a tinted box.
- **Fill stays faint** (the preset alphas) so the region reads as a wash BEHIND the nodes; the box is drawn first (Z-order layer 1).
- **Fit** (§Container fit): enclose every member with ≥30px padding (the main `agentic loop` container uses 50px sides / 60-70 top-bottom). The box's OUTER edge counts as content for the 50px viewBox padding; an edge leaving the region for ANOTHER region simply crosses the dashed border.
- **Loop-backs stay INSIDE (CRITICAL)**: a loop-back whose source AND destination are both nodes inside this container must route INSIDE the box — in an internal gutter between the container edge and the nodes — NOT out in the page margin beyond the container. Size the container to include that gutter (the loop-back path counts as a contained member for the fit check). A return arc drawn outside its own region's box reads as escaping the region it belongs to. → see `examples/dark.svg` (the `agentic loop` loop-back returns inside the container, not around it).
- **Label** on the top border via an **opaque** `container-gap` fill (`var(--bg)`) that breaks the dashed border behind the text — UNLIKE edge labels (which are transparent), a container label MUST keep this solid gap, sized to fully cover the dashes behind the text so none poke through; 16px (`container-label` tier).

#### Callout (user-interrupt) — orthogonal single-elbow arrow

The callout box sits OUTSIDE any container. **Box height = 60px** (same as all other nodes — uniform). **Label = 18px medium weight, single line** (NOT multi-line; widen the box to fit the text instead).

The arrow from callout box to the loop area is a **single orthogonal elbow** — RIGHT then UP, with ONE rounded corner. NO curves, NO Z-shapes, NO multiple bends.

**Connection points** (CRITICAL):
- **Start**: callout box **RIGHT-CENTER edge** (x = callout_right, y = callout_y_center)
- **End**: container **BOTTOM-CENTER edge** (x = container_x_center, y = container_bottom)
- **Bend**: at `(end_x, start_y)` — one corner, rounded with r=12

Copy-paste svg in §Pattern — Callout arrow.

**Wrong:** Multi-line callout text in an 80px-tall box — breaks uniform 60px node height.
**Wrong:** Curved cubic Bezier — looks loose / hand-drawn, inconsistent with the orthogonal flow arrows.
**Wrong:** Z-elbow with multiple bends — clunky.
**Wrong:** Connecting from callout TOP edge or from arbitrary middle of container — should be RIGHT-CENTER to BOTTOM-CENTER.
**Right:** 60px-tall callout with single-line 18px text; single elbow from callout right-center to container bottom-center; one rounded corner at the bend.

### Spacing Rules

| Constant | Value |
|---|---|
| Node height | 60px single / 80px title+sublabel / content card grows to fit content |
| Node corner radius (rx) | 12px (container uses 20px) |
| Min horizontal gap on same row | 60px |
| Vertical gap between rows | 80px default; expand (≈120px+) when arrows / edge labels route BETWEEN the two rows (e.g. a fan-out with `record` / `archive` labels), so the routing has room — a bare stacked column with nothing between needs only 80px |
| Container inner padding | 50px sides, 60px top/bottom |
| Legend gap from diagram content | 30px |
| Legend gap BETWEEN items | ≥24px (sequential by text width — never a fixed pitch) |
| **SVG viewBox padding** (around all content) | **50px on EVERY side** (left / right / top / bottom) |
| Legend swatch size | 22px wide × 12px tall |

**ViewBox padding symmetry rule (CRITICAL)**: all four paddings are 50px and the opposing pair MUST be equal, measured against the ACTUAL viewBox bounds (`min-x` / `min-y` need NOT be 0) — top padding (`min_content_y − viewBox_min_y`) = bottom (`viewBox_max_y − max_content_y`) = 50px; left (`min_content_x − viewBox_min_x`) = right (`viewBox_max_x − max_content_x`) = 50px. The background rect (`extract_svg.py`) is derived from these SAME viewBox bounds, so content, padding, and background stay aligned even when the viewBox origin is non-zero. Asymmetric padding (e.g., 50px top + 90px bottom) reads as visually unbalanced and "framed wrong" when embedded in a doc.

**Wrong:** content y=50 to y=360, viewBox y=0 to y=440 → top padding 50, bottom padding 440-360=80. Asymmetric.
**Right:** content y=50 to y=360, viewBox y=0 to y=410 → top 50, bottom 50. Symmetric. (Same logic for left/right against `viewBox_width`.)

**Legend completeness rule**: BEFORE finalizing viewBox height, compute legend dimensions:
- Legend total width ≈ `sum(swatch_22 + gap_8 + text_width + 24) for each role` — place items at exactly these running offsets (see §Pattern — In-SVG Legend); NEVER a fixed per-item pitch
- Legend height ≈ 16px (single-row swatch + text)
- Legend bottom y = content bottom y + 30 (gap)
- ViewBox height must extend to `legend_bottom_y + 50` (padding)
- Render window height must be `viewBox height + 32` (body padding margin)

**Wrong:** viewBox y=400, legend at y=390, render window 432px — legend gets clipped to 8px visible.
**Right:** viewBox y=460, legend at y=425, render window 492px — legend fully visible.

### Output width — DEFAULT + HARD CAP, not a fill target (CRITICAL)

A standalone SVG renders at its raw viewBox px by default, so different diagrams come out different sizes and, dropped into one markdown file, read as mismatched. Give every deliverable an explicit **pixel width** (and aspect-correct height) on the `<svg>` root. But 1500 / 825 are a **ceiling and a starting default — NOT a canvas to fill.**

- **viewBox (canvas) width: default 1500, HARD MAX 1500 — never a fill target.** Do NOT spread / pad / stretch content across the whole canvas just to reach 1500. A flow that naturally needs ~900 units should use a ~900 viewBox (content + 50px padding each side), NOT a sparse 1500 with huge empty gaps. **Pick the SMALLEST viewBox width that holds the content at proper spacing, capped at 1500.** (§Horizontal space pressure is for content that genuinely wants MORE than 1500 — compress it DOWN to fit the cap.)
- **Display width: default 825px, HARD MAX 825.** Safe for GitHub's README column; never exceed it. A diagram whose `viewBox_width ≤ 825` is NOT upscaled — use `width = viewBox_width` (a tiny pattern demo stays small). Otherwise `width = 825`.
- **A SET shown together shares ONE viewBox width** so text scale matches across them: size each to its content, then give them ALL the largest of those widths (≤1500). Equal viewBox width ⇒ one shared scale ⇒ identical text size. A lone diagram has no such constraint — size it to its own content.
- **Height always follows the diagram's own aspect ratio:** `height = round(display_width × viewBox_height / viewBox_width)`. NEVER distort aspect — within a set only WIDTH is shared; heights differ.

At display 825 / viewBox 1500 the scale is `0.55` (18px text → ≈10px); at a smaller content-fit viewBox the same 18px renders larger — fine for a standalone diagram. Only a SET needs the shared width for uniform text.

Mechanism: put `width` / `height` on the `<svg ...>` tag in the v1 HTML — the extract script copies the open tag verbatim, so the size carries into the standalone `.svg`. (The HTML preview's `svg { width: 100% }` CSS still wins there, so the editable preview stays responsive.) For the PNG review raster, render at full viewBox resolution (strip the width/height first, or render the HTML) so labels stay legible.

In the Step 6 report, give the recommended markdown embed line per diagram, e.g. `<img src="flowchart-foo.svg" width="825">`.

### Routing Rules (CRITICAL)

**All edges are orthogonal.** Every segment is horizontal or vertical. Corners are rounded arcs with **r=12**. NO diagonals. NO cubic bezier curves. The ONLY permitted non-orthogonal mark is the **bridge / hop arc** at a crossing (below).

Corner pattern: `... L cx,(cy-12) Q cx,cy (cx+12),cy L ...`

**Crossings — avoid first, then disambiguate.** Prefer to reposition nodes / use perimeter gutters so edges don't cross at all. But a crossing is NO LONGER a hard failure — when one is unavoidable, you MUST make it visually unambiguous with one of these, in order of preference:

1. **Bridge / hop arc (PREFERRED)** — the crossing line "jumps" the other with a small semicircular hop (radius ≈ 8px) so the two clearly don't connect. See §Pattern — Bridge / hop crossover. Convention: the hopping line is drawn ON TOP (later in z-order); typically the horizontal hops over the vertical.
2. **Distinct color** — route the crossing edge in a different palette stroke (e.g., a return edge in `--flow-loopback`) so the two lines read as separate.
3. **Dashed vs solid** — make one edge dashed (`7 5`) so the crossing pair is distinguishable.

An **undifferentiated crossing** (two identical solid lines simply overlapping, no hop / color / dash) is still a defect — always pick one treatment above.

### Z-order (back to front)

1. Container
2. Loop-back / return arrows (behind nodes)
3. Forward flow arrows
4. Callout arrow
5. Edge labels (offset off the line; no background fill)
6. Nodes (rects)
7. Node labels (text)
8. Legend

## Layout Reasoning (CRITICAL — think BEFORE placing nodes)

13-point checklist — run BEFORE writing coordinates:

1. **Dominant flow direction** — pick one (LTR or TTB), don't mix.
2. **Entry on natural side** — left for LTR, top for TTB.
3. **Exit on opposite side.**
4. **Same-role clustering** — group same-role nodes when meaningful.
5. **Critical path on main spine.**
6. **Side branches subordinate to spine.**
7. **Parallel tracks aligned to reveal parallelism.**
8. **Loop-back arrows SHORT** — reposition source/dest if loopback would snake.
9. **Side-branch destinations cluster** — if a node fans out to two stores, those 2 nodes should be visually adjacent below it.
10. **Edge labels offset from line** — above horizontal segments (−14px), right of vertical segments (+6px, `text-anchor="start"`); centered on the longest segment's midpoint.
11. **Reserve gutters** — top/bottom/left/right edges of viewBox for long routes.
12. **One axis at a time** — boring orthogonal beats clever cramped.
13. **Alignment audit** — same-row Y, same-column X, same-role uniform width, line origin from box center, edge labels on midpoint.

**Same-role color assignment**: when multiple project concepts map to the same role, give them the SAME color. Do NOT sub-categorize within a role (e.g., don't split "workflow command" vs "review command" vs "inventory command" into 3 colors — they're all `action`).

**Legend label naming**: name each role in the project's own domain vocabulary (see §Pattern — In-SVG Legend) — e.g. "agent" for AI runtimes, "user" for humans, "external service" for third-party APIs; the CSS token stays generic.

### Horizontal space pressure (CRITICAL — a DESIGN and a REVIEW obligation)

The canvas is narrow (viewBox 1500, displayed ~825px). A long left-to-right chain — many nodes in one row, or several sources feeding one node from a separate left column — quickly overflows the width or shrinks the 18px text below readability. Do NOT just accept a cramped layout. Actively RELIEVE the pressure, in roughly this order:

1. **Move a mid-flow node off the main spine.** A node B that is both a target and a source (sitting mid-spine between A and C) drops to a parallel row: keep A → C on the spine and route A → B down, B → C back up. The spine loses one node-width + gap.
2. **Stack fan-in sources vertically, aligned with their target** — never a separate left column. Two sources feeding one node sit directly above and below it (same center-x), arrows going straight down / up. The convergence then costs ONE node-width, not a column + elbow arrows. (See the fan-in / fan-out rules in §Line origin, and `examples/fan-in-out.svg`.)
3. **Redistribute gaps** — widen the gaps that carry an edge label so the 18px label fits; tighten the unlabeled ones. Total width unchanged.
4. **Cluster side-branches** under their source rather than stretching the row.

**If, after all that, the content still won't fit the width at readable text size, switch the whole diagram to a VERTICAL (top-to-bottom) flow.** A tall, narrow diagram reads fine in a doc; a wide one that overflows the column or shrinks text to unreadable does not. Choosing TTB over LTR is a legitimate — often better — choice for a long pipeline, and it must be decided BEFORE placing nodes (checklist item 1).

This is BOTH a design obligation and a review obligation: the layout-review subagent MUST flag a diagram that overflows / is cramped / has tiny text when one of the moves above (or going vertical) would fix it, and say which.

## Patterns (copy-paste blocks)

### Pattern — Node (any role: colored border + pale fill)

Every node carries its role's pale fill + colored border via the role's class (defined in each preset's `<style>`). Default height 60px; widen for text, or grow taller for a content card.

```svg
<rect class="role-action" x="X" y="Y" width="W" height="60" rx="12" ry="12" />
<text class="node-label" x="X+W/2" y="Y+37" text-anchor="middle">label</text>
```

### Pattern — Node with sublabel (title + description)

```svg
<rect class="role-action" x="X" y="Y" width="W" height="80" rx="12" ry="12" />
<text class="node-label"    x="X+W/2" y="Y+33" text-anchor="middle">main label</text>
<text class="node-sublabel" x="X+W/2" y="Y+56" text-anchor="middle">brief description</text>
```

### Pattern — Multi-line content card (title + details + optional port)

A node whose HEIGHT grows to hold a bold title, one or more 14px detail lines, and an optional accent / port line (e.g. a service name + tech stack + port). Width stays text-driven (widest line); only height changes. Centre every line on the box's `cx`; stack detail lines ~30px apart; give the port line a little extra gap above it.

```svg
<!-- card: title + 3 details + 1 port; height 180 (box spans y = Y .. Y+180) -->
<rect class="role-action" x="X" y="Y" width="W" height="180" rx="12" ry="12" />
<text class="node-label"  x="X+W/2" y="Y+42"  text-anchor="middle">Frontend</text>
<text class="node-detail" x="X+W/2" y="Y+72"  text-anchor="middle">React</text>
<text class="node-detail" x="X+W/2" y="Y+102" text-anchor="middle">TypeScript</text>
<text class="node-detail" x="X+W/2" y="Y+132" text-anchor="middle">Tailwind CSS</text>
<text class="node-port"   x="X+W/2" y="Y+166" text-anchor="middle">:3000</text>
```

CSS: `.node-detail { font-weight:500; font-size:14px; fill:var(--label-text); }` · `.node-port { font-weight:600; font-size:14px; fill:var(--agent-stroke); }` (port in an accent color).

Height ≈ `24 (top) + 28 (title) + 30 × n_detail + (34 if a port line) + 20 (bottom)`. Cards can take any role color (give each its own role class). When several cards share a row, centre them ALL on the shared arrow line — equal heights line up, differing heights are fine too. See `examples/content-card.svg` (a 60px node feeding a cyan Frontend and an emerald Backend card, same size).

### Pattern — Forward arrow (horizontal)

`A` = source-edge x; `B` = destination-edge x. Line endpoint at `B − 14`; triangle fills the 14px gap so apex lands exactly on `B`.

```svg
<line class="flow-arrow" x1="A" y1="Y" x2="(B-14)" y2="Y" marker-end="url(#arrow-flow)" />
```

### Pattern — Forward arrow (orthogonal elbow, down→right→down)

`y2` = destination top-edge y. Final line segment ends at `y2 − 14`; triangle apex lands on `y2`.

```svg
<path class="flow-arrow"
      d="M x1,y1
         L x1,(yc-12) Q x1,yc (x1+12),yc
         L (x2-12),yc Q x2,yc x2,(yc+12)
         L x2,(y2-14)"
      marker-end="url(#arrow-flow)" />
```

### Pattern — Shared trunk fan-out (1 source → 2 targets, SYMMETRIC Y — ARCED split)

Stem drops from the source center, then splits into mirror-image branches to two targets straddling `cx` (`cxL = cx−D`, `cxR = cx+D`). `yc = y_bottom+30` is the split channel; `target_top` is the targets' shared top-edge y. The stem stops **12px short** of `yc`; each branch **arcs out** of it with a quarter-arc (the same `Q` as a corner), so the fork is rounded — not a hard T. Segments stay orthogonal throughout.

```svg
<!-- shared stem stops 12px ABOVE the split channel -->
<line class="flow-arrow" x1="cx" y1="y_bottom" x2="cx" y2="(yc-12)" />
<!-- left branch: arc OUT of the stem (down→left), run, then arc down into the target -->
<path class="flow-arrow"
      d="M cx,(yc-12) Q cx,yc (cx-12),yc L (cxL+12),yc Q cxL,yc cxL,(yc+12) L cxL,(target_top-14)"
      marker-end="url(#arrow-flow)" />
<!-- right branch (mirror of left) -->
<path class="flow-arrow"
      d="M cx,(yc-12) Q cx,yc (cx+12),yc L (cxR-12),yc Q cxR,yc cxR,(yc+12) L cxR,(target_top-14)"
      marker-end="url(#arrow-flow)" />
```

The two `Q cx,yc …` arcs at the split mirror each other (left curves to `(cx−12,yc)`, right to `(cx+12,yc)`), so the stem fans open symmetrically. See `examples/fan-in-out.svg` (the M → X / Y fan-out).

### Pattern — Branch arcing off a through-line (tee)

A line that CONTINUES to its own target while also spawning a side branch (e.g. a main line A → C that also branches down to B). The through-line is drawn straight; the branch **arcs out of it** at `x=Xb` with a quarter-arc, then turns to its target — same rounded-fork principle as the Y, applied to one branch off a continuing line.

```svg
<!-- through-line continues STRAIGHT to its own target -->
<path class="flow-arrow" d="M x_start,H L … (its target)" marker-end="url(#arrow-flow)" />
<!-- branch peels off at x=Xb, arcing from the line down to a target below -->
<path class="flow-arrow"
      d="M (Xb-12),H Q Xb,H Xb,(H+12) L Xb,(target_top-14)"
      marker-end="url(#arrow-flow)" />
```

The branch starts 12px before `Xb` on the through-line and arcs down at `Xb`; the through-line keeps going straight past it. See `examples/fan-in-out.svg` (the P → Q line branching down to R / S).

### Pattern — Fan-in (N sources → 1 target, INDEPENDENT arrows — NOT a Y)

Each source draws its OWN arrow into the target; never merge sources into a shared stem before the target. Two stacked sources to the left of a node typically route horizontally then elbow into the node's top and bottom (or its upper / lower left edge) as two separate lines — see `examples/fan-in-out.svg` (A / B / C → M).

`examples/fan-in-out.svg` renders all three: a fan-IN (A / B / C → M, three independent arrows), a fan-OUT (M → X / Y, one symmetric Y trunk with an ARCED split), and a fan-out off a through-line (TWO independent branches arc off P → Q, one to R and one to S — not one stem that splits).

### Pattern — Bridge / hop crossover (the ONLY allowed arc besides corners)

When a horizontal edge at `y=H` must cross a vertical edge at `x=V` and you can't reroute, the horizontal line hops over with a small semicircular bump (radius `r=8`, arcing UP toward smaller y). Draw the hopping line LAST so it sits on top of the line it crosses.

```svg
<!-- left→right horizontal hopping the vertical at x=V; bump arcs upward (−y) -->
<path class="flow-arrow"
      d="M x_start,H
         L (V-8),H A 8 8 0 0 1 (V+8),H
         L x_end,H"
      marker-end="url(#arrow-flow)" />
```

`A 8 8 0 0 1` = radius-8 arc, `sweep-flag=1` lifts the midpoint ≈8px above the line and lands back on `y=H` at `x=V+8`. For a RIGHT→LEFT line, flip the sweep flag to `A 8 8 0 0 0` so the bump still arcs up. The vertical line it crosses is drawn normally (straight) — only the hopping line carries the arc.

See `examples/bridge-crossover.svg` for a rendered example: a central vertical `E → F` with two horizontals hopping over it — `A → B` solid and `C → D` dashed (the hop arc works for both stroke styles).

### Pattern — Loop-back & dashed conditional (CSS-only)

Path geometry follows §Routing Rules; only the class + marker change.

- Loop-back: `class="loopback-arrow"` + `marker-end="url(#arrow-loopback)"`. CSS: `stroke: var(--flow-loopback); stroke-width: 5; fill: none; stroke-linecap: round; stroke-linejoin: round;`
- Dashed conditional: `class="flow-arrow dashed"`. CSS: `.flow-arrow.dashed { stroke-width: 3; stroke-dasharray: 7 5; }`

### Pattern — Callout arrow (single-elbow RIGHT→UP)

Start at callout right-center, bend once at `(container_cx, callout_cy)`, end at `container_bottom − 14` (so triangle tip lands on container bottom edge).

```svg
<path class="callout-arrow"
      d="M callout_right,callout_cy
         L (container_cx - 12),callout_cy Q container_cx,callout_cy container_cx,(callout_cy - 12)
         L container_cx,(container_bottom - 14)"
      marker-end="url(#arrow-callout)" />
```

CSS: `.callout-arrow { stroke: var(--callout-stroke); stroke-width: 3; fill: none; stroke-dasharray: 7 5; stroke-linecap: round; stroke-linejoin: round; }`

See `examples/dark.svg` — callout box → single-elbow dashed arrow up to the container's bottom-center.

### Pattern — Edge label (offset from line, centered, NO background)

```svg
<!-- For horizontal segment: position 14px ABOVE the arrow -->
<g transform="translate(MIDPOINT_X, ARROW_Y - 14)">
  <text class="edge-label" text-anchor="middle" y="4">label text</text>
</g>

<!-- For vertical segment: text-anchor=start, position 6px RIGHT of arrow -->
<g transform="translate(ARROW_X + 6, MIDPOINT_Y)">
  <text class="edge-label" text-anchor="start" y="4">label text</text>
</g>
```

No `<rect>` background — the offset keeps the label clear of the line, and the text reads off the solid `var(--bg)` card; an opaque cutout would punch a hole in any nearby stroke (§Edge labels). See `examples/bridge-crossover.svg` — the `hops over` label sits offset above the long left segment of the hopping edge.

### Pattern — Marker defs (3 markers; include all)

```svg
<defs>
  <marker id="arrow-flow" viewBox="0 0 14 12" refX="0" refY="6"
          markerWidth="14" markerHeight="12"
          markerUnits="userSpaceOnUse" orient="auto">
    <path d="M 0 0 L 14 6 L 0 12 z" />
  </marker>
  <marker id="arrow-loopback" viewBox="0 0 14 12" refX="0" refY="6"
          markerWidth="14" markerHeight="12"
          markerUnits="userSpaceOnUse" orient="auto">
    <path d="M 0 0 L 14 6 L 0 12 z" />
  </marker>
  <marker id="arrow-callout" viewBox="0 0 14 12" refX="0" refY="6"
          markerWidth="14" markerHeight="12"
          markerUnits="userSpaceOnUse" orient="auto">
    <path d="M 0 0 L 14 6 L 0 12 z" />
  </marker>
</defs>
```

CSS:
```css
#arrow-flow     path { fill: var(--flow-line); }
#arrow-loopback path { fill: var(--flow-loopback); }
#arrow-callout  path { fill: var(--callout-stroke); }
```

### Pattern — In-SVG Legend (bottom-left, project-aware labels)

Place at the bottom-left. Label each swatch in the project's domain vocabulary, NOT the generic role token — e.g. `agent` → "user" (humans) / "service" (microservices); `data` → "log" / "queue" / "database"; `action` → "command" / "step" / "process". Include ONLY the roles that actually appear.

**Lay items out SEQUENTIALLY by text width — NEVER a fixed per-item pitch.** Each item occupies `swatch(22) + gap(8) + text_width`; the next item's `x` = previous item's right edge **+ ≥24px**. A hardcoded pitch (every item at +100, +120 …) silently overlaps once a label is long or at 18px — the next swatch lands under the previous label. Compute each `x` from the running total; `text_width` is the §Typography — Text-width estimate (**character-class sum**, not a flat `chars × 10`). The inter-item gap here is exact, so a crude flat estimate over-reserves narrow / space-heavy labels and renders **visibly uneven gaps** — use the class sum.

```svg
<g class="legend" transform="translate(50, LEGEND_Y)">
  <!-- Repeat for each role actually used; pick a domain-appropriate label.
       item x = prev_x + 22 + 8 + ceil(prev_text_width) + 24 -->
  <g transform="translate(0, 0)">
    <rect width="22" height="12" rx="3" fill="var(--action-fill)" />
    <text x="30" y="10" class="legend-label">skills</text>
  </g>
  <g transform="translate(99, 0)">   <!-- 0 + 30 + ("skills" ≈ 45 via class sum: s·k·s=10×3, i·l·l=5×3) + 24 = 99 -->
    <rect width="22" height="12" rx="3" fill="var(--data-fill)" stroke="var(--data-stroke)" stroke-width="1.2" />
    <text x="30" y="10" class="legend-label">log</text>
  </g>
</g>
```

See `examples/dark.svg` — `terminal / action / callout` at `0 / 135 / 250`, each gap ≥24px regardless of label length.

## Presets

| Preset | Background | Use when |
|---|---|---|
| `dark` (default) | slate-950 `#020617` | dark-mode UI / terminal screenshots |
| `light` | cream `#F0EEE6` | docs / blog / light-mode product UI |
| `mono-print` | white | print / academic / no-color |

## Reference examples — READ the matching one before you draw (MANDATORY)

`examples/` holds the canonical, render-verified diagrams. **Before writing v1 coordinates, Read (both `.html` and `.svg`) the example(s) matching your diagram's features.** For the theme trio, read ONLY the one matching your chosen theme — all three share identical geometry.

| Example | Read it for |
|---|---|
| `dark` / `light` / `mono-print` (read only your theme) | A full diagram at the default canvas: container, loop-back, callout, legend spacing. |
| `fan-in-out` | Fan-in (N→1), fan-out (1→N arced Y), branches off a through-line. |
| `bridge-crossover` | Hop arc over a crossing (solid + dashed). |
| `content-card` | Content card: bold title + detail lines, height grows to fit; cards in different role colors. |

## Workflow

All artifacts go in `./tmp_diagram/` relative to the current working directory (project root, NOT `/tmp/`). Create the directory if it does not exist: `mkdir -p tmp_diagram`.

1. **Ask output format + canvas width + theme + corner rounding** (`AskUserQuestion`, four questions in one call):

   > **Language (L3 · USER)**: the four questions below + all their option labels + any Step 2 clarifying question are user-facing, so phrase them in `conversation_language` per `ai_context/skills_config.md §Language`. The canonical option *values* / theme + format keywords (`svg` / `png` / `html` / `dark` / `light` / `mono-print` / `auto`) and role names stay English regardless.

   **Q1 — output format** (single-select, 4 options in order):
   - `svg (recommended)` — standalone SVG, opens in any browser, lossless scaling
   - `png` — rasterized for chat / docs that don't accept SVG
   - `html` — editable source (CSS in `<head>`, inline SVG in `<body>`); keep for re-editing
   - `all three`

   **Q2 — canvas (viewBox) width** (single-select; see §Output width — the cap is never a fill target):
   - `auto — fit to content, ≤1500 (recommended)` — pick the SMALLEST viewBox that holds the content at 50px padding, capped at 1500; do NOT pad out to fill the canvas
   - `1500 (full default)` — use the full default canvas (e.g. to match an existing 1500-wide set)
   - `custom` — user supplies a viewBox width (display width = `min(viewBox, 825)`)

   **Q3 — theme** (single-select, 3 options; default `dark` — see §Presets). Skip this question only when the user already named a theme in their request:
   - `dark (default)` — slate-950 `#020617`; dark-mode UI / terminal screenshots
   - `light` — cream `#F0EEE6` + sage; docs / blog / light-mode product UI
   - `mono-print` — B&W; print / academic / no-color

   **Q4 — corner rounding** (single-select; affects only the diagram's SVG / PNG output — when Q1 = `html` only, record the answer but skip applying the radius). Default `yes — radius 25`:
   - `yes — rounded, radius 25 (recommended)` — round the diagram's background corners with `rx` / `ry` = 25 (viewBox user units)
   - `yes — rounded, custom radius` — round with a user-supplied integer radius (viewBox user units; capture it via the ask tool's free-text path)
   - `no — square corners`

   Record all four answers. The format answer determines which files survive Step 6 (the workflow always builds HTML → SVG; a PNG is rendered only when the Step 5 heavyweight review runs or the format itself needs it — `png` / `all three`). The canvas-width answer sets the viewBox cap for Step 2 layout; for a multi-diagram SET, apply the chosen policy once and use ONE shared width across the set. The theme answer fixes the preset for Steps 3–4 and is what §Reference examples' "read ONLY your theme" keys off — load only the chosen theme's color table + example, never all three. The corner-rounding answer sets `<radius>` (25 / custom / 0 for square), threaded to `extract_svg.py --radius <radius>` at Steps 4 + 5; for a multi-diagram SET use ONE shared radius across the set.

2. **Plan** — three passes before writing any coordinate:
   - **Understand** — restate the node + edge spec. Ask **one** clarifying question ONLY if material ambiguity remains (the sole conditional interrupt outside the two standard asks — Step 1 + Step 5); otherwise proceed on the most reasonable reading and record the assumption in the Step 6 report.
   - **Map domain → roles** — list every node + its role (`action` / `agent` / `data` / `decision` / `event` / `state` / `terminal` / `callout`, or an `accent` slot); **all process steps / commands → `action`** (don't sub-categorize); decide the **legend label** for each used role per project domain (e.g. "agent" for AI runtimes, "log" for log dirs).
   - **Layout reasoning** — apply the §Layout Reasoning 13-point checklist.

3. **Read the matching reference example(s), THEN generate v1 HTML** — first Read (both `.html` and `.svg`) the example(s) matching your diagram's features; for the theme trio read ONLY your chosen theme (see §Reference examples — MANDATORY). Then write `./tmp_diagram/flowchart-v1-<slug>.html` with inline SVG: copy the chosen preset's `<style>` block verbatim from `examples/<preset>.html`, and match the example's geometry for any feature it shows.

   > **Language (L3 · DISK)**: the diagram's own visible text — node labels / sublabels / legend entries / captions / content-card detail lines — is disk-bound output baked into the `.html` / `.svg`, so write it in `content_language` per `ai_context/skills_config.md §Language` (exception: label text the user supplied verbatim is kept as given). Role / CSS class names, `--var` tokens, file paths, and code identifiers stay English regardless.

4. **Build & lint v1 (always — cheap, no interrupt)** — extract the SVG, then run the deterministic linter and fix every HIGH before anyone reviews. Rendering is NOT done here — it belongs to the Step 5 review branch.
   - **Extract** the `.svg` from the `.html`: the `<style>` block is moved into the SVG (CDATA-wrapped) with a `var(--bg)` background rect (rounded to `rx` / `ry` = `<radius>` per the Step 1 answer; omit `--radius` / pass `0` for square) and an explicit `text { font-family: var(--font); }` rule injected (otherwise SVG `<text>` loses the body font inheritance and falls back to browser default — usually serif):
     ```bash
     python3 "${CLAUDE_PLUGIN_ROOT}/skills/draw-diagram/scripts/extract_svg.py" \
       ./tmp_diagram/flowchart-v1-<slug>.html \
       ./tmp_diagram/flowchart-v1-<slug>.svg --radius <radius>
     ```
   - **Lint** the extracted SVG — zero-token, no false positives; checks exactly from the source coordinates the invariants subagents historically eyeballed wrong (~50% false-positive rate): marker `refX=0` / `markerUnits=userSpaceOnUse` / 14×12 size, content clipped outside the viewBox, loop-back endpoints off the node center-x, an edge segment crossing a non-endpoint node, and pure-black strokes/fills.
     ```bash
     python3 "${CLAUDE_PLUGIN_ROOT}/skills/draw-diagram/scripts/lint_svg.py" \
       ./tmp_diagram/flowchart-v1-<slug>.svg
     ```
     Exit code `1` = at least one HIGH. **Always fix every lint HIGH** — these are deterministic real bugs: `Edit` the `.html`, re-extract, re-lint until clean. This runs regardless of the Step 5 choice. The linter does NOT judge palette / text-overflow / balance / requirement match / padding symmetry — those are the review subagent's job (Step 5).

5. **Ask: heavyweight review + fix?** (`AskUserQuestion`, ONE question — the second and last standard ask). Geometry is already lint-clean; this gates only the EXPENSIVE pass (PNG render + 1 review subagent + visual-claim verification + patch). Two options, default the lightweight one:
   - **No — ship the lint-clean v1 (recommended)** — skip the subagent entirely; render a PNG ONLY if the Step 1 format needs it (`png` / `all three`); promote `flowchart-v1-<slug>.*` → `flowchart-<slug>.*`; go to Step 6.
   - **Yes — run the heavyweight review** — then, in order:
     1. **Render** v1 to PNG (the Read tool needs a raster):
        ```bash
        google-chrome --headless --disable-gpu --no-sandbox --hide-scrollbars \
          --window-size=<W>,<H> --default-background-color=00000000 \
          --screenshot=./tmp_diagram/flowchart-v1-<slug>.png \
          "file://$(pwd)/tmp_diagram/flowchart-v1-<slug>.svg"
        ```
        `<W>` = viewBox width + 64; `<H>` = viewBox height + 32. `--default-background-color=00000000` keeps the area outside a rounded bg rect transparent (a harmless no-op for square corners — always include it).
     2. **Dispatch ONE review subagent** (merged Visual + Logical + Requirement — see §Subagent Review Prompt). It reads the PNG **only** — NOT this SKILL.md (the prompt's checklist is self-contained); the deterministic geometry is already covered by Step 4's lint. It owns ONLY the judgements a coordinate check cannot make: palette, text overflow, balance / horizontal-space pressure, fan-in/out shape, padding symmetry, and requirement match (all nodes / edges / labels present).
     3. **Synthesize + verify** — categorize the subagent's findings critical / important / nitpick. Its VISUAL claims carry a ~50% false-positive risk (e.g. "text overflows", "looks unbalanced") — **verify each against the PNG yourself with Read before acting**.
     4. **Patch or promote** — no critical / important fix → promote v1 (rename to `flowchart-<slug>.*`). Otherwise **patch in place**: `Edit` the real fixes into the `.html` (targeted edits — do NOT rewrite from scratch), re-extract the SVG (same `--radius <radius>`), **re-lint** (must come back clean), re-render for visual confirmation; save as `flowchart-<slug>.*`. **Hard cap: 2 patch iterations.**

6. **Filter outputs per Step 1 choice + Present**. Always delete any leftover intermediate (`-v1-`) files. **The final `.html` source is kept by DEFAULT regardless of format choice** — it is the editable source, and deleting it strands re-editing (the extracted `.svg` is awkward to hand-edit: CDATA-wrapped CSS + injected bg rect). Keep per choice:
    - `svg` (default) → keep `.svg` **+ `.html` source**; delete `.png`
    - `png` → keep `.png` **+ `.html` source**; delete `.svg`
    - `html` → keep `.html`; delete `.svg` + `.png`
    - `all three` → keep `.html` + `.svg` + `.png`

    Report: kept paths, preset, node/edge counts, lint result (`clean` / HIGHs fixed), whether the Step 5 heavyweight review ran (+ any v1→final changes), AND the **re-extract command** so the user can regenerate the deliverable after editing the HTML source:
    ```bash
    python3 "${CLAUDE_PLUGIN_ROOT}/skills/draw-diagram/scripts/extract_svg.py" \
      tmp_diagram/flowchart-<slug>.html tmp_diagram/flowchart-<slug>.svg --radius <radius>
    ```

## Subagent Review Prompt

ONE merged subagent. It reads the PNG **only** — NOT this SKILL.md (the checklist below is self-contained) — and owns only the visual / requirement judgements a coordinate check cannot make. The deterministic geometry (marker `refX` / `markerUnits` / size, viewBox clipping, loop-back center-x alignment, edge-through-node collisions, pure-black strokes) is already verified by Step 4's `lint_svg.py` — the subagent must NOT re-report those.

```
Inputs: PNG <path>, original user description (mermaid source / prose), the node/edge spec. If a reference image was provided its path is in this prompt.

Use the Read tool to view the PNG (and the reference image, if any). Do NOT read any spec file — this checklist is complete. Do NOT re-check marker geometry, loop-back centering, edge-through-node collisions, viewBox clipping, or pure-black colors: a deterministic linter already owns those. Focus on what only an eye can judge:

VISUAL
1. **Crossings** — flag ONLY undifferentiated ones (two identical solid lines overlapping with no bridge/hop arc, distinct color, or dash).
2. **Container fit** — container rect fully encloses every contained node with ≥30px padding; flag an edge cutting through a node. A loop-back whose source AND destination are both INSIDE a container must route inside the box (internal gutter), NOT in the page margin outside it.
3. **Arrow tips** — every arrow shows a visible triangle whose apex touches the destination edge (visible gap or overshoot = fail).
4. **Text** — no cut-off / overflow; node labels uniformly 18px.
5. **Palette** — only locked-palette colors.
6. **Legend** — present (for the roles used), not cut off, labels 18px, items spaced sequentially by text width (no swatch under a prior label) AND inter-item gaps look UNIFORM (a noticeably wider gap = over-reserved width; flag it).
7. **ViewBox padding symmetry** — the four paddings look ≈50px; top≈bottom and left≈right (no framed-wrong feel).
8. **ALIGNMENT AUDIT** — same-row Y / same-column X / same-role uniform width / line origin from box center / edge labels offset (above horizontal, right of vertical) / fan-OUT = SYMMETRIC arced-split Y / fan-IN = independent arrows (no merged stem).
9. **No in-SVG title** — the SVG holds only nodes, edges, labels, legend (no baked-in heading).
10. **Label backgrounds** — edge/line labels have NO background fill (flag an opaque box covering a stroke); container/group labels DO keep an opaque `var(--bg)` gap fully breaking the dashed border (flag dashes poking through).
11. **Background card** — the rounded `var(--bg)` background covers the WHOLE viewBox: all four corners rounded identically, no transparent strip / square-cut side.
12. **Reference image match** — if one was provided, does composition / arrow style / layout match? Note any divergence.

LOGICAL
13. **Same-role color** — same-role nodes share ONE color (don't split one role into sub-colors).
14. **Legend labels** project-domain-appropriate (e.g. "agent" for AI runtimes, not "actor").
15. **Data-store siblings** share width when labels permit; arrows leave from box CENTER.
16. **HORIZONTAL SPACE PRESSURE** — overflowing / cramped / tiny text from too much in one row? Name the relieving fix (move a mid-flow node to a parallel row / stack fan-in sources vertically over their target / redistribute gaps), or say it should be re-done VERTICAL. Do not pass a cramped wide layout silently.
17. **Fan-IN vs fan-OUT** — convergence (N→1) = INDEPENDENT arrows; divergence (1→N) = SYMMETRIC shared-trunk Y with an ARCED split. Flag a merged-Y fan-in, a lopsided fan-out, or a hard-T split.

REQUIREMENT (against the user's source)
18. All nodes present; all edges present (count); no wiring errors; no extras.
19. Edge + node labels match the source exactly (including paths like "logs/review_reports").
20. Role assignments fit the project semantics.

Report HIGH/MEDIUM/LOW findings. Under 450 words. Do NOT propose fixes.
```

## Output

All artifacts live in `./tmp_diagram/` (relative to the cwd, NOT `/tmp/`). What survives Step 6 depends on the user's Step 1 format choice:

| Format choice | Kept in `./tmp_diagram/` |
|---|---|
| `svg` (default) | `flowchart-<slug>.svg` + `.html` source |
| `png` | `flowchart-<slug>.png` + `.html` source |
| `html` | `flowchart-<slug>.html` |
| `all three` | `.html` + `.svg` + `.png` |

All intermediate (`-v1-`) files are deleted at Step 6. SVG is the canonical deliverable (standalone, embeds CSS + Google Font @import, opens in any browser). **The `.html` source is retained alongside the deliverable by default** so the diagram can be re-edited and re-extracted (Step 6 prints the re-extract command) without redrawing from scratch. PNG is a raster export.

If the user wants the diagram permanently in the project (e.g., `assets/diagrams/`), `cp` from `./tmp_diagram/` to the chosen path.

## Anti-patterns (hard NOs)

Boundary rules not already enforced by a §Section above:

- **Diagonal arrows / cubic curves anywhere** — every edge (including callout) is orthogonal; the callout uses exactly ONE rounded corner (no Z-elbow, no cubic). The SOLE non-orthogonal exception is the bridge/hop arc at a crossing.
- **Edge crossing a node it doesn't connect to** — if an arrow segment passes through a non-source/dest node's bounding rect, reroute or reposition. `lint_svg.py` (Step 4) catches this deterministically — do NOT ship a diagram with an unresolved `edge-through-node` HIGH.
- **Pure-black text or arrows** — use the palette's softened greys (`--text`, `--flow-line`); pure `#000` clashes with the cream / slate backgrounds. `lint_svg.py` flags literal `#000` / `black` / `rgb(0,0,0)`.
- **Skipping the Step 4 lint** (it always runs — geometry safety net), or, when the Step 5 heavyweight review IS chosen, accepting the subagent's VISUAL claims without verifying against the rendered PNG yourself (subagent visual-claim false-positive rate ~50%). Lint findings are deterministic and trusted as-is — re-verify only the subagent's visual claims, never the lint output.
- **Outputting `.html` or `.png` as the deliverable** — SVG is what the user gets; HTML is editable source; PNG is throwaway review raster.
- **Extracting SVG without injecting `text { font-family: var(--font); }`** — the body rule's font inheritance is gone in standalone SVG; without an explicit text rule, every `<text>` falls back to browser default (serif).

Already enforced in their own §Section (not repeated here): single-role color assignment (§Layout Reasoning), uniform 18px node / edge / legend text + no in-SVG title (§Typography), `markerUnits="userSpaceOnUse"` (§Arrows), crossing disambiguation (§Routing Rules), the 2-iteration hard cap (§Workflow).
