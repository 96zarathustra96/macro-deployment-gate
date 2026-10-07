"""Put/Call Sentiment proxy: VIX 20-day rate of change (%). Rapidly rising VIX = fear.
ROC -30% -> 100, ROC +50% -> 0."""
from .common import frame, linmap

NAME = "Put/Call"


def compute(data):
    vix = data["market"]["^VIX"].dropna()
    roc = (vix / vix.shift(20) - 1.0).dropna() * 100.0
    return frame(roc, linmap(roc, -30, 50))
