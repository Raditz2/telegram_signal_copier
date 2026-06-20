"""
risk_manager.py — Evaluates signals against risk rules before execution.
"""
import logging

logger = logging.getLogger(__name__)


class RiskManager:
    """Evaluates whether a signal should be executed based on risk parameters."""

    def __init__(
        self,
        risk_per_trade: float = 1.0,
        max_daily_loss: float = 5.0,
        max_concurrent_positions: int = 3,
        max_drawdown: float = 20.0,
        effective_leverage: float = 10.0,
    ):
        self.risk_per_trade = risk_per_trade
        self.max_daily_loss = max_daily_loss
        self.max_concurrent_positions = max_concurrent_positions
        self.max_drawdown = max_drawdown
        self.effective_leverage = effective_leverage

    def evaluate(self, signal: dict, balance: float, equity: float,
                 open_positions_count: int, daily_pnl: float) -> dict | None:
        """
        Evaluate if a signal should be traded. Returns an order dict or None.

        The returned order dict includes calculated lot_size based on risk.
        """
        direction = signal.get("direction", "")
        if direction == "CLOSE":
            return {"action": "CLOSE", "pair": "ALL", "lot_size": 0, "sl": 0, "tp": 0}

        # Check concurrent positions
        if open_positions_count >= self.max_concurrent_positions:
            logger.info("Risk: max concurrent positions reached (%d)", open_positions_count)
            return None

        # Check daily loss
        if daily_pnl < 0 and abs(daily_pnl / balance * 100) >= self.max_daily_loss:
            logger.info("Risk: max daily loss reached (%.2f%%)", abs(daily_pnl / balance * 100))
            return None

        # Check drawdown
        if balance > 0 and equity < balance * (1 - self.max_drawdown / 100):
            logger.info("Risk: max drawdown reached")
            return None

        # Calculate lot size based on risk percentage
        entry = signal.get("entry", 0)
        sl = signal.get("sl", 0)
        pair = signal.get("instrument", "UNKNOWN")

        lot_size = self._calculate_lot_size(balance, entry, sl)
        if lot_size <= 0:
            lot_size = 0.01  # minimum

        return {
            "action": direction,
            "pair": pair,
            "lot_size": round(lot_size, 2),
            "sl": sl,
            "tp": signal.get("tp", []),
        }

    def _calculate_lot_size(self, balance: float, entry: float, sl: float) -> float:
        """Calculate lot size based on risk percentage and SL distance."""
        if entry <= 0 or sl <= 0 or balance <= 0:
            return 0.01

        risk_amount = balance * (self.risk_per_trade / 100)
        sl_pips = abs(entry - sl)

        if sl_pips <= 0:
            return 0.01

        # Standard forex: 1 pip = 0.0001 for most pairs, 1 lot = 100,000 units
        # For XAUUSD (Gold): 1 pip = 0.01, 1 lot = 100 oz
        pip_value_per_lot = 10  # $10 per pip per lot for standard forex

        lot_size = risk_amount / (sl_pips * pip_value_per_lot)
        return max(0.01, round(lot_size, 2))
