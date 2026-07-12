#!/usr/bin/env python3
"""Deterministic geometry linter for a draw-diagram standalone .svg.

Usage:
    lint_svg.py <diagram.svg>

Checks the invariants that the review subagents historically got WRONG
(false-positive rate ~50% on eyeballed-from-raster geometry claims). These
are all computable EXACTLY from the SVG source coordinates, so the linter
replaces the geometry portion of the visual review with a zero-token,
no-false-positive pass. The single review subagent is left with the genuinely
visual judgements (palette, text overflow, balance, requirement match) that a
coordinate check cannot make.

Checks (HIGH = a real geometry bug; MEDIUM = advisory, eyeball to confirm):
  1. markers          (HIGH)   — all <marker>s: refX=0, markerUnits=userSpaceOnUse, 14x12
  2. content-in-viewbox (HIGH) — no node/edge geometry clipped outside the viewBox
  3. loopback-origin  (HIGH)   — loopback arrow endpoints sit on a node's center-x
  4. edge-through-node (HIGH)  — no orthogonal edge segment crosses a non-endpoint node
  5. pure-black       (HIGH)   — no literal #000 / black / rgb(0,0,0) stroke/fill

Padding SYMMETRY is deliberately NOT linted (text + legend bounds can't be
measured from coordinates alone) — it stays a visual-subagent judgement.
Exit code: 0 if no HIGH findings, 1 if any HIGH. MEDIUM never fails the run.
Geometry is parsed with regex (no XML dep, matching extract_svg.py's style).
"""
import re
import sys
from pathlib import Path

# Tolerances (viewBox user units).
ALIGN_TOL = 2       # loopback endpoint vs node center-x
CLIP_TOL = 1        # how far outside the viewBox counts as clipped
INTERIOR = 6        # shrink a node rect by this before the cross test
ENTRY_MARGIN = 16   # an endpoint within this of a node = that node is an endpoint owner


def _floats(s):
    return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", s)]


def parse_rects(svg):
    """All <rect> open tags → list of dicts with geometry + class + fill."""
    out = []
    for m in re.finditer(r"<rect\b([^>]*?)/?>", svg):
        attrs = m.group(1)
        def a(name):
            mm = re.search(rf'{name}\s*=\s*"([^"]*)"', attrs)
            return mm.group(1) if mm else None
        x, y, w, h = a("x"), a("y"), a("width"), a("height")
        if None in (x, y, w, h):
            continue
        try:
            out.append({
                "x": float(x), "y": float(y),
                "w": float(w), "h": float(h),
                "cls": a("class") or "",
                "fill": a("fill") or "",
            })
        except ValueError:
            continue
    return out


def parse_segments(svg):
    """Top-level <line>/<path> arrows → list of (kind, [points]).

    Edge labels live in transformed <g> wrappers and hold only <text>; arrows
    (flow / loopback / callout) are absolute top-level, so their raw coords are
    page coords. Each path 'd' is reduced to its anchor points (M/L and the
    endpoint of every Q/A); only axis-aligned segments are returned for the
    cross test (diagonal hop-arc spans are skipped).
    """
    segs = []
    for m in re.finditer(r"<line\b([^>]*?)/?>", svg):
        attrs = m.group(1)
        cls_m = re.search(r'class\s*=\s*"([^"]*)"', attrs)
        cls = cls_m.group(1) if cls_m else ""
        if "arrow" not in cls:                       # skip non-edge lines
            continue
        def a(name):
            mm = re.search(rf'{name}\s*=\s*"([^"]*)"', attrs)
            return float(mm.group(1)) if mm else None
        x1, y1, x2, y2 = a("x1"), a("y1"), a("x2"), a("y2")
        if None not in (x1, y1, x2, y2):
            segs.append((cls, [(x1, y1), (x2, y2)]))
    for m in re.finditer(r'<path\b([^>]*?)\bd\s*=\s*"([^"]*)"([^>]*?)/?>', svg):
        cls_m = re.search(r'class\s*=\s*"([^"]*)"', m.group(1) + m.group(3))
        cls = cls_m.group(1) if cls_m else ""
        if "arrow" not in cls:                       # skip <marker> triangles etc.
            continue
        pts = parse_path_points(m.group(2))
        if len(pts) >= 2:
            segs.append((cls, pts))
    return segs


