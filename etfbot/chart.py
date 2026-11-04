"""Self-contained interactive HTML chart: strategy equity curves on one chart.

Palette: validated categorical slots (light + dark) from the dataviz reference
palette. The blend always takes slot 1; components take slots 2-4 in the order
given; buy-and-hold is a dashed neutral reference line. Two light-mode slots sit
below 3:1 contrast, so every line is direct-labelled and a table view is included.
"""
from __future__ import annotations

import html
import json

import pandas as pd

LIGHT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
DARK = ["#3987e5", "#d95926", "#199e70", "#c98500"]
NAMES = {"trend": "Trend 200d", "faber": "Faber 10m", "tsmom": "12m momentum", "sma_cross": "50/200 cross",
         "turn_of_month": "Turn of month", "rsi2": "RSI(2) dips", "trend_voltarget": "Trend + vol target", "pre_holiday": "Pre-holiday",
         "options_expiry_week": "Option-expiry week", "calendar_composite": "Calendar composite",
         "blend": "Blend", "buy_hold": "Buy & hold"}


def write_html(result: dict, path: str) -> str:
    curves: dict[str, pd.Series] = result["curves"]
    frame = pd.concat(curves, axis=1).dropna()
    weekly = frame.groupby(frame.index.to_period("W-FRI")).tail(1)
    order = ["blend"] + result["components"] + ["buy_hold"]
    series = []
    for i, key in enumerate(order):
        if key == "blend":
            slot = 0
        elif key == "buy_hold":
            slot = None
        else:
            slot = 1 + result["components"].index(key)
        series.append({"key": key, "name": NAMES.get(key, key), "slot": slot,
                       "values": [round(float(v), 2) for v in weekly[key]]})
    payload = {"dates": [d.strftime("%Y-%m-%d") for d in weekly.index], "series": series,
               "oos": result["oos_start"], "start": result["start_equity_gbp"]}

    rows = []
    for r in sorted(result["table"], key=lambda r: order.index(r["series"])):
        def pct(x):
            return "-" if x is None or x != x else f"{x:.1%}"
        rows.append(f"<tr><td>{html.escape(NAMES.get(r['series'], r['series']))}</td>"
                    f"<td>£{r['end_value_gbp']:,.0f}</td><td>{pct(r['cagr'])}</td><td>{pct(r['max_drawdown'])}</td>"
                    f"<td>{pct(r['oos_cagr'])}</td><td>{(r['oos_sharpe'] or 0):.2f}</td>"
                    f"<td>{pct(r['oos_max_drawdown'])}</td></tr>")
    verdict = result["blend_skeptic_verdict"]
    failed = [k for k, v in result["blend_checks"].items() if not v]
    title = f"{html.escape(result['ucits'])}: {len(result['components'])} strategies and their blend vs buy & hold"
    sub = (f"Growth of £{result['start_equity_gbp']:,.0f}, log scale, after costs. "
           f"Components picked by {html.escape(result['picked_by'])}. Blend Skeptic verdict: {verdict}"
           + (f" (failed: {', '.join(failed)})" if failed else "") + ".")
    if result.get("synthetic"):
        sub = "SYNTHETIC PRACTICE DATA, not real markets. " + sub

    css_light = "".join(f"--s{i}:{c};" for i, c in enumerate(LIGHT))
    css_dark = "".join(f"--s{i}:{c};" for i, c in enumerate(DARK))
    return_path = path
    doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
.viz-root{{color-scheme:light;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--grid:#e6e5e0;--ref:#8a8985;{css_light}
 font:14px/1.4 system-ui,-apple-system,"Segoe UI",sans-serif;background:var(--surface);color:var(--ink);margin:0;padding:20px;max-width:1000px}}
