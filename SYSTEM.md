---
title: Hydra Trading System — SYSTEM.md
description: System architecture and component documentation for the Hydra Copy Trade distribution system
---

# 🪬 Hydra Trading System — SYSTEM.md

**Version:** 1.0.0
**Last Updated:** 2026-06-02
**Source:** [Qwen Architecture Proposal](https://chat.qwen.ai/s/t_7c68e30f-f77d-4ca1-8687-ab6cbf7f40ea)
**System Type:** Copy Trade / Signal Distribution

---

## 📊 System Overview

| Metric | Value |
|--------|-------|
| Total Python Files | 9 |
| Total Python LOC | 1,658 |
| Total MQL5 Files | 2 |
| Total MQL5 LOC | 172 |
| Total SQL Files | 2 |
| Total Project Files | 19 |
| Total Project LOC | ~1,830 |
| Development Status | 🟢 Phase 1-5 Complete |

## 🏗️ Architecture

The Hydra Trading System is a **standalone signal distribution layer** that sits between the Master Trading System (HERMES) and client MT5 VPS accounts.

### Data Flow
```
Master System (HERMES/GUTS/etc.)
    → TradeSignal (JSON via HTTP POST)
    → Hydra Signal Server (FastAPI)
    → Telegram Bot API (broadcast)
    → HydraCopyEA on client MT5 (parse + execute)
    → Trade Fill Report (HTTP POST back)
    → Performance Tracker (PostgreSQL)
    → Admin Dashboard (Streamlit)
```

---

## 🧩 Active Systems

### 1. Hydra Signal Server
**File:** `backend/signal_server.py` | **LOC:** 430 | **Status:** ✅ Active

FastAPI server that receives trading signals from the master system, validates them, formats as Telegram messages with embedded JSON, and dispatches to all subscribed clients.

**Key Endpoints:**
- `POST /api/v1/signal/send` — Single signal dispatch
- `POST /api/v1/signal/batch` — Batch signal dispatch
- `POST /api/v1/signal/cancel/{id}` — Cancel pending signal
- `POST /api/v1/client/register` — Register new client
- `GET /api/v1/client/list` — List all clients
- `PATCH /api/v1/client/{id}/status` — Update client status
- `GET /health` — Health check
- `GET /api/v1/stats` — System statistics

**Data Models:**
- `TradeSignal` — Standardised signal (type, priority, symbol, prices, lot, risk)
- `ClientInfo` — Client registration (currency, multiplier, risk, status)
- `SignalType`: BUY, SELL, CLOSE_ALL, MODIFY_SL, PARTIAL_CLOSE, CANCEL
- `SignalPriority`: NORMAL, URGENT, EMERGENCY

**In-Memory State:** CLIENTS_DB, SIGNAL_HISTORY (replace with PostgreSQL in production)

### 2. Hydra Telegram Bot
**File:** `backend/telegram_bot.py` | **LOC:** 380 | **Status:** ✅ Active

Telegram Bot that manages client interactions via inline keyboards and commands. Core signal storage for EA polling.

**Commands:**
- `/start` — Welcome menu with inline keyboard
- `/register <account> <currency> <multiplier>` — Client registration
- `/status` — Subscription status
- `/pause` / `/resume` — Toggle signal subscription
- `/report [today|weekly]` — Performance reports

**Signal Parser:** Extracts JSON from `<blockquote>` tags for EA consumption
**Signal Buffer:** In-memory with auto-expiry; production: Redis/DB

### 3. HydraCopyEA (MQL5)
**File:** `ea/HydraCopyEA.mq5` | **LOC:** 370 | **Status:** ✅ Active

MT5 Expert Advisor installed on client VPS. Core copytrade engine.

**Features:**
- Signal polling from Telegram via WebRequest
- Signal queue with expiry management
- Automatic lot calculation (risk-based, USD + USC support)
- Slippage check before execution
- Risk management (max daily loss, max drawdown)
- Trade confirmation reporting
- Periodic performance reporting
- Registration on startup

**Input Parameters:**
- MagicNumber, RiskPercent, LotMultiplier, MaxLotCap
- AutoExecute, Slippage
- MaxDailyLoss, MaxDrawdown, EnableNewsFilter
- SendReports, ReportInterval

### 4. HydraEA Utils
**File:** `ea/HydraEA_Utils.mqh` | **LOC:** 170 | **Status:** ✅ Active

Shared MQL5 utility library with string helpers, symbol info wrappers, risk calculation, and news filter.

### 5. Performance Tracker
**File:** `backend/performance_tracker.py` | **LOC:** 320 | **Status:** ✅ Active

Tracks signals dispatched, trade fills from client EAs, and computes per-client metrics.

**Data Classes:** SignalLog, TradeFill, ClientPerformance
**Methods:** log_signal_dispatched, log_trade_fill, update_trade_outcome, get_daily_report, get_client_summary, get_admin_summary
**Storage:** PostgreSQL (via asyncpg) with in-memory fallback

### 6. Report Scheduler
**File:** `backend/report_scheduler.py` | **LOC:** 320 | **Status:** ✅ Active

APScheduler-based report dispatch system.

**Schedules:**
- Hourly: every hour at :00
- Daily: 23:55 UTC
- Weekly: Sunday 23:55 UTC

**Report Types:** Hourly P&L, Daily Summary, Weekly Summary, Admin Overview

### 7. Admin Dashboard
**File:** `admin_dashboard/app.py` | **LOC:** 480 | **Status:** ✅ Active

Streamlit web UI for real-time monitoring and management.

**Pages:**
- **Dashboard:** System health, signal activity chart, client currency distribution
- **Clients:** Client list with filters, registration form
- **Signals:** Signal dispatch log with filters
- **Performance:** P&L charts, win rate, top clients
- **Settings:** Server, Telegram, reporting, risk configuration

### 8. Database
**Files:** `backend/database/schema.sql`, `migrations/001_initial_schema.sql` | **LOC:** 280

PostgreSQL database with full schema for:
- `clients` — Registration, config, status
- `signals` — Full signal dispatch log
- `trade_fills` — Fill confirmations with prices and outcomes
- `daily_reports` — Cached daily aggregations
- `system_events` — Audit log
- `v_client_performance` — Performance view
- `v_daily_aggregate` — Aggregate view
- `update_trade_outcome()` — Stored procedure

### 9. Configuration & Infrastructure
- `config.yaml` — Central configuration (server, telegram, db, risk, reporting, signal)
- `requirements.txt` — Python dependency manifest
- `docker-compose.yml` — Multi-service Docker orchestration
- `Dockerfile` — Container definition
- `.env.example` — Environment template

---

## 🔄 Signal Lifecycle

```
1. MASTER SYSTEM (HERMES)
   ├── SMC Grid Detection
   ├── Judas Swing Signal  
   └── ICT/FVG Pattern
        │
        ▼
2. TRADE SIGNAL (JSON)
   ├── signal_id (UUID)
   ├── signal_type (BUY/SELL)
   ├── symbol, prices, SL, TP
   ├── risk_percent, lot_multiplier
   └── source, grid_layer
        │
        ▼
3. SIGNAL SERVER (FastAPI)
   ├── Validate signal
   ├── Format Telegram HTML
   ├── Filter eligible clients
   └── Broadcast via Telegram Bot API
        │
        ▼
4. CLIENT EA (HydraCopyEA)
   ├── Poll Telegram for signals
   ├── Parse JSON from blockquote
   ├── Check expiry
   ├── Verify symbol match
   ├── Calculate lot size (risk-based)
   ├── Check slippage
   ├── Execute trade (BUY/SELL)
   └── Send confirmation + report
        │
        ▼
5. PERFORMANCE TRACKER
   ├── Log signal dispatch
   ├── Log trade fill
   ├── Calculate P&L
   └── Generate reports
        │
        ▼
6. ADMIN DASHBOARD
   ├── Real-time metrics
   ├── Client performance
   └── System health
```

---

## ⚙️ Configuration Reference

### config.yaml Structure

```yaml
system:
  name: "Hydra Trading System"
  version: "1.0.0"

server:
  host: "0.0.0.0"
  port: 8788

telegram:
  bot_token: "YOUR_TELEGRAM_BOT_TOKEN"  # Env: HYDRA_TELEGRAM_BOT_TOKEN
  admin_chat_id: 0                       # Env: HYDRA_ADMIN_CHAT_ID

database:
  url: "postgresql://hydra:hydra_pass@localhost:5432/hydra_trading"

clients:
  usc_lot_multiplier: 100.0     # Cent account multiplier
  usd_lot_multiplier: 1.0       # Standard account multiplier

risk:
  max_daily_loss_percent: 5.0
  max_drawdown_percent: 15.0
```

---

## 🔌 Integration Points

### Integration with HERMES
The Hydra system receives signals from HERMES via HTTP POST. Integrate by:
1. Adding a `send_to_hydra()` call after HERMES generates a trade signal
2. Pointing to `http://localhost:8788/api/v1/signal/send`
3. Including standard TradeSignal JSON payload

### Integration with Client MT5
1. Client installs HydraCopyEA.ex5 on their MT5 VPS
2. EA connects via Telegram Bot API polling
3. EA auto-calculates lot size for USD or USC accounts
4. EA reports fills back via Telegram

---

## 🛡️ Safety & Risk Controls

| Control | Description | Default |
|---------|-------------|---------|
| Daily Loss Limit | Stops new trades when exceeded | 5% |
| Max Drawdown | Closes all positions when exceeded | 15% |
| News Filter | Skips trading during major news | Enabled |
| Slippage Check | Rejects fills exceeding threshold | 30 points |
| Signal Expiry | Auto-cancels stale signals | 30 min |
| Rate Limiting | Prevents Telegram spam | Built-in |
| Client Whitelist | Only registered chat IDs receive signals | Required |
