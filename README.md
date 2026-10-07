# Macro Deployment Gate

A Python system with a Streamlit dashboard that answers one question:

> **Should I be deploying capital right now, and how aggressively?**

It pulls 6 macro signals, scores each 0–100, and blends them into a single deployment score that maps to a sizing zone.

| Score | Zone | Rule |
|---|---|---|
| 70–100 | **FULL DEPLOY** | 100% sizing |
| 40–69 | **REDUCED** | 60% sizing, higher bar for new positions |
| 0–39 | **DEFENSIVE** | 25% sizing, no new longs, scanner disabled |

## Signals

| # | Signal | File | Reading | Mapping | Weight |
|---|---|---|---|---|---|
| 1 | VIX Level | `signals/vix_level.py` | VIX percentile vs trailing 1 year | low VIX = high score; +5 if VIX < 15, −10 if VIX > 30 | 0.25 |
| 2 | VIX Term Structure | `signals/vix_term_structure.py` | VIX / VIX3M | 0.85 → 100, 1.15 → 0 | 0.20 |
| 3 | Market Breadth | `signals/breadth.py` | % of S&P 500 above 200-day SMA | 80% → 100, 30% → 0 | 0.20 |
| 4 | Credit Spreads | `signals/credit_spreads.py` | −log(HYG/TLT), z-score vs 1 year | z −2 → 100, z +2 → 0 | 0.15 |
| 5 | Put/Call Sentiment | `signals/put_call.py` | VIX 20-day rate of change (proxy) | −30% → 100, +50% → 0 | 0.10 |
| 6 | Factor Crowding | `signals/crowding.py` | 60-day corr of momentum vs value long/short | +0.3 → 100, −0.8 → 0 | 0.10 |

The composite (`signals/composite.py`) is the weighted blend. A score is only reported on days when all 6 signals have data.

## Backtest

`backtest/deployment_backtest.py` recomputes the score daily over the last 2 years and buckets each day's SPY return by **yesterday's** zone (no look-ahead). It reports the average SPY return, hit rate and volatility per zone, plus a zone-sized strategy (100% / 60% / 25% SPY exposure) against buy-and-hold.

## Quick start

Requires Python 3.9+.

```bash
git clone https://github.com/<your-username>/macro-deployment-gate.git
cd macro-deployment-gate
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python run_macro_gate.py           # download data + compute scores (~30-60s first run)
streamlit run app.py               # open the dashboard
```

`run_macro_gate.py` options:

```bash
python run_macro_gate.py --no-refresh            # recompute from cached data
python run_macro_gate.py --refresh-fundamentals  # re-fetch price-to-book (otherwise cached 30 days)
```

Results are written to `cache/results.pkl` and `cache/latest.json`. Downstream tools (for example a stock scanner that should switch off in DEFENSIVE mode) can read `latest.json`.

## Dashboard

- Big deployment score and zone, with the sizing rule
- Table of all 6 signals: score bar, raw reading, weight
- 12-month score history with zone bands
- SPY chart shaded by deployment zone (2-year backtest)
- Performance-by-zone table and buy-and-hold comparison
- Sidebar **Refresh** button (same as running `run_macro_gate.py`)

Dark theme (`#0b0e17`) is set in `.streamlit/config.toml`, so run Streamlit from the repo root.

## Project layout

```
├── run_macro_gate.py          # entry point: refresh data + recalculate
├── app.py                     # Streamlit dashboard
├── pipeline.py                # data -> signals -> composite -> backtest -> cache/
├── data.py                    # yfinance downloads + on-disk cache
├── signals/
│   ├── common.py              # linear mapping + percentile helpers
│   ├── vix_level.py
│   ├── vix_term_structure.py
│   ├── breadth.py
│   ├── credit_spreads.py
│   ├── put_call.py
│   ├── crowding.py
│   └── composite.py           # weights + zones
├── backtest/
│   └── deployment_backtest.py
├── .streamlit/config.toml     # dark theme
└── requirements.txt
```

## Data and caveats

- **Data source:** Yahoo Finance via `yfinance`. The S&P 500 constituent list comes from the [datasets/s-and-p-500-companies](https://github.com/datasets/s-and-p-500-companies) CSV.
- **Survivorship bias:** Breadth and the momentum basket use *today's* S&P 500 members for the whole history, so past readings lean optimistic.
- **Value basket:** yfinance keeps no history of price-to-book, so the value long/short uses a current P/B snapshot applied to the whole period (a mild look-ahead). If fewer than 200 P/B values are available, it falls back to the IWD − IWF (Russell 1000 Value minus Growth) ETF spread.
- **Proxies:** Put/Call uses VIX rate of change, and Credit uses the HYG/TLT ratio, not true option volume or OAS spreads.
- **Warm-up:** signals need up to about a year of history, so the score series starts later than the price data.
- Yahoo rate-limits heavy use. The first run downloads about 500 tickers; later runs can use `--no-refresh`.

## Disclaimer

For research and education only. This is not investment advice. Past backtest results do not predict future returns.
