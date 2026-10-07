"""Market Breadth: % of S&P 500 members above their 200-day SMA. 80% -> 100, 30% -> 0.
Uses today's constituents for the whole history (survivorship bias)."""
from .common import frame, linmap

NAME = "Breadth"
MIN_NAMES = 300  # need a real cross-section before trusting the reading


def compute(data):
    px = data["universe"]
    sma = px.rolling(200, min_periods=200).mean()
    valid = sma.notna() & px.notna()
    n = valid.sum(axis=1)
    pct = ((px > sma) & valid).sum(axis=1) / n * 100.0
    pct = pct[n >= MIN_NAMES]
    return frame(pct, linmap(pct, 80, 30))
