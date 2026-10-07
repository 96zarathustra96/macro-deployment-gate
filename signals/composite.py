"""Composite deployment score: weighted blend of the 6 signal scores + deployment zone.

If a signal has no reading on a given day (e.g. still warming up), the remaining weights are
renormalised so the score stays on a 0-100 scale; `coverage` records how much weight was present.
"""
import pandas as pd

from . import breadth, credit_spreads, crowding, put_call, vix_level, vix_term_structure

SIGNALS = [  # (module, weight)
    (vix_level, 0.25),
    (vix_term_structure, 0.20),
    (breadth, 0.20),
    (credit_spreads, 0.15),
    (put_call, 0.10),
    (crowding, 0.10),
]

ZONES = [  # (min score, zone, sizing)
    (70, "FULL DEPLOY", 1.00),
    (40, "REDUCED", 0.60),
    (0, "DEFENSIVE", 0.25),
]
ZONE_RULES = {
    "FULL DEPLOY": "100% sizing",
    "REDUCED": "60% sizing, higher bar for new positions",
    "DEFENSIVE": "25% sizing, no new longs, scanner disabled",
}
MIN_COVERAGE = 0.999  # only call a score "complete" when all 6 signals report


def zone_for(score):
    if pd.isna(score):
        return None
    for floor, name, _ in ZONES:
        if score >= floor:
            return name


def sizing_for(zone):
    return {name: size for _, name, size in ZONES}.get(zone)


def compute(data):
    """Returns (signals dict of per-signal frames, composite frame indexed by date)."""
    signals = {mod.NAME: mod.compute(data) for mod, _ in SIGNALS}
    scores = pd.concat({mod.NAME: signals[mod.NAME]["score"] for mod, _ in SIGNALS}, axis=1)
    weights = pd.Series({mod.NAME: w for mod, w in SIGNALS})
    present = scores.notna()
    coverage = present.mul(weights, axis=1).sum(axis=1)
    score = scores.fillna(0).mul(weights, axis=1).sum(axis=1) / coverage
    comp = pd.DataFrame({"score": score, "coverage": coverage}).join(scores)
    comp = comp[comp["coverage"] >= MIN_COVERAGE]
    comp["zone"] = comp["score"].map(zone_for)
    comp["sizing"] = comp["zone"].map(sizing_for)
    return signals, comp
