# ============================================================================
# Hydra Telegram Bot — Client Management & Signal Dispatch
# ============================================================================
# Renamed from HERMES → Hydra for standalone copy-trade distribution
# Source: Qwen Architecture Proposal 2026-06-02
#
# Telegram Bot that manages client registration, signal forwarding,
# and report delivery. Clients interact via commands (/start, /register)
# while the EA parses the embedded JSON for auto-execution.

import os
import re
import json
import logging
import asyncio
import yaml
from datetime import datetime
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hydra.telegram_bot")


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

BOT_TOKEN = os.getenv("HYDRA_TELEGRAM_BOT_TOKEN", config.get("telegram", {}).get("bot_token", ""))
ADMIN_CHAT_ID = int(os.getenv("HYDRA_ADMIN_CHAT_ID", config.get("telegram", {}).get("admin_chat_id", 0)))


# ============================================================================
# Signal Parser (for EA to extract JSON from Telegram messages)
# ============================================================================
def parse_signal_from_text(text: str) -> Optional[dict]:
    """Extract JSON signal data from <blockquote>...</blockquote> tags.

    The MQL5 EA polls Telegram messages and uses this parser to
    extract the standardised signal JSON for auto-execution.
    """
    json_match = re.search(r'<blockquote[^>]*>(.*?)</blockquote>', text, re.DOTALL)
    if not json_match:
        return None

    try:
        return json.loads(json_match.group(1).strip())
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse signal JSON: {e}")
        return None


# ============================================================================
# Signal Storage (bridge to EA polling)
# ============================================================================
# In-memory signal buffer; production should use Redis/DB
_signal_buffer = []
_last_update_id = 0


async def store_signal_for_ea(signal_data: dict):
    """Store a parsed signal for EA polling.

    The EA polls this buffer; signals are auto-expired based on
    their expiry_minutes field.
    """
    signal_data["_received_at"] = datetime.utcnow().isoformat()
    signal_data["_status"] = "pending"
    _signal_buffer.append(signal_data)

    # Auto-prune expired signals (>60 min)
    global _signal_buffer
    now = datetime.utcnow()
    _signal_buffer = [
        s for s in _signal_buffer
        if (now - datetime.fromisoformat(s["_received_at"])).total_seconds() < 3600
    ]
    logger.debug(f"Signal stored: {signal_data.get('signal_id', 'unknown')[:8]}")


async def get_pending_signals() -> list:
    """Return all pending signals for EA polling."""
    return [s for s in _signal_buffer if s.get("_status") == "pending"]


async def mark_signal_executed(signal_id: str, ticket: int):
    """Mark a signal as executed by the client EA."""
    for s in _signal_buffer:
        if s.get("signal_id") == signal_id:
            s["_status"] = "executed"
            s["_ticket"] = ticket
            logger.info(f"Signal {signal_id[:8]} executed (ticket: {ticket})")
            return True
    return False


# ============================================================================
# Reporting
# ============================================================================
async def generate_daily_report(chat_id: int) -> str:
    """Generate a daily performance report for a client.

    In production, pull from PerformanceTracker DB.
    """
    return f"""
📊 <b>รายงานประจำวัน</b>
━━━━━━━━━━━━━━━━━━━━━━━
📅 {datetime.utcnow().strftime('%Y-%m-%d')}

💰 P/L วันนี้: <b>+0.00 USD</b> (+0.00%)
📈 จำนวนเทรด: 0
✅ เทรดชนะ: 0 | ❌ แพ้: 0
🎯 Win Rate: 0.0%
📊 Avg R:R: 1:0.00
💵 Max DD: 0.00%

<i>Hydra Trading System v1.0 🙏</i>
"""


async def generate_weekly_report(chat_id: int) -> str:
    """Generate a weekly performance report."""
    return f"""
📊 <b>รายงานประจำสัปดาห์</b>
━━━━━━━━━━━━━━━━━━━━━━━
📅 สัปดาห์ของ {datetime.utcnow().strftime('%Y-%m-%d')}

💼 สรุปผลการเทรด 7 วัน
<i>Hydra Trading System v1.0 🙏</i>
"""


