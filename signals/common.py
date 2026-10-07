import numpy as np
import pandas as pd


def linmap(x, x_at_100, x_at_0):
    """Linear map so x_at_100 -> 100 and x_at_0 -> 0, clipped to [0, 100]. Works either direction."""
    score = (x - x_at_0) / (x_at_100 - x_at_0) * 100.0
    return score.clip(0, 100) if isinstance(score, pd.Series) else float(np.clip(score, 0, 100))


def trailing_pct_rank(s, window=252):
    """Percentile (0-100) of each value within its trailing window, today included."""
    return s.rolling(window, min_periods=window).apply(lambda w: (w <= w[-1]).mean() * 100.0, raw=True)


def frame(raw, score):
    """Standard signal output: one row per day with the raw reading and its 0-100 score."""
    return pd.DataFrame({"raw": raw, "score": score})
