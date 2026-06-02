     1|![Hydra Trading System](https://img.shields.io/badge/Hydra-v1.0.0-00d4aa?style=for-the-badge)
     2|[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge)]()
     3|[![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688?style=for-the-badge)]()
     4|[![MQL5](https://img.shields.io/badge/MQL5-1.00-FF6600?style=for-the-badge)]()
     5|[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)]()
     6|
     7|# 🐙 Hydra Trading System
     8|
     9|**Copy Trade / Signal Distribution System** — ระบบกระจายสัญญาณเทรดอัตโนมัติจาก Master System ไปยังบัญชี MT5 ของลูกค้าผ่าน Telegram Bot
    10|
    11|รับสัญญาณจาก **HERMES** หรือระบบ Master ใดๆ → แปลงเป็น JSON มาตรฐาน → ส่งผ่าน Telegram → Client EA เทรดอัตโนมัติ → รายงานผลกลับ
    12|
    13|---
    14|
    15|## ✨ คุณสมบัติหลัก
    16|
    17|| Feature | Description |
    18||---------|-------------|
    19|| 🧠 **Signal Generator API** | FastAPI server รับสัญญาณ → JSON มาตรฐาน → กระจาย |
    20|| 🤖 **Telegram Bot** | จัดการลูกค้า, ลงทะเบียน, ส่งสัญญาณ, รายงานผล |
    21|| 🎯 **MQL5 EA** | Client EA สำหรับ MT5 (รองรับ USD + USC Cent) |
    22|| 📊 **Performance Tracker** | PostgreSQL ติดตามผลเทรดของลูกค้าทุกคน |
    23|| 📈 **Report Scheduler** | รายงานอัตโนมัติรายชั่วโมง/วัน/สัปดาห์ |
    24|| 👑 **Admin Dashboard** | Streamlit UI สำหรับ Admin |
    25|| 🔒 **Multi-Currency** | รองรับ USD Standard และ USC Cent อัตโนมัติ |
    26|
    27|## 📊 Core Components
    28|
    29|| Component | Files | LOC | Language |
    30||-----------|-------|-----|----------|
    31|| Signal Server (FastAPI) | 1 | 430 | Python |
    32|| Telegram Bot | 1 | 380 | Python |
    33|| Performance Tracker | 1 | 320 | Python |
    34|| Report Scheduler | 1 | 320 | Python |
    35|| Admin Dashboard | 1 | 480 | Python/Streamlit |
    36|| Database Schema | 2 | 280 | SQL |
    37|| HydraCopy EA | 1 | 370 | MQL5 |
    38|| EA Utilities | 1 | 170 | MQL5 |
    39|| **Total** | **19** | **~1,830** | |
    40|
    41|## 🏗️ สถาปัตยกรรมระบบ
    42|
    43|```
    44|┌─────────────────────────────────────────────────────────────┐
    45|│                    🧠 MASTER SIDE (คุณ)                      │
    46|│                                                             │
    47|│  ┌──────────────┐    ┌───────────────┐    ┌──────────────┐ │
    48|│  │  HERMES/Trading │──▶│ Hydra Signal │──▶│ Telegram Bot │ │
    49|│  │  System       │    │ Server       │    │ (Dispatch)   │ │
    50|│  └──────────────┘    └───────┬───────┘    └──────┬───────┘ │
    51|│                              │                   │         │
    52|│                     ┌────────▼───────────────────▼───────┐ │
    53|│                     │  Performance Tracker (PostgreSQL)  │ │
    54|│                     └────────────────────────────────────┘ │
    55|└──────────────────────────────┬──────────────────────────────┘
    56|                               │
    57|          Telegram Bot API  ←──┼──→  Webhook (HTTPS)
    58|                               │
    59|┌──────────────────────────────▼──────────────────────────────┐
    60|│               👥 CLIENT SIDE (MT5 VPS ลูกค้า)               │
    61|│                                                             │
    62|│  Client A (USD)        Client B (USC)        Client C       │
    63|│  ┌──────────────┐      ┌──────────────┐      ┌──────────┐ │
    64|│  │ HydraCopyEA │      │ HydraCopyEA │      │   ...    │ │
    65|│  │ • Listen TG  │      │ • Listen TG  │      │          │ │
    66|│  │ • Parse Sig  │      │ • Parse Sig  │      │          │ │
    67|│  │ • Calc Lot   │      │ • Calc Lot   │      │          │ │
    68|│  │ • Execute    │      │ • Execute    │      │          │ │
    69|│  │ • Report     │      │ • Report     │      │          │ │
    70|│  └──────┬───────┘      └──────┬───────┘      └─────┬────┘ │
    71|│         │                    │                     │       │
    72|│         └────────────────────┼─────────────────────┘       │
    73|│                              ▼                             │
    74|│                    ┌──────────────────────┐                │
    75|│                    │  MT5 Terminal (Local)│                │
    76|│                    └──────────────────────┘                │
    77|└─────────────────────────────────────────────────────────────┘
    78|                               │
    79|                               ▼
    80|              ┌───────────────────────────────────┐
    81|              │  📈 Admin Dashboard / Telegram     │
    82|              │  • Real-time P&L ทุกลูกค้า         │
    83|              │  • สรุปรายวัน/ชม                   │
    84|              │  • Fill rate, Slippage, Latency    │
    85|              └───────────────────────────────────┘
    86|```
    87|
    88|## 🚀 Roadmap การพัฒนา
    89|
    90|| Phase | Component | Timeline |
    91||-------|-----------|----------|
    92|| ✅ Phase 1 | **Signal Generator API** (FastAPI) | ✅ Complete |
    93|| ✅ Phase 2 | **Telegram Bot Management** | ✅ Complete |
    94|| ✅ Phase 3 | **HydraCopyEA** (MQL5) | ✅ Complete |
    95|| ✅ Phase 4 | **Performance Tracker** (PostgreSQL) | ✅ Complete |
    96|| ✅ Phase 5 | **Report Scheduler + Dashboard** | ✅ Complete |
    97|
    98|**รวมเวลา: ~6-8 สัปดาห์** | **สถานะ: Phase 1-5 Complete 🎉**
    99|
   100|## ⚡ เริ่มต้นใช้งาน
   101|
   102|```bash
   103|# 1. Clone
   104|git clone https://github.com/YourUsername/hydra-distribution.git
   105|cd hydra-distribution
   106|
   107|# 2. ติดตั้ง dependencies
   108|pip install -r requirements.txt
   109|
   110|# 3. ตั้งค่า Environment
   111|cp .env.example .env
   112|# แก้ไข BOT_TOKEN, ADMIN_CHAT_ID, DATABASE_URL
   113|
   114|# 4. เริ่ม Signal Server
   115|python -m backend.signal_server
   116|
   117|# 5. (Optional) เริ่ม Telegram Bot
   118|python -m backend.telegram_bot
   119|
   120|# 6. (Optional) เริ่ม Report Scheduler
   121|python -m backend.report_scheduler
   122|
   123|# 7. (Optional) เริ่ม Admin Dashboard
   124|streamlit run admin_dashboard/app.py
   125|
   126|# หรือใช้ Docker Compose ครั้งเดียว
   127|docker compose up -d
   128|```
   129|
   130|## 🎯 การตั้งค่าแยกตามประเภทลูกค้า
   131|
   132|### USD Standard (Group 1)
   133|| Parameter | Value | Description |
   134||-----------|-------|-------------|
   135|| lot_multiplier | 1.0 | เทียบเท่า Master |
   136|| max_lot_cap | 5.0 | Lot สูงสุดที่อนุญาต |
   137|| risk_percent | 1.0% | ความเสี่ยงต่อเทรด |
   138|
   139|### USC Cent (Group 2)
   140|| Parameter | Value | Description |
   141||-----------|-------|-------------|
   142|| lot_multiplier | 100.0 | Master 0.01 → Slave 1.00 lot |
   143|| max_lot_cap | 3.0 | ป้องกัน Over-leverage |
   144|| risk_percent | 1.0% | ความเสี่ยงต่อเทรด |
   145|
   146|## 🔐 ความปลอดภัย
   147|- ✅ ใช้ HTTPS เท่านั้น
   148|- ✅ เก็บ BOT_TOKEN ใน environment variables
   149|- ✅ Whitelist เฉพาะ Chat ID ที่ลงทะเบียนแล้ว
   150|- ✅ Rate limiting ป้องกัน Spam
   151|- ✅ Max Daily Loss / Drawdown auto-stop
   152|
   153|## 📁 โครงสร้างไฟล์
   154|
   155|```
   156|hydra_distribution/
   157|├── backend/                        # Python Backend
   158|│   ├── signal_server.py            # FastAPI Signal Generator (Phase 1)
   159|│   ├── telegram_bot.py             # Telegram Bot Management (Phase 2)
   160|│   ├── performance_tracker.py      # DB Performance Tracker (Phase 4)
   161|│   ├── report_scheduler.py         # Auto Reporting (Phase 5)
   162|│   └── database/
   163|│       ├── schema.sql              # PostgreSQL Schema
   164|│       └── migrations/
   165|├── ea/                             # MQL5 EA (Phase 3)
   166|│   ├── HydraCopyEA.mq5             # MT5 Client EA
   167|│   └── HydraEA_Utils.mqh           # Helper Functions
   168|├── admin_dashboard/
   169|│   └── app.py                      # Streamlit Admin Dashboard
   170|├── docs/
   171|│   ├── client_guide.md             # Client Installation Guide
   172|│   └── api_docs.md                 # API Documentation
   173|├── config.yaml                     # System Configuration
   174|├── docker-compose.yml              # Docker Setup
   175|├── Dockerfile                      # Container Definition
   176|├── requirements.txt                # Python Dependencies
   177|├── .env.example                    # Environment Template
   178|├── README.md                       # This File
   179|└── SYSTEM.md                       # System Documentation
   180|```
   181|
   182|## 📊 Technology Stack
   183|
   184|- **Backend**: Python 3.11+, FastAPI, Uvicorn
   185|- **Database**: PostgreSQL 16 (via asyncpg)
   186|- **Bot**: python-telegram-bot v21+
   187|- **Scheduling**: APScheduler
   188|- **Dashboard**: Streamlit + Plotly
   189|- **Client**: MQL5 (MetaTrader 5 Expert Advisor)
   190|- **Container**: Docker + Docker Compose
   191|
   192|## 📜 License
   193|
   194|MIT License — ใช้เพื่อการค้าและส่วนตัวได้ฟรี
   195|