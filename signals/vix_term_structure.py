"""VIX Term Structure: VIX / VIX3M. Below 1.0 = contango (calm), above 1.0 = backwardation (stress).
Map: 0.85 -> 100, 1.15 -> 0."""
from .common import frame, linmap

NAME = "Term Structure"


def compute(data):
    m = data["market"]
    ratio = (m["^VIX"] / m["^VIX3M"]).dropna()
    return frame(ratio, linmap(ratio, 0.85, 1.15))