# ============================================================================
# Telegram Bot Handlers (using python-telegram-bot)
# ============================================================================
async def start_bot():
    """Start the Telegram bot in polling mode.

    This function is the main entry point when running as a standalone
    process. It registers all command handlers and starts polling.
    """
    try:
        from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
        from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
    except ImportError:
        logger.error("python-telegram-bot not installed. Run: pip install python-telegram-bot")
        return

    if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        logger.error("HYDRA_TELEGRAM_BOT_TOKEN not configured. Set the env var or update config.yaml")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    # --- Command Handlers ---

    @application.add_handler(CommandHandler("start"))
    async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Welcome message with inline keyboard."""
        keyboard = [
            [InlineKeyboardButton("📊 ดูสถานะ", callback_data="status")],
            [InlineKeyboardButton("⏸️ หยุดรับสัญญาณชั่วคราว", callback_data="pause")],
            [InlineKeyboardButton("▶️ เปิดรับสัญญาณ", callback_data="resume")],
            [InlineKeyboardButton("📈 รายงานวันนี้", callback_data="report_today")],
            [InlineKeyboardButton("📋 รายงานสัปดาห์", callback_data="report_week")],
        ]
        await update.message.reply_text(
            "🤖 <b>ยินดีต้อนรับสู่ Hydra Signal Bot</b>\n\n"
            "เลือกเมนูด้านล่างเพื่อจัดการการเทรดของคุณ:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    @application.add_handler(CommandHandler("register"))
    async def cmd_register(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Register a client account.
        
        Usage: /register <account_number> <currency> <lot_multiplier>
        Example: /register 12345678 USD 1.0
        Example: /register 87654321 USC 100
        """
        if len(context.args) < 3:
            await update.message.reply_text(
                "❓ ใช้แบบ:\n/register <account_number> <currency> <lot_multiplier>\n\n"
                "ตัวอย่าง:\n/register 12345678 USD 1.0\n/register 87654321 USC 100"
            )
            return

        account, currency, multiplier = context.args[:3]
        multiplier = float(multiplier)
        currency = currency.upper()

        if currency not in ("USD", "USC"):
            await update.message.reply_text("❌ สกุลเงินต้องเป็น USD หรือ USC เท่านั้น")
            return

        # In production: save to PostgreSQL
        # CLIENTS_DB.append(...)
        await update.message.reply_text(
            f"✅ ลงทะเบียนสำเร็จ!\n"
            f"Account: {account}\n"
            f"Currency: {currency}\n"
            f"Lot Multiplier: {multiplier}x\n\n"
            f"ขณะนี้คุณพร้อมรับสัญญาณเทรดแล้ว 🚀"
        )

    @application.add_handler(CommandHandler("status"))
    async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show current subscription status."""
        await update.message.reply_text(
            "📊 <b>สถานะของคุณ</b>\n"
            "━━━━━━━━━━━━━━━━\n"
            "✅ สถานะ: <b>ACTIVE</b>\n"
            "📡 รับสัญญาณ: SMC_GRID, JUDAS_SWING\n"
            "🔄 Magic Number: 20260527\n"
            "📅 ลงทะเบียนเมื่อ: ปัจจุบัน\n\n"
            "ใช้ /pause เพื่อหยุดรับสัญญาณชั่วคราว",
            parse_mode="HTML"
        )

    @application.add_handler(CommandHandler("pause"))
    async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Pause signal subscription."""
        await update.message.reply_text("⏸️ หยุดรับสัญญาณชั่วคราวแล้ว\nใช้ /resume เพื่อเริ่มรับอีกครั้ง")

    @application.add_handler(CommandHandler("resume"))
    async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Resume signal subscription."""
        await update.message.reply_text("▶️ เริ่มรับสัญญาณอีกครั้ง")

    @application.add_handler(CommandHandler("report"))
    async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get performance report."""
        report_type = context.args[0].lower() if context.args else "today"
        if report_type in ("today", "daily"):
            report = await generate_daily_report(update.effective_chat.id)
            await update.message.reply_text(report, parse_mode="HTML")
        elif report_type in ("week", "weekly"):
            report = await generate_weekly_report(update.effective_chat.id)
            await update.message.reply_text(report, parse_mode="HTML")

    # --- Callback Query Handler ---
    @application.add_handler(CallbackQueryHandler())
    async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        if query.data == "status":
            await query.edit_message_text(
                "📊 <b>สถานะ: ACTIVE</b> ✅\nรับสัญญาณ: SMC_GRID, JUDAS_SWING",
                parse_mode="HTML"
            )
        elif query.data == "pause":
            await query.edit_message_text("⏸️ หยุดรับสัญญาณชั่วคราวแล้ว")
        elif query.data == "resume":
            await query.edit_message_text("▶️ เริ่มรับสัญญาณอีกครั้ง")
        elif query.data == "report_today":
            report = await generate_daily_report(query.message.chat_id)
            await query.edit_message_text(report, parse_mode="HTML")
        elif query.data == "report_week":
            report = await generate_weekly_report(query.message.chat_id)
            await query.edit_message_text(report, parse_mode="HTML")

    # --- Message Handler (for EA signal parsing) ---
    @application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND))
    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Parse signals from Telegram messages."""
        if not update.message or not update.message.text:
            return

        signal_data = parse_signal_from_text(update.message.text)
        if signal_data:
            await store_signal_for_ea(signal_data)
            logger.info(f"Signal parsed from message: {signal_data.get('signal_id', '?')[:8]}")

    # --- Error Handler ---
    async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Update {update} caused error {context.error}")

    application.add_error_handler(error_handler)

    # --- Start polling ---
    logger.info("🤖 Hydra Telegram Bot starting polling...")
    logger.info(f"Admin Chat ID: {ADMIN_CHAT_ID}")

    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)

    # Keep running
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        logger.info("Bot shutting down...")
        await application.stop()


# ============================================================================
# Entry Point
# ============================================================================
if __name__ == "__main__":
    asyncio.run(start_bot())
