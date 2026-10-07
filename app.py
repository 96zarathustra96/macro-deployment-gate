"""Streamlit dashboard for the macro deployment gate.

    cd macro_gate && streamlit run app.py
"""
import threading
import time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import pipeline
from signals.composite import SIGNALS, ZONE_RULES

BG = "#0b0e17"
TEXT = "#e6e9f0"
MUTED = "#8b93a7"
MAX_AGE_HOURS = 12
ZONE_COLORS = {"FULL DEPLOY": "#22c55e", "REDUCED": "#f59e0b", "DEFENSIVE": "#ef4444"}

st.set_page_config(page_title="Macro Deployment Gate", layout="wide")
st.markdown(f"""
<style>
  .stApp {{ background-color: {BG}; }}
  .zone-pill {{ display: inline-block; padding: 6px 16px; border-radius: 999px; font-weight: 700;
               font-size: 22px; color: {BG}; }}
  .muted {{ color: {MUTED}; }}
</style>""", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load(_stamp):
    return pipeline.load_results()


with st.sidebar:
    st.header("Data")
    if st.button("Refresh data + recalculate", type="primary"):
        with st.spinner("Downloading prices and recomputing (about 30-60s)..."):
            pipeline.run(refresh=True)
        st.cache_data.clear()
    st.caption("Same as running `python run_macro_gate.py`.")

@st.cache_resource
def refresh_lock():
    return threading.Lock()


# Hosted (e.g. Streamlit Cloud) the cache/ folder starts empty and is wiped on restart, so compute on
# first load and whenever results are older than MAX_AGE_HOURS. The lock stops concurrent viewers
# from all downloading at once.
age_hours = ((time.time() - pipeline.RESULTS.stat().st_mtime) / 3600) if pipeline.RESULTS.exists() else None
if age_hours is None or age_hours > MAX_AGE_HOURS:
    with refresh_lock():
        if not pipeline.RESULTS.exists() or (time.time() - pipeline.RESULTS.stat().st_mtime) / 3600 > MAX_AGE_HOURS:
            try:
                with st.spinner("Downloading market data and computing scores (about 1 minute)..."):
                    pipeline.run(refresh=True)
                st.cache_data.clear()
            except Exception as e:  # keep serving stale results if a refresh fails
                st.error(f"Data refresh failed: {e}")

stamp = pipeline.RESULTS.stat().st_mtime if pipeline.RESULTS.exists() else None
res = load(stamp)
if res is None:
    st.title("Macro Deployment Gate")
    st.warning("No results yet. Run `python run_macro_gate.py` or press **Refresh** in the sidebar.")
    st.stop()

L, comp, bt, table = res["latest"], res["composite"], res["backtest"], res["backtest_table"]
zone_color = ZONE_COLORS[L["zone"]]

# --- Header: the answer ---------------------------------------------------------------------
st.title("Macro Deployment Gate")
st.markdown('<span class="muted">Should I be deploying capital right now, and how aggressively?</span>',
            unsafe_allow_html=True)
RAW_FMT = {"VIX Level": "VIX {:.2f}", "Term Structure": "ratio {:.3f}", "Breadth": "{:.1f}% > 200d",
           "Credit": "z {:+.2f}", "Put/Call": "20d {:+.1f}%", "Crowding": "corr {:+.2f}"}
left, right = st.columns([1, 2])
with left:
    # inline style: Streamlit's own <p> rules outrank a stylesheet class
    st.markdown(f'<div style="font-size:140px;font-weight:800;line-height:1;color:{zone_color}">'
                f'{L["score"]:.1f}</div>', unsafe_allow_html=True)
    st.markdown(f'<span class="zone-pill" style="background:{zone_color}">{L["zone"]}</span>',
                unsafe_allow_html=True)
    st.markdown(f"**{ZONE_RULES[L['zone']]}**")
    st.caption(f"Data as of {L['as_of']} · computed {L['generated_at']}")
with right:  # all 6 signals at a glance
    st.markdown("**Signals**")
    sig_table = pd.DataFrame([
        {"Signal": mod.NAME,
         "Score": L["signals"][mod.NAME]["score"],
         "Reading": RAW_FMT[mod.NAME].format(L["signals"][mod.NAME]["raw"]),
         "Weight": f"{weight:.0%}"}
        for mod, weight in SIGNALS])
    st.dataframe(
        sig_table, hide_index=True, use_container_width=True,
        column_config={"Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100,
                                                                format="%.0f", width="small"),
                       "Weight": st.column_config.TextColumn("Weight", width="small")})

