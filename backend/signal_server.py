     1|# ============================================================================
     2|# Hydra Signal Server — FastAPI Signal Distribution API
     3|# ============================================================================
     4|# Renamed from HERMES → Hydra for standalone copy-trade distribution
     5|# Source: Qwen Architecture Proposal 2026-06-02 — Copy Trade / Signal Distribution
     6|#
     7|# Receives trading signals from the master trading system (HERMES), formats
     8|# them as standardized JSON, and dispatches to all registered clients via
     9|# Telegram Bot API. Supports multi-priority signals, lot sizing for USD/USC
    10|# accounts, expiry, and risk controls.
    11|
    12|from fastapi import FastAPI, HTTPException, Depends
    13|from fastapi.middleware.cors import CORSMiddleware
    14|from pydantic import BaseModel, Field
    15|from typing import Optional, List
    16|from datetime import datetime
    17|from enum import Enum
    18|import json
    19|import uuid
    20|import logging
    21|import os
    22|import yaml
    23|
    24|logging.basicConfig(level=logging.INFO)
    25|logger = logging.getLogger("hydra.signal_server")
    26|
    27|# ============================================================================
    28|# Configuration
    29|# ============================================================================
    30|def load_config():
    31|    config_path = os.getenv("HYDRA_CONFIG", "config.yaml")
    32|    if os.path.exists(config_path):
    33|        with open(config_path, "r") as f:
    34|            return yaml.safe_load(f)
    35|    return {}
    36|
    37|config = load_config()
    38|
    39|app = FastAPI(
    40|    title="Hydra Signal Distribution Server",
    41|    description="Copy Trade / Signal Distribution API for MT5 client VPS accounts",
    42|    version="1.0.0"
    43|)
    44|
    45|app.add_middleware(
    46|    CORSMiddleware,
    47|    allow_origins=["*"],
    48|    allow_credentials=True,
    49|    allow_methods=["*"],
    50|    allow_headers=["*"],
    51|)
    52|
    53|# ============================================================================
    54|# Data Models
    55|# ============================================================================
    56|class SignalType(str, Enum):
    57|    BUY = "BUY"
    58|    SELL = "SELL"
    59|    CLOSE_ALL = "CLOSE_ALL"
    60|    MODIFY_SL = "MODIFY_SL"
    61|    PARTIAL_CLOSE = "PARTIAL_CLOSE"
    62|    CANCEL = "CANCEL"
    63|
    64|class SignalPriority(str, Enum):
    65|    NORMAL = "NORMAL"        # Grid Layer 1-3
    66|    URGENT = "URGENT"        # Judas Swing, Sweep Trap
    67|    EMERGENCY = "EMERGENCY"  # News kill-switch, Risk alert
    68|
    69|class TradeSignal(BaseModel):
    70|    """Standardised signal sent to all EA clients."""
    71|    signal_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Signal UUID")
    72|    timestamp: datetime = Field(default_factory=datetime.utcnow)
    73|    signal_type: SignalType
    74|    priority: SignalPriority = SignalPriority.NORMAL
    75|    symbol: str = Field(..., pattern=r"^[A-Z0-9\.]+$")
    76|    direction: Optional[str] = None  # "BUY" or "SELL"
    77|    entry_price: float = Field(..., gt=0)
    78|    sl_price: float = Field(..., gt=0)
    79|    tp_prices: List[float] = Field(default_factory=list)  # TP1, TP2, TP3
    80|    lot_multiplier: float = Field(1.0, ge=0.1, le=10.0)  # For lot scaling
    81|    risk_percent: float = Field(1.0, ge=0.1, le=5.0)     # % of portfolio
    82|    max_lot_cap: float = Field(5.0, gt=0)                 # Max lot cap
    83|    comment: str = ""                                       # e.g. "HYDRA_L2_FVG"
    84|    expiry_minutes: int = Field(30, ge=1, le=1440)         # Expiry in minutes
    85|    source: str = "HERMES"                                  # Strategy name
    86|    grid_layer: Optional[int] = Field(None, ge=1, le=4)    # Grid layer
    87|
    88|class SignalResponse(BaseModel):
    89|    success: bool
    90|    signal_id: str
    91|    message: str
    92|    dispatched_to: int = 0
    93|
    94|class ClientInfo(BaseModel):
    95|    """Client account information."""
    96|    client_id: str
    97|    telegram_chat_id: int
    98|    account_number: str
    99|    account_currency: str  # "USD" or "USC"
   100|    lot_multiplier: float  # Lot multiplier from Master
   101|    risk_percent: float    # Accepted risk %
   102|    max_lot_cap: float     # Max lot cap
   103|    status: str = "ACTIVE"  # ACTIVE, PAUSED, SUSPENDED
   104|    subscribed_strategies: List[str] = ["SMC_GRID", "JUDAS_SWING", "ICT_SMC"]
   105|    registered_at: datetime = Field(default_factory=datetime.utcnow)
   106|
   107|class HealthResponse(BaseModel):
   108|    status: str
   109|    version: str
   110|    uptime: str
   111|    active_clients: int
   112|    total_signals_dispatched: int
   113|
   114|# ============================================================================
   115|# In-Memory State (use PostgreSQL in production)
   116|# ============================================================================
   117|# Clients database
   118|CLIENTS_DB: List[ClientInfo] = []
   119|# Signal dispatch history
   120|SIGNAL_HISTORY: List[dict] = []
   121|# Server start time
   122|START_TIME = datetime.utcnow()
   123|
   124|# ============================================================================
   125|# Signal Dispatch Endpoints
   126|# ============================================================================
   127|@app.post("/api/v1/signal/send", response_model=SignalResponse)
   128|async def send_signal(signal: TradeSignal):
   129|    """
   130|    Receive a signal from the master trading system and dispatch
   131|    to all eligible clients via Telegram Bot.
   132|    """
   133|    # 1. Validate signal
   134|    if signal.signal_type not in (SignalType.BUY, SignalType.SELL):
   135|        raise HTTPException(400, "Invalid signal type for new trade. Use BUY or SELL.")
   136|
   137|    # 2. Format message for Telegram
   138|    tg_message = format_signal_for_telegram(signal)
   139|
   140|    # 3. Broadcast to all active subscribed clients
   141|    dispatched = 0
   142|    for client in CLIENTS_DB:
   143|        if client.status == "ACTIVE" and signal.source in client.subscribed_strategies:
   144|            try:
   145|                await broadcast_to_client(client, signal, tg_message)
   146|                dispatched += 1
   147|            except Exception as e:
   148|                logger.error(f"Failed to dispatch to {client.client_id}: {e}")
   149|
   150|    # 4. Log to history
   151|    entry = {
   152|        "signal_id": signal.signal_id,
   153|        "timestamp": signal.timestamp.isoformat(),
   154|        "symbol": signal.symbol,
   155|        "direction": signal.signal_type.value,
   156|        "priority": signal.priority.value,
   157|        "dispatched_to": dispatched,
   158|        "source": signal.source
   159|    }
   160|    SIGNAL_HISTORY.append(entry)
   161|    logger.info(f"Signal {signal.signal_id[:8]} dispatched to {dispatched} clients")
   162|
   163|    return SignalResponse(
   164|        success=True,
   165|        signal_id=signal.signal_id,
   166|        message=f"Signal dispatched to {dispatched} clients",
   167|        dispatched_to=dispatched
   168|    )
   169|
   170|@app.post("/api/v1/signal/cancel/{signal_id}")
   171|async def cancel_signal(signal_id: str):
   172|    """Cancel a pending signal across all clients."""
   173|    cancel_msg = {
   174|        "action": "CANCEL",
   175|        "signal_id": signal_id,
   176|        "timestamp": datetime.utcnow().isoformat()
   177|    }
   178|    await broadcast_cancel(cancel_msg)
   179|    logger.info(f"Signal {signal_id[:8]} cancelled across all clients")
   180|    return {"success": True, "signal_id": signal_id}
   181|
   182|@app.post("/api/v1/signal/batch", response_model=List[SignalResponse])
   183|async def send_batch_signals(signals: List[TradeSignal]):
   184|    """Send multiple signals in a single batch."""
   185|    results = []
   186|    for signal in signals:
   187|        result = await send_signal(signal)
   188|        results.append(result)
   189|    return results
   190|
   191|# ============================================================================
   192|# Client Management Endpoints
   193|# ============================================================================
   194|@app.post("/api/v1/client/register")
   195|async def register_client(client: ClientInfo):
   196|    """Register a new client for signal distribution."""
   197|    # Check if client already exists
   198|    for existing in CLIENTS_DB:
   199|        if existing.client_id == client.client_id:
   200|            raise HTTPException(400, f"Client {client.client_id} already registered")
   201|        if existing.telegram_chat_id == client.telegram_chat_id:
   202|            raise HTTPException(400, f"Telegram chat {client.telegram_chat_id} already registered")
   203|
   204|    CLIENTS_DB.append(client)
   205|    logger.info(f"New client registered: {client.client_id} ({client.account_currency})")
   206|    return {
   207|        "success": True,
   208|        "client_id": client.client_id,
   209|        "message": f"Client {client.client_id} registered successfully"
   210|    }
   211|
   212|@app.get("/api/v1/client/list")
   213|async def list_clients(status: Optional[str] = None):
   214|    """List all registered clients, optionally filtered by status."""
   215|    if status:
   216|        return [c for c in CLIENTS_DB if c.status == status]
   217|    return CLIENTS_DB
   218|
   219|@app.patch("/api/v1/client/{client_id}/status")
   220|async def update_client_status(client_id: str, status: str):
   221|    """Update client subscription status."""
   222|    if status not in ("ACTIVE", "PAUSED", "SUSPENDED"):
   223|        raise HTTPException(400, f"Invalid status: {status}")
   224|
   225|    for client in CLIENTS_DB:
   226|        if client.client_id == client_id:
   227|            client.status = status
   228|            logger.info(f"Client {client_id} status → {status}")
   229|            return {"success": True, "client_id": client_id, "status": status}
   230|    raise HTTPException(404, f"Client {client_id} not found")
   231|
   232|@app.delete("/api/v1/client/{client_id}")
   233|async def remove_client(client_id: str):
   234|    """Remove a client from the distribution list."""
   235|    for i, client in enumerate(CLIENTS_DB):
   236|        if client.client_id == client_id:
   237|            CLIENTS_DB.pop(i)
   238|            logger.info(f"Client {client_id} removed")
   239|            return {"success": True, "client_id": client_id}
   240|    raise HTTPException(404, f"Client {client_id} not found")
   241|
   242|# ============================================================================
   243|# Status & Health Endpoints
   244|# ============================================================================
   245|@app.get("/health", response_model=HealthResponse)
   246|async def health_check():
   247|    """System health endpoint."""
   248|    uptime_seconds = (datetime.utcnow() - START_TIME).total_seconds()
   249|    hours, remainder = divmod(int(uptime_seconds), 3600)
   250|    minutes, seconds = divmod(remainder, 60)
   251|
   252|    return HealthResponse(
   253|        status="healthy",
   254|        version="1.0.0",
   255|        uptime=f"{hours}h {minutes}m {seconds}s",
   256|        active_clients=sum(1 for c in CLIENTS_DB if c.status == "ACTIVE"),
   257|        total_signals_dispatched=len(SIGNAL_HISTORY)
   258|    )
   259|
   260|@app.get("/api/v1/stats")
   261|async def get_stats():
   262|    """Get signal distribution statistics."""
   263|    active = sum(1 for c in CLIENTS_DB if c.status == "ACTIVE")
   264|    paused = sum(1 for c in CLIENTS_DB if c.status == "PAUSED")
   265|    total = len(CLIENTS_DB)
   266|
   267|    usd_clients = sum(1 for c in CLIENTS_DB if c.account_currency == "USD")
   268|    usc_clients = sum(1 for c in CLIENTS_DB if c.account_currency == "USC")
   269|
   270|    return {
   271|        "total_clients": total,
   272|        "active_clients": active,
   273|        "paused_clients": paused,
   274|        "total_signals": len(SIGNAL_HISTORY),
   275|        "clients_by_currency": {
   276|            "USD": usd_clients,
   277|            "USC": usc_clients
   278|        },
   279|        "uptime_seconds": int((datetime.utcnow() - START_TIME).total_seconds())
   280|    }
   281|
   282|# ============================================================================
   283|# Signal Formatting & Dispatch Helpers
   284|# ============================================================================
   285|def format_signal_for_telegram(signal: TradeSignal) -> str:
   286|    """Format trading signal as a Telegram HTML message
   287|    readable by both humans and the MQL5 EA parser."""
   288|
   289|    emoji = "🟢" if signal.signal_type == SignalType.BUY else "🔴"
   290|    priority_emoji = {
   291|        SignalPriority.NORMAL: "⚪",
   292|        SignalPriority.URGENT: "🟡",
   293|        SignalPriority.EMERGENCY: "🚨"
   294|    }[signal.priority]
   295|
   296|    # TP formatting
   297|    tp_str = " | ".join([f"TP{i+1}: {tp:.5f}" for i, tp in enumerate(signal.tp_prices)]) if signal.tp_prices else "Trailing"
   298|
   299|    message = f"""
   300|{priority_emoji} <b>HYDRA SIGNAL #{signal.signal_id[:8]}</b> {priority_emoji}
   301|{emoji} <b>{signal.signal_type.value}</b> {signal.symbol}
   302|━━━━━━━━━━━━━━━━━━━━━━━
   303|📍 Entry: <code>{signal.entry_price:.5f}</code>
   304|🛡️ SL: <code>{signal.sl_price:.5f}</code>
   305|💰 {tp_str}
   306|⚖️ Risk: {signal.risk_percent}% | Lot Mult: {signal.lot_multiplier}x
   307|🏷️ Source: {signal.source} | Layer: {signal.grid_layer or 'N/A'}
   308|⏱️ Expires in: {signal.expiry_minutes} min
   309|<blockquote expandable>
   310|{json.dumps(signal.model_dump(mode='json'), indent=None)}
   311|</blockquote>
   312|<i>Auto-execute enabled. Reply /stop to pause.</i>
   313|"""
   314|    return message.strip()
   315|
   316|
   317|async def broadcast_to_client(client: ClientInfo, signal: TradeSignal, message: str):
   318|    """Send signal to a client via Telegram Bot API."""
   319|    import aiohttp
   320|
   321|    bot_token = os.getenv("HYDRA_TELEGRAM_BOT_TOKEN", config.get("telegram", {}).get("bot_token", ""))
   322|    if not bot_token:
   323|        logger.warning("HYDRA_TELEGRAM_BOT_TOKEN not set — skipping broadcast")
   324|        return
   325|
   326|    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
   327|
   328|    payload = {
   329|        "chat_id": client.telegram_chat_id,
   330|        "text": message,
   331|        "parse_mode": "HTML",
   332|        "disable_web_page_preview": True
   333|    }
   334|
   335|    async with aiohttp.ClientSession() as session:
   336|        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
   337|            if resp.status != 200:
   338|                error_text = await resp.text()
   339|                logger.error(f"Telegram send failed for {client.client_id}: {resp.status} - {error_text}")
   340|            else:
   341|                logger.debug(f"Signal sent to {client.client_id} (chat {client.telegram_chat_id})")
   342|
   343|
   344|async def broadcast_cancel(cancel_msg: dict):
   345|    """Broadcast a cancellation message to all active clients."""
   346|    import aiohttp
   347|
   348|    bot_token = os.getenv("HYDRA_TELEGRAM_BOT_TOKEN", config.get("telegram", {}).get("bot_token", ""))
   349|    if not bot_token:
   350|        return
   351|
   352|    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
   353|    text = f"🚫 <b>CANCELLED</b>: Signal {cancel_msg['signal_id'][:8]}\n⏱️ {cancel_msg['timestamp']}"
   354|
   355|    for client in CLIENTS_DB:
   356|        if client.status == "ACTIVE":
   357|            payload = {
   358|                "chat_id": client.telegram_chat_id,
   359|                "text": text,
   360|                "parse_mode": "HTML"
   361|            }
   362|            async with aiohttp.ClientSession() as session:
   363|                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as resp:
   364|                    if resp.status != 200:
   365|                        logger.error(f"Cancel broadcast failed for {client.client_id}")
   366|
   367|
   368|# ============================================================================
   369|# Startup / Shutdown
   370|# ============================================================================
   371|@app.on_event("startup")
   372|async def startup():
   373|    logger.info("=" * 60)
   374|    logger.info("🐙 Hydra Signal Distribution Server starting up...")
   375|    logger.info(f"Version: 1.0.0")
   376|    logger.info(f"Active clients at start: {len(CLIENTS_DB)}")
   377|    logger.info("=" * 60)
   378|
   379|@app.on_event("shutdown")
   380|async def shutdown():
   381|    logger.info("🐙 Hydra Signal Distribution Server shutting down...")
   382|
   383|# ============================================================================
   384|# Entry point
   385|# ============================================================================
   386|if __name__ == "__main__":
   387|    import uvicorn
   388|    host = os.getenv("HYDRA_SERVER_HOST", "0.0.0.0")
   389|    port = int(os.getenv("HYDRA_SERVER_PORT", "8788"))
   390|    uvicorn.run(app, host=host, port=port, log_level="info")
   391|