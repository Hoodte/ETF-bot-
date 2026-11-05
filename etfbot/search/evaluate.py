"""Search runner, trial ledger, robustness checks and shortlist report.

Flow (rules from config.yaml `search:`, fixed before running):
  1. benchmarks + baselines run first;
  2. every generated config is backtested on data that STOPS before the holdout;
  3. each trial is scored on the discovery period and every validation fold against the matched benchmark;
  4. the shortlist (passing trials ranked by worst-period MAR) is frozen, written to disk, then
     checked for nearby settings, higher costs and deflated Sharpe;
  5. only then is the frozen shortlist run on the untouched holdout.
"""
from __future__ import annotations

import copy
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

from . import engine as E
from . import generator as G
from . import schema as S

METRICS = ["cagr", "max_dd", "sharpe", "mar"]


def metrics(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) < 20:
        return {k: np.nan for k in METRICS}
    yrs = (r.index[-1] - r.index[0]).days / 365.25
    eq = (1 + r).cumprod()
    cagr = eq.iloc[-1] ** (1 / yrs) - 1
    dd = (eq / eq.cummax() - 1).min()
    sd = r.std()
    return {"cagr": float(cagr), "max_dd": float(dd), "sharpe": float(r.mean() / sd * np.sqrt(252)) if sd > 0 else 0.0,
            "mar": float(cagr / abs(dd)) if dd < 0 else np.nan}


def periods(sc: dict) -> dict[str, tuple[str, str]]:
    out = {"disc": tuple(sc["discovery"])}
    for k, (a, b) in enumerate(sc["validation"], 1):
        out[f"val{k}"] = (a, b)
    return out


def score(res: E.Result, bench: dict[str, dict], sc: dict, pers: dict) -> dict:
    row = {"turnover": res.turnover, "trades": res.trades}
    ok = True
    worst_mar = np.inf
    for name, (a, b) in pers.items():
        m = metrics(res.returns[a:b])
        bm = bench[name]
        for k in METRICS:
            row[f"{name}_{k}"] = m[k]
        row[f"{name}_exposure"] = float(res.exposure[a:b].mean())
        row[f"{name}_rel_cagr"] = m["cagr"] - bm["cagr"]
        row[f"{name}_dd_improve"] = m["max_dd"] - bm["max_dd"]
        if sc["require_lower_drawdown"] and not m["max_dd"] > bm["max_dd"]:
            ok = False
        if not m["cagr"] >= bm["cagr"] - sc["max_cagr_giveup"]:
            ok = False
        worst_mar = min(worst_mar, m["mar"] if m["mar"] == m["mar"] else -np.inf)
    row["passes"] = ok
    row["worst_mar"] = worst_mar
    return row


def bench_metrics(p: E.Panel, cost, start, pers) -> dict:
    b = E.run_benchmark(p, cost, start)
    return {name: metrics(b.returns[a:c]) for name, (a, c) in pers.items()}


