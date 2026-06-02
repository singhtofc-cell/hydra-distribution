# ============================================================================
# Hydra Signal Server — FastAPI Signal Distribution API
# ============================================================================
# Renamed from HERMES → Hydra for standalone copy-trade distribution
# Source: Qwen Architecture Proposal 2026-06-02 — Copy Trade / Signal Distribution
#
# Receives trading signals from the master trading system (HERMES), formats
# them as standardized JSON, and dispatches to all registered clients via
# Telegram Bot API. Supports multi-priority signals, lot sizing for USD/USC
# accounts, expiry, and risk controls.

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
import json
import uuid
import logging
import os
import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hydra.signal_server")

# ============================================================================
# Configuration
# ============================================================================
def load_config():
    config_path = os.getenv("HYDRA_CONFIG", "config.yaml")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    return {}

config = load_config()

app = FastAPI(
    title="Hydra Signal Distribution Server",
    description="Copy Trade / Signal Distribution API for MT5 client VPS accounts",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Data Models
# ============================================================================
class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    CLOSE_ALL = "CLOSE_ALL"
    MODIFY_SL = "MODIFY_SL"
    PARTIAL_CLOSE = "PARTIAL_CLOSE"
    CANCEL = "CANCEL"

class SignalPriority(str, Enum):
    NORMAL = "NORMAL"        # Grid Layer 1-3
    URGENT = "URGENT"        # Judas Swing, Sweep Trap
    EMERGENCY = "EMERGENCY"  # News kill-switch, Risk alert

class TradeSignal(BaseModel):
    """Standardised signal sent to all EA clients."""
    signal_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Signal UUID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    signal_type: SignalType
    priority: SignalPriority = SignalPriority.NORMAL
    symbol: str = Field(..., pattern=r"^[A-Z0-9\.]+$")
    direction: Optional[str] = None  # "BUY" or "SELL"
    entry_price: float = Field(..., gt=0)
    sl_price: float = Field(..., gt=0)
    tp_prices: List[float] = Field(default_factory=list)  # TP1, TP2, TP3
    lot_multiplier: float = Field(1.0, ge=0.1, le=10.0)  # For lot scaling
    risk_percent: float = Field(1.0, ge=0.1, le=5.0)     # % of portfolio
    max_lot_cap: float = Field(5.0, gt=0)                 # Max lot cap
    comment: str = ""                                       # e.g. "HYDRA_L2_FVG"
    expiry_minutes: int = Field(30, ge=1, le=1440)         # Expiry in minutes
    source: str = "HERMES"                                  # Strategy name
    grid_layer: Optional[int] = Field(None, ge=1, le=4)    # Grid layer

class SignalResponse(BaseModel):
    success: bool
    signal_id: str
    message: str
    dispatched_to: int = 0

class ClientInfo(BaseModel):
    """Client account information."""
    client_id: str
    telegram_chat_id: int
    account_number: str
    account_currency: str  # "USD" or "USC"
    lot_multiplier: float  # Lot multiplier from Master
    risk_percent: float    # Accepted risk %
    max_lot_cap: float     # Max lot cap
    status: str = "ACTIVE"  # ACTIVE, PAUSED, SUSPENDED
    subscribed_strategies: List[str] = ["SMC_GRID", "JUDAS_SWING", "ICT_SMC"]
    registered_at: datetime = Field(default_factory=datetime.utcnow)

class HealthResponse(BaseModel):
    status: str
    version: str
    uptime: str
    active_clients: int
    total_signals_dispatched: int

# ============================================================================
# In-Memory State (use PostgreSQL in production)
# ============================================================================
# Clients database
CLIENTS_DB: List[ClientInfo] = []
# Signal dispatch history
SIGNAL_HISTORY: List[dict] = []
# Server start time
START_TIME = datetime.utcnow()

# ============================================================================
# Signal Dispatch Endpoints
# ============================================================================
@app.post("/api/v1/signal/send", response_model=SignalResponse)
async def send_signal(signal: TradeSignal):
    """
    Receive a signal from the master trading system and dispatch
    to all eligible clients via Telegram Bot.
    """
    # 1. Validate signal
    if signal.signal_type not in (SignalType.BUY, SignalType.SELL):
        raise HTTPException(400, "Invalid signal type for new trade. Use BUY or SELL.")

    # 2. Format message for Telegram
    tg_message = format_signal_for_telegram(signal)

    # 3. Broadcast to all active subscribed clients
    dispatched = 0
    for client in CLIENTS_DB:
        if client.status == "ACTIVE" and signal.source in client.subscribed_strategies:
            try:
                await broadcast_to_client(client, signal, tg_message)
                dispatched += 1
            except Exception as e:
                logger.error(f"Failed to dispatch to {client.client_id}: {e}")

    # 4. Log to history
    entry = {
        "signal_id": signal.signal_id,
        "timestamp": signal.timestamp.isoformat(),
        "symbol": signal.symbol,
        "direction": signal.signal_type.value,
        "priority": signal.priority.value,
        "dispatched_to": dispatched,
        "source": signal.source
    }
    SIGNAL_HISTORY.append(entry)
    logger.info(f"Signal {signal.signal_id[:8]} dispatched to {dispatched} clients")

    return SignalResponse(
        success=True,
        signal_id=signal.signal_id,
        message=f"Signal dispatched to {dispatched} clients",
        dispatched_to=dispatched
    )

@app.post("/api/v1/signal/cancel/{signal_id}")
async def cancel_signal(signal_id: str):
    """Cancel a pending signal across all clients."""
    cancel_msg = {
        "action": "CANCEL",
        "signal_id": signal_id,
        "timestamp": datetime.utcnow().isoformat()
    }
    await broadcast_cancel(cancel_msg)
    logger.info(f"Signal {signal_id[:8]} cancelled across all clients")
    return {"success": True, "signal_id": signal_id}

@app.post("/api/v1/signal/batch", response_model=List[SignalResponse])
async def send_batch_signals(signals: List[TradeSignal]):
    """Send multiple signals in a single batch."""
    results = []
    for signal in signals:
        result = await send_signal(signal)
        results.append(result)
    return results

# ============================================================================
# Client Management Endpoints
# ============================================================================
@app.post("/api/v1/client/register")
async def register_client(client: ClientInfo):
    """Register a new client for signal distribution."""
    # Check if client already exists
    for existing in CLIENTS_DB:
        if existing.client_id == client.client_id:
            raise HTTPException(400, f"Client {client.client_id} already registered")
        if existing.telegram_chat_id == client.telegram_chat_id:
            raise HTTPException(400, f"Telegram chat {client.telegram_chat_id} already registered")

    CLIENTS_DB.append(client)
    logger.info(f"New client registered: {client.client_id} ({client.account_currency})")
    return {
        "success": True,
        "client_id": client.client_id,
        "message": f"Client {client.client_id} registered successfully"
    }

@app.get("/api/v1/client/list")
async def list_clients(status: Optional[str] = None):
    """List all registered clients, optionally filtered by status."""
    if status:
        return [c for c in CLIENTS_DB if c.status == status]
    return CLIENTS_DB

@app.patch("/api/v1/client/{client_id}/status")
async def update_client_status(client_id: str, status: str):
    """Update client subscription status."""
    if status not in ("ACTIVE", "PAUSED", "SUSPENDED"):
        raise HTTPException(400, f"Invalid status: {status}")

    for client in CLIENTS_DB:
        if client.client_id == client_id:
            client.status = status
            logger.info(f"Client {client_id} status → {status}")
            return {"success": True, "client_id": client_id, "status": status}
    raise HTTPException(404, f"Client {client_id} not found")

@app.delete("/api/v1/client/{client_id}")
async def remove_client(client_id: str):
    """Remove a client from the distribution list."""
    for i, client in enumerate(CLIENTS_DB):
        if client.client_id == client_id:
            CLIENTS_DB.pop(i)
            logger.info(f"Client {client_id} removed")
            return {"success": True, "client_id": client_id}
    raise HTTPException(404, f"Client {client_id} not found")

# ============================================================================
# Status & Health Endpoints
# ============================================================================
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """System health endpoint."""
    uptime_seconds = (datetime.utcnow() - START_TIME).total_seconds()
    hours, remainder = divmod(int(uptime_seconds), 3600)
    minutes, seconds = divmod(remainder, 60)

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        uptime=f"{hours}h {minutes}m {seconds}s",
        active_clients=sum(1 for c in CLIENTS_DB if c.status == "ACTIVE"),
        total_signals_dispatched=len(SIGNAL_HISTORY)
    )

