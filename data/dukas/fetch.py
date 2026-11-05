"""Dukascopy candle downloader (hour candles monthly files; minute candles daily files). Polite pacing + backoff."""
import lzma, struct, sys, time, urllib.request, urllib.error
from datetime import date, timedelta
import pandas as pd
MAP = {"EURUSD": ("EURUSD", 1e5), "GBPUSD": ("GBPUSD", 1e5), "USDJPY": ("USDJPY", 1e3), "AUDUSD": ("AUDUSD", 1e5),
       "USDCAD": ("USDCAD", 1e5), "USDCHF": ("USDCHF", 1e5), "NZDUSD": ("NZDUSD", 1e5), "EURJPY": ("EURJPY", 1e3),
       "GBPJPY": ("GBPJPY", 1e3), "EURGBP": ("EURGBP", 1e5), "NAS100": ("USATECHIDXUSD", 1e3), "SPX500": ("USA500IDXUSD", 1e3),
       "US30": ("USA30IDXUSD", 1e3), "XAUUSD": ("XAUUSD", 1e3), "XAGUSD": ("XAGUSD", 1e3), "DAX": ("DEUIDXEUR", 1e3)}
REC = struct.Struct(">IIIIIf")
def get(url, tries=8):
    for k in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read()
        except urllib.error.HTTPError as e:
            if e.code == 404: return b""
            time.sleep(min(120, 10 * 2 ** k))
        except Exception:
            time.sleep(min(120, 5 * 2 ** k))
    raise RuntimeError(url)
def parse(b, start, div):
    if not b: return []
    raw = lzma.decompress(b); out = []
    for i in range(len(raw) // 24):
        t, o, c, l, h, v = REC.unpack_from(raw, i * 24)
        out.append((start + pd.Timedelta(seconds=t), o / div, h / div, l / div, c / div, v))
    return out
def hourly(sym, side="BID", y0=2016, y1=2026, m1=10):
    slug, div = MAP[sym]; rows = []
    for y in range(y0, y1 + 1):
        for m in range(1, 13):
            if (y, m) > (y1, m1): break
            b = get(f"https://datafeed.dukascopy.com/datafeed/{slug}/{y}/{m-1:02d}/{side}_candles_hour_1.bi5")
            rows += parse(b, pd.Timestamp(y, m, 1, tz="UTC"), div); time.sleep(0.4)
    df = pd.DataFrame(rows, columns=["t", "Open", "High", "Low", "Close", "Volume"]).set_index("t")
    return df[df.Volume > 0]
def minutes(sym, d0, d1, side="BID"):
    slug, div = MAP[sym]; rows = []; d = d0
    while d <= d1:
        if d.weekday() != 5:
            b = get(f"https://datafeed.dukascopy.com/datafeed/{slug}/{d.year}/{d.month-1:02d}/{d.day:02d}/{side}_candles_min_1.bi5")
            rows += parse(b, pd.Timestamp(d, tz="UTC"), div); time.sleep(0.25)
        d += timedelta(days=1)
    df = pd.DataFrame(rows, columns=["t", "Open", "High", "Low", "Close", "Volume"]).set_index("t")
    return df[df.Volume > 0]
if __name__ == "__main__":
    mode, syms = sys.argv[1], sys.argv[2].split(",")
    for s in syms:
        t0 = time.time()
        if mode == "hour":
            df = hourly(s); df.to_pickle(f"{s}_1h.pkl")
            ask = hourly(s, "ASK", 2023, 2026, 10); spr = (ask.Close - df.Close.reindex(ask.index)).dropna()
            pd.Series({"median_spread": spr.median(), "price": df.Close.iloc[-1]}).to_pickle(f"{s}_spread.pkl")
            print(s, "hour", len(df), df.index[0], df.index[-1], f"spread {spr.median():.5f} ({spr.median()/df.Close.iloc[-1]*1e4:.2f} bps)", f"{time.time()-t0:.0f}s", flush=True)
        else:
            y0 = int(sys.argv[3]) if len(sys.argv) > 3 else 2019
            df = minutes(s, date(y0, 1, 1), date(2026, 10, 31)); df.to_pickle(f"{s}_1m.pkl")
            print(s, "min", len(df), df.index[0], df.index[-1], f"{time.time()-t0:.0f}s", flush=True)
