import json, time, urllib.request, pandas as pd
rows = []
months = pd.date_range("2015-06-01", "2026-11-01", freq="MS")
for a, b in zip(months[:-1], months[1:]):
    u = f"https://economic-calendar.tradingview.com/events?from={a:%Y-%m-%d}T00:00:00.000Z&to={b:%Y-%m-%d}T00:00:00.000Z&countries=GB,EU,DE,AU,JP"
    for k in range(5):
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Origin": "https://www.tradingview.com"})
            rows += json.load(urllib.request.urlopen(req, timeout=60))["result"]; break
        except Exception as e:
            time.sleep(5 * (k + 1))
    time.sleep(0.5)
df = pd.DataFrame(rows).drop_duplicates(subset=["id"]) if rows and "id" in rows[0] else pd.DataFrame(rows)
df.to_pickle("tv_calendar_intl.pkl"); print(len(df), df.date.min(), df.date.max())
