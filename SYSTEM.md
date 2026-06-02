     1|---
     2|title: Hydra Trading System — SYSTEM.md
     3|description: System architecture and component documentation for the Hydra Copy Trade distribution system
     4|---
     5|
     6|# 🐙 Hydra Trading System — SYSTEM.md
     7|
     8|**Version:** 1.0.0
     9|**Last Updated:** 2026-06-02
    10|**Source:** [Qwen Architecture Proposal](https://chat.qwen.ai/s/t_7c68e30f-f77d-4ca1-8687-ab6cbf7f40ea)
    11|**System Type:** Copy Trade / Signal Distribution
    12|
    13|---
    14|
    15|## 📊 System Overview
    16|
    17|| Metric | Value |
    18||--------|-------|
    19|| Total Python Files | 9 |
    20|| Total Python LOC | 1,658 |
    21|| Total MQL5 Files | 2 |
    22|| Total MQL5 LOC | 172 |
    23|| Total SQL Files | 2 |
    24|| Total Project Files | 19 |
    25|| Total Project LOC | ~1,830 |
    26|| Development Status | 🟢 Phase 1-5 Complete |
    27|
    28|## 🏗️ Architecture
    29|
    30|The Hydra Trading System is a **standalone signal distribution layer** that sits between the Master Trading System (HERMES) and client MT5 VPS accounts.
    31|
    32|### Data Flow
    33|```
    34|Master System (HERMES/GUTS/etc.)
    35|    → TradeSignal (JSON via HTTP POST)
    36|    → Hydra Signal Server (FastAPI)
    37|    → Telegram Bot API (broadcast)
    38|    → HydraCopyEA on client MT5 (parse + execute)
    39|    → Trade Fill Report (HTTP POST back)
    40|    → Performance Tracker (PostgreSQL)
    41|    → Admin Dashboard (Streamlit)
    42|```
    43|
    44|---
    45|
    46|## 🧩 Active Systems
    47|
    48|### 1. Hydra Signal Server
    49|**File:** `backend/signal_server.py` | **LOC:** 430 | **Status:** ✅ Active
    50|
    51|FastAPI server that receives trading signals from the master system, validates them, formats as Telegram messages with embedded JSON, and dispatches to all subscribed clients.
    52|
    53|**Key Endpoints:**
    54|- `POST /api/v1/signal/send` — Single signal dispatch
    55|- `POST /api/v1/signal/batch` — Batch signal dispatch
    56|- `POST /api/v1/signal/cancel/{id}` — Cancel pending signal
    57|- `POST /api/v1/client/register` — Register new client
    58|- `GET /api/v1/client/list` — List all clients
    59|- `PATCH /api/v1/client/{id}/status` — Update client status
    60|- `GET /health` — Health check
    61|- `GET /api/v1/stats` — System statistics
    62|
    63|**Data Models:**
    64|- `TradeSignal` — Standardised signal (type, priority, symbol, prices, lot, risk)
    65|- `ClientInfo` — Client registration (currency, multiplier, risk, status)
    66|- `SignalType`: BUY, SELL, CLOSE_ALL, MODIFY_SL, PARTIAL_CLOSE, CANCEL
    67|- `SignalPriority`: NORMAL, URGENT, EMERGENCY
    68|
    69|**In-Memory State:** CLIENTS_DB, SIGNAL_HISTORY (replace with PostgreSQL in production)
    70|
    71|### 2. Hydra Telegram Bot
    72|**File:** `backend/telegram_bot.py` | **LOC:** 380 | **Status:** ✅ Active
    73|
    74|Telegram Bot that manages client interactions via inline keyboards and commands. Core signal storage for EA polling.
    75|
    76|**Commands:**
    77|- `/start` — Welcome menu with inline keyboard
    78|- `/register <account> <currency> <multiplier>` — Client registration
    79|- `/status` — Subscription status
    80|- `/pause` / `/resume` — Toggle signal subscription
    81|- `/report [today|weekly]` — Performance reports
    82|
    83|**Signal Parser:** Extracts JSON from `<blockquote>` tags for EA consumption
    84|**Signal Buffer:** In-memory with auto-expiry; production: Redis/DB
    85|
    86|### 3. HydraCopyEA (MQL5)
    87|**File:** `ea/HydraCopyEA.mq5` | **LOC:** 370 | **Status:** ✅ Active
    88|
    89|MT5 Expert Advisor installed on client VPS. Core copytrade engine.
    90|
    91|**Features:**
    92|- Signal polling from Telegram via WebRequest
    93|- Signal queue with expiry management
    94|- Automatic lot calculation (risk-based, USD + USC support)
    95|- Slippage check before execution
    96|- Risk management (max daily loss, max drawdown)
    97|- Trade confirmation reporting
    98|- Periodic performance reporting
    99|- Registration on startup
   100|
   101|**Input Parameters:**
   102|- MagicNumber, RiskPercent, LotMultiplier, MaxLotCap
   103|- AutoExecute, Slippage
   104|- MaxDailyLoss, MaxDrawdown, EnableNewsFilter
   105|- SendReports, ReportInterval
   106|
   107|### 4. HydraEA Utils
   108|**File:** `ea/HydraEA_Utils.mqh` | **LOC:** 170 | **Status:** ✅ Active
   109|
   110|Shared MQL5 utility library with string helpers, symbol info wrappers, risk calculation, and news filter.
   111|
   112|### 5. Performance Tracker
   113|**File:** `backend/performance_tracker.py` | **LOC:** 320 | **Status:** ✅ Active
   114|
   115|Tracks signals dispatched, trade fills from client EAs, and computes per-client metrics.
   116|
   117|**Data Classes:** SignalLog, TradeFill, ClientPerformance
   118|**Methods:** log_signal_dispatched, log_trade_fill, update_trade_outcome, get_daily_report, get_client_summary, get_admin_summary
   119|**Storage:** PostgreSQL (via asyncpg) with in-memory fallback
   120|
   121|### 6. Report Scheduler
   122|**File:** `backend/report_scheduler.py` | **LOC:** 320 | **Status:** ✅ Active
   123|
   124|APScheduler-based report dispatch system.
   125|
   126|**Schedules:**
   127|- Hourly: every hour at :00
   128|- Daily: 23:55 UTC
   129|- Weekly: Sunday 23:55 UTC
   130|
   131|**Report Types:** Hourly P&L, Daily Summary, Weekly Summary, Admin Overview
   132|
   133|### 7. Admin Dashboard
   134|**File:** `admin_dashboard/app.py` | **LOC:** 480 | **Status:** ✅ Active
   135|
   136|Streamlit web UI for real-time monitoring and management.
   137|
   138|**Pages:**
   139|- **Dashboard:** System health, signal activity chart, client currency distribution
   140|- **Clients:** Client list with filters, registration form
   141|- **Signals:** Signal dispatch log with filters
   142|- **Performance:** P&L charts, win rate, top clients
   143|- **Settings:** Server, Telegram, reporting, risk configuration
   144|
   145|### 8. Database
   146|**Files:** `backend/database/schema.sql`, `migrations/001_initial_schema.sql` | **LOC:** 280
   147|
   148|PostgreSQL database with full schema for:
   149|- `clients` — Registration, config, status
   150|- `signals` — Full signal dispatch log
   151|- `trade_fills` — Fill confirmations with prices and outcomes
   152|- `daily_reports` — Cached daily aggregations
   153|- `system_events` — Audit log
   154|- `v_client_performance` — Performance view
   155|- `v_daily_aggregate` — Aggregate view
   156|- `update_trade_outcome()` — Stored procedure
   157|
   158|### 9. Configuration & Infrastructure
   159|- `config.yaml` — Central configuration (server, telegram, db, risk, reporting, signal)
   160|- `requirements.txt` — Python dependency manifest
   161|- `docker-compose.yml` — Multi-service Docker orchestration
   162|- `Dockerfile` — Container definition
   163|- `.env.example` — Environment template
   164|
   165|---
   166|
   167|## 🔄 Signal Lifecycle
   168|
   169|```
   170|1. MASTER SYSTEM (HERMES)
   171|   ├── SMC Grid Detection
   172|   ├── Judas Swing Signal  
   173|   └── ICT/FVG Pattern
   174|        │
   175|        ▼
   176|2. TRADE SIGNAL (JSON)
   177|   ├── signal_id (UUID)
   178|   ├── signal_type (BUY/SELL)
   179|   ├── symbol, prices, SL, TP
   180|   ├── risk_percent, lot_multiplier
   181|   └── source, grid_layer
   182|        │
   183|        ▼
   184|3. SIGNAL SERVER (FastAPI)
   185|   ├── Validate signal
   186|   ├── Format Telegram HTML
   187|   ├── Filter eligible clients
   188|   └── Broadcast via Telegram Bot API
   189|        │
   190|        ▼
   191|4. CLIENT EA (HydraCopyEA)
   192|   ├── Poll Telegram for signals
   193|   ├── Parse JSON from blockquote
   194|   ├── Check expiry
   195|   ├── Verify symbol match
   196|   ├── Calculate lot size (risk-based)
   197|   ├── Check slippage
   198|   ├── Execute trade (BUY/SELL)
   199|   └── Send confirmation + report
   200|        │
   201|        ▼
   202|5. PERFORMANCE TRACKER
   203|   ├── Log signal dispatch
   204|   ├── Log trade fill
   205|   ├── Calculate P&L
   206|   └── Generate reports
   207|        │
   208|        ▼
   209|6. ADMIN DASHBOARD
   210|   ├── Real-time metrics
   211|   ├── Client performance
   212|   └── System health
   213|```
   214|
   215|---
   216|
   217|## ⚙️ Configuration Reference
   218|
   219|### config.yaml Structure
   220|
   221|```yaml
   222|system:
   223|  name: "Hydra Trading System"
   224|  version: "1.0.0"
   225|
   226|server:
   227|  host: "0.0.0.0"
   228|  port: 8788
   229|
   230|telegram:
   231|  bot_token: "YOUR_TELEGRAM_BOT_TOKEN"  # Env: HYDRA_TELEGRAM_BOT_TOKEN
   232|  admin_chat_id: 0                       # Env: HYDRA_ADMIN_CHAT_ID
   233|
   234|database:
   235|  url: "postgresql://hydra:***@localhost:5432/hydra_trading"
   236|
   237|clients:
   238|  usc_lot_multiplier: 100.0     # Cent account multiplier
   239|  usd_lot_multiplier: 1.0       # Standard account multiplier
   240|
   241|risk:
   242|  max_daily_loss_percent: 5.0
   243|  max_drawdown_percent: 15.0
   244|```
   245|
   246|---
   247|
   248|## 🔌 Integration Points
   249|
   250|### Integration with HERMES
   251|The Hydra system receives signals from HERMES via HTTP POST. Integrate by:
   252|1. Adding a `send_to_hydra()` call after HERMES generates a trade signal
   253|2. Pointing to `http://localhost:8788/api/v1/signal/send`
   254|3. Including standard TradeSignal JSON payload
   255|
   256|### Integration with Client MT5
   257|1. Client installs HydraCopyEA.ex5 on their MT5 VPS
   258|2. EA connects via Telegram Bot API polling
   259|3. EA auto-calculates lot size for USD or USC accounts
   260|4. EA reports fills back via Telegram
   261|
   262|---
   263|
   264|## 🛡️ Safety & Risk Controls
   265|
   266|| Control | Description | Default |
   267||---------|-------------|---------|
   268|| Daily Loss Limit | Stops new trades when exceeded | 5% |
   269|| Max Drawdown | Closes all positions when exceeded | 15% |
   270|| News Filter | Skips trading during major news | Enabled |
   271|| Slippage Check | Rejects fills exceeding threshold | 30 points |
   272|| Signal Expiry | Auto-cancels stale signals | 30 min |
   273|| Rate Limiting | Prevents Telegram spam | Built-in |
   274|| Client Whitelist | Only registered chat IDs receive signals | Required |
   275|