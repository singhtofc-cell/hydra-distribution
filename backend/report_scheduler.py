# ============================================================================
# Hydra Report Scheduler — Automated Signal & Performance Reports
# ============================================================================
# Renamed from HERMES → Hydra for standalone copy-trade distribution
# Source: Qwen Architecture Proposal 2026-06-02 — Phase 5
#
# Sends automated performance reports (hourly/daily/weekly) to clients
# and admin summary via the Telegram Bot. Uses APScheduler for cron-style
# scheduling.

import os
import json
import logging
import asyncio
import yaml
from datetime import datetime, timedelta
from typing import Optional, Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hydra.report_scheduler")


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


class ReportScheduler:
    """Automated report dispatch system for Hydra clients.

    Schedules and sends performance reports at configurable intervals
    (hourly, daily, weekly) to both clients and the admin.
    """

    def __init__(self, tracker=None):
        self.tracker = tracker  # PerformanceTracker instance
        self.bot_token = BOT_TOKEN
        self.admin_chat_id = ADMIN_CHAT_ID
        self._scheduler = None

    # ------------------------------------------------------------------
    # Report Formatting
    # ------------------------------------------------------------------
    def _format_hourly_report(self, stats: dict) -> str:
        """Format an hourly performance report."""
        pnl = stats.get("total_pnl", 0)
        pnl_emoji = "🟢" if pnl >= 0 else "🔴"
        return f"""
⏰ <b>รายงานรายชั่วโมง</b>
🕐 {stats.get('hour', 'N/A')}:00
━━━━━━━━━━━━━━━━━━━━
{pnl_emoji} P/L: <b>{pnl:+.2f} {stats.get('currency', 'USD')}</b>
📈 เทรดวันนี้: {stats.get('today_trades', 0)}
💵 Equity: {stats.get('equity', 0):.2f}
<i>Hydra Trading System v1.0</i>
""".strip()

    def _format_daily_report(self, report: dict, client: dict) -> str:
        """Format a daily performance report."""
        currency = client.get("account_currency", "USD")
        pnl = report.get("total_pnl", 0)
        pnl_emoji = "🟢" if pnl >= 0 else "🔴"

        return f"""
📊 <b>รายงานประจำวัน</b>
📅 {report.get('date', 'N/A')}
━━━━━━━━━━━━━━━━━━━━
{pnl_emoji} P/L: <b>{pnl:+.2f} {currency}</b>
📈 เทรดทั้งหมด: {report.get('total_trades', 0)}
✅ ชนะ: {report.get('wins', 0)} | ❌ แพ้: {report.get('losses', 0)}
🎯 Win Rate: {report.get('win_rate', 0):.1f}%

<i>Hydra Trading System v1.0 🙏</i>
""".strip()

    def _format_admin_summary(self, summary: dict) -> str:
        """Format an admin summary across all clients."""
        return f"""
👑 <b>Admin Summary — Hydra Distribution</b>
🕐 {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
━━━━━━━━━━━━━━━━━━━━━━━
👥 ลูกค้าทั้งหมด: <b>{summary.get('total_clients', 0)}</b>
📡 สัญญาณที่ส่ง: <b>{summary.get('total_signals_dispatched', 0)}</b>
📈 เทรดทั้งหมด: <b>{summary.get('total_trades_executed', 0)}</b>
✅ ชนะ: {summary.get('total_wins', 0)} | ❌ แพ้: {summary.get('total_losses', 0)}
🎯 Win Rate รวม: <b>{summary.get('overall_win_rate', 0):.1f}%</b>

<i>Hydra Trading System v1.0</i>
""".strip()

    # ------------------------------------------------------------------
    # Telegram Dispatch
    # ------------------------------------------------------------------
    async def send_telegram_message(self, chat_id: int, message: str):
        """Send a formatted message to a Telegram chat."""
        if not self.bot_token or self.bot_token == "YOUR_TELEGRAM_BOT_TOKEN":
            logger.warning("Bot token not configured — cannot send")
            return

        import aiohttp
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"Telegram send failed to {chat_id}: {resp.status}")
                else:
                    logger.debug(f"Report sent to chat {chat_id}")

    # ------------------------------------------------------------------
    # Report Generators (override with real data in production)
    # ------------------------------------------------------------------
    async def _get_active_clients(self) -> List[dict]:
        """Fetch all active clients from the database."""
        # In production: query PostgreSQL
        return []  # Override with real client list

    async def hourly_report(self):
        """Send hourly performance reports to all active clients."""
        now = datetime.utcnow()
        logger.info(f"Generating hourly report for {now.strftime('%H:00')}")

        clients = await self._get_active_clients()
        for client in clients:
            # TODO: pull real stats from PerformanceTracker
            stats = {
                "hour": now.hour,
                "total_pnl": 0.0,
                "today_trades": 0,
                "equity": 0.0,
                "currency": client.get("account_currency", "USD")
            }
            message = self._format_hourly_report(stats)
            await self.send_telegram_message(client["telegram_chat_id"], message)

        # Also send to admin
        if self.admin_chat_id:
            admin_msg = f"⏰ รายงานรายชั่วโมง {now.hour}:00 — ส่งถึง {len(clients)} ลูกค้า"
            await self.send_telegram_message(self.admin_chat_id, admin_msg)

    async def daily_report(self):
        """Send daily performance reports to all active clients + admin."""
        today = datetime.utcnow().date()
        logger.info(f"Generating daily report for {today}")

        clients = await self._get_active_clients()
        for client in clients:
            report = await self.tracker.get_daily_report(
                client["client_id"],
                datetime.combine(today, datetime.min.time())
            ) if self.tracker else {
                "date": today.isoformat(),
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0,
                "total_pnl": 0
            }

            message = self._format_daily_report(report, client)
            await self.send_telegram_message(client["telegram_chat_id"], message)

        # Admin summary
        if self.admin_chat_id and self.tracker:
            admin_summary = await self.tracker.get_admin_summary()
            message = self._format_admin_summary(admin_summary)
            await self.send_telegram_message(self.admin_chat_id, message)

    async def weekly_report(self):
        """Send weekly summary reports."""
        logger.info("Generating weekly report...")
        await self.daily_report()  # Same format, but extends to weekly scope

    # ------------------------------------------------------------------
    # Scheduler
    # ------------------------------------------------------------------
    async def start(self):
        """Start the APScheduler with configured job intervals."""
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            from apscheduler.triggers.cron import CronTrigger
        except ImportError:
            logger.warning("APScheduler not installed. Install: pip install apscheduler")
            return

        self._scheduler = AsyncIOScheduler()

        # Hourly report (at minute 0)
        self._scheduler.add_job(
            self.hourly_report,
            CronTrigger(minute=0),
            id="hydra_hourly_report",
            name="Hydra Hourly Report"
        )

        # Daily report (at 23:55 UTC)
        self._scheduler.add_job(
            self.daily_report,
            CronTrigger(hour=23, minute=55),
            id="hydra_daily_report",
            name="Hydra Daily Report"
        )

        # Weekly report (Sunday 23:55)
        self._scheduler.add_job(
            self.weekly_report,
            CronTrigger(day_of_week="sun", hour=23, minute=55),
            id="hydra_weekly_report",
            name="Hydra Weekly Report"
        )

        self._scheduler.start()
        logger.info("✅ Hydra Report Scheduler started")
        logger.info("  - Hourly: every hour at :00")
        logger.info("  - Daily: 23:55 UTC")
        logger.info("  - Weekly: Sunday 23:55 UTC")

        # Keep running
        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            logger.info("Scheduler shutting down...")
            self._scheduler.shutdown()


# ============================================================================
# Entry Point
# ============================================================================
async def main():
    scheduler = ReportScheduler()
    await scheduler.start()


if __name__ == "__main__":
    asyncio.run(main())
