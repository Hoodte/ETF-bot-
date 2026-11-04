"""London Stock Exchange calendar (XLON) via exchange_calendars.

Used so the bot never tries to trade on a weekend or UK market holiday.
Falls back to a weekday-only check (with a warning) if the library is missing.
"""
from __future__ import annotations

import pandas as pd

EXCHANGE = "XLON"


def _cal():
    try:
        import exchange_calendars as xc
    except ImportError:
        return None
    return xc.get_calendar(EXCHANGE)


def status(day: pd.Timestamp | str | None = None) -> dict:
    d = pd.Timestamp(day if day is not None else pd.Timestamp.now(tz="Europe/London").date()).normalize()
    cal = _cal()
    if cal is None:
        is_open = d.weekday() < 5
        return {"date": str(d.date()), "exchange": EXCHANGE, "is_trading_day": is_open,
                "warning": "exchange_calendars not installed: weekday check only, holidays ignored"}
    is_open = bool(cal.is_session(d))
    nxt = cal.next_session(d) if is_open else cal.date_to_session(d, direction="next")
    week = pd.date_range(d - pd.Timedelta(days=d.weekday()), periods=5)
    sessions = [x for x in week if cal.is_session(x)]
    return {"date": str(d.date()), "exchange": EXCHANGE, "is_trading_day": is_open,
            "next_trading_day": str(pd.Timestamp(nxt).date()),
            "is_last_trading_day_of_week": bool(is_open and sessions and sessions[-1] == d)}
