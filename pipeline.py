"""Shared pipeline: load data -> 6 signals -> composite -> backtest -> save results to cache/."""
import json
from datetime import datetime

import pandas as pd

from backtest import deployment_backtest
from data import CACHE, load_all
from signals import composite

RESULTS = CACHE / "results.pkl"
LATEST_JSON = CACHE / "latest.json"


def run(refresh=True, refresh_fundamentals=False):
    data = load_all(refresh=refresh, refresh_fundamentals=refresh_fundamentals)
    signals, comp = composite.compute(data)
    if comp.empty:
        raise RuntimeError("No complete composite score: a signal has no data (check the downloads).")
    bt_df, bt_table, bt_summary = deployment_backtest.run(comp, data["market"]["SPY"])

    last = comp.iloc[-1]
    latest = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "as_of": comp.index[-1].date().isoformat(),
        "score": round(float(last["score"]), 1),
        "zone": last["zone"],
        "sizing": last["sizing"],
        "rule": composite.ZONE_RULES[last["zone"]],
        "signals": {
            mod.NAME: {
                "weight": w,
                "raw": round(float(signals[mod.NAME]["raw"].dropna().iloc[-1]), 4),
                "score": round(float(last[mod.NAME]), 1),
            }
            for mod, w in composite.SIGNALS
        },
        "value_source": signals["Crowding"].attrs.get("value_source"),
        "universe_size": int(data["universe"].shape[1]),
        "backtest": bt_summary,
    }
    results = {"latest": latest, "composite": comp, "backtest": bt_df, "backtest_table": bt_table}
    pd.to_pickle(results, RESULTS)
    LATEST_JSON.write_text(json.dumps(latest, indent=2, default=str))
    return results


def load_results():
    return pd.read_pickle(RESULTS) if RESULTS.exists() else None