@media (prefers-color-scheme:dark){{.viz-root{{color-scheme:dark;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--grid:#33332f;--ref:#8f8e88;{css_dark}}}}}
body{{margin:0;background:#fcfcfb}} @media (prefers-color-scheme:dark){{body{{background:#1a1a19}}}} h1{{font-size:17px;margin:0 0 4px}} .sub{{color:var(--ink2);margin:0 0 12px}}
.legend{{display:flex;flex-wrap:wrap;gap:14px;margin:0 0 6px;color:var(--ink2)}} .legend span{{display:inline-flex;align-items:center;gap:6px}}
.sw{{width:18px;height:0;border-top:2px solid}} svg{{width:100%;height:auto;display:block;overflow:visible}}
.tip{{position:absolute;pointer-events:none;background:var(--surface);border:1px solid var(--grid);border-radius:6px;padding:8px 10px;
 box-shadow:0 2px 8px rgba(0,0,0,.12);font-size:13px;display:none;min-width:170px}} .tip b{{display:block;margin-bottom:4px}}
.tip div{{display:flex;justify-content:space-between;gap:12px}} table{{border-collapse:collapse;margin-top:16px;width:100%;font-size:13px}}
th,td{{text-align:right;padding:6px 8px;border-bottom:1px solid var(--grid)}} th:first-child,td:first-child{{text-align:left}} th{{color:var(--ink2);font-weight:500}}
.note{{color:var(--ink2);font-size:12px;margin-top:10px}}
</style></head>
<body><div class="viz-root" id="root" style="position:relative">
<h1>{title}</h1><p class="sub">{sub}</p>
<div class="legend" id="legend"></div>
<svg id="chart" viewBox="0 0 960 460" role="img" aria-label="{title}"></svg>
<div class="tip" id="tip"></div>
<table><thead><tr><th>Series</th><th>End value</th><th>CAGR</th><th>Max drawdown</th><th>OOS CAGR</th><th>OOS Sharpe</th><th>OOS max DD</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<p class="note">OOS = out-of-sample, from {payload['oos']}: the part of history used only for judging, never for choosing. Past results are not a forecast.</p>
</div>
<script>
const D = {json.dumps(payload)};
const svg = document.getElementById('chart'), tip = document.getElementById('tip'), root = document.getElementById('root');
const W = 960, H = 460, M = {{l: 64, r: 130, t: 12, b: 34}};
const NS = 'http://www.w3.org/2000/svg';
const css = v => getComputedStyle(root).getPropertyValue(v).trim();
const col = s => s.slot === null ? 'var(--ref)' : `var(--s${{s.slot}})`;
const t = D.dates.map(d => Date.parse(d));
const all = D.series.flatMap(s => s.values);
const lo = Math.log(Math.min(...all) * 0.95), hi = Math.log(Math.max(...all) * 1.05);
const X = ms => M.l + (ms - t[0]) / (t[t.length - 1] - t[0]) * (W - M.l - M.r);
const Y = v => M.t + (hi - Math.log(v)) / (hi - lo) * (H - M.t - M.b);
const el = (n, a, p = svg) => {{ const e = document.createElementNS(NS, n); for (const k in a) e.setAttribute(k, a[k]); p.appendChild(e); return e; }};
const gbp = v => '£' + Math.round(v).toLocaleString('en-GB');
// y ticks: 1-2-5 steps
const ticks = []; for (let e = Math.floor(Math.log10(Math.exp(lo))); e <= Math.ceil(Math.log10(Math.exp(hi))); e++)
  for (const m of [1, 2, 5]) {{ const v = m * 10 ** e; if (Math.log(v) >= lo && Math.log(v) <= hi) ticks.push(v); }}
for (const v of ticks) {{
  el('line', {{x1: M.l, x2: W - M.r, y1: Y(v), y2: Y(v), stroke: 'var(--grid)', 'stroke-width': 1}});
  el('text', {{x: M.l - 8, y: Y(v) + 4, 'text-anchor': 'end', fill: 'var(--ink2)', 'font-size': 12}}).textContent = gbp(v);
}}
const y0 = new Date(t[0]).getFullYear(), y1 = new Date(t[t.length - 1]).getFullYear();
const step = Math.max(1, Math.ceil((y1 - y0) / 10));
for (let y = y0 + 1; y <= y1; y += step) {{
  const x = X(Date.UTC(y, 0, 1));
  el('text', {{x, y: H - 10, 'text-anchor': 'middle', fill: 'var(--ink2)', 'font-size': 12}}).textContent = y;
}}
el('line', {{x1: M.l, x2: W - M.r, y1: H - M.b, y2: H - M.b, stroke: 'var(--ref)', 'stroke-width': 1}});
const xo = X(Date.parse(D.oos));
el('line', {{x1: xo, x2: xo, y1: M.t, y2: H - M.b, stroke: 'var(--ref)', 'stroke-width': 1, 'stroke-dasharray': '4 4'}});
el('text', {{x: xo + 6, y: M.t + 12, fill: 'var(--ink2)', 'font-size': 12}}).textContent = 'Out-of-sample →';
// lines: draw reference and components first, blend last (on top)
const drawOrder = [...D.series].sort((a, b) => (a.key === 'blend') - (b.key === 'blend'));
for (const s of drawOrder) {{
  const d = s.values.map((v, i) => (i ? 'L' : 'M') + X(t[i]).toFixed(1) + ' ' + Y(v).toFixed(1)).join('');
  el('path', {{d, fill: 'none', stroke: col(s), 'stroke-width': s.key === 'blend' ? 2.5 : 2,
    'stroke-dasharray': s.slot === null ? '6 4' : 'none', 'stroke-linejoin': 'round', 'stroke-linecap': 'round'}});
}}
// direct labels at the right end, nudged apart
const labs = D.series.map(s => ({{s, y: Y(s.values[s.values.length - 1])}})).sort((a, b) => a.y - b.y);
for (let i = 1; i < labs.length; i++) if (labs[i].y - labs[i - 1].y < 15) labs[i].y = labs[i - 1].y + 15;
for (const l of labs) {{
  el('text', {{x: W - M.r + 8, y: l.y + 4, fill: 'var(--ink)', 'font-size': 12, 'font-weight': l.s.key === 'blend' ? 600 : 400}})
    .textContent = l.s.name;
}}
// legend
const lg = document.getElementById('legend');
for (const s of D.series) {{
  const sp = document.createElement('span');
  sp.innerHTML = `<i class="sw" style="border-top:2px ${{s.slot === null ? 'dashed' : 'solid'}} ${{col(s)}}"></i>${{s.name}}`;
  lg.appendChild(sp);
}}
// hover: crosshair + dots + tooltip
const cross = el('line', {{y1: M.t, y2: H - M.b, stroke: 'var(--ink2)', 'stroke-width': 1, visibility: 'hidden'}});
const dots = D.series.map(s => el('circle', {{r: 4, fill: col(s), stroke: 'var(--surface)', 'stroke-width': 2, visibility: 'hidden'}}));
const hit = el('rect', {{x: M.l, y: M.t, width: W - M.l - M.r, height: H - M.t - M.b, fill: 'transparent'}});
function show(evt) {{
  const pt = svg.createSVGPoint(); pt.x = evt.clientX; pt.y = evt.clientY;
  const p = pt.matrixTransform(svg.getScreenCTM().inverse());
  const ms = t[0] + (p.x - M.l) / (W - M.l - M.r) * (t[t.length - 1] - t[0]);
  let i = 0, best = Infinity; t.forEach((v, j) => {{ const d = Math.abs(v - ms); if (d < best) {{ best = d; i = j; }} }});
  const x = X(t[i]);
  cross.setAttribute('x1', x); cross.setAttribute('x2', x); cross.setAttribute('visibility', 'visible');
  D.series.forEach((s, k) => {{ dots[k].setAttribute('cx', x); dots[k].setAttribute('cy', Y(s.values[i])); dots[k].setAttribute('visibility', 'visible'); }});
  tip.innerHTML = `<b>${{new Date(t[i]).toLocaleDateString('en-GB', {{day: 'numeric', month: 'short', year: 'numeric'}})}}</b>` +
    [...D.series].sort((a, b) => b.values[i] - a.values[i]).map(s => `<div><span>${{s.name}}</span><span>${{gbp(s.values[i])}}</span></div>`).join('');
  tip.style.display = 'block';
  const r = root.getBoundingClientRect(), sx = svg.getBoundingClientRect();
  const left = evt.clientX - r.left + 14, maxLeft = r.width - tip.offsetWidth - 8;
  tip.style.left = Math.min(left, maxLeft) + 'px'; tip.style.top = (sx.top - r.top + 20) + 'px';
}}
hit.addEventListener('mousemove', show); hit.addEventListener('touchstart', e => show(e.touches[0]), {{passive: true}});
hit.addEventListener('touchmove', e => show(e.touches[0]), {{passive: true}});
hit.addEventListener('mouseleave', () => {{ tip.style.display = 'none'; cross.setAttribute('visibility', 'hidden'); dots.forEach(d => d.setAttribute('visibility', 'hidden')); }});
</script></body></html>"""
    with open(return_path, "w", encoding="utf-8") as f:
        f.write(doc)
    return return_path
