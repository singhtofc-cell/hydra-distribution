# ============================================================================
# Hydra Trading System — Client Guide
# ============================================================================
# คู่มือการติดตั้งและใช้งาน EA สำหรับลูกค้า
# (Client installation and usage guide for Hydra Copy EA)

# 🪬 Hydra Copy Trade System
# ===========================
#
# ยินดีต้อนรับ! คุณกำลังใช้ระบบ Copy Trade ที่รับสัญญาณเทรดจาก Master
# แล้วส่งตรงถึง MT5 ของคุณผ่าน Telegram Bot

# 📋 ข้อกำหนดเบื้องต้น
# =====================
# 1. MT5 (MetaTrader 5) ติดตั้งบน VPS หรือเครื่องของคุณ
# 2. บัญชี Exness (Standard USD หรือ Cent USC)
# 3. ติดต่อ Admin เพื่อรับ BOT_TOKEN และลงทะเบียน
# 4. Telegram Account ที่ใช้งาน Active

# 📥 การติดตั้ง EA
# =================
# 1. ดาวน์โหลดไฟล์ HydraCopyEA.ex5
# 2. วางในโฟลเดอร์: <MT5_Data>\MQL5\Experts\
# 3. วางไฟล์ HydraEA_Utils.mqh ใน: <MT5_Data>\MQL5\Include\
# 4. วางไฟล์ bot_token.txt ใน: <MT5_Data>\MQL5\Files\Hydra\
# 5. รีสตาร์ท MT5 หรือกด Refresh ใน Navigator
# 6. ลาก EA ไปวางบน chart ที่ต้องการ
# 7. ตั้งค่า Input Parameters

# ⚙️ Input Parameters
# =====================
#
# 🔑 Main Settings:
# - BotUsername: ชื่อ Telegram Bot (default: HydraSignalBot)
# - MagicNumber: ตัวเลขเฉพาะของ EA (default: 20260527)
# - RiskPercent: % ความเสี่ยงต่อการเทรด (default: 1.0%)
# - LotMultiplier: ตัวคูณ Lot (USD=1.0, USC=100)
# - MaxLotCap: Lot สูงสุดที่อนุญาต (default: 5.0)
# - AutoExecute: เทรดอัตโนมัติ (default: true)
# - Slippage: Slippage ที่ยอมรับ (default: 30 points)
#
# 🛡️ Risk Management:
# - MaxDailyLoss: % ขาดทุนสูงสุดต่อวัน (default: 5%)
# - MaxDrawdown: % DD สูงสุด → ปิดทั้งหมด (default: 15%)
# - EnableNewsFilter: หยุดเทรดช่วงข่าว (default: true)
#
# 📊 Reporting:
# - SendReports: ส่งรายงานกลับ Master (default: true)
# - ReportInterval: ส่งรายงานทุก X นาที (default: 60)

# 🎯 การตั้งค่าแยกตามประเภทบัญชี
# ===============================
#
# 📌 USD Standard (Exness Standard):
#   LotMultiplier = 1.0
#   MaxLotCap = 5.0
#   รับ Master 0.01 lot → เทรด 0.01 lot
#
# 📌 USC Cent (Exness Standard Cent):
#   LotMultiplier = 100
#   MaxLotCap = 3.0 (ป้องกัน Over-leverage)
#   รับ Master 0.01 lot → เทรด 1.00 lot (Cent)

# 📊 คำอธิบายสัญญาณ
# ====================
# ⚪ NORMAL: สัญญาณ Grid Layer 1-3 ปกติ
# 🟡 URGENT: สัญญาณ Judas Swing, Sweep Trap
# 🚨 EMERGENCY: News kill-switch, Risk Alert
# 🟢 BUY: สัญญาณซื้อ
# 🔴 SELL: สัญญาณขาย
# 🚫 CLOSE_ALL: ปิดออเดอร์ทั้งหมด

# 🔄 การทำงานของระบบ
# ====================
# 1. Master System (HERMES) สร้างสัญญาณเทรด
# 2. Hydra Signal Server รับและจัดรูปแบบ JSON
# 3. Telegram Bot ส่งสัญญาณไปยังลูกค้าทุกคน
# 4. HydraCopyEA บน MT5 ของคุณรับสัญญาณ
# 5. EA คำนวณ Lot ตาม Risk% ของคุณ
# 6. เทรดอัตโนมัติ (หรือรอ manual)
# 7. ส่งรายงานผลกลับไปยัง Master

# ⏱️ กำหนดการรายงาน
# ====================
# - รายงานรายชั่วโมง: ทุกๆ ชั่วโมงที่ :00
# - รายงานรายวัน: 23:55 UTC
# - รายงานรายสัปดาห์: วันอาทิตย์ 23:55 UTC

# 🛡️ การจัดการความเสี่ยง
# ========================
# - ระบบจะหยุดเทรดอัตโนมัติเมื่อถึง Max Daily Loss
# - ปิดออเดอร์ทั้งหมดเมื่อถึง Max Drawdown
# - หลีกเลี่ยงการเทรดช่วงข่าวสำคัญ
# - Rate limiting ป้องกัน Spam

# ❓ FAQ
# =======
# Q: ต้องติดตั้งอะไรบ้าง?
# A: แค่ดาวน์โหลด EA → วางใน Experts folder → ลากลง Chart
#
# Q: ใช้กับบัญชีไหนได้บ้าง?
# A: Exness Standard USD และ Standard Cent USC
#
# Q: เปลี่ยน Lot ได้ไหม?
# A: ได้! ปรับ LotMultiplier และ MaxLotCap ใน Input
#
# Q: อยากหยุดรับสัญญาณชั่วคราว?
# A: ส่ง /pause ใน Telegram Bot
#
# Q: ดูผลเทรดได้ที่ไหน?
# A: ส่ง /report ใน Telegram Bot หรือเปิด Dashboard

# 📞 การสนับสนุน
# ================
# หากมีปัญหาหรือข้อสงสัย ติดต่อ Admin ผ่าน Telegram
# หรือส่งอีเมลที่: support@hydra-trading.com
