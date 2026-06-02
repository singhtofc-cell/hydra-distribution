![Hydra Trading System](https://img.shields.io/badge/Hydra-v1.0.0-00d4aa?style=for-the-badge)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688?style=for-the-badge)]()
[![MQL5](https://img.shields.io/badge/MQL5-1.00-FF6600?style=for-the-badge)]()
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)]()

# 🪬 Hydra Trading System

**Copy Trade / Signal Distribution System** — ระบบกระจายสัญญาณเทรดอัตโนมัติจาก Master System ไปยังบัญชี MT5 ของลูกค้าผ่าน Telegram Bot

รับสัญญาณจาก **HERMES** หรือระบบ Master ใดๆ → แปลงเป็น JSON มาตรฐาน → ส่งผ่าน Telegram → Client EA เทรดอัตโนมัติ → รายงานผลกลับ

---

## ✨ คุณสมบัติหลัก

| Feature | Description |
|---------|-------------|
| 🧠 **Signal Generator API** | FastAPI server รับสัญญาณ → JSON มาตรฐาน → กระจาย |
| 🤖 **Telegram Bot** | จัดการลูกค้า, ลงทะเบียน, ส่งสัญญาณ, รายงานผล |
| 🎯 **MQL5 EA** | Client EA สำหรับ MT5 (รองรับ USD + USC Cent) |
| 📊 **Performance Tracker** | PostgreSQL ติดตามผลเทรดของลูกค้าทุกคน |
| 📈 **Report Scheduler** | รายงานอัตโนมัติรายชั่วโมง/วัน/สัปดาห์ |
| 👑 **Admin Dashboard** | Streamlit UI สำหรับ Admin |
| 🔒 **Multi-Currency** | รองรับ USD Standard และ USC Cent อัตโนมัติ |

## 📊 Core Components

| Component | Files | LOC | Language |
|-----------|-------|-----|----------|
| Signal Server (FastAPI) | 1 | 430 | Python |
| Telegram Bot | 1 | 380 | Python |
| Performance Tracker | 1 | 320 | Python |
| Report Scheduler | 1 | 320 | Python |
| Admin Dashboard | 1 | 480 | Python/Streamlit |
| Database Schema | 2 | 280 | SQL |
| HydraCopy EA | 1 | 370 | MQL5 |
| EA Utilities | 1 | 170 | MQL5 |
| **Total** | **19** | **~1,830** | |

## 🏗️ สถาปัตยกรรมระบบ

```
┌──────────────────────────────────────────────────────────────┐
│                    🧠 MASTER SIDE (คุณ)                      │
│                                                              │
│  ┌────────────────┐    ┌───────────────┐    ┌──────────────┐ │
│  │  HERMES/Trading│──▶│ Hydra Signal   │──▶│ Telegram Bot │ │
│  │  System        │    │ Server        │    │ (Dispatch)   │ │
│  └────────────────┘    └───────┬───────┘    └──────┬───────┘ │
│                              │                   │           │
│                     ┌────────▼───────────────────▼───────┐   │
│                     │  Performance Tracker (PostgreSQL)  │   │
│                     └────────────────────────────────────┘   │
└──────────────────────────────┬───────────────────────────────┘
                               │
          Telegram Bot API  ←──┼──→  Webhook (HTTPS)
                               │
┌──────────────────────────────▼────────────────────────────┐
│               👥 CLIENT SIDE (MT5 VPS ลูกค้า)              │
│                                                           │
│  Client A (USD)        Client B (USC)        Client C     │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────┐ │
│  │ HydraCopyEA  │      │ HydraCopyEA  │      │   ...    │ │
│  │ • Listen TG  │      │ • Listen TG  │      │          │ │
│  │ • Parse Sig  │      │ • Parse Sig  │      │          │ │
│  │ • Calc Lot   │      │ • Calc Lot   │      │          │ │
│  │ • Execute    │      │ • Execute    │      │          │ │
│  │ • Report     │      │ • Report     │      │          │ │
│  └──────┬───────┘      └──────┬───────┘      └─────┬────┘ │
│         │                    │                     │      │
│         └────────────────────┼─────────────────────┘      │
│                              ▼                            │
│                    ┌──────────────────────┐               │
│                    │  MT5 Terminal (Local)│               │
│                    └──────────────────────┘               │
└───────────────────────────────────────────────────────────┘
                               │
                               ▼
              ┌───────────────────────────────────┐
              │  📈 Admin Dashboard / Telegram   │
              │  • Real-time P&L ทุกลูกค้า          │
              │  • สรุปรายวัน/ชม                    │
              │  • Fill rate, Slippage, Latency   │
              └───────────────────────────────────┘
```

## 🚀 Roadmap การพัฒนา

| Phase | Component | Timeline |
|-------|-----------|----------|
| ✅ Phase 1 | **Signal Generator API** (FastAPI) | ✅ Complete |
| ✅ Phase 2 | **Telegram Bot Management** | ✅ Complete |
| ✅ Phase 3 | **HydraCopyEA** (MQL5) | ✅ Complete |
| ✅ Phase 4 | **Performance Tracker** (PostgreSQL) | ✅ Complete |
| ✅ Phase 5 | **Report Scheduler + Dashboard** | ✅ Complete |

**รวมเวลา: ~6-8 สัปดาห์** | **สถานะ: Phase 1-5 Complete 🎉**

## ⚡ เริ่มต้นใช้งาน

```bash
# 1. Clone
git clone https://github.com/YourUsername/hydra-distribution.git
cd hydra-distribution

# 2. ติดตั้ง dependencies
pip install -r requirements.txt

# 3. ตั้งค่า Environment
cp .env.example .env
# แก้ไข BOT_TOKEN, ADMIN_CHAT_ID, DATABASE_URL

# 4. เริ่ม Signal Server
python -m backend.signal_server

# 5. (Optional) เริ่ม Telegram Bot
python -m backend.telegram_bot

# 6. (Optional) เริ่ม Report Scheduler
python -m backend.report_scheduler

# 7. (Optional) เริ่ม Admin Dashboard
streamlit run admin_dashboard/app.py

# หรือใช้ Docker Compose ครั้งเดียว
docker compose up -d
```

## 🎯 การตั้งค่าแยกตามประเภทลูกค้า

### USD Standard (Group 1)
| Parameter | Value | Description |
|-----------|-------|-------------|
| lot_multiplier | 1.0 | เทียบเท่า Master |
| max_lot_cap | 5.0 | Lot สูงสุดที่อนุญาต |
| risk_percent | 1.0% | ความเสี่ยงต่อเทรด |

### USC Cent (Group 2)
| Parameter | Value | Description |
|-----------|-------|-------------|
| lot_multiplier | 100.0 | Master 0.01 → Slave 1.00 lot |
| max_lot_cap | 3.0 | ป้องกัน Over-leverage |
| risk_percent | 1.0% | ความเสี่ยงต่อเทรด |

## 🔐 ความปลอดภัย
- ✅ ใช้ HTTPS เท่านั้น
- ✅ เก็บ BOT_TOKEN ใน environment variables
- ✅ Whitelist เฉพาะ Chat ID ที่ลงทะเบียนแล้ว
- ✅ Rate limiting ป้องกัน Spam
- ✅ Max Daily Loss / Drawdown auto-stop

## 📁 โครงสร้างไฟล์

```
hydra_distribution/
├── backend/                        # Python Backend
│   ├── signal_server.py            # FastAPI Signal Generator (Phase 1)
│   ├── telegram_bot.py             # Telegram Bot Management (Phase 2)
│   ├── performance_tracker.py      # DB Performance Tracker (Phase 4)
│   ├── report_scheduler.py         # Auto Reporting (Phase 5)
│   └── database/
│       ├── schema.sql              # PostgreSQL Schema
│       └── migrations/
├── ea/                             # MQL5 EA (Phase 3)
│   ├── HydraCopyEA.mq5             # MT5 Client EA
│   └── HydraEA_Utils.mqh           # Helper Functions
├── admin_dashboard/
│   └── app.py                      # Streamlit Admin Dashboard
├── docs/
│   ├── client_guide.md             # Client Installation Guide
│   └── api_docs.md                 # API Documentation
├── config.yaml                     # System Configuration
├── docker-compose.yml              # Docker Setup
├── Dockerfile                      # Container Definition
├── requirements.txt                # Python Dependencies
├── .env.example                    # Environment Template
├── README.md                       # This File
└── SYSTEM.md                       # System Documentation
```

## 📊 Technology Stack

- **Backend**: Python 3.11+, FastAPI, Uvicorn
- **Database**: PostgreSQL 16 (via asyncpg)
- **Bot**: python-telegram-bot v21+
- **Scheduling**: APScheduler
- **Dashboard**: Streamlit + Plotly
- **Client**: MQL5 (MetaTrader 5 Expert Advisor)
- **Container**: Docker + Docker Compose

## 📜 License

MIT License — ห้ามใช้เพื่อการค้าและส่วนตัวได้ฟรี
