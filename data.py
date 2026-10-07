"""Data loading + on-disk caching for the macro gate.

Everything is pulled from Yahoo Finance via yfinance and cached as pickles in ./cache so the
dashboard and repeat runs don't re-download. Pass refresh=True to force a re-download.
"""
import io
import logging
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

warnings.filterwarnings("ignore")
# yfinance logs (and recovers from) sporadic 401 "Invalid Crumb" errors on .info lookups; failed lookups are skipped
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "cache"
CACHE.mkdir(exist_ok=True)

HISTORY = "4y"  # 2y backtest + 1y lookbacks + 200d SMA warm-up
MARKET_TICKERS = ["^VIX", "^VIX3M", "HYG", "TLT", "SPY", "IWD", "IWF"]
CONSTITUENTS_URL = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"
FUNDAMENTALS_MAX_AGE_DAYS = 30


def _cached(name, refresh, build, max_age_days=None):
    path = CACHE / f"{name}.pkl"
    if path.exists() and not refresh:
        age_days = (time.time() - path.stat().st_mtime) / 86400
        if max_age_days is None or age_days < max_age_days:
            return pd.read_pickle(path)
    obj = build()
    pd.to_pickle(obj, path)
    return obj


def _download_closes(tickers):
    df = yf.download(tickers, period=HISTORY, auto_adjust=True, progress=False, threads=True)["Close"]
    if isinstance(df, pd.Series):
        df = df.to_frame(tickers[0])
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df.sort_index()


def load_market(refresh=False):
    """Daily closes for VIX, VIX3M, HYG, TLT, SPY and the IWD/IWF value fallback."""
    def build():
        # Small holiday mismatches between the index and ETF calendars -> short forward-fill only.
        return _download_closes(MARKET_TICKERS).ffill(limit=3)
    return _cached("market", refresh, build)


def load_constituents(refresh=False):
    def build():
        r = requests.get(CONSTITUENTS_URL, timeout=30)
        r.raise_for_status()
        syms = pd.read_csv(io.StringIO(r.text))["Symbol"].astype(str)
        return sorted(s.replace(".", "-") for s in syms)  # Yahoo uses BRK-B, not BRK.B
    return _cached("constituents", refresh, build)


def load_universe(refresh=False):
    """Daily closes for current S&P 500 constituents (survivorship-biased: today's members only)."""
    def build():
        return _download_closes(load_constituents(refresh))
    return _cached("universe", refresh, build)


def load_price_to_book(refresh=False):
    """Current price-to-book snapshot per constituent. yfinance has no history of this, so it is a
    static ranking applied to the whole backtest (mild look-ahead; documented on the dashboard)."""
    def fetch(sym):
        try:
            return sym, yf.Ticker(sym).info.get("priceToBook")
        except Exception:
            return sym, None

    def build():
        with ThreadPoolExecutor(max_workers=8) as pool:
            rows = dict(pool.map(fetch, load_constituents()))
        s = pd.Series(rows, dtype="float64")
        return s[(s > 0) & s.notna()]
    return _cached("price_to_book", refresh, build, max_age_days=FUNDAMENTALS_MAX_AGE_DAYS)


def load_all(refresh=False, refresh_fundamentals=False):
    return {
        "market": load_market(refresh),
        "universe": load_universe(refresh),
        "price_to_book": load_price_to_book(refresh_fundamentals),
    }
