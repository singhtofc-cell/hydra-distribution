# 🪬 Hydra Trading System — คู่มือการติดตั้งและใช้งาน (ฉบับย่อ)

> **เวอร์ชันเต็ม (HTML พร้อมภาพประกอบ):** ดูได้ที่ `docs/setup_guide.html`
> เปิดไฟล์ใน Browser เพื่อดูคู่มือแบบ Step-by-Step พร้อมรูปภาพ

---

## 📋 สารบัญ

1. [เตรียมความพร้อม](#1-เตรียมความพร้อม)
2. [สร้าง Telegram Bot](#2-สร้าง-telegram-bot)
3. [ตั้งค่า Signal Server](#3-ตั้งค่า-signal-server)
4. [ลงทะเบียน Token](#4-ลงทะเบียน-token)
5. [ติดตั้ง EA บน MT5](#5-ติดตั้ง-ea-บน-mt5)
6. [ตั้งค่า Input Parameters](#6-ตั้งค่า-input-parameters)
7. [ลงทะเบียนกับ Bot](#7-ลงทะเบียนกับ-bot)
8. [ทดสอบระบบ](#8-ทดสอบระบบ)
9. [รายงานและติดตาม](#9-รายงานและติดตาม)
10. [แก้ไขปัญหา](#10-แก้ไขปัญหา)

---

## 1. เตรียมความพร้อม

### ✅ สิ่งที่ต้องมี
- ✅ บัญชี Exness (Standard USD หรือ Standard Cent USC)
- ✅ MT5 ติดตั้งบน VPS หรือเครื่องของคุณ
- ✅ บัญชี Telegram ที่ใช้งานอยู่
- ✅ VPS ที่เปิดตลอด 24/7
- ✅ Internet connection ที่เสถียร

### 📌 ข้อมูลที่ต้องเตรียม
| ข้อมูล | คำอธิบาย | ตัวอย่าง |
|--------|----------|----------|
| Telegram Chat ID | ID ที่ Bot จะส่งสัญญาณไปให้ | `123456789` |
| MT5 Account Number | เลขบัญชี MT5 | `12345678` |
| Account Currency | USD หรือ USC | `USD` หรือ `USC` |
| Lot Multiplier | ตัวคูณ Lot | `1.0` (USD) หรือ `100` (USC) |

---

## 2. สร้าง Telegram Bot

1. เปิด Telegram → ค้นหา `@BotFather`
2. พิมพ์ `/newbot`
3. ตั้งชื่อ: `Hydra Signal Bot`
4. ตั้ง Username: `YourHydraSignalBot` (ต้องลงท้ายด้วย `bot`)
5. **เก็บ BOT_TOKEN ที่ได้!**

### ตั้งค่า Bot Commands
พิมพ์ `/setcommands` ใน BotFather แล้วส่ง:
```
start - 🤖 เริ่มต้นใช้งาน
register - 📝 ลงทะเบียนบัญชี MT5
status - 📊 ดูสถานะปัจจุบัน
pause - ⏸️ หยุดรับสัญญาณชั่วคราว
resume - ▶️ เริ่มรับสัญญาณอีกครั้ง
report - 📈 ดูรายงานผลการเทรด
```

---

## 3. ตั้งค่า Signal Server

### ด้วย Docker (แนะนำ)
```bash
git clone https://github.com/singhtofc-cell/Hydra-Trading-System.git
cd Hydra-Trading-System
cp .env.example .env
# แก้ไข .env — ใส่ BOT_TOKEN, ADMIN_CHAT_ID
docker compose up -d
# ตรวจสอบ
curl http://localhost:8788/health
```

### ด้วย Python
```bash
git clone https://github.com/singhtofc-cell/Hydra-Trading-System.git
cd Hydra-Trading-System
pip install -r requirements.txt
export HYDRA_TELEGRAM_BOT_TOKEN="1234567890:ABC..."
export HYDRA_ADMIN_CHAT_ID="123456789"
python -m backend.signal_server
```

---

## 4. ลงทะเบียน Token

1. เปิดไฟล์ `.env` → ใส่ Token จริง
2. หา Chat ID ของตัวเอง: ค้นหา `@userinfobot` ใน Telegram

---

## 5. ติดตั้ง EA บน MT5

1. ดาวน์โหลด `HydraCopyEA.ex5` จาก Admin
2. เปิด MT5 → **File → Open Data Folder**
3. วาง EA ใน `MQL5\Experts\`
4. วาง `HydraEA_Utils.mqh` ใน `MQL5\Include\`
5. สร้าง `MQL5\Files\Hydra\bot_token.txt` — ใส่ Token (บรรทัดเดียว)
6. Restart MT5 → ลาก EA ลง Chart

### เปิด Allow Automated Trading
**Tools → Options → Expert Advisors:**
- ✅ Allow Automated Trading
- ✅ Allow DLL imports
- ✅ เพิ่ม `https://api.telegram.org` ใน WebRequest

---

## 6. ตั้งค่า Input Parameters

### 🔑 Main Settings
| Parameter | คำอธิบาย | USD | USC |
|-----------|----------|-----|-----|
| InpRiskPercent | % ความเสี่ยง | `1.0` | `1.0` |
| InpLotMultiplier | ตัวคูณ Lot | `1.0` | `100` |
| InpMaxLotCap | Lot สูงสุด | `5.0` | `3.0` |
| InpAutoExecute | เทรดอัตโนมัติ | `true` | `true` |
| InpSlippage | Slippage (points) | `30` | `30` |

### 🛡️ Risk Management
| Parameter | ค่า | คำอธิบาย |
|-----------|-----|----------|
| InpMaxDailyLoss | `5.0` | % ขาดทุนสูงสุดต่อวัน |
| InpMaxDrawdown | `15.0` | % DD สูงสุด → ปิดทั้งหมด |
| InpEnableNewsFilter | `true` | หยุดเทรดช่วงข่าว |

---

## 7. ลงทะเบียนกับ Bot

เปิด Telegram Bot → พิมพ์:
```
/register 12345678 USD 1.0
```
หรือสำหรับ Cent:
```
/register 87654321 USC 100
```

### คำสั่งทั้งหมด
| คำสั่ง | การทำงาน |
|--------|----------|
| `/start` | แสดงเมนูต้อนรับ |
| `/register [acc] [cur] [mult]` | ลงทะเบียนบัญชี |
| `/status` | ดูสถานะ |
| `/pause` | หยุดรับสัญญาณ |
| `/resume` | เริ่มรับสัญญาณ |
| `/report` | ดูรายงานวันนี้ |
| `/report weekly` | ดูรายงานสัปดาห์ |

---

## 8. ทดสอบระบบ

### ตรวจสอบ Health
```bash
curl http://YOUR_SERVER:8788/health
```

### ส่ง Signal ทดสอบ
```bash
curl -X POST http://localhost:8788/api/v1/signal/send \
  -H "Content-Type: application/json" \
  -d '{
    "signal_type": "BUY",
    "symbol": "XAUUSD",
    "entry_price": 2350.50,
    "sl_price": 2330.00,
    "tp_prices": [2370.00],
    "lot_multiplier": 1.0,
    "risk_percent": 1.0,
    "source": "TEST"
  }'
```

### ตรวจสอบ EA Log
เปิด MT5 → **Expert Tab** → ควรเห็นข้อความ:
```
🤖 Hydra Copy EA initialized
✅ Signal executed
📍 Order placed: Ticket=12345678 Lot=0.01
```

### ตรวจสอบ Telegram
เปิด Bot → ควรได้รับข้อความ Signal

---

## 9. รายงานและติดตาม

### ⏰ กำหนดการ
| ประเภท | เวลา | เนื้อหา |
|--------|------|---------|
| รายชั่วโมง | ทุกชั่วโมงที่ :00 | P&L, Equity |
| รายวัน | 23:55 UTC | P&L, Win Rate, จำนวนเทรด |
| รายสัปดาห์ | อาทิตย์ 23:55 UTC | สรุปทั้งสัปดาห์ |

### 🖥️ Admin Dashboard
เปิดเบราว์เซอร์ไปที่: `http://YOUR_SERVER:8501`

---

## 10. แก้ไขปัญหา

| ปัญหา | สาเหตุ | วิธีแก้ |
|-------|--------|--------|
| EA ไม่ติด Chart | ปิด Auto Trading | Tools → Options → Allow Automated Trading |
| ไม่ได้สัญญาณ | WebRequest ถูกบล็อก | เพิ่ม api.telegram.org ใน Allow URL |
| Bot token not found | ไม่มีไฟล์ Token | สร้าง bot_token.txt ใน Files\Hydra\ |
| Server ไม่เริ่ม | Port ซ้ำ | เปลี่ยน HYDRA_SERVER_PORT |
| Slippage สูง | ราคาเคลื่อนที่เร็ว | เพิ่ม InpSlippage เป็น 50 |

---

## 📊 ตารางสรุปแยกตามบัญชี

| พารามิเตอร์ | USD Standard | USC Cent |
|-------------|--------------|----------|
| Lot Multiplier | 1.0x | 100x |
| Max Lot Cap | 5.0 | 3.0 |
| Risk % | 1.0% | 1.0% |
| Master 0.01 → | 0.01 USD lot | 1.00 USC lot |
| เหมาะสำหรับพอร์ต | $100-$10,000+ | 5,000-500,000 USC |

---

> **ดูคู่มือแบบเต็มรูปแบบพร้อมภาพประกอบได้ที่:** `docs/setup_guide.html`
> *Hydra Trading System v1.0 — Build with 🧠 for Exness MT5 VPS Copy Trade*
