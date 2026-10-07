"""Factor Crowding: 60-day rolling correlation between momentum and value long/short returns.
Corr +0.3 -> 100 (normal), corr -0.8 -> 0 (extreme crowding / reversal risk).

Momentum L/S: top 50 minus bottom 50 by 12-1 month return, rebalanced monthly (no look-ahead).
Value L/S:    lowest 50 minus highest 50 price-to-book. P/B is a current snapshot (yfinance has no
              history), so it is applied statically. If too few P/B values are available, falls back
              to the IWD (Russell 1000 Value) minus IWF (Russell 1000 Growth) ETF spread.
"""
import pandas as pd

from .common import frame, linmap

NAME = "Crowding"
BASKET = 50
MIN_PB_NAMES = 200


def momentum_ls(px):
    rets = px.pct_change(fill_method=None)
    signal = px.shift(21) / px.shift(252) - 1.0          # 12-1 month momentum, known at t
    month_ends = px.groupby(px.index.to_period("M")).tail(1).index
    weights = pd.DataFrame(0.0, index=px.index, columns=px.columns)
    for d in month_ends:
        row = signal.loc[d].dropna()
        if len(row) < 2 * BASKET:
            continue
        ranked = row.sort_values()
        w = pd.Series(0.0, index=px.columns)
        w[ranked.index[-BASKET:]] = 1.0 / BASKET
        w[ranked.index[:BASKET]] = -1.0 / BASKET
        weights.loc[d] = w
    # hold month-end weights through the following month; trade from the next day
    held = weights.loc[month_ends].reindex(px.index).ffill().shift(1)
    ls = (held * rets).sum(axis=1, min_count=1)
    return ls[held.abs().sum(axis=1) > 0]


def value_ls(px, pb, market):
    pb = pb.reindex(px.columns).dropna()
    if len(pb) >= MIN_PB_NAMES:
        ranked = pb.sort_values()
        rets = px.pct_change(fill_method=None)
        cheap, rich = ranked.index[:BASKET], ranked.index[-BASKET:]
        return rets[cheap].mean(axis=1) - rets[rich].mean(axis=1), "price-to-book baskets"
    etf = market[["IWD", "IWF"]].pct_change(fill_method=None)
    return etf["IWD"] - etf["IWF"], "IWD-IWF ETF fallback"


def compute(data):
    px = data["universe"]
    mom = momentum_ls(px)
    val, source = value_ls(px, data.get("price_to_book", pd.Series(dtype=float)), data["market"])
    both = pd.concat([mom, val], axis=1, keys=["mom", "val"]).dropna()
    corr = both["mom"].rolling(60, min_periods=60).corr(both["val"]).dropna()
    out = frame(corr, linmap(corr, 0.3, -0.8))
    out.attrs["value_source"] = source
    return out