def parse_path_points(d):
    """Anchor points of a path 'd'. M/L take x,y; Q takes the last pair
    (endpoint, not the control); A takes the last pair (arc endpoint)."""
    pts = []
    for cmd, body in re.findall(r"([MLQA])([^MLQA]*)", d):
        nums = _floats(body)
        if cmd in ("M", "L") and len(nums) >= 2:
            pts.append((nums[0], nums[1]))
        elif cmd == "Q" and len(nums) >= 4:
            pts.append((nums[2], nums[3]))
        elif cmd == "A" and len(nums) >= 7:
            pts.append((nums[-2], nums[-1]))
    return pts


# ---- checks -----------------------------------------------------------------

def check_markers(svg, findings):
    markers = re.findall(r"<marker\b([^>]*)>", svg)
    if not markers:
        findings.append(("HIGH", "markers", "no <marker> defs found"))
        return
    for attrs in markers:
        mid = (re.search(r'id\s*=\s*"([^"]*)"', attrs) or [None, "?"])[1] \
            if re.search(r'id\s*=\s*"([^"]*)"', attrs) else "?"
        refx = re.search(r'refX\s*=\s*"([^"]*)"', attrs)
        if not refx or refx.group(1).strip() not in ("0", "0.0"):
            findings.append(("HIGH", "markers",
                f'marker "{mid}": refX must be 0 (got {refx.group(1) if refx else "missing"}) '
                "— line would overlap the triangle interior"))
        if 'markerUnits="userSpaceOnUse"' not in attrs.replace(" ", "") \
                and "markerUnits='userSpaceOnUse'" not in attrs:
            mu = re.search(r'markerUnits\s*=\s*"([^"]*)"', attrs)
            findings.append(("HIGH", "markers",
                f'marker "{mid}": markerUnits must be userSpaceOnUse '
                f'(got {mu.group(1) if mu else "missing"})'))
        mw = re.search(r'markerWidth\s*=\s*"([^"]*)"', attrs)
        mh = re.search(r'markerHeight\s*=\s*"([^"]*)"', attrs)
        if not (mw and mh and mw.group(1) == "14" and mh.group(1) == "12"):
            findings.append(("MEDIUM", "markers",
                f'marker "{mid}": expected 14x12 '
                f'(got {mw.group(1) if mw else "?"}x{mh.group(1) if mh else "?"})'))


def content_bbox(nodes, containers, segs):
    xs, ys = [], []
    for r in nodes + containers:
        xs += [r["x"], r["x"] + r["w"]]
        ys += [r["y"], r["y"] + r["h"]]
    for _, pts in segs:
        for px, py in pts:
            xs.append(px)
            ys.append(py)
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def check_viewbox(svg, nodes, containers, segs, findings):
    vb = re.search(r'viewBox\s*=\s*"([^"]+)"', svg)
    if not vb:
        findings.append(("HIGH", "content-in-viewbox", "no viewBox on <svg>"))
        return
    nums = _floats(vb.group(1))
    if len(nums) != 4:
        findings.append(("HIGH", "content-in-viewbox", "malformed viewBox"))
        return
    vx, vy, vw, vh = nums
    bbox = content_bbox(nodes, containers, segs)
    if not bbox:
        return
    min_x, min_y, max_x, max_y = bbox
    # Clip = node/edge geometry outside the viewBox (HIGH). Padding SYMMETRY is
    # intentionally NOT checked here: text + legend bounds are excluded from the
    # bbox, so the bottom/right padding can't be measured exactly — it stays a
    # visual-subagent judgement. The clip test only needs node/edge geometry.
    if min_x < vx - CLIP_TOL or min_y < vy - CLIP_TOL \
            or max_x > vx + vw + CLIP_TOL or max_y > vy + vh + CLIP_TOL:
        findings.append(("HIGH", "content-in-viewbox",
            f"geometry [{min_x:.0f},{min_y:.0f} .. {max_x:.0f},{max_y:.0f}] "
            f"is clipped outside viewBox [{vx:.0f},{vy:.0f} .. "
            f"{vx + vw:.0f},{vy + vh:.0f}]"))


