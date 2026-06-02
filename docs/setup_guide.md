     1|# 🐙 Hydra Trading System — คู่มือการติดตั้งและใช้งาน (ฉบับย่อ)
     2|
     3|> **เวอร์ชันเต็ม (HTML พร้อมภาพประกอบ):** ดูได้ที่ `docs/setup_guide.html`
     4|> เปิดไฟล์ใน Browser เพื่อดูคู่มือแบบ Step-by-Step พร้อมรูปภาพ
     5|
     6|---
     7|
     8|## 📋 สารบัญ
     9|
    10|1. [เตรียมความพร้อม](#1-เตรียมความพร้อม)
    11|2. [สร้าง Telegram Bot](#2-สร้าง-telegram-bot)
    12|3. [ตั้งค่า Signal Server](#3-ตั้งค่า-signal-server)
    13|4. [ลงทะเบียน Token](#4-ลงทะเบียน-token)
    14|5. [ติดตั้ง EA บน MT5](#5-ติดตั้ง-ea-บน-mt5)
    15|6. [ตั้งค่า Input Parameters](#6-ตั้งค่า-input-parameters)
    16|7. [ลงทะเบียนกับ Bot](#7-ลงทะเบียนกับ-bot)
    17|8. [ทดสอบระบบ](#8-ทดสอบระบบ)
    18|9. [รายงานและติดตาม](#9-รายงานและติดตาม)
    19|10. [แก้ไขปัญหา](#10-แก้ไขปัญหา)
    20|
    21|---
    22|
    23|## 1. เตรียมความพร้อม
    24|
    25|### ✅ สิ่งที่ต้องมี
    26|- ✅ บัญชี Exness (Standard USD หรือ Standard Cent USC)
    27|- ✅ MT5 ติดตั้งบน VPS หรือเครื่องของคุณ
    28|- ✅ บัญชี Telegram ที่ใช้งานอยู่
    29|- ✅ VPS ที่เปิดตลอด 24/7
    30|- ✅ Internet connection ที่เสถียร
    31|
    32|### 📌 ข้อมูลที่ต้องเตรียม
    33|| ข้อมูล | คำอธิบาย | ตัวอย่าง |
    34||--------|----------|----------|
    35|| Telegram Chat ID | ID ที่ Bot จะส่งสัญญาณไปให้ | `123456789` |
    36|| MT5 Account Number | เลขบัญชี MT5 | `12345678` |
    37|| Account Currency | USD หรือ USC | `USD` หรือ `USC` |
    38|| Lot Multiplier | ตัวคูณ Lot | `1.0` (USD) หรือ `100` (USC) |
    39|
    40|---
    41|
    42|## 2. สร้าง Telegram Bot
    43|
    44|1. เปิด Telegram → ค้นหา `@BotFather`
    45|2. พิมพ์ `/newbot`
    46|3. ตั้งชื่อ: `Hydra Signal Bot`
    47|4. ตั้ง Username: `YourHydraSignalBot` (ต้องลงท้ายด้วย `bot`)
    48|5. **เก็บ BOT_TOKEN ที่ได้!**
    49|
    50|### ตั้งค่า Bot Commands
    51|พิมพ์ `/setcommands` ใน BotFather แล้วส่ง:
    52|```
    53|start - 🤖 เริ่มต้นใช้งาน
    54|register - 📝 ลงทะเบียนบัญชี MT5
    55|status - 📊 ดูสถานะปัจจุบัน
    56|pause - ⏸️ หยุดรับสัญญาณชั่วคราว
    57|resume - ▶️ เริ่มรับสัญญาณอีกครั้ง
    58|report - 📈 ดูรายงานผลการเทรด
    59|```
    60|
    61|---
    62|
    63|## 3. ตั้งค่า Signal Server
    64|
    65|### ด้วย Docker (แนะนำ)
    66|```bash
    67|git clone https://github.com/singhtofc-cell/Hydra-Trading-System.git
    68|cd Hydra-Trading-System
    69|cp .env.example .env
    70|# แก้ไข .env — ใส่ BOT_TOKEN, ADMIN_CHAT_ID
    71|docker compose up -d
    72|# ตรวจสอบ
    73|curl http://localhost:8788/health
    74|```
    75|
    76|### ด้วย Python
    77|```bash
    78|git clone https://github.com/singhtofc-cell/Hydra-Trading-System.git
    79|cd Hydra-Trading-System
    80|pip install -r requirements.txt
    81|export HYDRA_TELEGRAM_BOT_TOKEN="1234567890:ABC..."
    82|export HYDRA_ADMIN_CHAT_ID="123456789"
    83|python -m backend.signal_server
    84|```
    85|
    86|---
    87|
    88|## 4. ลงทะเบียน Token
    89|
    90|1. เปิดไฟล์ `.env` → ใส่ Token จริง
    91|2. หา Chat ID ของตัวเอง: ค้นหา `@userinfobot` ใน Telegram
    92|
    93|---
    94|
    95|## 5. ติดตั้ง EA บน MT5
    96|
    97|1. ดาวน์โหลด `HydraCopyEA.ex5` จาก Admin
    98|2. เปิด MT5 → **File → Open Data Folder**
    99|3. วาง EA ใน `MQL5\Experts\`
   100|4. วาง `HydraEA_Utils.mqh` ใน `MQL5\Include\`
   101|5. สร้าง `MQL5\Files\Hydra\bot_token.txt` — ใส่ Token (บรรทัดเดียว)
   102|6. Restart MT5 → ลาก EA ลง Chart
   103|
   104|### เปิด Allow Automated Trading
   105|**Tools → Options → Expert Advisors:**
   106|- ✅ Allow Automated Trading
   107|- ✅ Allow DLL imports
   108|- ✅ เพิ่ม `https://api.telegram.org` ใน WebRequest
   109|
   110|---
   111|
   112|## 6. ตั้งค่า Input Parameters
   113|
   114|### 🔑 Main Settings
   115|| Parameter | คำอธิบาย | USD | USC |
   116||-----------|----------|-----|-----|
   117|| InpRiskPercent | % ความเสี่ยง | `1.0` | `1.0` |
   118|| InpLotMultiplier | ตัวคูณ Lot | `1.0` | `100` |
   119|| InpMaxLotCap | Lot สูงสุด | `5.0` | `3.0` |
   120|| InpAutoExecute | เทรดอัตโนมัติ | `true` | `true` |
   121|| InpSlippage | Slippage (points) | `30` | `30` |
   122|
   123|### 🛡️ Risk Management
   124|| Parameter | ค่า | คำอธิบาย |
   125||-----------|-----|----------|
   126|| InpMaxDailyLoss | `5.0` | % ขาดทุนสูงสุดต่อวัน |
   127|| InpMaxDrawdown | `15.0` | % DD สูงสุด → ปิดทั้งหมด |
   128|| InpEnableNewsFilter | `true` | หยุดเทรดช่วงข่าว |
   129|
   130|---
   131|
   132|## 7. ลงทะเบียนกับ Bot
   133|
   134|เปิด Telegram Bot → พิมพ์:
   135|```
   136|/register 12345678 USD 1.0
   137|```
   138|หรือสำหรับ Cent:
   139|```
   140|/register 87654321 USC 100
   141|```
   142|
   143|### คำสั่งทั้งหมด
   144|| คำสั่ง | การทำงาน |
   145||--------|----------|
   146|| `/start` | แสดงเมนูต้อนรับ |
   147|| `/register [acc] [cur] [mult]` | ลงทะเบียนบัญชี |
   148|| `/status` | ดูสถานะ |
   149|| `/pause` | หยุดรับสัญญาณ |
   150|| `/resume` | เริ่มรับสัญญาณ |
   151|| `/report` | ดูรายงานวันนี้ |
   152|| `/report weekly` | ดูรายงานสัปดาห์ |
   153|
   154|---
   155|
   156|## 8. ทดสอบระบบ
   157|
   158|### ตรวจสอบ Health
   159|```bash
   160|curl http://YOUR_SERVER:8788/health
   161|```
   162|
   163|### ส่ง Signal ทดสอบ
   164|```bash
   165|curl -X POST http://localhost:8788/api/v1/signal/send \
   166|  -H "Content-Type: application/json" \
   167|  -d '{
   168|    "signal_type": "BUY",
   169|    "symbol": "XAUUSD",
   170|    "entry_price": 2350.50,
   171|    "sl_price": 2330.00,
   172|    "tp_prices": [2370.00],
   173|    "lot_multiplier": 1.0,
   174|    "risk_percent": 1.0,
   175|    "source": "TEST"
   176|  }'
   177|```
   178|
   179|### ตรวจสอบ EA Log
   180|เปิด MT5 → **Expert Tab** → ควรเห็นข้อความ:
   181|```
   182|🤖 Hydra Copy EA initialized
   183|✅ Signal executed
   184|📍 Order placed: Ticket=12345678 Lot=0.01
   185|```
   186|
   187|### ตรวจสอบ Telegram
   188|เปิด Bot → ควรได้รับข้อความ Signal
   189|
   190|---
   191|
   192|## 9. รายงานและติดตาม
   193|
   194|### ⏰ กำหนดการ
   195|| ประเภท | เวลา | เนื้อหา |
   196||--------|------|---------|
   197|| รายชั่วโมง | ทุกชั่วโมงที่ :00 | P&L, Equity |
   198|| รายวัน | 23:55 UTC | P&L, Win Rate, จำนวนเทรด |
   199|| รายสัปดาห์ | อาทิตย์ 23:55 UTC | สรุปทั้งสัปดาห์ |
   200|
   201|### 🖥️ Admin Dashboard
   202|เปิดเบราว์เซอร์ไปที่: `http://YOUR_SERVER:8501`
   203|
   204|---
   205|
   206|## 10. แก้ไขปัญหา
   207|
   208|| ปัญหา | สาเหตุ | วิธีแก้ |
   209||-------|--------|--------|
   210|| EA ไม่ติด Chart | ปิด Auto Trading | Tools → Options → Allow Automated Trading |
   211|| ไม่ได้สัญญาณ | WebRequest ถูกบล็อก | เพิ่ม api.telegram.org ใน Allow URL |
   212|| Bot token not found | ไม่มีไฟล์ Token | สร้าง bot_token.txt ใน Files\Hydra\ |
   213|| Server ไม่เริ่ม | Port ซ้ำ | เปลี่ยน HYDRA_SERVER_PORT |
   214|| Slippage สูง | ราคาเคลื่อนที่เร็ว | เพิ่ม InpSlippage เป็น 50 |
   215|
   216|---
   217|
   218|## 📊 ตารางสรุปแยกตามบัญชี
   219|
   220|| พารามิเตอร์ | USD Standard | USC Cent |
   221||-------------|--------------|----------|
   222|| Lot Multiplier | 1.0x | 100x |
   223|| Max Lot Cap | 5.0 | 3.0 |
   224|| Risk % | 1.0% | 1.0% |
   225|| Master 0.01 → | 0.01 USD lot | 1.00 USC lot |
   226|| เหมาะสำหรับพอร์ต | $100-$10,000+ | 5,000-500,000 USC |
   227|
   228|---
   229|
   230|> **ดูคู่มือแบบเต็มรูปแบบพร้อมภาพประกอบได้ที่:** `docs/setup_guide.html`
   231|> *Hydra Trading System v1.0 — Build with 🧠 for Exness MT5 VPS Copy Trade*
   232|