"""Credit Spreads: HYG vs TLT spread proxy, z-scored against its trailing year.
Proxy = -log(HYG / TLT): junk underperforming Treasuries = wider spreads.
Tight (z = -2) -> 100, wide (z = +2) -> 0."""
import numpy as np

from .common import frame, linmap

NAME = "Credit"


def compute(data):
    m = data["market"]
    spread = -np.log(m["HYG"] / m["TLT"]).dropna()
    mean = spread.rolling(252, min_periods=252).mean()
    std = spread.rolling(252, min_periods=252).std()
    z = ((spread - mean) / std).dropna()
    return frame(z, linmap(z, -2, 2))