# --- Score history ------------------------------------------------------------------------
hist = comp["score"].tail(252)
fig = go.Figure(go.Scatter(x=hist.index, y=hist, mode="lines", line=dict(color=TEXT, width=2)))
for y0, y1, z in [(70, 100, "FULL DEPLOY"), (40, 70, "REDUCED"), (0, 40, "DEFENSIVE")]:
    fig.add_hrect(y0=y0, y1=y1, fillcolor=ZONE_COLORS[z], opacity=0.10, line_width=0)
fig.update_layout(title="Deployment score, last 12 months", height=280, paper_bgcolor=BG,
                  plot_bgcolor=BG, font_color=TEXT, margin=dict(l=10, r=10, t=40, b=10),
                  yaxis=dict(range=[0, 100], gridcolor="#1f2637"), xaxis=dict(gridcolor="#1f2637"))
st.plotly_chart(fig, use_container_width=True)

# --- SPY chart colour-coded by zone ---------------------------------------------------------
st.subheader("SPY, coloured by deployment zone (2-year backtest)")
st.caption("Each day is shaded by the zone known at the open (yesterday's score), the same no-look-ahead "
           "rule the backtest uses.")
fig = go.Figure()
runs = (bt["zone_prev"] != bt["zone_prev"].shift()).cumsum()
for _, seg in bt.groupby(runs):
    fig.add_vrect(x0=seg.index[0], x1=seg.index[-1] + pd.Timedelta(days=1),
                  fillcolor=ZONE_COLORS[seg["zone_prev"].iloc[0]], opacity=0.18, line_width=0)
fig.add_trace(go.Scatter(x=bt.index, y=bt["spy"], mode="lines", name="SPY", line=dict(color=TEXT, width=1.6)))
for z, c in ZONE_COLORS.items():  # legend entries for the shading
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", marker=dict(size=12, color=c, symbol="square"),
                             name=z))
fig.update_layout(height=420, paper_bgcolor=BG, plot_bgcolor=BG, font_color=TEXT,
                  margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=1.08),
                  yaxis=dict(gridcolor="#1f2637"), xaxis=dict(gridcolor="#1f2637"))
st.plotly_chart(fig, use_container_width=True)

# --- Performance comparison ---------------------------------------------------------------
st.subheader("Performance by zone")
b = L["backtest"]
show = table.copy()
show["% of days"] = show["% of days"].map("{:.0%}".format)
for c in ["Avg SPY daily return", "Daily volatility"]:
    show[c] = show[c].map(lambda v: "n/a" if pd.isna(v) else f"{v * 100:+.3f}%")
show["Annualised SPY return"] = show["Annualised SPY return"].map(lambda v: "n/a" if pd.isna(v) else f"{v:+.1%}")
show["Hit rate (SPY up)"] = show["Hit rate (SPY up)"].map(lambda v: "n/a" if pd.isna(v) else f"{v:.1%}")
st.dataframe(show, hide_index=True, use_container_width=True)

c1, c2, c3, c4 = st.columns(4)
c1.metric("SPY buy & hold", f"{b['spy_total_return']:+.1%}")
c2.metric("Zone-sized SPY", f"{b['strategy_total_return']:+.1%}")
c3.metric("SPY max drawdown", f"{b['spy_max_drawdown']:.1%}")
c4.metric("Zone-sized max drawdown", f"{b['strategy_max_drawdown']:.1%}")
st.caption(f"{b['start']} → {b['end']}, {b['days']} trading days. Zone-sized = SPY exposure of 100% / 60% / 25% "
           "by the previous day's zone.")

with st.expander("Method notes and caveats"):
    st.markdown(f"""
- **Survivorship bias:** Breadth and the momentum basket use today's {L['universe_size']} S&P 500 members for the
  whole history, so past readings lean optimistic.
- **Value basket:** {L['value_source']}. Price-to-book is a current snapshot (yfinance keeps no history), applied
  to the whole period, which is a mild look-ahead in the Crowding signal.
- **Put/Call** is proxied by VIX 20-day rate of change; **Credit** by -log(HYG/TLT), z-scored over 1 year.
- Signals need up to ~1 year of warm-up, so the score history starts later than the price history.
- Data: Yahoo Finance via yfinance. Not investment advice.
""")
