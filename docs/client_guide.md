     1|# ============================================================================
     2|# Hydra Trading System — Client Guide
     3|# ============================================================================
     4|# คู่มือการติดตั้งและใช้งาน EA สำหรับลูกค้า
     5|# (Client installation and usage guide for Hydra Copy EA)
     6|
     7|# 🐙 Hydra Copy Trade System
     8|# ===========================
     9|#
    10|# ยินดีต้อนรับ! คุณกำลังใช้ระบบ Copy Trade ที่รับสัญญาณเทรดจาก Master
    11|# แล้วส่งตรงถึง MT5 ของคุณผ่าน Telegram Bot
    12|
    13|# 📋 ข้อกำหนดเบื้องต้น
    14|# =====================
    15|# 1. MT5 (MetaTrader 5) ติดตั้งบน VPS หรือเครื่องของคุณ
    16|# 2. บัญชี Exness (Standard USD หรือ Cent USC)
    17|# 3. ติดต่อ Admin เพื่อรับ BOT_TOKEN และลงทะเบียน
    18|# 4. Telegram Account ที่ใช้งาน Active
    19|
    20|# 📥 การติดตั้ง EA
    21|# =================
    22|# 1. ดาวน์โหลดไฟล์ HydraCopyEA.ex5
    23|# 2. วางในโฟลเดอร์: <MT5_Data>\MQL5\Experts\
    24|# 3. วางไฟล์ HydraEA_Utils.mqh ใน: <MT5_Data>\MQL5\Include\
    25|# 4. วางไฟล์ bot_token.txt ใน: <MT5_Data>\MQL5\Files\Hydra\
    26|# 5. รีสตาร์ท MT5 หรือกด Refresh ใน Navigator
    27|# 6. ลาก EA ไปวางบน chart ที่ต้องการ
    28|# 7. ตั้งค่า Input Parameters
    29|
    30|# ⚙️ Input Parameters
    31|# =====================
    32|#
    33|# 🔑 Main Settings:
    34|# - BotUsername: ชื่อ Telegram Bot (default: HydraSignalBot)
    35|# - MagicNumber: ตัวเลขเฉพาะของ EA (default: 20260527)
    36|# - RiskPercent: % ความเสี่ยงต่อการเทรด (default: 1.0%)
    37|# - LotMultiplier: ตัวคูณ Lot (USD=1.0, USC=100)
    38|# - MaxLotCap: Lot สูงสุดที่อนุญาต (default: 5.0)
    39|# - AutoExecute: เทรดอัตโนมัติ (default: true)
    40|# - Slippage: Slippage ที่ยอมรับ (default: 30 points)
    41|#
    42|# 🛡️ Risk Management:
    43|# - MaxDailyLoss: % ขาดทุนสูงสุดต่อวัน (default: 5%)
    44|# - MaxDrawdown: % DD สูงสุด → ปิดทั้งหมด (default: 15%)
    45|# - EnableNewsFilter: หยุดเทรดช่วงข่าว (default: true)
    46|#
    47|# 📊 Reporting:
    48|# - SendReports: ส่งรายงานกลับ Master (default: true)
    49|# - ReportInterval: ส่งรายงานทุก X นาที (default: 60)
    50|
    51|# 🎯 การตั้งค่าแยกตามประเภทบัญชี
    52|# ===============================
    53|#
    54|# 📌 USD Standard (Exness Standard):
    55|#   LotMultiplier = 1.0
    56|#   MaxLotCap = 5.0
    57|#   รับ Master 0.01 lot → เทรด 0.01 lot
    58|#
    59|# 📌 USC Cent (Exness Standard Cent):
    60|#   LotMultiplier = 100
    61|#   MaxLotCap = 3.0 (ป้องกัน Over-leverage)
    62|#   รับ Master 0.01 lot → เทรด 1.00 lot (Cent)
    63|
    64|# 📊 คำอธิบายสัญญาณ
    65|# ====================
    66|# ⚪ NORMAL: สัญญาณ Grid Layer 1-3 ปกติ
    67|# 🟡 URGENT: สัญญาณ Judas Swing, Sweep Trap
    68|# 🚨 EMERGENCY: News kill-switch, Risk Alert
    69|# 🟢 BUY: สัญญาณซื้อ
    70|# 🔴 SELL: สัญญาณขาย
    71|# 🚫 CLOSE_ALL: ปิดออเดอร์ทั้งหมด
    72|
    73|# 🔄 การทำงานของระบบ
    74|# ====================
    75|# 1. Master System (HERMES) สร้างสัญญาณเทรด
    76|# 2. Hydra Signal Server รับและจัดรูปแบบ JSON
    77|# 3. Telegram Bot ส่งสัญญาณไปยังลูกค้าทุกคน
    78|# 4. HydraCopyEA บน MT5 ของคุณรับสัญญาณ
    79|# 5. EA คำนวณ Lot ตาม Risk% ของคุณ
    80|# 6. เทรดอัตโนมัติ (หรือรอ manual)
    81|# 7. ส่งรายงานผลกลับไปยัง Master
    82|
    83|# ⏱️ กำหนดการรายงาน
    84|# ====================
    85|# - รายงานรายชั่วโมง: ทุกๆ ชั่วโมงที่ :00
    86|# - รายงานรายวัน: 23:55 UTC
    87|# - รายงานรายสัปดาห์: วันอาทิตย์ 23:55 UTC
    88|
    89|# 🛡️ การจัดการความเสี่ยง
    90|# ========================
    91|# - ระบบจะหยุดเทรดอัตโนมัติเมื่อถึง Max Daily Loss
    92|# - ปิดออเดอร์ทั้งหมดเมื่อถึง Max Drawdown
    93|# - หลีกเลี่ยงการเทรดช่วงข่าวสำคัญ
    94|# - Rate limiting ป้องกัน Spam
    95|
    96|# ❓ FAQ
    97|# =======
    98|# Q: ต้องติดตั้งอะไรบ้าง?
    99|# A: แค่ดาวน์โหลด EA → วางใน Experts folder → ลากลง Chart
   100|#
   101|# Q: ใช้กับบัญชีไหนได้บ้าง?
   102|# A: Exness Standard USD และ Standard Cent USC
   103|#
   104|# Q: เปลี่ยน Lot ได้ไหม?
   105|# A: ได้! ปรับ LotMultiplier และ MaxLotCap ใน Input
   106|#
   107|# Q: อยากหยุดรับสัญญาณชั่วคราว?
   108|# A: ส่ง /pause ใน Telegram Bot
   109|#
   110|# Q: ดูผลเทรดได้ที่ไหน?
   111|# A: ส่ง /report ใน Telegram Bot หรือเปิด Dashboard
   112|
   113|# 📞 การสนับสนุน
   114|# ================
   115|# หากมีปัญหาหรือข้อสงสัย ติดต่อ Admin ผ่าน Telegram
   116|# หรือส่งอีเมลที่: support@hydra-trading.com
   117|