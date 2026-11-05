"""Intraday search runner: ledger, pass rule, frozen shortlist, robustness, holdout and funded-account sim."""
from __future__ import annotations

import copy
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

from . import engine as E
from . import schema as S


def periods(sc, first_day) -> dict:
    out = {"disc": (str(first_day.date()), sc["discovery_end"])}
    for k, (a, b) in enumerate(sc["validation"], 1):
        out[f"val{k}"] = (a, b)
    return out


def daily_pnl(tr: pd.DataFrame, days: pd.DatetimeIndex) -> pd.Series:
    s = tr.groupby(tr.exit_time.dt.floor("D")).pnl_atr.sum() if len(tr) else pd.Series(dtype=float)
    return s.reindex(days, fill_value=0.0)


def stats(tr: pd.DataFrame, days: pd.DatetimeIndex) -> dict:
    dp = daily_pnl(tr, days)
    yrs = max((days[-1] - days[0]).days / 365.25, 1e-9)
    ann = len(days) / yrs
    sd = dp.std()
    wins, losses = tr.pnl_atr[tr.pnl_atr > 0].sum(), -tr.pnl_atr[tr.pnl_atr < 0].sum()
    eq = dp.cumsum()
    return {"sharpe": float(dp.mean() / sd * np.sqrt(ann)) if sd > 0 else 0.0,
            "pf": float(wins / losses) if losses > 0 else (np.inf if wins > 0 else 0.0),
            "trades": int(len(tr)), "per_week": float(len(tr) / (yrs * 52.18)),
            "win_rate": float((tr.pnl_atr > 0).mean()) if len(tr) else 0.0,
            "avg_atr": float(tr.pnl_atr.mean()) if len(tr) else 0.0,
            "max_dd_atr": float((eq - eq.cummax()).min()) if len(eq) else 0.0}


def evaluate_trades(tr, data: E.Data, pers, sc) -> dict:
    row, ok, worst = {}, True, np.inf
    all_days = data.days
    for name, (a, b) in pers.items():
        days = all_days[(all_days >= pd.Timestamp(a, tz="UTC")) & (all_days <= pd.Timestamp(b, tz="UTC"))]
        sub = tr[(tr.exit_time >= days[0]) & (tr.exit_time < days[-1] + pd.Timedelta(days=1))] if len(days) else tr.iloc[:0]
        st = stats(sub, days)
        for k, v in st.items():
            row[f"{name}_{k}"] = v
        if st["sharpe"] < sc["min_sharpe"] or st["pf"] < sc["min_profit_factor"]:
            ok = False
        worst = min(worst, st["sharpe"])
    days = all_days[all_days <= pd.Timestamp(list(pers.values())[-1][1], tz="UTC")]
    tot = stats(tr[tr.exit_time < days[-1] + pd.Timedelta(days=1)], days)
    row["search_per_week"] = tot["per_week"]; row["search_sharpe"] = tot["sharpe"]; row["search_pf"] = tot["pf"]
    if tot["per_week"] < sc["min_trades_per_week"]:
        ok = False
    row["passes"], row["worst_sharpe"] = ok, worst
    return row


def load(sc, end=None) -> dict[str, E.Data]:
    return {k: E.Data(v[0], v[1], v[3], end) for k, v in sc["datasets"].items()}


