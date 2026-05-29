"""
Portfolio-level circuit breaker.

Automatically suspends trading when portfolio-level risk thresholds are
breached.  Provides a hard safety floor independent of individual-trade
stop-losses.

Thresholds monitored:
- Daily loss limit  : cumulative P&L for the current trading day
- Maximum drawdown  : peak-to-trough drawdown from the equity high-water mark
- Consecutive losses: number of back-to-back losing trades

When a threshold is breached the circuit breaker enters a cooldown period
during which all new trade signals are blocked.

Usage:
    from circuit_breaker import CircuitBreaker

    cb = CircuitBreaker(
        max_daily_loss_pct=0.02,
        max_drawdown_pct=0.10,
        max_consecutive_losses=5,
        cooldown_bars=20,
    )
    for bar_pnl in bar_pnl_series:
        cb.record_bar(bar_pnl)
        status = cb.check(current_equity, peak_equity, daily_pnl, consecutive_losses)
        if status["tripped"]:
            break  # suspend trading
    cb.reset_daily()  # call at start of each trading day
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CircuitBreaker:
    """
    Portfolio-level circuit breaker with configurable thresholds.

    Parameters
    ----------
    max_daily_loss_pct    : float — max allowed daily loss as a fraction of equity
                            (e.g. 0.02 = 2%).  Compared against the running daily P&L.
    max_drawdown_pct      : float — max allowed drawdown from the equity high-water mark
                            (e.g. 0.10 = 10%).
    max_consecutive_losses: int   — max allowed consecutive losing trades / bars.
    cooldown_bars         : int   — number of bars to block new trades after a trip.
    """

    max_daily_loss_pct: float = 0.02
    max_drawdown_pct: float = 0.10
    max_consecutive_losses: int = 5
    cooldown_bars: int = 20

    # Internal counters — not meant to be set at construction time
    _daily_pnl: float = field(default=0.0, init=False, repr=False)
    _consecutive_losses: int = field(default=0, init=False, repr=False)
    _cooldown_remaining: int = field(default=0, init=False, repr=False)
    _tripped: bool = field(default=False, init=False, repr=False)
    _trip_reason: Optional[str] = field(default=None, init=False, repr=False)

    # ------------------------------------------------------------------
    # Bar-level update
    # ------------------------------------------------------------------

    def record_bar(self, pnl: float) -> None:
        """
        Update internal state after each bar / trade outcome.

        Call this BEFORE check() each bar.

        Parameters
        ----------
        pnl : float — fractional P&L for this bar (positive = profit, negative = loss)
        """
        self._daily_pnl += float(pnl)

        if pnl < 0:
            self._consecutive_losses += 1
        else:
            self._consecutive_losses = 0

        if self._cooldown_remaining > 0:
            self._cooldown_remaining -= 1
            if self._cooldown_remaining == 0:
                self._tripped = False
                self._trip_reason = None

    # ------------------------------------------------------------------
    # Threshold check
    # ------------------------------------------------------------------

    def check(
        self,
        current_equity: float,
        peak_equity: float,
        daily_pnl: Optional[float] = None,
        consecutive_losses: Optional[int] = None,
    ) -> dict:
        """
        Evaluate all circuit-breaker thresholds.

        Callers may supply their own daily_pnl / consecutive_losses overrides
        (e.g. from an external position manager).  If None, the internally
        tracked values are used.

        Parameters
        ----------
        current_equity     : float — current portfolio NAV
        peak_equity        : float — highest NAV since last reset / inception
        daily_pnl          : float | None — override for daily P&L tracker
        consecutive_losses : int | None   — override for loss streak counter

        Returns
        -------
        dict with keys:
            tripped            : bool
            reason             : str | None  — human-readable trip reason
            cooldown_remaining : int — bars left in cooldown (0 = not tripped)
        """
        daily = daily_pnl if daily_pnl is not None else self._daily_pnl
        consec = consecutive_losses if consecutive_losses is not None else self._consecutive_losses

        # If already in cooldown, check remaining
        if self._cooldown_remaining > 0:
            return {
                "tripped": True,
                "reason": self._trip_reason,
                "cooldown_remaining": self._cooldown_remaining,
            }

        reason: Optional[str] = None

        # 1. Daily loss limit
        if peak_equity > 0:
            daily_loss_pct = -daily / peak_equity  # positive when losing
            if daily_loss_pct >= self.max_daily_loss_pct:
                reason = (
                    f"Daily loss {daily_loss_pct:.2%} exceeded limit "
                    f"{self.max_daily_loss_pct:.2%}"
                )

        # 2. Maximum drawdown
        if reason is None and peak_equity > 0 and current_equity < peak_equity:
            drawdown_pct = (peak_equity - current_equity) / peak_equity
            if drawdown_pct >= self.max_drawdown_pct:
                reason = (
                    f"Drawdown {drawdown_pct:.2%} exceeded limit "
                    f"{self.max_drawdown_pct:.2%}"
                )

        # 3. Consecutive losses
        if reason is None and consec >= self.max_consecutive_losses:
            reason = (
                f"Consecutive losses {consec} reached limit "
                f"{self.max_consecutive_losses}"
            )

        if reason is not None:
            self._tripped = True
            self._trip_reason = reason
            self._cooldown_remaining = self.cooldown_bars

        return {
            "tripped": reason is not None,
            "reason": reason,
            "cooldown_remaining": self._cooldown_remaining if reason is not None else 0,
        }

    # ------------------------------------------------------------------
    # Day-end reset
    # ------------------------------------------------------------------

    def reset_daily(self) -> None:
        """
        Reset the daily P&L accumulator.

        Call at the start of each trading day (or after rolling-window period).
        Does NOT reset the cooldown or drawdown tracking.
        """
        self._daily_pnl = 0.0

    def reset_all(self) -> None:
        """
        Full reset of all internal counters.

        Clears the cooldown, consecutive-loss counter, and daily P&L.
        """
        self._daily_pnl = 0.0
        self._consecutive_losses = 0
        self._cooldown_remaining = 0
        self._tripped = False
        self._trip_reason = None

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def state(self) -> dict:
        """
        Return all current internal state counters.

        Returns
        -------
        dict with keys:
            daily_pnl            : float
            consecutive_losses   : int
            cooldown_remaining   : int
            tripped              : bool
            trip_reason          : str | None
            thresholds           : dict with the configured limits
        """
        return {
            "daily_pnl": self._daily_pnl,
            "consecutive_losses": self._consecutive_losses,
            "cooldown_remaining": self._cooldown_remaining,
            "tripped": self._tripped,
            "trip_reason": self._trip_reason,
            "thresholds": {
                "max_daily_loss_pct": self.max_daily_loss_pct,
                "max_drawdown_pct": self.max_drawdown_pct,
                "max_consecutive_losses": self.max_consecutive_losses,
                "cooldown_bars": self.cooldown_bars,
            },
        }

    def is_active(self) -> bool:
        """Return True when trading is currently allowed (not tripped / cooling down)."""
        return self._cooldown_remaining == 0
