"""
greencode/cli/report.py
━━━━━━━━━━━━━━━━━━━━━━━
Generates CO₂ reports from measurement history.

Zero external dependencies — stdlib only + measure.py.
Charts rendered via native Canvas API (no CDN required).

Usage:
    from .report import save_html_report, save_json_report, generate_pr_comment
"""

from __future__ import annotations

import json
import datetime
from pathlib import Path
from typing import Optional

from .measure import load_history, GRADE_LABELS

REPORT_DIR = Path(".greencode")


# ── Stats ─────────────────────────────────────────────────────

def compute_stats(history: list[dict]) -> dict:
    if not history:
        return {}

    grams  = [r["grams_co2"] for r in history]
    grades = [r["grade"]     for r in history]

    trend = "stable"
    if len(grams) >= 4:
        mid   = len(grams) // 2
        first = sum(grams[:mid]) / mid
        last  = sum(grams[mid:]) / (len(grams) - mid)
        pct   = (last - first) / first * 100 if first else 0
        if pct >  10: trend = "increasing"
        if pct < -10: trend = "decreasing"

    return {
        "total_measurements": len(history),
        "total_grams":        round(sum(grams), 4),
        "avg_grams":          round(sum(grams) / len(grams), 4),
        "min_grams":          round(min(grams), 4),
        "max_grams":          round(max(grams), 4),
        "latest_grams":       round(grams[-1], 4),
        "latest_grade":       grades[-1],
        "grade_counts":       {g: grades.count(g) for g in ["green", "yellow", "red"]},
        "trend":              trend,
        "first_date":         history[0]["timestamp"][:10],
        "latest_date":        history[-1]["timestamp"][:10],
    }


# ── JSON report ───────────────────────────────────────────────

def generate_json_report(history: Optional[list] = None) -> dict:
    h = history or load_history()
    return {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "stats":        compute_stats(h),
        "history":      h,
    }


def save_json_report(path: Optional[str] = None) -> Path:
    out = Path(path) if path else REPORT_DIR / "report.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(generate_json_report(), indent=2), encoding="utf-8")
    return out


# ── PR comment ────────────────────────────────────────────────

def generate_pr_comment(current: dict, previous: Optional[dict] = None) -> str:
    g     = current["grade"]
    meta  = GRADE_LABELS[g]
    grams = current["grams_co2"]

    lines = [
        f"## {meta['emoji']} GreenCode \u2014 Carbon Footprint",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| **CO\u2082** | `{grams:.4f}g` |",
        f"| **Grade** | **{g.upper()}** {meta['emoji']} |",
        f"| **Commit** | `{current.get('commit', 'unknown')}` |",
        f"| **Branch** | `{current.get('branch', 'unknown')}` |",
    ]

    if previous and previous.get("grams_co2"):
        delta = grams - previous["grams_co2"]
        pct   = delta / previous["grams_co2"] * 100
        sign  = "+" if delta >= 0 else ""
        arrow = "\u25b2" if delta > 0 else "\u25bc"
        lines.append(
            f"| **vs prev** | {arrow} `{sign}{delta:.4f}g` ({sign}{pct:.1f}%) |"
        )

    lines += [
        "",
        "> [GreenCode](https://alexap0st0l.github.io/GreenCode/) "
        "\u00b7 [methodology](https://alexap0st0l.github.io/GreenCode/#how)",
    ]
    return "\n".join(lines)


# ── HTML dashboard ────────────────────────────────────────────