def run_search(cfg_all: dict, out_dir: str | Path, samples: int | None = None, log=print) -> Path:
    sc = cfg_all["search"]
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    raw = E.load_ohlcv()
    dv = E.data_version(raw)
    search_end = (pd.Timestamp(sc["holdout_start"]) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    panels = {u: E.build_panel(raw, u, end=search_end) for u in S.UNIVERSES}
    pers = periods(sc)
    start = sc["discovery"][0]
    cost = sc["cost_bps"]
    bench = {u: bench_metrics(panels[u], cost, start, pers) for u in S.UNIVERSES}
    brows = [{"universe": u, "period": k, **v} for u, d in bench.items() for k, v in d.items()]
    pd.DataFrame(brows).to_csv(out / "benchmarks.csv", index=False)
    rows, rets = [], {}
    t0 = time.time()
    for n, (stage, c, status, reasons, cid) in enumerate(G.generate(samples or sc["samples"], sc["seed"])):
        row = {"trial": n, "config_id": cid, "stage": stage, "status": status, "family": c.get("family"),
               "universe": c.get("universe"), "description": S.describe(c) if status != "invalid" else "",
               "reasons": "; ".join(reasons), "config": json.dumps(c, sort_keys=True), "data_version": dv,
               "schema_version": S.SCHEMA_VERSION, "cost_bps": cost, "search_end": search_end}
        if status == "valid":
            res = E.run(c, panels[c["universe"]], cost, start)
            row.update(score(res, bench[c["universe"]], sc, pers))
            r = res.returns[start:search_end]
            rets[cid] = r
        rows.append(row)
        if n % 500 == 0:
            log(f"  {n} configs attempted ({time.time() - t0:.0f}s)")
    df = pd.DataFrame(rows)
    # deflated Sharpe over the whole search (discovery + validation, daily), N = trials actually tested
    tested = df[df.status == "valid"]
    srs = {cid: r.mean() / r.std() for cid, r in rets.items() if r.std() > 0}
    var = float(np.var(list(srs.values()), ddof=1))
    n_tested = len(tested)
    emax = np.sqrt(var) * ((1 - np.euler_gamma) * norm.ppf(1 - 1 / n_tested) + np.euler_gamma * norm.ppf(1 - 1 / (n_tested * np.e)))
    def dsr(cid):
        r = rets.get(cid)
        if r is None or r.std() == 0:
            return np.nan
        sr, T = r.mean() / r.std(), len(r)
        g3, g4 = r.skew(), r.kurt() + 3
        return float(norm.cdf((sr - emax) * np.sqrt(T - 1) / np.sqrt(max(1 - g3 * sr + (g4 - 1) / 4 * sr ** 2, 1e-12))))
    df["deflated_sharpe"] = [dsr(c) if s == "valid" else np.nan for c, s in zip(df.config_id, df.status)]
    df.to_csv(out / "trials.csv", index=False)
    meta = {"data_version": dv, "n_attempted": int(len(df)), "n_tested": int(n_tested),
            "n_invalid": int((df.status == "invalid").sum()), "n_duplicate": int((df.status == "duplicate").sum()),
            "n_passing": int(tested.passes.sum()), "search_end": search_end, "rules": sc,
            "survivorship_bias": "All ETFs in the universes exist today; delisted funds are absent."}
    json.dump(meta, open(out / "meta.json", "w"), indent=1, default=str)
    log(f"search done: {n_tested} tested, {meta['n_passing']} pass, {meta['n_invalid']} invalid, {meta['n_duplicate']} duplicate")
    return out


# ------------------------------------------------------------------ shortlist
def freeze_shortlist(out: Path, sc: dict) -> pd.DataFrame:
    df = pd.read_csv(out / "trials.csv")
    ok = df[(df.status == "valid") & (df.passes == True)].sort_values("worst_mar", ascending=False)  # noqa: E712
    picks, per = [], {}
    for _, r in ok.iterrows():
        k = (r.universe, r.family)
        if per.get(k, 0) >= sc["max_per_family_universe"]:
            continue
        per[k] = per.get(k, 0) + 1
        picks.append(r)
        if len(picks) >= sc["shortlist_size"]:
            break
    sl = pd.DataFrame(picks)
    sl.to_csv(out / "shortlist_frozen.csv", index=False)
    return sl


def neighbours(cfg: dict) -> list[dict]:
    """Adjacent grid values and +/-10% off-grid values for every numeric parameter."""
    out = []
    grids = {"sma": S.SMA, "tsmom": S.MOM, "rel_mom": S.MOM, "breakout": S.BRK}
    def around(v, grid):
        vals = {int(round(v * 0.9)), int(round(v * 1.1))}
        if v in grid:
            i = grid.index(v)
            vals |= {grid[j] for j in (i - 1, i + 1) if 0 <= j < len(grid)}
        return sorted(vals - {v})
    for slot in ("signal", "second"):
        s = cfg.get(slot)
        if not s:
            continue
        for key in ("n", "fast", "slow"):
            if key not in s:
                continue
            grid = S.SMA if s["type"] == "ma_cross" else grids[s["type"]]
            for v in around(s[key], grid):
                c = copy.deepcopy(cfg); c[slot][key] = v
                if c[slot].get("fast", 0) < c[slot].get("slow", 1e9):
                    out.append(c)
    if cfg["sizing"] == "inv_vol":
        for v in around(cfg["vol_lookback"], [20, 60, 120]):
            c = copy.deepcopy(cfg); c["vol_lookback"] = v; out.append(c)
    return out


def robustness(out: Path, cfg_all: dict, log=print) -> pd.DataFrame:
    sc = cfg_all["search"]
    sl = pd.read_csv(out / "shortlist_frozen.csv")
    raw = E.load_ohlcv()
    search_end = (pd.Timestamp(sc["holdout_start"]) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    pers = periods(sc); start = sc["discovery"][0]; cost = sc["cost_bps"]
    panels = {u: E.build_panel(raw, u, end=search_end) for u in S.UNIVERSES}
    full = {u: E.build_panel(raw, u) for u in S.UNIVERSES}
    rows = []
    for _, r in sl.iterrows():
        c = json.loads(r.config); u = c["universe"]
        bench = bench_metrics(panels[u], cost, start, pers)
        # nearby settings
        nb = neighbours(c); nb_fail = 0; nb_mars = []
        for x in nb:
            s = score(E.run(x, panels[u], cost, start), bench, sc, pers)
            nb_mars.append(s["worst_mar"])
            if not s["passes"] or s["worst_mar"] < sc["neighbour_mar_floor"] * r.worst_mar:
                nb_fail += 1
        # higher costs (benchmark at the same higher cost)
        cost_ok = {}
        for m in sc["stress_cost_multipliers"]:
            bm = bench_metrics(panels[u], cost * m, start, pers)
            cost_ok[m] = bool(score(E.run(c, panels[u], cost * m, start), bm, sc, pers)["passes"])
        # holdout: frozen config, untouched period
        hs = sc["holdout_start"]
        res = E.run(c, full[u], cost, start)
        b = E.run_benchmark(full[u], cost, start)
        hm, hb = metrics(res.returns[hs:]), metrics(b.returns[hs:])
        hold_pass = (hm["max_dd"] > hb["max_dd"]) and (hm["cagr"] >= hb["cagr"] - sc["max_cagr_giveup"])
        rows.append({"config_id": r.config_id, "description": r.description, "family": r.family, "universe": u,
                     "worst_mar_search": r.worst_mar, "deflated_sharpe": r.deflated_sharpe,
                     "neighbours": len(nb), "neighbours_failing": nb_fail, "sensitive": nb_fail > 0,
                     **{f"passes_cost_x{m}": v for m, v in cost_ok.items()},
                     "holdout_cagr": hm["cagr"], "holdout_max_dd": hm["max_dd"], "holdout_sharpe": hm["sharpe"],
                     "bench_holdout_cagr": hb["cagr"], "bench_holdout_max_dd": hb["max_dd"], "holdout_pass": bool(hold_pass),
                     "turnover": r.turnover, "trades": r.trades, "config": r.config})
        log(f"  checked {r.description}")
    rb = pd.DataFrame(rows)
    rb["robust"] = (~rb.sensitive) & rb[[c for c in rb.columns if c.startswith("passes_cost")]].all(axis=1)
    rb.to_csv(out / "shortlist_checked.csv", index=False)
    return rb


def report(out: Path, cfg_all: dict) -> str:
    sc = cfg_all["search"]
    meta = json.load(open(out / "meta.json"))
    df = pd.read_csv(out / "trials.csv"); bench = pd.read_csv(out / "benchmarks.csv")
    rb = pd.read_csv(out / "shortlist_checked.csv")
    t = df[df.status == "valid"]
    pc = lambda x: f"{x:.1%}" if x == x else "n/a"  # noqa: E731
    L = ["# ETF strategy search: shortlist report", "",
         f"Data `{meta['data_version']}`. Search data ends {meta['search_end']}; holdout from {sc['holdout_start']} was untouched until the shortlist was frozen.",
         f"Attempted {meta['n_attempted']} configs: **{meta['n_tested']} tested**, {meta['n_invalid']} rejected as invalid, {meta['n_duplicate']} duplicates.",
         f"Costs {sc['cost_bps']} bps per unit traded; signals at the close, fills at the next open.",
         f"Pass rule (every period: discovery {sc['discovery'][0][:4]}-{sc['discovery'][1][:4]}, "
         + ", ".join(f"{a[:4]}-{b[:4]}" for a, b in sc["validation"])
         + f"): smaller max drawdown than the matched equal-weight benchmark, and CAGR no more than {sc['max_cagr_giveup']:.0%}/yr behind it.",
         f"**Survivorship bias:** {meta['survivorship_bias']}", "",
         "## Benchmarks (equal weight, every eligible ETF, monthly)", "", "| Universe | Period | CAGR | Max DD | Sharpe |", "|---|---|---|---|---|"]
    for _, b in bench.iterrows():
        L.append(f"| {b.universe} | {b.period} | {pc(b.cagr)} | {pc(b.max_dd)} | {b.sharpe:.2f} |")
    L += ["", "## Which strategy families held up", "",
          "| Universe | Family | Tested | Pass all periods | Pass rate | Best worst-period MAR |", "|---|---|---|---|---|---|"]
    for (u, f), g in t.groupby(["universe", "family"]):
        L.append(f"| {u} | {f} | {len(g)} | {int(g.passes.sum())} | {g.passes.mean():.0%} | {g.worst_mar.max():.2f} |")
    L += ["", "## Frozen shortlist: robustness and holdout", "",
          "Robust = every nearby setting also passes (and keeps 50% or more of the MAR), and it still passes at 2x and 3x costs.", "",
          "| Strategy | Search worst MAR | DSR | Nearby failing | 2x cost | 3x cost | Robust | Holdout CAGR (bench) | Holdout max DD (bench) | Holdout pass |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in rb.iterrows():
        L.append(f"| `{r.description}` | {r.worst_mar_search:.2f} | {r.deflated_sharpe:.2f} | {r.neighbours_failing}/{r.neighbours} | "
                 f"{'yes' if r.passes_cost_x2 else 'no'} | {'yes' if r.passes_cost_x3 else 'no'} | {'**yes**' if r.robust else 'no'} | "
                 f"{pc(r.holdout_cagr)} ({pc(r.bench_holdout_cagr)}) | {pc(r.holdout_max_dd)} ({pc(r.bench_holdout_max_dd)}) | {'yes' if r.holdout_pass else 'no'} |")
    good = rb[rb.robust & rb.holdout_pass]
    L += ["", "## Verdict", "",
          f"{len(good)} of {len(rb)} shortlisted strategies are robust AND passed the untouched holdout." if len(rb) else "Nothing passed the search rule.",
          "Deflated Sharpe (DSR) corrects for the number of trials tested; below 0.95 means the Sharpe alone could be luck.",
          "The pass rule is about **lower drawdown at a limited return cost**, not about beating the benchmark's return.", ""]
    txt = "\n".join(L)
    (out / "SHORTLIST_REPORT.md").write_text(txt)
    return txt