def search_end(sc):
    return (pd.Timestamp(sc["holdout_start"]) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")


def run_search(cfg_all, out, samples=None, log=print):
    sc = cfg_all["daytrade"]; out = Path(out); out.mkdir(parents=True, exist_ok=True)
    end = search_end(sc)
    data = load(sc, end)
    rows, dps = [], {}
    t0 = time.time()
    for n, (stage, c, status, reasons, cid) in enumerate(S.generate(sc["datasets"], samples or sc["samples"], sc["seed"])):
        row = {"trial": n, "config_id": cid, "stage": stage, "status": status, "dataset": c["dataset"],
               "family": c["signal"]["family"], "description": S.describe(c) if status != "invalid" else "",
               "reasons": "; ".join(reasons), "config": json.dumps(c, sort_keys=True),
               "cost_bps": sc["datasets"][c["dataset"]][2], "search_end": end}
        if status == "valid":
            d = data[c["dataset"]]
            tr = E.run(c, d, row["cost_bps"])
            pers = periods(sc, d.idx[0].floor("D"))
            row.update(evaluate_trades(tr, d, pers, sc))
            all_days = d.days
            dps[cid] = daily_pnl(tr, all_days)
        rows.append(row)
        if n % 500 == 0:
            log(f"  {n} configs ({time.time() - t0:.0f}s)")
    df = pd.DataFrame(rows)
    tested = df[df.status == "valid"]
    srs = [s.mean() / s.std() for s in dps.values() if s.std() > 0]
    var, N = float(np.var(srs, ddof=1)), len(tested)
    emax = np.sqrt(var) * ((1 - np.euler_gamma) * norm.ppf(1 - 1 / N) + np.euler_gamma * norm.ppf(1 - 1 / (N * np.e)))
    def dsr(cid):
        r = dps.get(cid)
        if r is None or r.std() == 0:
            return np.nan
        sr, T, g3, g4 = r.mean() / r.std(), len(r), r.skew(), r.kurt() + 3
        return float(norm.cdf((sr - emax) * np.sqrt(T - 1) / np.sqrt(max(1 - g3 * sr + (g4 - 1) / 4 * sr ** 2, 1e-12))))
    df["deflated_sharpe"] = [dsr(c) if s == "valid" else np.nan for c, s in zip(df.config_id, df.status)]
    df.to_csv(out / "trials.csv", index=False)
    meta = {"n_attempted": len(df), "n_tested": N, "n_invalid": int((df.status == "invalid").sum()),
            "n_duplicate": int((df.status == "duplicate").sum()), "n_passing": int(tested.passes.sum()),
            "search_end": end, "rules": sc}
    json.dump(meta, open(out / "meta.json", "w"), indent=1, default=str)
    log(f"search done: {N} tested, {meta['n_passing']} pass")
    return out


def freeze_shortlist(out, sc):
    df = pd.read_csv(out / "trials.csv")
    ok = df[(df.status == "valid") & (df.passes == True)].sort_values("worst_sharpe", ascending=False)  # noqa: E712
    picks, per = [], {}
    for _, r in ok.iterrows():
        k = (r.dataset, r.family)
        if per.get(k, 0) >= sc["max_per_dataset_family"]:
            continue
        per[k] = per.get(k, 0) + 1; picks.append(r)
        if len(picks) >= sc["shortlist_size"]:
            break
    sl = pd.DataFrame(picks); sl.to_csv(out / "shortlist_frozen.csv", index=False)
    return sl


def neighbours(c):
    out = []
    s = c["signal"]
    for k, grid in S.PARAMS[s["family"]].items():
        v = s[k]
        if isinstance(v, str):
            continue
        cands = set()
        if v in grid:
            i = grid.index(v); cands |= {grid[j] for j in (i - 1, i + 1) if 0 <= j < len(grid)}
        cands |= {type(v)(round(v * 0.85, 2)), type(v)(round(v * 1.15, 2))}
        for x in sorted(cands - {v}):
            if x > 0:
                n = copy.deepcopy(c); n["signal"][k] = x; out.append(n)
    hold_grid = S.ALLOWED["hold"]
    i = hold_grid.index(c["hold"])
    for j in (i - 1, i + 1):
        if 0 <= j < len(hold_grid):
            n = copy.deepcopy(c); n["hold"] = hold_grid[j]; out.append(n)
    if c["exit"] == "bracket":
        for ds, dt in ((0.25, 0), (-0.25, 0), (0, 0.5), (0, -0.5)):
            n = copy.deepcopy(c); n["bracket"] = [c["bracket"][0] + ds, c["bracket"][1] + dt]
            if min(n["bracket"]) > 0:
                out.append(n)
    return out


def funded(dp_atr: pd.Series, risk: float, paths=10000, days=252, block=20, seed=5, split=0.8):
    """dp_atr: daily P&L in ATR units. risk: account fraction per 1 ATR unit. Closed-trade P&L only."""
    base = dp_atr.to_numpy() * risk
    rng = np.random.default_rng(seed); nbk = -(-days // block)
    ii = (rng.integers(0, len(base) - block, (paths, nbk))[:, :, None] + np.arange(block)).reshape(paths, -1)[:, :days]
    R = base[ii]; eq = 1 + np.cumsum(R, axis=1)
    lost = ((eq <= 0.9) | (R <= -0.05)).any(1)
    prof = np.where(~lost, np.maximum(eq[:, -1] - 1, 0) * 100000 * split, 0)
    return float((~lost).mean()), float(np.median(prof) / 12), float(prof.mean() / 12)


def robustness(out, cfg_all, log=print):
    sc = cfg_all["daytrade"]; out = Path(out)
    sl = pd.read_csv(out / "shortlist_frozen.csv")
    data_s = load(sc, search_end(sc)); data_f = load(sc)
    rows = []
    for _, r in sl.iterrows():
        c = json.loads(r.config); d = data_s[c["dataset"]]; cost = sc["datasets"][c["dataset"]][2]
        pers = periods(sc, d.idx[0].floor("D"))
        nb, fail = neighbours(c), 0
        for x in nb:
            ev = evaluate_trades(E.run(x, d, cost), d, pers, sc)
            if not ev["passes"]:
                fail += 1
        cost_ok = {m: bool(evaluate_trades(E.run(c, d, cost * m), d, pers, sc)["passes"]) for m in sc["stress_cost_multipliers"]}
        f = data_f[c["dataset"]]
        tr = E.run(c, f, cost)
        all_days = f.days
        hdays = all_days[all_days >= pd.Timestamp(sc["holdout_start"], tz="UTC")]
        h = stats(tr[tr.exit_time >= hdays[0]], hdays)
        h2 = stats(E.run(c, f, cost * 2).pipe(lambda t: t[t.exit_time >= hdays[0]]), hdays)
        dp = daily_pnl(tr, all_days)
        best = (0, 0, 0, 0)
        for risk in (0.0005, 0.001, 0.0015, 0.002, 0.003, 0.004, 0.005):
            k, med, avg = funded(dp, risk)
            if k >= 0.85 and avg > best[3]:
                best = (risk, k, med, avg)
        rows.append({"config_id": r.config_id, "description": r.description, "dataset": c["dataset"], "family": r.family,
                     "worst_sharpe_search": r.worst_sharpe, "search_per_week": r.search_per_week, "deflated_sharpe": r.deflated_sharpe,
                     "neighbours": len(nb), "neighbours_failing": fail,
                     **{f"passes_cost_x{m}": v for m, v in cost_ok.items()},
                     "holdout_sharpe": h["sharpe"], "holdout_pf": h["pf"], "holdout_trades": h["trades"],
                     "holdout_per_week": h["per_week"], "holdout_win_rate": h["win_rate"], "holdout_sharpe_2x_cost": h2["sharpe"],
                     "holdout_pass": bool(h["sharpe"] > 0 and h["pf"] > 1),
                     "prop_risk_per_atr": best[0], "prop_keep": best[1], "prop_typical_month": best[2], "prop_avg_month": best[3],
                     "config": r.config})
        log(f"  checked {r.description}")
    rb = pd.DataFrame(rows)
    if len(rb):
        rb["robust"] = (rb.neighbours_failing <= rb.neighbours * 0.25) & rb.passes_cost_x2
    rb.to_csv(out / "shortlist_checked.csv", index=False)
    return rb


def report(out, cfg_all):
    sc = cfg_all["daytrade"]; out = Path(out)
    meta = json.load(open(out / "meta.json")); df = pd.read_csv(out / "trials.csv")
    rbp = out / "shortlist_checked.csv"
    rb = pd.read_csv(rbp) if rbp.exists() and rbp.stat().st_size > 2 else pd.DataFrame()
    t = df[df.status == "valid"]
    L = ["# Intraday strategy search: report", "",
         f"Attempted {meta['n_attempted']} configs: **{meta['n_tested']} tested**, {meta['n_invalid']} invalid, {meta['n_duplicate']} duplicates. Search data ends {meta['search_end']}; the holdout from {sc['holdout_start']} was untouched until the shortlist was frozen.",
         f"Pass rule: Sharpe of at least {sc['min_sharpe']} and profit factor of at least {sc['min_profit_factor']} net of costs, in discovery (to {sc['discovery_end'][:4]}) and in both validation folds (2021-22, 2023-24), with at least {sc['min_trades_per_week']} trades a week.",
         "Costs per side: " + ", ".join(f"{k} {v[2]} bps" for k, v in sc["datasets"].items()) + ". Entries at the next bar's open; stops/targets from the signal bar; stop assumed first if both are hit in one bar.", "",
         "## Pass rate by dataset and family", "", "| Dataset | Family | Tested | Pass | Best worst-period Sharpe | Median search Sharpe |", "|---|---|---|---|---|---|"]
    for (dname, f), g in t.groupby(["dataset", "family"]):
        L.append(f"| {dname} | {f} | {len(g)} | {int(g.passes.sum())} | {g.worst_sharpe.max():.2f} | {g.search_sharpe.median():.2f} |")
    if len(rb):
        L += ["", "## Frozen shortlist: robustness, holdout and funded account", "",
              "Robust = 75% or more of nearby settings also pass, and it passes at 2x costs. Holdout pass = Sharpe above 0 and profit factor above 1 on 2025-26.", "",
              "| Strategy | Search worst Sharpe | Trades/wk | DSR | Nearby failing | 2x cost | Robust | Holdout Sharpe | Holdout PF | Holdout Sharpe at 2x cost | $100k: keep / typical / avg month |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
        for _, r in rb.iterrows():
            prop = f"{r.prop_keep:.0%} / ${r.prop_typical_month:,.0f} / ${r.prop_avg_month:,.0f}" if r.prop_risk_per_atr else "none safe"
            L.append(f"| `{r.description}` | {r.worst_sharpe_search:.2f} | {r.search_per_week:.1f} | {r.deflated_sharpe:.2f} | {r.neighbours_failing}/{r.neighbours} | "
                     f"{'yes' if r.passes_cost_x2 else 'no'} | {'**yes**' if r.robust else 'no'} | {r.holdout_sharpe:.2f} | {r.holdout_pf:.2f} | {r.holdout_sharpe_2x_cost:.2f} | {prop} |")
        good = rb[rb.robust & rb.holdout_pass & (rb.deflated_sharpe >= 0.95)]
        L += ["", "## Verdict", "", f"{len(good)} of {len(rb)} are robust, passed the holdout AND have a deflated Sharpe of 0.95 or more."]
    else:
        L += ["", "## Verdict", "", "No configuration passed the pre-registered rule in every period."]
    L += ["", "Funded sim: closed-trade daily P&L, -10% max loss, -5% daily loss, 80% split, 10,000 bootstrapped years; the size shown is the largest that keeps the account in 85% or more of years. Intraday open losses are not modelled, so the real daily-loss risk is higher.", ""]
    txt = "\n".join(L); (out / "REPORT.md").write_text(txt)
    return txt
