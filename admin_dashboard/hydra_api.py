# ============================================================================
# Hydra API Client — Connects Dashboard to Hydra Signal Server
# ============================================================================
# Provides real API calls to the Hydra Signal Server endpoints.
# Falls back to mock data if the server is unreachable.

import os
import json
import yaml
import logging
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from dataclasses import dataclass

logger = logging.getLogger("hydra.api_client")


# ============================================================================
# Data Classes
# ============================================================================
@dataclass
class ServerHealth:
    status: str
    version: str
    uptime: str
    active_clients: int
    total_signals_dispatched: int

@dataclass
class SystemStats:
    total_clients: int
    active_clients: int
    paused_clients: int
    total_signals: int
    clients_by_currency: dict
    uptime_seconds: int

@dataclass
class TradeSignal:
    signal_id: str
    timestamp: str
    symbol: str
    signal_type: str
    direction: str
    priority: str
    entry_price: float
    sl_price: float
    tp_prices: list
    source: str
    dispatched_to: int

@dataclass
class ClientInfo:
    client_id: str
    telegram_chat_id: int
    account_number: str
    account_currency: str
    lot_multiplier: float
    risk_percent: float
    max_lot_cap: float
    status: str
    subscribed_strategies: list
    registered_at: Optional[str] = None


# ============================================================================
# Hydra API Client
# ============================================================================
class HydraAPIClient:
    """Connect to Hydra Signal Server for real data.

    If the server is unreachable, falls back to generated mock data
    so the dashboard is always usable during development.
    """

    def __init__(self, base_url: Optional[str] = None):
        config = self._load_config()
        self.base_url = (base_url or
                         os.getenv("HYDRA_SERVER_URL", "") or
                         f"http://{config.get('server', {}).get('host', '127.0.0.1')}:{config.get('server', {}).get('port', 8788)}")
        self._connected = False
        self._last_check = None

    @staticmethod
    def _load_config() -> dict:
        config_path = os.getenv("HYDRA_CONFIG", "config.yaml")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                return yaml.safe_load(f) or {}
        return {}

    # ------------------------------------------------------------------
    # Connection Management
    # ------------------------------------------------------------------
    def _request(self, method: str, path: str, data: Optional[dict] = None) -> Optional[dict]:
        """Make an HTTP request to the Hydra Signal Server."""
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        try:
            if data and method == "POST":
                body = json.dumps(data).encode()
                req = urllib.request.Request(url, data=body,
                                              headers={"Content-Type": "application/json"},
                                              method="POST")
            else:
                req = urllib.request.Request(url, method=method)

            with urllib.request.urlopen(req, timeout=5) as resp:
                return json.loads(resp.read())
        except (urllib.error.URLError, urllib.error.HTTPError, ConnectionRefusedError, TimeoutError) as e:
            logger.debug(f"API request failed: {url} — {e}")
            return None
        except json.JSONDecodeError:
            return None

    # ------------------------------------------------------------------
    # Health & Stats
    # ------------------------------------------------------------------
    def check_health(self) -> Optional[ServerHealth]:
        """GET /health — Returns server health status."""
        result = self._request("GET", "/health")
        if result:
            self._connected = True
            return ServerHealth(**result)
        self._connected = False
        return None

    def get_stats(self) -> Optional[SystemStats]:
        """GET /api/v1/stats — Returns system statistics."""
        result = self._request("GET", "/api/v1/stats")
        if result:
            return SystemStats(**result)
        return None

    def is_connected(self) -> bool:
        """Check if the server is reachable (cached 30s)."""
        now = datetime.utcnow()
        if self._last_check and (now - self._last_check).seconds < 30:
            return self._connected
        self._last_check = now
        health = self.check_health()
        return self._connected

    # ------------------------------------------------------------------
    # Clients
    # ------------------------------------------------------------------
    def list_clients(self, status: Optional[str] = None) -> List[ClientInfo]:
        """GET /api/v1/client/list — Returns all clients."""
        path = "/api/v1/client/list"
        if status:
            path += f"?status={status}"
        result = self._request("GET", path)
        if result is not None:
            # The API returns a list of dicts
            if isinstance(result, list):
                return [ClientInfo(**c) for c in result]
        return []

    def register_client(self, client: dict) -> tuple[bool, str]:
        """POST /api/v1/client/register — Register a new client."""
        result = self._request("POST", "/api/v1/client/register", data=client)
        if result:
            return (True, result.get("message", "✅ Client registered"))
        return (False, "❌ Failed to register — server unreachable")

    def update_client_status(self, client_id: str, status: str) -> tuple[bool, str]:
        """PATCH /api/v1/client/{id}/status — Update client status."""
        result = self._request("PATCH", f"/api/v1/client/{client_id}/status", data={"status": status})
        if result and result.get("success"):
            return (True, f"✅ {client_id} → {status}")
        return (False, "❌ Failed to update status")

    def remove_client(self, client_id: str) -> tuple[bool, str]:
        """DELETE /api/v1/client/{id} — Remove a client."""
        result = self._request("DELETE", f"/api/v1/client/{client_id}")
        if result and result.get("success"):
            return (True, f"✅ {client_id} removed")
        return (False, "❌ Failed to remove client")

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------
    def send_signal(self, signal: dict) -> tuple[bool, dict, str]:
        """POST /api/v1/signal/send — Send a trading signal."""
        result = self._request("POST", "/api/v1/signal/send", data=signal)
        if result and result.get("success"):
            return (True, result, result.get("message", "✅ Signal sent"))
        return (False, result or {}, "❌ Failed to send signal")

    def cancel_signal(self, signal_id: str) -> tuple[bool, str]:
        """POST /api/v1/signal/cancel/{id} — Cancel a signal."""
        result = self._request("POST", f"/api/v1/signal/cancel/{signal_id}")
        if result and result.get("success"):
            return (True, f"✅ Signal {signal_id[:8]} cancelled")
        return (False, "❌ Failed to cancel signal")

    # ------------------------------------------------------------------
    # Mock Data Generator (for development without server)
    # ------------------------------------------------------------------
    @staticmethod
    def generate_mock_stats() -> dict:
        return {
            "total_clients": 12,
            "active_clients": 8,
            "paused_clients": 3,
            "suspended_clients": 1,
            "total_signals": 247,
            "signals_today": 18,
            "clients_by_currency": {"USD": 7, "USC": 5},
            "uptime_seconds": 86400,
            "todays_pnl": 52.30,
            "total_pnl": 847.50,
            "win_rate": 67.8,
            "avg_rr": "1:2.4",
        }

    @staticmethod
    def generate_mock_clients() -> list:
        return [
            {"client_id": f"CLIENT_{i:03d}",
             "status": "ACTIVE" if i < 8 else ("PAUSED" if i < 11 else "SUSPENDED"),
             "account_currency": "USD" if i % 2 == 0 else "USC",
             "account_number": f"{1000000 + i}",
             "lot_multiplier": 1.0 if i % 2 == 0 else 100.0,
             "risk_percent": 1.0, "max_lot_cap": 5.0,
             "telegram_chat_id": 10000000 + i,
             "subscribed_strategies": ["SMC_GRID", "JUDAS_SWING"],
             "registered_at": (datetime.utcnow() - timedelta(days=i*7)).isoformat()}
            for i in range(12)
        ]

    @staticmethod
    def generate_mock_signals(count: int = 50) -> list:
        symbols = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"]
        sources = ["SMC_GRID", "JUDAS_SWING", "ICT_SMC"]
        return [
            {"signal_id": f"sig_{i:04d}",
             "timestamp": (datetime.utcnow() - timedelta(hours=i*2)).isoformat(),
             "symbol": symbols[i % len(symbols)],
             "signal_type": "BUY" if i % 2 == 0 else "SELL",
             "direction": "BUY" if i % 2 == 0 else "SELL",
             "priority": ["NORMAL", "URGENT", "EMERGENCY"][i % 3],
             "entry_price": round(1500.0 + (i * 10.5), 2),
             "sl_price": round(1480.0 + (i * 10.5), 2),
             "tp_prices": [round(1520.0 + (i * 10.5), 2), round(1540.0 + (i * 10.5), 2)],
             "dispatched_to": [5, 8, 12][i % 3],
             "source": sources[i % len(sources)],
             "expiry_minutes": 30}
            for i in range(count)
        ]

    @staticmethod
    def generate_mock_performance() -> dict:
        return {
            "total_trades": 142,
            "today_trades": 12,
            "win_rate": 67.8,
            "win_rate_change": "+2.1",
            "total_pnl": 847.50,
            "today_pnl": 52.30,
            "avg_rr": "1:2.4",
            "max_drawdown": 8.5,
            "daily_pnl": [12.5, -8.3, 22.1, 15.0, -3.2, 30.5, 18.7, -5.5, 10.2, 25.8, -12.1, 8.9, 35.2, 5.0],
        }