def check_loopback(nodes, segs, findings):
    centers = sorted({round(r["x"] + r["w"] / 2, 1) for r in nodes})
    for cls, pts in segs:
        if "loopback" not in cls:
            continue
        for label, (px, _) in (("start", pts[0]), ("end", pts[-1])):
            if not any(abs(px - c) <= ALIGN_TOL for c in centers):
                near = min(centers, key=lambda c: abs(px - c)) if centers else None
                findings.append(("HIGH", "loopback-origin",
                    f"loopback {label} x={px:.0f} is not on any node center-x"
                    + (f" (nearest {near:.0f}, off by {abs(px - near):.0f})"
                       if near is not None else "")))


def _seg_crosses_rect(p1, p2, r):
    """True iff the axis-aligned segment p1->p2 passes through r's interior
    (shrunk by INTERIOR). Diagonal/zero-length segments return False."""
    x1, y1 = p1
    x2, y2 = p2
    rx1, ry1 = r["x"] + INTERIOR, r["y"] + INTERIOR
    rx2, ry2 = r["x"] + r["w"] - INTERIOR, r["y"] + r["h"] - INTERIOR
    if rx2 <= rx1 or ry2 <= ry1:
        return False
    if abs(y1 - y2) < 0.5 and abs(x1 - x2) >= 0.5:        # horizontal
        if not (ry1 < y1 < ry2):
            return False
        lo, hi = min(x1, x2), max(x1, x2)
        return min(hi, rx2) - max(lo, rx1) > INTERIOR
    if abs(x1 - x2) < 0.5 and abs(y1 - y2) >= 0.5:        # vertical
        if not (rx1 < x1 < rx2):
            return False
        lo, hi = min(y1, y2), max(y1, y2)
        return min(hi, ry2) - max(lo, ry1) > INTERIOR
    return False


def _owns_endpoint(r, pts):
    """A node 'owns' an edge endpoint if either end lands within ENTRY_MARGIN
    of the rect — that edge legitimately enters/exits this node."""
    for px, py in (pts[0], pts[-1]):
        if (r["x"] - ENTRY_MARGIN <= px <= r["x"] + r["w"] + ENTRY_MARGIN
                and r["y"] - ENTRY_MARGIN <= py <= r["y"] + r["h"] + ENTRY_MARGIN):
            return True
    return False


def check_edge_through_node(nodes, segs, findings):
    for cls, pts in segs:
        if "arrow" not in cls:
            continue
        for r in nodes:
            if _owns_endpoint(r, pts):
                continue
            for i in range(len(pts) - 1):
                if _seg_crosses_rect(pts[i], pts[i + 1], r):
                    label = r["cls"].replace("role-", "") or "node"
                    findings.append(("HIGH", "edge-through-node",
                        f"an edge segment crosses {label} node at "
                        f"[{r['x']:.0f},{r['y']:.0f} {r['w']:.0f}x{r['h']:.0f}] "
                        "(neither its source nor destination) — reroute"))
                    break


def check_pure_black(svg, findings):
    for m in re.finditer(r'(stroke|fill)\s*=\s*"(#000000|#000|black|rgb\(0,\s*0,\s*0\))"', svg):
        findings.append(("HIGH", "pure-black",
            f'{m.group(1)}="{m.group(2)}" — use a softened palette grey, not pure black'))


# ---- main -------------------------------------------------------------------

def lint(svg_path):
    svg = Path(svg_path).read_text()
    nodes = [r for r in parse_rects(svg) if "role-" in r["cls"]]
    containers = [r for r in parse_rects(svg)
                  if "container" in r["cls"] or "stroke-dasharray" in r["cls"]]
    segs = parse_segments(svg)

    findings = []
    check_markers(svg, findings)
    check_viewbox(svg, nodes, containers, segs, findings)
    check_loopback(nodes, segs, findings)
    check_edge_through_node(nodes, segs, findings)
    check_pure_black(svg, findings)

    highs = [f for f in findings if f[0] == "HIGH"]
    meds = [f for f in findings if f[0] == "MEDIUM"]
    print(f"LINT {Path(svg_path).name}: {len(highs)} HIGH, {len(meds)} MEDIUM "
          f"(nodes={len(nodes)}, edges={len(segs)})")
    for sev, check, msg in highs + meds:
        print(f"  [{sev}] {check}: {msg}")
    if not findings:
        print("  clean — all deterministic geometry checks pass")
    return 1 if highs else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(lint(sys.argv[1]))
