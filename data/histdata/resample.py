import sys, pandas as pd
for s in sys.argv[1].split(","):
    m = pd.read_pickle(f"data/histdata/{s}_1m.pkl")
    for tf in ("5min", "15min", "1h"):
        b = m.resample(tf, label="left", closed="left").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()
        b.to_pickle(f"data/histdata/{s}_{tf.replace('min','m')}.pkl")
    print(s, "resampled", flush=True)
