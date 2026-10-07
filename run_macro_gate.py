"""Entry point: refresh data + recalculate scores.

    python run_macro_gate.py                         # re-download prices, recompute everything
    python run_macro_gate.py --no-refresh            # recompute from cached data
    python run_macro_gate.py --refresh-fundamentals  # also re-fetch price-to-book (else cached 30 days)
"""
import argparse

import pipeline


def main():
    p = argparse.ArgumentParser(description="Macro deployment gate")
    p.add_argument("--no-refresh", action="store_true", help="use cached prices")
    p.add_argument("--refresh-fundamentals", action="store_true", help="re-fetch price-to-book snapshot")
    args = p.parse_args()

    res = pipeline.run(refresh=not args.no_refresh, refresh_fundamentals=args.refresh_fundamentals)
    L = res["latest"]
    print(f"Deployment score {L['score']:.1f}/100 -> {L['zone']} ({L['rule']})  as of {L['as_of']}")
    for name, s in L["signals"].items():
        print(f"  {name:<15} score {s['score']:5.1f}  raw {s['raw']:>9.4f}  weight {s['weight']:.2f}")
    print(f"  (value basket: {L['value_source']}; universe {L['universe_size']} names)")

    b = L["backtest"]
    print(f"\nBacktest {b['start']} -> {b['end']} ({b['days']} days, yesterday's zone -> today's SPY return)")
    t = res["backtest_table"]
    for _, r in t.iterrows():
        print(f"  {r['Zone']:<12} {r['Days']:>4} days  avg SPY {r['Avg SPY daily return']*100:+.3f}%/day"
              f"  hit {r['Hit rate (SPY up)']*100:4.1f}%")
    print(f"  SPY buy&hold {b['spy_total_return']*100:+.1f}% (max DD {b['spy_max_drawdown']*100:.1f}%)"
          f" | zone-sized {b['strategy_total_return']*100:+.1f}% (max DD {b['strategy_max_drawdown']*100:.1f}%)")


if __name__ == "__main__":
    main()
