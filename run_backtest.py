"""
Quick Run: Backtest Ichimoku + Optimize SL/TP trên XAUUSD.
Chạy xong trong vài giây (không cần RL training).
"""

import sys
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.data_loader import load_csv
from src.data.resampler import resample_ohlcv
from src.strategy.ichimoku_strategy import (
    StrategyParams, run_backtest, optimize_params, print_optimization_results
)
from src.models.mt5_report import compute_mt5_report, print_mt5_report

import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)


def run_single_backtest(data_dir: Path, year: int, month: str, timeframe: str = "M5", params: StrategyParams = None):
    """Chạy 1 backtest trên 1 tháng, in MT5 report."""
    if params is None:
        params = StrategyParams()

    csv_file = data_dir / f"XAUUSD_{year}_{month}.csv"
    df_m1 = load_csv(csv_file)
    if timeframe != "M1":
        df = resample_ohlcv(df_m1, timeframe)
    else:
        df = df_m1

    result = run_backtest(df, params)

    # Convert trades to DataFrame for MT5 report
    if result["trades"]:
        trade_data = []
        for t in result["trades"]:
            trade_data.append({
                "step": t.bars_held,
                "type": t.type,
                "entry": t.entry_price,
                "exit": t.exit_price,
                "pnl": t.pnl,
                "balance": t.balance_after,
            })
        trade_df = pd.DataFrame(trade_data)
    else:
        trade_df = pd.DataFrame()

    mt5 = compute_mt5_report(
        trade_log=trade_df,
        equity_history=result["equity_curve"].tolist(),
        initial_balance=result["initial_balance"],
        total_bars=result["total_bars"],
    )
    print_mt5_report(mt5, title=f"XAUUSD {year}-{month} ({timeframe}) | Ichimoku Cloud Break")

    # Print cải tiến hơn MQL5: trade-by-trade log
    if result["trades"]:
        print(f"\n  {'─'*100}")
        print(f"  TRADE LOG (Cải tiến hơn MQL5: Entry/Exit Reason, MFE/MAE)")
        print(f"  {'─'*100}")
        print(f"  {'#':>3} | {'Type':>5} | {'Entry':>10} | {'Exit':>10} | {'PnL':>10} | {'Bars':>5} | {'Entry Reason':>16} | {'Exit Reason':>14} | {'MFE':>6} | {'MAE':>6}")
        print(f"  {'─'*3}─┼─{'─'*5}─┼─{'─'*10}─┼─{'─'*10}─┼─{'─'*10}─┼─{'─'*5}─┼─{'─'*16}─┼─{'─'*14}─┼─{'─'*6}─┼─{'─'*6}")

        for i, t in enumerate(result["trades"]):
            pnl_str = f"${t.pnl:>9.2f}"
            print(
                f"  {i+1:>3} | {t.type:>5} | {t.entry_price:>10.2f} | {t.exit_price:>10.2f} | {pnl_str} | "
                f"{t.bars_held:>5} | {t.entry_reason:>16} | {t.exit_reason:>14} | {t.max_favorable:>5.2f} | {t.max_adverse:>5.2f}"
            )
        print()

    return result


def run_optimization(data_dir: Path, year: int, month: str, timeframe: str = "M5"):
    """Grid search SL/TP/trailing params."""
    csv_file = data_dir / f"XAUUSD_{year}_{month}.csv"
    df_m1 = load_csv(csv_file)
    if timeframe != "M1":
        df = resample_ohlcv(df_m1, timeframe)
    else:
        df = df_m1

    param_grid = {
        "stop_loss": [3.0, 5.0, 8.0, 10.0],
        "take_profit": [2.0, 3.0, 5.0, 8.0],
        "trailing_start": [1.0, 2.0, 3.0],
        "trailing_step": [0.3, 0.5, 1.0],
        "use_trailing_stop": [True, False],
        "cooldown_bars": [2, 5],
    }

    results = optimize_params(
        df, param_grid,
        sort_by="profit_factor",
        top_n=15,
    )

    print_optimization_results(results, title=f"Optimization XAUUSD {year}-{month} ({timeframe})")

    # Run best params
    if results:
        best = results[0]
        best_params = StrategyParams(**best["params"])
        print(f"\n🏆 Best params: {best['params']}")
        print(f"   Running full backtest with best params...\n")
        run_single_backtest(data_dir, year, month, timeframe, best_params)

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ichimoku XAUUSD Backtester")
    parser.add_argument("--mode", choices=["backtest", "optimize"], default="optimize")
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--month", type=str, default="01")
    parser.add_argument("--timeframe", type=str, default="M5")
    parser.add_argument("--sl", type=float, default=5.0)
    parser.add_argument("--tp", type=float, default=3.0)
    args = parser.parse_args()

    if args.mode == "backtest":
        params = StrategyParams(stop_loss=args.sl, take_profit=args.tp)
        run_single_backtest(PROJECT_ROOT, args.year, args.month, args.timeframe, params)
    else:
        run_optimization(PROJECT_ROOT, args.year, args.month, args.timeframe)
