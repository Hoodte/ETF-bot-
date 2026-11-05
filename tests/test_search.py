import copy

import numpy as np
import pandas as pd

from etfbot.search import engine as E, generator as G, schema as S


def _raw(seed=0, n=900):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2010-01-01", periods=n)
    cols = sorted(S.ASSET_CLASS)
    c = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, (n, len(cols))), axis=0)), index=idx, columns=cols)
    o = c.shift(1) * (1 + rng.normal(0, 0.002, c.shape)); o.iloc[0] = c.iloc[0]
    v = pd.DataFrame(1e6, index=idx, columns=cols)
    return pd.concat({"Open": o, "Close": c, "Volume": v}, axis=1)


def _cfg(**kw):
    c = G.baseline("multi_asset", "rel_mom"); c.update(kw); return c


def test_no_lookahead_future_shock_does_not_change_past():
    raw = _raw()
    cut = raw.index[600]
    shocked = raw.copy()
    for f in ("Open", "Close"):
        shocked.loc[raw.index > cut, f] *= 3.0
    for c in (_cfg(), _cfg(family="sma", signal={"type": "sma", "n": 50}, selection="all", rebalance="weekly"),
              _cfg(family="breakout", signal={"type": "breakout", "n": 20}, selection="all", entry_exit="confirm2")):
        a = E.run(c, E.build_panel(raw, "multi_asset"), 5).returns
        b = E.run(c, E.build_panel(shocked, "multi_asset"), 5).returns
        # returns through day cut-1 (open cut-1 -> open cut) cannot know anything after cut
        pd.testing.assert_series_equal(a[: raw.index[599]], b[: raw.index[599]])


def test_fill_happens_at_next_open():
    raw = _raw()
    p = E.build_panel(raw, "gold")
    c = G.baseline("gold", "sma"); c["signal"] = {"type": "sma", "n": 50}
    r = E.run(c, p, 0)
    reb = E.rebalance_mask(p.dates, "monthly")
    first = int(np.argmax(reb & (np.arange(len(reb)) >= 60)))
    # on the signal day itself we still hold the pre-trade position (cash at start)
    assert r.returns.iloc[first] == 0.0


def test_validation_rules():
    bad = _cfg(family="ma_cross", signal={"type": "ma_cross", "fast": 200, "slow": 50}, selection="all")
    assert any("fast" in e or "params" in e for e in S.validate(bad))
    assert S.validate(_cfg(selection="all"))                       # rel_mom must rank
    assert S.validate(G.baseline("gold", "sma") | {"selection": "top1"})
    assert S.validate(_cfg(entry_exit="buffer", selection="top_per_class"))
    assert not S.validate(_cfg(entry_exit="buffer", selection="top3"))
    assert S.buffer_exit_rank(3) > 3


def test_dedup_equivalent_configs():
    a = G.baseline("gold", "sma")
    b = copy.deepcopy(a); b.update(sizing="inv_vol", vol_lookback=60)   # one ETF: same weight either way
    assert S.config_id(a) == S.config_id(b)
    c = copy.deepcopy(a); c["signal"] = {"type": "sma", "n": 100}
    assert S.config_id(a) != S.config_id(c)


def test_generator_reproducible_and_unique():
    x = [(s, st, cid) for s, _, st, _, cid in G.generate(200, 7)]
    y = [(s, st, cid) for s, _, st, _, cid in G.generate(200, 7)]
    assert x == y
    ids = [cid for _, st, cid in x if st == "valid"]
    assert len(ids) == len(set(ids))


def test_weights_respect_limits():
    raw = _raw()
    p = E.build_panel(raw, "multi_asset")
    c = _cfg(selection="top3", sizing="inv_vol", vol_lookback=20, max_weight=0.25, max_equity=0.6, min_cash=0.1, defensive="shy")
    for i in range(300, 800, 50):
        w, shy, _ = E._targets(c, p, i, np.zeros(8, bool), np.zeros(8, bool), S.lookbacks(c))
        assert w.max() <= 0.25 + 1e-12 and w.sum() + shy <= 0.9 + 1e-12
