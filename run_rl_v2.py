"""
RL Bot v2: 1-Phase Runner.
Train 3 tháng (Q4 2025) → Test Jan 2026.
Multi-TF features (M5/M15/H1/H4) + Macro (DXY/VIX) + Ichimoku core.
PPO với 500k steps, live metrics, MT5 report.
"""

import sys
import time
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from stable_baselines3 import PPO
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import BaseCallback

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.data_loader import load_csv
from src.data.multi_tf_engine import build_multi_tf_features, normalize_features
from src.data.macro_data import get_macro_features, merge_macro_to_intraday
from src.env.trading_env import XAUUSDTradingEnv
from src.models.mt5_report import compute_mt5_report, print_mt5_report

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)


class LiveMetrics(BaseCallback):
    """Live PnL/WR/DD/Speed mỗi N steps. Auto-save best checkpoint."""

    def __init__(self, freq: int = 10000, save_dir: str = "models"):
        super().__init__(0)
        self.freq = freq
        self.save_dir = Path(save_dir)
        self._t0 = None
        self._best_ret = -999
        self._best_pf = 0
        self._best_step = 0
        self._pass_num = 0
        self._results_log = []  # Lưu tất cả pass results

    def _on_training_start(self):
        self._t0 = time.time()
        self.save_dir.mkdir(exist_ok=True)
        print(f"\n  {'Pass':>4} | {'Step':>7} | {'Speed':>6} | {'PnL':>10} | {'Return':>8} | {'WR':>6} | {'DD':>6} | {'Trades':>6} | {'Best?':>6}")
        print(f"  {'─'*4}─┼─{'─'*7}─┼─{'─'*6}─┼─{'─'*10}─┼─{'─'*8}─┼─{'─'*6}─┼─{'─'*6}─┼─{'─'*6}─┼─{'─'*6}")

    def _on_step(self):
        if self.n_calls % self.freq != 0:
            return True
        self._pass_num += 1
        dt = time.time() - self._t0
        spd = self.n_calls / (dt + 0.01)
        info = self.locals.get("infos", [{}])[0]
        ret = info.get("total_return", 0)
        wr = info.get("win_rate", 0)
        dd = info.get("max_drawdown", 0)
        pnl = info.get("total_pnl", 0)
        trades = info.get("total_trades", 0)

        # Track pass result
        pass_result = {
            "pass": self._pass_num, "step": self.n_calls,
            "pnl": round(pnl, 2), "return": round(ret, 2),
            "win_rate": round(wr, 1), "max_dd": round(dd, 2),
            "trades": trades, "speed": round(spd, 0),
        }
        self._results_log.append(pass_result)

        # Check if new best → auto-save
        is_best = ""
        if ret > self._best_ret and trades >= 10:
            self._best_ret = ret
            self._best_pf = wr
            self._best_step = self.n_calls
            is_best = " 🏆 SAVE"
            # Auto-save best model
            self.model.save(str(self.save_dir / "rl_v2_BEST.zip"))

        print(f"  {self._pass_num:>4} | {self.n_calls:>7,} | {spd:>5.0f}/s | ${pnl:>9.2f} | {ret:>7.2f}% | {wr:>5.1f}% | {dd:>5.1f}% | {trades:>6} |{is_best}")
        return True

    def _on_training_end(self):
        dt = time.time() - self._t0
        spd = self.num_timesteps / (dt + 0.01)

        # Save results log
        import json
        log_path = self.save_dir / "training_passes.json"
        with open(log_path, "w") as f:
            json.dump({
                "total_passes": self._pass_num,
                "best_pass": self._best_step // self.freq,
                "best_return": self._best_ret,
                "best_step": self._best_step,
                "training_time_sec": round(dt),
                "avg_speed": round(spd),
                "all_passes": self._results_log,
            }, f, indent=2)

        print(f"\n  ⏱️  Done: {dt:.0f}s ({spd:.0f} it/s)")
        print(f"  🏆 Best: Pass #{self._best_step // self.freq} (step {self._best_step:,}) = {self._best_ret:.2f}%")
        print(f"  💾 Best model: {self.save_dir / 'rl_v2_BEST.zip'}")
        print(f"  📋 All passes: {log_path}")


