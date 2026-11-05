import numpy as np
import pandas as pd

from etfbot.daytrade import engine as E, schema as S

DS = {"T_1h": ["x", 60, 2.0, 24], "T_5m": ["y", 5, 2.0, 24]}


def _data(tmp_path, n=3000, seed=1, shock_after=None):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=n, freq="h", tz="UTC")
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.004, n)))
    o = np.r_[c[0], c[:-1]] * (1 + rng.normal(0, 0.0005, n))
    h = np.maximum(o, c) * (1 + abs(rng.normal(0, 0.002, n))); l = np.minimum(o, c) * (1 - abs(rng.normal(0, 0.002, n)))
    df = pd.DataFrame({"Open": o, "High": h, "Low": l, "Close": c}, index=idx)
    if shock_after is not None:
        df.iloc[shock_after:] *= 2.5
    p = tmp_path / f"d{seed}_{shock_after}.pkl"; df.to_pickle(p)
    return E.Data(str(p), 60, 24)


def test_no_lookahead(tmp_path):
    a, b = _data(tmp_path), _data(tmp_path, shock_after=2000)
    for f in S.FAMILIES:
        c = S.baseline("T_1h", f)
        ta, tb = E.run(c, a, 2.0), E.run(c, b, 2.0)
        cut = a.idx[1999]
        ka, kb = ta[ta.exit_time < cut], tb[tb.exit_time < cut]
        pd.testing.assert_frame_equal(ka.reset_index(drop=True), kb.reset_index(drop=True))


def test_entry_next_open_and_stop_first():
    o = np.array([100, 100, 100, 100.0]); c = np.array([100, 100, 100, 100.0])
    h = np.array([100, 103, 100, 100.0]); l = np.array([100, 97, 100, 100.0])
    atr = np.ones(4); sig = np.array([1, 0, 0, 0], np.int8); last = np.zeros(4, bool)
    e, x, d, p = E.simulate(o, h, l, c, atr, sig, last, True, 1.0, 2.0, 10, False, 0.0)
    assert e[0] == 1 and x[0] == 1 and p[0] == -1.0          # both levels touched in bar 1 -> stop first


def test_gap_through_stop_skips_trade():
    o = np.array([100, 98, 98, 98.0]); c = np.array([100, 98, 98, 98.0]); h = o + 0.1; l = o - 0.1
    e, *_ = E.simulate(o, h, l, c, np.ones(4), np.array([1, 0, 0, 0], np.int8), np.zeros(4, bool), True, 1.0, 2.0, 10, False, 0.0)
    assert len(e) == 0


def test_validation_and_dedup():
    c = S.baseline("T_5m", "orb"); c["signal"]["minutes"] = 15
    assert not S.validate(c, DS)
    bad = S.baseline("T_1h", "orb"); bad["signal"]["minutes"] = 30
    assert S.validate(bad, DS)
    t1 = S.baseline("T_1h", "rsi_revert"); t2 = dict(t1, bracket=[1.0, 2.0])   # time exit ignores bracket
    assert S.config_id(S.normalise(t1)) == S.config_id(S.normalise(t2))
    x = [r[4] for r in S.generate(DS, 50, 3)]; y = [r[4] for r in S.generate(DS, 50, 3)]
    assert x == y
