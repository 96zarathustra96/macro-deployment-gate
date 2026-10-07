"""VIX Level: percentile-rank VIX against its trailing year. Low VIX = high score.
Bonus +5 if VIX < 15, penalty -10 if VIX > 30."""
from .common import frame, trailing_pct_rank

NAME = "VIX Level"


def compute(data):
    vix = data["market"]["^VIX"].dropna()
    score = 100.0 - trailing_pct_rank(vix, 252)
    score = score + 5.0 * (vix < 15) - 10.0 * (vix > 30)
    return frame(vix, score.clip(0, 100))