def generate_html_report(history: Optional[list] = None) -> str:
    h     = history or load_history()
    stats = compute_stats(h)

    if not h:
        return (
            "<!DOCTYPE html><html><body style='background:#07080C;color:#fff;"
            "font-family:monospace;padding:40px'>"
            "<p>No data yet. Run <code>greencode measure</code> first.</p>"
            "</body></html>"
        )

    recent = h[-40:]

    # JS-safe data arrays
    js_labels = json.dumps([f"{r['commit']} {r['timestamp'][:10]}" for r in recent])
    js_values = json.dumps([r["grams_co2"] for r in recent])
    js_colors = json.dumps([GRADE_LABELS[r["grade"]]["color"] for r in recent])

    latest = h[-1]
    lg     = GRADE_LABELS[latest["grade"]]
    gc     = stats.get("grade_counts", {"green": 0, "yellow": 0, "red": 0})

    trend_arrow = {"increasing": "▲", "decreasing": "▼", "stable": "→"}.get(
        stats.get("trend", "stable"), "→"
    )
    trend_color = {
        "increasing": "#F87171",
        "decreasing": "#4ADE80",
        "stable":     "#FCD34D",
    }.get(stats.get("trend", "stable"), "#FCD34D")

    # Table rows
    rows_html = ""
    for r in reversed(h[-50:]):
        m = GRADE_LABELS[r["grade"]]
        rows_html += (
            f"<tr>"
            f"<td>{r['timestamp'][:10]}</td>"
            f"<td class='hi'>{r.get('commit','—')}</td>"
            f"<td>{r.get('branch','—')}</td>"
            f"<td style='color:{m['color']};font-weight:700'>{r['grams_co2']:.4f}</td>"
            f"<td><span class='badge {r['grade']}'>{m['emoji']} {r['grade']}</span></td>"
            f"<td class='dim'>{r.get('note','—')}</td>"
            f"</tr>"
        )

    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>GreenCode \u2014 Dashboard</title>
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  background: #07080C;
  color: #F1F5F9;
  font-family: 'Courier New', Courier, monospace;
  line-height: 1.5;
}}
/* nav */
nav {{
  background: #0D0F16;
  border-bottom: 1px solid #1E2130;
  padding: 14px 28px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky;
  top: 0;
  z-index: 10;
}}
.logo {{ font-size: 16px; font-weight: 700; color: #4ADE80; }}
.logo span {{ color: #F1F5F9; }}
.live {{ font-size: 9px; color: #4ADE80; letter-spacing: 1px; }}
/* layout */
.wrap {{ max-width: 1000px; margin: 0 auto; padding: 28px 20px; }}
.label {{
  font-size: 8px;
  color: #6B7280;
  letter-spacing: 3px;
  margin-top: 28px;
  margin-bottom: 12px;
}}
/* grids */
.g4 {{ display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; }}
.g3 {{ display: grid; grid-template-columns: repeat(3,1fr); gap: 12px; }}
/* cards */
.card {{
  background: #0D0F16;
  border: 1px solid #1E2130;
  border-radius: 10px;
  padding: 18px;
}}
.val {{ font-size: 30px; font-weight: 700; line-height: 1; margin-bottom: 4px; }}
.sub {{ font-size: 8px; color: #6B7280; letter-spacing: 1px; }}
/* hero */
.hero {{
  border: 1px solid {lg["color"]}33;
  border-radius: 14px;
  padding: 24px 28px;
  background: linear-gradient(135deg, {lg["color"]}08, transparent);
  margin-bottom: 16px;
}}
.hero-val {{ font-size: 56px; font-weight: 700; color: {lg["color"]}; line-height: 1; }}
.hero-sub {{ font-size: 10px; color: #6B7280; margin-top: 6px; }}
.trend {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  padding: 4px 14px;
  border-radius: 20px;
  font-size: 11px;
  border: 1px solid {trend_color}44;
  color: {trend_color};
  background: {trend_color}0A;
}}
/* canvas */
.chart-wrap {{
  background: #0D0F16;
  border: 1px solid #1E2130;
  border-radius: 10px;
  padding: 16px;
}}
canvas {{ display: block; width: 100% !important; }}
/* table */
.tbl-wrap {{ background: #0D0F16; border: 1px solid #1E2130; border-radius: 10px; overflow-x: auto; }}
table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
th {{
  font-size: 8px;
  color: #6B7280;
  letter-spacing: 2px;
  padding: 10px;
  text-align: left;
  border-bottom: 1px solid #1E2130;
}}
td {{ padding: 9px 10px; border-bottom: 1px solid #111318; color: #9CA3AF; }}
tr:hover td {{ background: rgba(255,255,255,0.025); }}
td.hi {{ color: #F1F5F9; font-weight: 700; }}
td.dim {{ color: #374151; }}
.badge {{
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 9px;
  font-weight: 700;
}}
.badge.green  {{ background: rgba(74,222,128,0.12); color: #4ADE80; }}
.badge.yellow {{ background: rgba(251,191,36,0.12);  color: #FBBF24; }}
.badge.red    {{ background: rgba(248,113,113,0.12); color: #F87171; }}
/* footer */
footer {{
  margin-top: 28px;
  padding-top: 16px;
  border-top: 1px solid #1E2130;
  display: flex;
  justify-content: space-between;
  font-size: 9px;
  color: #374151;
}}
@media (max-width: 640px) {{
  .g4, .g3 {{ grid-template-columns: 1fr 1fr; }}
  .hero-val {{ font-size: 38px; }}
}}
</style>
</head>
<body>

<nav>
  <div class="logo">🌿 green<span>code</span>
    <span style="font-size:9px;color:#374151;font-weight:normal;margin-left:10px">DASHBOARD</span>
  </div>
  <div class="live">● LIVE &nbsp;{stats["total_measurements"]} RUNS</div>
</nav>

<div class="wrap">

  <div class="hero">
    <div style="font-size:8px;color:{lg["color"]};letter-spacing:3px;margin-bottom:10px">◈ LATEST MEASUREMENT</div>
    <div class="hero-val">
      {latest["grams_co2"]:.2f}<span style="font-size:22px;opacity:.6">g CO₂</span>
    </div>
    <div class="hero-sub">
      commit {latest.get("commit","—")} &nbsp;·&nbsp; {latest.get("branch","—")} &nbsp;·&nbsp; {latest["timestamp"][:10]}
    </div>
    <div class="trend">{trend_arrow} Trend: {stats.get("trend","stable").upper()}</div>
  </div>

  <div class="label">◈ KEY METRICS</div>
  <div class="g4">
    <div class="card">
      <div class="val" style="color:#60A5FA">{stats["avg_grams"]:.2f}<span style="font-size:14px">g</span></div>
      <div class="sub">AVERAGE</div>
    </div>
    <div class="card">
      <div class="val" style="color:#4ADE80">{stats["min_grams"]:.2f}<span style="font-size:14px">g</span></div>
      <div class="sub">BEST RUN</div>
    </div>
    <div class="card">
      <div class="val" style="color:#F87171">{stats["max_grams"]:.2f}<span style="font-size:14px">g</span></div>
      <div class="sub">WORST RUN</div>
    </div>
    <div class="card">
      <div class="val" style="color:#FCD34D">{stats["total_grams"]:.1f}<span style="font-size:14px">g</span></div>
      <div class="sub">TOTAL CO₂</div>
    </div>
  </div>

  <div class="label">◈ GRADE DISTRIBUTION</div>
  <div class="g3">
    <div class="card" style="border-color:#4ADE8033">
      <div class="val" style="color:#4ADE80">{gc.get("green",0)}</div>
      <div class="sub">🌿 GREEN RUNS</div>
    </div>
    <div class="card" style="border-color:#FBBF2433">
      <div class="val" style="color:#FBBF24">{gc.get("yellow",0)}</div>
      <div class="sub">🌡 YELLOW RUNS</div>
    </div>
    <div class="card" style="border-color:#F8717133">
      <div class="val" style="color:#F87171">{gc.get("red",0)}</div>
      <div class="sub">🔥 RED RUNS</div>
    </div>
  </div>

  <div class="label">◈ CO₂ OVER TIME</div>
  <div class="chart-wrap">
    <canvas id="lineChart" height="130"></canvas>
  </div>

  <div class="label">◈ GRADE PER RUN</div>
  <div class="chart-wrap">
    <canvas id="barChart" height="80"></canvas>
  </div>

  <div class="label">◈ HISTORY</div>
  <div class="tbl-wrap">
    <table>
      <thead>
        <tr>
          <th>DATE</th>
          <th>COMMIT</th>
          <th>BRANCH</th>
          <th>CO₂ (g)</th>
          <th>GRADE</th>
          <th>METHOD</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>
  </div>

  <footer>
    <span>🌿 greencode &nbsp;·&nbsp; generated {now} UTC</span>
    <span>github.com/AlexAp0st0l/GreenCode</span>
  </footer>

</div>

<script>
(function () {{
  const LABELS = {js_labels};
  const VALUES = {js_values};
  const COLORS = {js_colors};

  function draw(id, type) {{
    var el = document.getElementById(id);
    if (!el) return;
    var W  = el.parentElement.clientWidth - 32;  // subtract padding
    var H  = parseInt(el.getAttribute('height')) || 130;
    el.width  = W;
    el.height = H;
    var ctx = el.getContext('2d');

    var PAD  = {{ t: 16, r: 12, b: 40, l: 44 }};
    var cW   = W - PAD.l - PAD.r;
    var cH   = H - PAD.t - PAD.b;
    var minV = Math.min.apply(null, VALUES);
    var maxV = Math.max.apply(null, VALUES);
    // give a little breathing room
    minV = Math.max(0, minV - (maxV - minV) * 0.15);
    maxV = maxV + (maxV - minV) * 0.1 || 1;
    var range = maxV - minV || 1;

    function xOf(i) {{ return PAD.l + (i / Math.max(VALUES.length - 1, 1)) * cW; }}
    function yOf(v) {{ return PAD.t + cH - ((v - minV) / range) * cH; }}

    ctx.clearRect(0, 0, W, H);

    // ── grid ──
    ctx.strokeStyle = '#0D1010';
    ctx.lineWidth   = 1;
    ctx.fillStyle   = '#374151';
    ctx.font        = '9px monospace';
    ctx.textAlign   = 'right';
    for (var t = 0; t <= 4; t++) {{
      var gy = PAD.t + (t / 4) * cH;
      ctx.beginPath();
      ctx.moveTo(PAD.l, gy);
      ctx.lineTo(W - PAD.r, gy);
      ctx.stroke();
      var gv = maxV - (t / 4) * range;
      ctx.fillText(gv.toFixed(1), PAD.l - 4, gy + 4);
    }}

    if (type === 'line') {{
      // ── reference lines ──
      [[10, '#4ADE8044'], [50, '#F8717144']].forEach(function(pair) {{
        var ref = pair[0], col = pair[1];
        if (ref >= minV && ref <= maxV) {{
          var ry = yOf(ref);
          ctx.save();
          ctx.strokeStyle = col;
          ctx.setLineDash([4, 4]);
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(PAD.l, ry);
          ctx.lineTo(W - PAD.r, ry);
          ctx.stroke();
          ctx.restore();
        }}
      }});

      // ── area ──
      var grad = ctx.createLinearGradient(0, PAD.t, 0, H - PAD.b);
      grad.addColorStop(0, 'rgba(74,222,128,0.18)');
      grad.addColorStop(1, 'rgba(74,222,128,0)');
      ctx.beginPath();
      ctx.moveTo(xOf(0), yOf(VALUES[0]));
      for (var i = 1; i < VALUES.length; i++) ctx.lineTo(xOf(i), yOf(VALUES[i]));
      ctx.lineTo(xOf(VALUES.length - 1), H - PAD.b);
      ctx.lineTo(xOf(0), H - PAD.b);
      ctx.closePath();
      ctx.fillStyle = grad;
      ctx.fill();

      // ── line ──
      ctx.beginPath();
      ctx.strokeStyle = '#4ADE80';
      ctx.lineWidth   = 2;
      ctx.setLineDash([]);
      for (var i = 0; i < VALUES.length; i++) {{
        if (i === 0) ctx.moveTo(xOf(i), yOf(VALUES[i]));
        else ctx.lineTo(xOf(i), yOf(VALUES[i]));
      }}
      ctx.stroke();

      // ── dots ──
      VALUES.forEach(function(v, i) {{
        ctx.beginPath();
        ctx.arc(xOf(i), yOf(v), 5, 0, Math.PI * 2);
        ctx.fillStyle   = COLORS[i];
        ctx.strokeStyle = '#07080C';
        ctx.lineWidth   = 1.5;
        ctx.fill();
        ctx.stroke();
      }});

    }} else {{
      // ── bars ──
      var bW  = (cW / VALUES.length) * 0.65;
      var gap = (cW / VALUES.length) * 0.35;
      VALUES.forEach(function(v, i) {{
        var bH  = ((v - minV) / range) * cH;
        var bX  = PAD.l + i * (bW + gap);
        var bY  = PAD.t + cH - bH;
        ctx.fillStyle   = COLORS[i] + '99';
        ctx.strokeStyle = COLORS[i];
        ctx.lineWidth   = 1;
        ctx.beginPath();
        if (ctx.roundRect) ctx.roundRect(bX, bY, bW, bH, [3, 3, 0, 0]);
        else ctx.rect(bX, bY, bW, bH);
        ctx.fill();
        ctx.stroke();
      }});
    }}

    // ── x-axis labels ──
    ctx.textAlign = 'center';
    ctx.fillStyle = '#374151';
    ctx.font      = '8px monospace';
    var step = Math.max(1, Math.floor(LABELS.length / 8));
    LABELS.forEach(function(l, i) {{
      if (i % step === 0) {{
        var lx = xOf(i);
        ctx.save();
        ctx.translate(lx, H - PAD.b + 12);
        ctx.rotate(-0.45);
        ctx.textAlign = 'right';
        ctx.fillText(l.slice(0, 12), 0, 0);
        ctx.restore();
      }}
    }});
  }}

  function renderAll() {{
    draw('lineChart', 'line');
    draw('barChart',  'bar');
  }}

  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', renderAll);
  }} else {{
    renderAll();
  }}
  window.addEventListener('resize', renderAll);
}})();
</script>

</body>
</html>"""


def save_html_report(path: Optional[str] = None) -> Path:
    out = Path(path) if path else REPORT_DIR / "dashboard.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(generate_html_report(), encoding="utf-8")
    return out
