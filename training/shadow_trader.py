"""
Shadow trading framework.

Records every model signal as a "shadow trade" — tracking whether the
signal would have been profitable without risking real capital.  This
provides continuous live evaluation separate from the backtested metrics.

The shadow log persists to a JSON file so it survives restarts.

Usage:
    from shadow_trader import ShadowTrader

    st = ShadowTrader(output_dir="models/shadow", threshold=0.62)
    # On each new bar:
    st.log_signal(bar_time_utc="2024-01-15T10:00:00Z", signal_prob=0.71)
    # After outcome is known (e.g. next bar close):
    st.mark_outcome(bar_time_utc="2024-01-15T10:00:00Z", actual_return=0.0012)
    # Inspect performance:
    report = st.performance_report()
    st.save()
"""
from __future__ import annotations

import json
import pathlib
from datetime import datetime, timezone
from typing import Optional


class ShadowTrader:
    """
    Lightweight shadow trading logger.

    Records model signals and their outcomes to evaluate live prediction
    quality without executing real trades.

    Parameters
    ----------
    output_dir  : str | pathlib.Path — directory where shadow_trades.json is stored
    threshold   : float — probability threshold above which a signal is 'active'
    """

    _FILENAME = "shadow_trades.json"

    def __init__(
        self,
        output_dir: str | pathlib.Path,
        threshold: float = 0.62,
    ) -> None:
        self.output_dir = pathlib.Path(output_dir)
        self.threshold = threshold
        self._trades: list[dict] = []

    # ------------------------------------------------------------------
    # Signal logging
    # ------------------------------------------------------------------

    def log_signal(
        self,
        bar_time_utc: str,
        signal_prob: float,
        actual_return: Optional[float] = None,
    ) -> None:
        """
        Record a model signal for a bar.

        Parameters
        ----------
        bar_time_utc : str  — ISO-8601 UTC timestamp of the bar (e.g. "2024-01-15T10:00:00Z")
        signal_prob  : float — model output probability (0–1)
        actual_return: float | None — if known at logging time, set immediately
        """
        record = {
            "bar_time_utc": bar_time_utc,
            "signal_prob": float(signal_prob),
            "active": signal_prob >= self.threshold,
            "actual_return": float(actual_return) if actual_return is not None else None,
            "logged_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        # Avoid duplicates — update if same timestamp exists
        existing = next((t for t in self._trades if t["bar_time_utc"] == bar_time_utc), None)
        if existing is not None:
            existing.update(record)
        else:
            self._trades.append(record)

    def mark_outcome(self, bar_time_utc: str, actual_return: float) -> None:
        """
        Record the actual outcome for a previously logged signal.

        Parameters
        ----------
        bar_time_utc  : str   — must match a previously logged bar time
        actual_return : float — fractional return on the bar following the signal
        """
        record = next((t for t in self._trades if t["bar_time_utc"] == bar_time_utc), None)
        if record is None:
            # Auto-create a placeholder so we don't lose outcome data
            self.log_signal(bar_time_utc, signal_prob=0.0, actual_return=actual_return)
            return
        record["actual_return"] = float(actual_return)

    # ------------------------------------------------------------------
    # Performance reporting
    # ------------------------------------------------------------------

    def performance_report(self) -> dict:
        """
        Compute summary performance statistics for all completed shadow trades.

        Returns
        -------
        dict with keys:
            n_signals       : int   — total logged signals
            n_active        : int   — signals above threshold
            n_with_outcome  : int   — trades with actual_return recorded
            precision       : float | None — fraction of active trades with positive return
            mean_return     : float | None — mean return per active completed trade
            cum_return      : float | None — compounded equity from all active trades
            generated_at_utc: str   — ISO timestamp of report generation
        """
        active_with_outcome = [
            t for t in self._trades if t["active"] and t["actual_return"] is not None
        ]
        n_signals = len(self._trades)
        n_active = sum(1 for t in self._trades if t["active"])
        n_with_outcome = len(active_with_outcome)

        precision: Optional[float] = None
        mean_return: Optional[float] = None
        cum_return: Optional[float] = None

        if n_with_outcome > 0:
            returns = [t["actual_return"] for t in active_with_outcome]
            wins = sum(1 for r in returns if r > 0)
            precision = wins / n_with_outcome
            mean_return = sum(returns) / n_with_outcome
            eq = 1.0
            for r in returns:
                eq *= (1.0 + r)
            cum_return = eq - 1.0

        return {
            "n_signals": n_signals,
            "n_active": n_active,
            "n_with_outcome": n_with_outcome,
            "precision": precision,
            "mean_return": mean_return,
            "cum_return": cum_return,
            "generated_at_utc": datetime.now(tz=timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self) -> pathlib.Path:
        """
        Write the shadow trade log to output_dir/shadow_trades.json.

        Returns the path written to.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / self._FILENAME
        payload = {
            "threshold": self.threshold,
            "trades": self._trades,
            "saved_at_utc": datetime.now(tz=timezone.utc).isoformat(),
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    def load(self) -> None:
        """
        Load the shadow trade log from output_dir/shadow_trades.json.

        Replaces the current in-memory state.  Raises FileNotFoundError if
        the file does not exist.
        """
        path = self.output_dir / self._FILENAME
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.threshold = float(payload.get("threshold", self.threshold))
        self._trades = payload.get("trades", [])

    def clear(self) -> None:
        """Remove all in-memory trade records (does not touch the JSON file)."""
        self._trades = []

    def __len__(self) -> int:
        return len(self._trades)

    def __repr__(self) -> str:
        return (
            f"ShadowTrader(output_dir={self.output_dir!r}, threshold={self.threshold}, "
            f"n_trades={len(self._trades)})"
        )
