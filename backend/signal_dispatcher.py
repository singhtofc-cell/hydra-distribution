# ============================================================================
# Hydra Signal Dispatcher — Python Telegram Bot Signal Sender
# ============================================================================
# Renamed from HERMES → Hydra for standalone copy-trade distribution
# Source: Qwen Architecture Proposal 2026-06-02 — Client EA + Telegram
#
# Sends trading signals to all registered client EAs via Telegram Bot API.
# Used by the Master to broadcast signals to every connected client.
# Each client's EA polls Telegram and executes trades on their local MT5.

import json
import logging
import os
import time
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger("hydra.signal_dispatcher")


class HydraSignalDispatcher:
    """Dispatch trading signals to all registered client EAs via Telegram.

    Clients install HydraClientEA.mq5 on their local MT5 (same machine as
    Telegram Desktop). The EA polls Telegram, receives signals, and
    executes trades with the client's configured risk %.

    Usage:
        dispatcher = HydraSignalDispatcher("YOUR_BOT_TOKEN")
        dispatcher.register_client("123456789", "12345678", 1.0)
        dispatcher.send_signal({
            "symbol": "XAUUSD",
            "direction": "BUY",
            "entry_price": 2350.50,
            "sl_price": 2330.00,
            "tp1": 2370.00,
            "tp2": 2390.00,
            "tp3": 2420.00,
            "risk_percent": 1.0,
            "expiry_minutes": 30
        })
    """

    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.registered_clients: List[Dict] = []
        self._signal_counter = 0

    def register_client(self, chat_id: str, account_number: str,
                        risk_percent: float = 1.0) -> Dict:
        """Register a new client for signal distribution."""
        client = {
            "chat_id": chat_id,
            "account_number": account_number,
            "risk_percent": risk_percent,
            "status": "ACTIVE",
            "registered_at": datetime.utcnow().isoformat()
        }
        self.registered_clients.append(client)
        logger.info(f"✅ Client registered: {account_number} (chat: {chat_id})")
        return client

    def unregister_client(self, chat_id: str) -> bool:
        """Remove a client from signal distribution."""
        for i, c in enumerate(self.registered_clients):
            if c["chat_id"] == chat_id:
                self.registered_clients.pop(i)
                logger.info(f"❌ Client unregistered: {c['account_number']}")
                return True
        return False

    def pause_client(self, chat_id: str) -> bool:
        """Pause signal delivery to a client."""
        for c in self.registered_clients:
            if c["chat_id"] == chat_id:
                c["status"] = "PAUSED"
                return True
        return False

    def resume_client(self, chat_id: str) -> bool:
        """Resume signal delivery to a client."""
        for c in self.registered_clients:
            if c["chat_id"] == chat_id:
                c["status"] = "ACTIVE"
                return True
        return False

    def send_signal(self, signal: Dict) -> Dict:
        """Send a trading signal to all active clients.

        Signal format:
        {
            "symbol": str,
            "direction": "BUY" | "SELL",
            "entry_price": float,
            "sl_price": float,
            "tp1": float,
            "tp2": float (optional),
            "tp3": float (optional),
            "risk_percent": float (default 1.0),
            "expiry_minutes": int (default 30)
        }
        """
        self._signal_counter += 1
        signal_id = f"{signal['direction']}_{signal['symbol']}_{self._signal_counter:04d}"
        now = int(time.time())

        results = {"total": 0, "success": 0, "failed": 0, "details": []}

        for client in self.registered_clients:
            if client.get("status") != "ACTIVE":
                continue

            chat_id = client["chat_id"]

            # Build signal text for EA parsing
            signal_text = (
                f"hydra_signal_{signal['direction']}_"
                f"{signal_id}_{signal['symbol']}_"
                f"{signal['entry_price']}_{signal['sl_price']}_"
                f"{signal.get('tp1', 0)}_{signal.get('tp2', 0)}_{signal.get('tp3', 0)}_"
                f"{signal.get('risk_percent', 1.0)}_{signal.get('expiry_minutes', 30)}"
            )

            # Send raw signal text
            ok1 = self._send_message(chat_id, signal_text)

            # Send human-readable notification
            emoji = "🟢" if signal["direction"] == "BUY" else "🔴"
            message = (
                f"{emoji} <b>สัญญาณเทรดใหม่</b>\n\n"
                f"{emoji} {signal['direction']} {signal['symbol']}\n"
                f"📍 Entry: {signal['entry_price']}\n"
                f"🛡️ SL: {signal['sl_price']}\n"
                f"💰 TP1: {signal.get('tp1', '-')}\n"
                f"💰 TP2: {signal.get('tp2', '-')}\n"
                f"💰 TP3: {signal.get('tp3', '-')}\n"
                f"⚖️ Risk: {signal.get('risk_percent', 1.0)}%"
            )
            ok2 = self._send_message(chat_id, message, parse_mode="HTML")

            results["total"] += 1
            if ok1 and ok2:
                results["success"] += 1
                results["details"].append({"chat_id": chat_id, "status": "sent"})
            else:
                results["failed"] += 1
                results["details"].append({"chat_id": chat_id, "status": "failed"})

            logger.info(f"📤 Signal {signal_id} → {client['account_number']} "
                       f"{'✅' if ok1 and ok2 else '❌'}")

        results["signal_id"] = signal_id
        return results

    def broadcast_message(self, message: str, parse_mode: str = ""):
        """Broadcast a text message to all active clients."""
        for client in self.registered_clients:
            if client["status"] == "ACTIVE":
                self._send_message(client["chat_id"], message, parse_mode)

    def _send_message(self, chat_id: str, text: str,
                      parse_mode: str = "") -> bool:
        """Send a message to a Telegram chat."""
        import requests

        url = f"{self.base_url}/sendMessage"
        payload = {"chat_id": chat_id, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode

        try:
            resp = requests.post(url, json=payload, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return False

    def list_clients(self) -> List[Dict]:
        """Return list of all registered clients."""
        return self.registered_clients

    def get_stats(self) -> Dict:
        """Return dispatch statistics."""
        active = sum(1 for c in self.registered_clients if c["status"] == "ACTIVE")
        paused = sum(1 for c in self.registered_clients if c["status"] == "PAUSED")
        return {
            "total_clients": len(self.registered_clients),
            "active_clients": active,
            "paused_clients": paused,
            "signals_sent": self._signal_counter
        }


# ============================================================================
# Example Usage
# ============================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Initialize dispatcher
    bot_token = os.getenv("HYDRA_TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN")
    dispatcher = HydraSignalDispatcher(bot_token)

    # Register test clients
    dispatcher.register_client("123456789", "10000001", 1.0)
    dispatcher.register_client("987654321", "20000001", 2.0)

    # Send test signal
    signal = {
        "symbol": "XAUUSD",
        "direction": "BUY",
        "entry_price": 2350.50,
        "sl_price": 2330.00,
        "tp1": 2370.00,
        "tp2": 2390.00,
        "tp3": 2420.00,
        "risk_percent": 1.0,
        "expiry_minutes": 30
    }

    result = dispatcher.send_signal(signal)
    print(f"Signal sent: {json.dumps(result, indent=2)}")
    print(f"Stats: {json.dumps(dispatcher.get_stats(), indent=2)}")