def prepare_data(data_dir: Path, year: int, months: list, with_macro: bool = True):
    """Load multi-month data → multi-TF features → normalize."""
    # Load & concat M1 data
    dfs = []
    for m in months:
        f = data_dir / f"XAUUSD_{year}_{m}.csv"
        if f.exists():
            dfs.append(load_csv(f))
    if not dfs:
        raise FileNotFoundError(f"No data for {year} months {months}")

    df_m1 = pd.concat(dfs).sort_index()
    df_m1 = df_m1[~df_m1.index.duplicated(keep="first")]

    # Multi-TF features
    logger.info(f"🔧 Building multi-TF features...")
    df = build_multi_tf_features(df_m1, timeframes=["M5", "M15", "H1", "H4"])

    # Macro data (optional - may fail if no internet)
    if with_macro:
        try:
            start = df.index[0].strftime("%Y-%m-%d")
            end = (df.index[-1] + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            macro = get_macro_features(start, end)
            if not macro.empty:
                df = merge_macro_to_intraday(df, macro)
                logger.info(f"📈 Macro data merged")
        except Exception as e:
            logger.warning(f"⚠️ Macro data failed: {e} (continuing without)")

    # Normalize
    df = normalize_features(df)

    feature_cols = [c for c in df.columns if c not in ["open", "high", "low", "close", "volume"]]
    logger.info(f"✅ Ready: {len(feature_cols)} features, {len(df)} bars")
    return df, feature_cols


def run_v2(
    data_dir: Path = None,
    timesteps: int = 500_000,
    sl: float = 5.0,
    tp: float = 3.0,
):
    """
    1-Phase: Train Q4 2025 → Test Jan 2026.
    Multi-TF + Macro + Ichimoku PPO.
    """
    if data_dir is None:
        data_dir = PROJECT_ROOT

    # === TRAIN DATA: Oct-Dec 2025 ===
    logger.info(f"\n{'='*60}")
    logger.info(f"🏋️ TRAIN: 2025 Oct-Dec (3 tháng)")
    logger.info(f"{'='*60}")

    train_df, feature_cols = prepare_data(data_dir, 2025, ["10", "11", "12"], with_macro=False)

    train_env = Monitor(XAUUSDTradingEnv(
        df=train_df, feature_columns=feature_cols,
        initial_balance=10000, lot_size=0.01,
        spread=0.36, reward_mode="sharpe",
        stop_loss=sl, take_profit=tp,
        use_sl_tp=True, trade_cooldown=5,
        random_start=True,
    ))

    model = PPO(
        "MlpPolicy", train_env,
        learning_rate=3e-4, n_steps=1024,
        batch_size=64, n_epochs=5,
        gamma=0.99, clip_range=0.2, ent_coef=0.01,
        policy_kwargs={"net_arch": [256, 256]},
        verbose=0, device="auto",
    )

    logger.info(f"🚀 Training {timesteps:,} steps | {len(feature_cols)} features | SL=${sl} TP=${tp}")

    save_dir = data_dir / "models"
    save_dir.mkdir(exist_ok=True)
    model.learn(total_timesteps=timesteps, callback=LiveMetrics(freq=10000, save_dir=str(save_dir)), progress_bar=True)

    # Save final model too
    model.save(str(save_dir / "rl_v2_FINAL.zip"))
    logger.info(f"💾 Final model: {save_dir / 'rl_v2_FINAL.zip'}")

    # === TEST: Jan 2026 (dùng BEST model) ===
    logger.info(f"\n{'='*60}")
    logger.info(f"📊 TEST: 2026 Jan (dùng BEST checkpoint)")
    logger.info(f"{'='*60}")

    # Load BEST model (không phải model cuối)
    best_path = save_dir / "rl_v2_BEST.zip"
    if best_path.exists():
        test_model = PPO.load(str(best_path))
        logger.info(f"✅ Loaded BEST model: {best_path}")
    else:
        test_model = model
        logger.warning(f"⚠️ No BEST model found, using final model")

    test_df, test_features = prepare_data(data_dir, 2026, ["01"], with_macro=False)

    test_env = XAUUSDTradingEnv(
        df=test_df, feature_columns=test_features,
        initial_balance=10000, lot_size=0.01,
        spread=0.36, reward_mode="sharpe",
        stop_loss=sl, take_profit=tp,
        use_sl_tp=True, trade_cooldown=5,
        random_start=False,
    )

    obs, _ = test_env.reset()
    done = False
    while not done:
        action, _ = test_model.predict(obs, deterministic=True)
        obs, _, terminated, truncated, _ = test_env.step(action)
        done = terminated or truncated

    # === MT5 REPORT ===
    trade_log = test_env.get_trade_log()
    mt5 = compute_mt5_report(
        trade_log=trade_log,
        equity_history=test_env.equity_history,
        initial_balance=10000,
        total_bars=len(test_df),
    )
    print_mt5_report(mt5, title="RL Bot v2 | XAUUSD Jan 2026 (M5) | BEST Checkpoint")

    summary = test_env.get_performance_summary()
    logger.info(f"\n📊 Summary: Return={summary['total_return']:.2f}% | PF={summary['profit_factor']:.2f} | WR={summary['win_rate']:.1f}% | DD={summary['max_drawdown']:.1f}% | Trades={summary['total_trades']}")

    return summary


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="RL Bot v2 - Ichimoku Multi-TF")
    parser.add_argument("--timesteps", type=int, default=500_000)
    parser.add_argument("--sl", type=float, default=5.0)
    parser.add_argument("--tp", type=float, default=3.0)
    args = parser.parse_args()

    run_v2(timesteps=args.timesteps, sl=args.sl, tp=args.tp)
