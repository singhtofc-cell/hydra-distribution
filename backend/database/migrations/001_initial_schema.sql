-- ============================================================================
-- Migration 001: Initial Schema
-- ============================================================================
-- Run: psql -U hydra -d hydra_trading -f schema.sql

-- Applied at: 2026-06-02
-- Rollback: DROP TABLE IF EXISTS system_events, daily_reports, trade_fills, signals, clients CASCADE;
SELECT 'Migration 001 applied successfully' AS status;