@app.get("/api/v1/stats")
async def get_stats():
    """Get signal distribution statistics."""
    active = sum(1 for c in CLIENTS_DB if c.status == "ACTIVE")
    paused = sum(1 for c in CLIENTS_DB if c.status == "PAUSED")
    total = len(CLIENTS_DB)

    usd_clients = sum(1 for c in CLIENTS_DB if c.account_currency == "USD")
    usc_clients = sum(1 for c in CLIENTS_DB if c.account_currency == "USC")

    return {
        "total_clients": total,
        "active_clients": active,
        "paused_clients": paused,
        "total_signals": len(SIGNAL_HISTORY),
        "clients_by_currency": {
            "USD": usd_clients,
            "USC": usc_clients
        },
        "uptime_seconds": int((datetime.utcnow() - START_TIME).total_seconds())
    }

# ============================================================================
# Signal Formatting & Dispatch Helpers
# ============================================================================
def format_signal_for_telegram(signal: TradeSignal) -> str:
    """Format trading signal as a Telegram HTML message
    readable by both humans and the MQL5 EA parser."""

    emoji = "🟢" if signal.signal_type == SignalType.BUY else "🔴"
    priority_emoji = {
        SignalPriority.NORMAL: "⚪",
        SignalPriority.URGENT: "🟡",
        SignalPriority.EMERGENCY: "🚨"
    }[signal.priority]

    # TP formatting
    tp_str = " | ".join([f"TP{i+1}: {tp:.5f}" for i, tp in enumerate(signal.tp_prices)]) if signal.tp_prices else "Trailing"

    message = f"""
{priority_emoji} <b>HYDRA SIGNAL #{signal.signal_id[:8]}</b> {priority_emoji}
{emoji} <b>{signal.signal_type.value}</b> {signal.symbol}
━━━━━━━━━━━━━━━━━━━━━━━
📍 Entry: <code>{signal.entry_price:.5f}</code>
🛡️ SL: <code>{signal.sl_price:.5f}</code>
💰 {tp_str}
⚖️ Risk: {signal.risk_percent}% | Lot Mult: {signal.lot_multiplier}x
🏷️ Source: {signal.source} | Layer: {signal.grid_layer or 'N/A'}
⏱️ Expires in: {signal.expiry_minutes} min
<blockquote expandable>
{json.dumps(signal.model_dump(mode='json'), indent=None)}
</blockquote>
<i>Auto-execute enabled. Reply /stop to pause.</i>
"""
    return message.strip()


