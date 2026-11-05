import sys, os, time, io, zipfile
sys.path.insert(0, "/home/claude/philipperemy/fx-1-minute-data")
from histdata.api import download_hist_data, Platform, TimeFrame
import pandas as pd
os.chdir("/home/claude/etf-bot-/data/histdata")
for pair in sys.argv[1].split(","):
    parts = []
    jobs = [(str(y), None) for y in range(2016, 2026)] + [("2026", str(m)) for m in range(1, 11)]
    for y, m in jobs:
        for k in range(4):
            try:
                f = download_hist_data(year=y, month=m, pair=pair, platform=Platform.GENERIC_ASCII, time_frame=TimeFrame.ONE_MINUTE, output_directory=".", verbose=False)
                z = zipfile.ZipFile(f); name = [n for n in z.namelist() if n.endswith(".csv")][0]
                df = pd.read_csv(z.open(name), sep=";", header=None, names=["t", "Open", "High", "Low", "Close", "V"])
                parts.append(df); os.remove(f); break
            except Exception as e:
                if k == 3: print(pair, y, m, "FAILED", repr(e)[:120], flush=True)
                time.sleep(5 * (k + 1))
        time.sleep(1)
    df = pd.concat(parts)
    idx = pd.to_datetime(df.t, format="%Y%m%d %H%M%S") + pd.Timedelta(hours=5)      # HistData = EST without DST -> UTC
    out = df[["Open", "High", "Low", "Close"]].astype(float); out.index = idx.dt.tz_localize("UTC")
    out = out[~out.index.duplicated()].sort_index()
    out.to_pickle(f"{pair.upper()}_1m.pkl"); print(pair, len(out), out.index[0], out.index[-1], flush=True)
