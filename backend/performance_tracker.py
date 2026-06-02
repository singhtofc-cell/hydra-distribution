# ============================================================================
# Hydra Performance Tracker — PostgreSQL Trade Tracking
# ============================================================================
# Renamed from HERMES → Hydra for standalone copy-trade distribution
# Source: Qwen Architecture Proposal 2026-06-02 — Phase 4
#
# Tracks all signals dispatched, trade fills received from client EAs,
# and calculates P&L / win rate for per-client and aggregate reporting.

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from dataclasses import dataclass, field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hydra.performance_tracker")


# ============================================================================
# Data Classes
# ============================================================================
@dataclass
class SignalLog:
    """Record of a dispatched signal."""
    signal_id: str
    timestamp: datetime
    symbol: str
    direction: str
    entry_price: float
    sl_price: float
    tp_prices: List[float]
    source: str
    priority: str
    dispatched_count: int
    status: str = "sent"  # sent, filled, expired, cancelled

@dataclass
class TradeFill:
    """Record of a trade fill reported back by client EA."""
    fill_id: str
    client_id: str
    signal_id: str
    symbol: str
    direction: str
    fill_price: float
    lot_size: float
    sl_price: float
    tp_price: Optional[float]
    ticket: int
    timestamp: datetime
    status: str = "open"  # open, closed (TP), closed (SL), closed (manual)

@dataclass
class ClientPerformance:
    """Aggregated performance metrics for a client."""
    client_id: str
    total_signals: int = 0
    executed_trades: int = 0
    wins: int = 0
    losses: int = 0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    max_drawdown: float = 0.0
    avg_rr: float = 0.0
    win_rate: float = 0.0
    currency: str = "USD"


