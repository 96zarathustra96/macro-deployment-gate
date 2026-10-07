"""Historical backtest of the deployment zones over the last 2 years.

No look-ahead: each day's SPY return is bucketed by YESTERDAY's composite zone (the zone you would
have known at today's open). Also tracks a sized strategy (100% / 60% / 25% SPY exposure).
"""
import pandas as pd

from signals.composite import ZONES

TRADING_DAYS = 252
LOOKBACK_DAYS = 2 * TRADING_DAYS


def run(comp, spy):
    spy_ret = spy.pct_change(fill_method=None)
    df = pd.DataFrame({
        "spy": spy,
        "spy_ret": spy_ret,
        "score_prev": comp["score"].shift(1),
        "zone_prev": comp["zone"].shift(1),
        "sizing_prev": comp["sizing"].shift(1),
        "zone": comp["zone"],
    }).dropna(subset=["spy_ret", "zone_prev"]).tail(LOOKBACK_DAYS)
    df["strategy_ret"] = df["sizing_prev"] * df["spy_ret"]
    df["spy_equity"] = (1 + df["spy_ret"]).cumprod()
    df["strategy_equity"] = (1 + df["strategy_ret"]).cumprod()

    rows = []
    for _, zone, sizing in ZONES:
        r = df.loc[df["zone_prev"] == zone, "spy_ret"]
        rows.append({
            "Zone": zone,
            "Sizing": f"{sizing:.0%}",
            "Days": len(r),
            "% of days": len(r) / len(df) if len(df) else float("nan"),
            "Avg SPY daily return": r.mean() if len(r) else float("nan"),
            "Annualised SPY return": r.mean() * TRADING_DAYS if len(r) else float("nan"),
            "Hit rate (SPY up)": (r > 0).mean() if len(r) else float("nan"),
            "Daily volatility": r.std() if len(r) > 1 else float("nan"),
        })
    table = pd.DataFrame(rows)

    def total(x):
        return x.iloc[-1] - 1 if len(x) else float("nan")

    def max_dd(eq):
        return (eq / eq.cummax() - 1).min() if len(eq) else float("nan")

    summary = {
        "start": df.index[0].date().isoformat() if len(df) else None,
        "end": df.index[-1].date().isoformat() if len(df) else None,
        "days": len(df),
        "spy_total_return": total(df["spy_equity"]),
        "strategy_total_return": total(df["strategy_equity"]),
        "spy_max_drawdown": max_dd(df["spy_equity"]),
        "strategy_max_drawdown": max_dd(df["strategy_equity"]),
    }
    return df, table, summary