async def broadcast_to_client(client: ClientInfo, signal: TradeSignal, message: str):
    """Send signal to a client via Telegram Bot API."""
    import aiohttp

    bot_token = os.getenv("HYDRA_TELEGRAM_BOT_TOKEN", config.get("telegram", {}).get("bot_token", ""))
    if not bot_token:
        logger.warning("HYDRA_TELEGRAM_BOT_TOKEN not set — skipping broadcast")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    payload = {
        "chat_id": client.telegram_chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                logger.error(f"Telegram send failed for {client.client_id}: {resp.status} - {error_text}")
            else:
                logger.debug(f"Signal sent to {client.client_id} (chat {client.telegram_chat_id})")


async def broadcast_cancel(cancel_msg: dict):
    """Broadcast a cancellation message to all active clients."""
    import aiohttp

    bot_token = os.getenv("HYDRA_TELEGRAM_BOT_TOKEN", config.get("telegram", {}).get("bot_token", ""))
    if not bot_token:
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    text = f"🚫 <b>CANCELLED</b>: Signal {cancel_msg['signal_id'][:8]}\n⏱️ {cancel_msg['timestamp']}"

    for client in CLIENTS_DB:
        if client.status == "ACTIVE":
            payload = {
                "chat_id": client.telegram_chat_id,
                "text": text,
                "parse_mode": "HTML"
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status != 200:
                        logger.error(f"Cancel broadcast failed for {client.client_id}")


# ============================================================================
# Startup / Shutdown
# ============================================================================
@app.on_event("startup")
async def startup():
    logger.info("=" * 60)
    logger.info("🪬 Hydra Signal Distribution Server starting up...")
    logger.info(f"Version: 1.0.0")
    logger.info(f"Active clients at start: {len(CLIENTS_DB)}")
    logger.info("=" * 60)

@app.on_event("shutdown")
async def shutdown():
    logger.info("🪬 Hydra Signal Distribution Server shutting down...")

# ============================================================================
# Entry point
# ============================================================================
if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HYDRA_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("HYDRA_SERVER_PORT", "8788"))
    uvicorn.run(app, host=host, port=port, log_level="info")