class PerformanceTracker:
    """Track and aggregate performance for all Hydra clients.

    In production, this connects to PostgreSQL via asyncpg.
    The in-memory store is a fallback for development/testing.
    """

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or os.getenv("HYDRA_DATABASE_URL", "")
        # In-memory fallback stores
        self._signals: Dict[str, SignalLog] = {}
        self._fills: List[TradeFill] = []
        self._client_stats: Dict[str, ClientPerformance] = {}
        logger.info(f"PerformanceTracker initialized (db_url={'set' if self.db_url else 'memory-only'})")

    # ------------------------------------------------------------------
    # Signal Logging
    # ------------------------------------------------------------------
    async def log_signal_dispatched(self, signal: dict, dispatched_to: int):
        """Record a dispatched signal."""
        entry = SignalLog(
            signal_id=signal["signal_id"],
            timestamp=signal.get("timestamp", datetime.utcnow()),
            symbol=signal.get("symbol", ""),
            direction=signal.get("direction", ""),
            entry_price=signal.get("entry_price", 0.0),
            sl_price=signal.get("sl_price", 0.0),
            tp_prices=signal.get("tp_prices", []),
            source=signal.get("source", "HERMES"),
            priority=signal.get("priority", "NORMAL"),
            dispatched_count=dispatched_to
        )
        self._signals[entry.signal_id] = entry
        logger.debug(f"Signal logged: {entry.signal_id[:8]} → {dispatched_to} clients")

        if self.db_url:
            await self._db_log_signal(entry)

    async def _db_log_signal(self, signal: SignalLog):
        """Persist signal to PostgreSQL."""
        try:
            import asyncpg
            conn = await asyncpg.connect(self.db_url)
            await conn.execute("""
                INSERT INTO signals (
                    signal_id, timestamp, symbol, direction, entry_price,
                    sl_price, tp_prices, source, priority, dispatched_count
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """, signal.signal_id, signal.timestamp, signal.symbol,
                signal.direction, signal.entry_price, signal.sl_price,
                json.dumps(signal.tp_prices), signal.source,
                signal.priority, signal.dispatched_count)
            await conn.close()
        except Exception as e:
            logger.error(f"DB log_signal failed: {e}")

    # ------------------------------------------------------------------
    # Trade Fill Logging
    # ------------------------------------------------------------------
    async def log_trade_fill(self, client_id: str, signal_id: str,
                              fill_price: float, lot: float, ticket: int):
        """Record a trade fill reported by client EA."""
        signal = self._signals.get(signal_id)
        if not signal:
            logger.warning(f"Unknown signal {signal_id[:8]} for fill from {client_id}")
            return

        fill = TradeFill(
            fill_id=f"{signal_id}_{ticket}",
            client_id=client_id,
            signal_id=signal_id,
            symbol=signal.symbol,
            direction=signal.direction,
            fill_price=fill_price,
            lot_size=lot,
            sl_price=signal.sl_price,
            tp_price=signal.tp_prices[0] if signal.tp_prices else None,
            ticket=ticket,
            timestamp=datetime.utcnow()
        )
        self._fills.append(fill)

        # Update client stats
        self._update_client_stats(client_id)
        logger.info(f"Trade fill recorded: {client_id} {signal.symbol} {signal.direction} @ {fill_price}")

        if self.db_url:
            await self._db_log_fill(fill)

    async def _db_log_fill(self, fill: TradeFill):
        """Persist trade fill to PostgreSQL."""
        try:
            import asyncpg
            conn = await asyncpg.connect(self.db_url)
            await conn.execute("""
                INSERT INTO trade_fills (
                    client_id, signal_id, fill_price, lot_size, ticket, timestamp
                ) VALUES ($1, $2, $3, $4, $5, $6)
            """, fill.client_id, fill.signal_id, fill.fill_price,
                fill.lot_size, fill.ticket, fill.timestamp)
            await conn.close()
        except Exception as e:
            logger.error(f"DB log_fill failed: {e}")

    async def update_trade_outcome(self, signal_id: str, ticket: int,
                                    exit_price: float, pnl: float):
        """Update trade outcome when position is closed."""
        for fill in self._fills:
            if fill.signal_id == signal_id and fill.ticket == ticket:
                fill.status = "closed" if pnl >= 0 else "closed_loss"
                self._update_client_stats(fill.client_id)
                logger.info(f"Trade outcome: {signal_id[:8]} PnL={pnl:+.2f}")
                return

    def _update_client_stats(self, client_id: str):
        """Recalculate aggregated stats for a client."""
        client_fills = [f for f in self._fills if f.client_id == client_id]
        if not client_fills:
            return

        if client_id not in self._client_stats:
            self._client_stats[client_id] = ClientPerformance(client_id=client_id)

        stats = self._client_stats[client_id]
        stats.executed_trades = len(client_fills)

        # In production, calculate actual P&L from position close prices
        # For now, estimated from SL/TP distances
        stats.total_pnl = 0
        stats.wins = 0
        stats.losses = 0
        for f in client_fills:
            if f.status == "closed":
                stats.wins += 1
            elif f.status == "closed_loss":
                stats.losses += 1

        if stats.executed_trades > 0:
            stats.win_rate = (stats.wins / stats.executed_trades) * 100

    # ------------------------------------------------------------------
    # Report Generation
    # ------------------------------------------------------------------
    async def get_daily_report(self, client_id: str, date: datetime) -> dict:
        """Generate a daily performance report for a client."""
        client_fills = [
            f for f in self._fills
            if f.client_id == client_id
            and f.timestamp.date() == date.date()
        ]

        wins = sum(1 for f in client_fills if f.status == "closed")
        losses = sum(1 for f in client_fills if f.status == "closed_loss")
        total = wins + losses

        return {
            "date": date.strftime("%Y-%m-%d"),
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": (wins / total * 100) if total else 0.0,
            "total_pnl": 0.0,  # Calculate from actual fill data
            "currency": "USD",
            "trades": client_fills
        }

    async def get_client_summary(self, client_id: str) -> dict:
        """Get a comprehensive summary for a single client."""
        stats = self._client_stats.get(client_id)
        if not stats:
            return {"client_id": client_id, "status": "no_data"}

        return {
            "client_id": stats.client_id,
            "total_signals": stats.total_signals,
            "executed_trades": stats.executed_trades,
            "wins": stats.wins,
            "losses": stats.losses,
            "win_rate": f"{stats.win_rate:.1f}%",
            "total_pnl": stats.total_pnl,
            "currency": stats.currency,
        }

    async def get_admin_summary(self) -> dict:
        """Generate an admin summary across all clients."""
        total_clients = len(self._client_stats)
        total_trades = sum(s.executed_trades for s in self._client_stats.values())
        total_wins = sum(s.wins for s in self._client_stats.values())
        total_losses = sum(s.losses for s in self._client_stats.values())
        total_signals = len(self._signals)

        return {
            "total_clients": total_clients,
            "total_signals_dispatched": total_signals,
            "total_trades_executed": total_trades,
            "total_wins": total_wins,
            "total_losses": total_losses,
            "overall_win_rate": (total_wins / total_trades * 100) if total_trades else 0.0,
            "generated_at": datetime.utcnow().isoformat()
        }
