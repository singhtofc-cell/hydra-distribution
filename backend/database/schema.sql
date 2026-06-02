-- ============================================================================
-- Hydra Trading System — PostgreSQL Database Schema
-- ============================================================================
-- Renamed from HERMES → Hydra for standalone copy-trade distribution
-- Source: Qwen Architecture Proposal 2026-06-02 — Phase 4
--
-- Supports: signal dispatch logging, client management, trade fill tracking,
-- automated reporting, and admin dashboards.

-- ============================================================================
-- ENUMS
-- ============================================================================
CREATE TYPE client_status AS ENUM ('ACTIVE', 'PAUSED', 'SUSPENDED');
CREATE TYPE signal_type AS ENUM ('BUY', 'SELL', 'CLOSE_ALL', 'MODIFY_SL', 'PARTIAL_CLOSE', 'CANCEL');
CREATE TYPE signal_priority AS ENUM ('NORMAL', 'URGENT', 'EMERGENCY');
CREATE TYPE signal_status AS ENUM ('sent', 'filled', 'expired', 'cancelled');
CREATE TYPE trade_status AS ENUM ('open', 'closed_tp', 'closed_sl', 'closed_manual');
CREATE TYPE account_currency AS ENUM ('USD', 'USC');

-- ============================================================================
-- CLIENTS
-- ============================================================================
CREATE TABLE IF NOT EXISTS clients (
    client_id          VARCHAR(64) PRIMARY KEY,
    telegram_chat_id   BIGINT UNIQUE NOT NULL,
    account_number     VARCHAR(64) NOT NULL,
    account_currency   account_currency NOT NULL DEFAULT 'USD',
    lot_multiplier     DECIMAL(10,2) NOT NULL DEFAULT 1.0,
    risk_percent       DECIMAL(4,2) NOT NULL DEFAULT 1.0,
    max_lot_cap        DECIMAL(10,2) NOT NULL DEFAULT 5.0,
    status             client_status NOT NULL DEFAULT 'ACTIVE',
    subscribed_strategies TEXT[] DEFAULT '{SMC_GRID, JUDAS_SWING, ICT_SMC}',
    registered_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_active_at     TIMESTAMPTZ,
    notes              TEXT,

    CONSTRAINT valid_risk CHECK (risk_percent >= 0.1 AND risk_percent <= 5.0),
    CONSTRAINT valid_lot CHECK (lot_multiplier >= 0.1 AND lot_multiplier <= 1000.0),
    CONSTRAINT valid_lot_cap CHECK (max_lot_cap > 0 AND max_lot_cap <= 100.0)
);

CREATE INDEX idx_clients_status ON clients(status);
CREATE INDEX idx_clients_currency ON clients(account_currency);

-- ============================================================================
-- SIGNALS (dispatched signals log)
-- ============================================================================
CREATE TABLE IF NOT EXISTS signals (
    signal_id          VARCHAR(64) PRIMARY KEY,
    timestamp          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    signal_type        signal_type NOT NULL,
    priority           signal_priority NOT NULL DEFAULT 'NORMAL',
    symbol             VARCHAR(32) NOT NULL,
    direction          signal_type,
    entry_price        DECIMAL(12,5) NOT NULL,
    sl_price           DECIMAL(12,5) NOT NULL,
    tp_prices          JSONB DEFAULT '[]',
    lot_multiplier     DECIMAL(4,2) DEFAULT 1.0,
    risk_percent       DECIMAL(4,2) DEFAULT 1.0,
    max_lot_cap        DECIMAL(10,2) DEFAULT 5.0,
    comment            VARCHAR(128) DEFAULT '',
    expiry_minutes     INT DEFAULT 30,
    source             VARCHAR(64) DEFAULT 'HERMES',
    grid_layer         INT,
    dispatched_count   INT DEFAULT 0,
    status             signal_status NOT NULL DEFAULT 'sent',

    CONSTRAINT valid_expiry CHECK (expiry_minutes >= 1 AND expiry_minutes <= 1440),
    CONSTRAINT valid_grid_layer CHECK (grid_layer IS NULL OR (grid_layer >= 1 AND grid_layer <= 4))
);

CREATE INDEX idx_signals_timestamp ON signals(timestamp DESC);
CREATE INDEX idx_signals_status ON signals(status);
CREATE INDEX idx_signals_source ON signals(source);
CREATE INDEX idx_signals_symbol ON signals(symbol);

-- ============================================================================
-- TRADE FILLS (confirmations from client EAs)
-- ============================================================================
CREATE TABLE IF NOT EXISTS trade_fills (
    fill_id            VARCHAR(128) PRIMARY KEY,
    client_id          VARCHAR(64) NOT NULL REFERENCES clients(client_id) ON DELETE CASCADE,
    signal_id          VARCHAR(64) NOT NULL REFERENCES signals(signal_id) ON DELETE CASCADE,
    symbol             VARCHAR(32) NOT NULL,
    direction          signal_type NOT NULL,
    fill_price         DECIMAL(12,5) NOT NULL,
    lot_size           DECIMAL(10,2) NOT NULL,
    sl_price           DECIMAL(12,5),
    tp_price           DECIMAL(12,5),
    ticket             BIGINT NOT NULL,
    timestamp          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status             trade_status NOT NULL DEFAULT 'open',
    exit_price         DECIMAL(12,5),
    exit_timestamp     TIMESTAMPTZ,
    pnl                DECIMAL(12,2),
    pnl_pct            DECIMAL(6,2),
    slippage_points    INT,
    latency_ms         INT,
    notes              TEXT
);

CREATE INDEX idx_fills_client ON trade_fills(client_id);
CREATE INDEX idx_fills_signal ON trade_fills(signal_id);
CREATE INDEX idx_fills_timestamp ON trade_fills(timestamp DESC);
CREATE INDEX idx_fills_status ON trade_fills(status);

-- ============================================================================
-- DAILY REPORTS (cached daily aggregation)
-- ============================================================================
CREATE TABLE IF NOT EXISTS daily_reports (
    report_id          SERIAL PRIMARY KEY,
    client_id          VARCHAR(64) NOT NULL REFERENCES clients(client_id) ON DELETE CASCADE,
    report_date        DATE NOT NULL,
    total_trades       INT DEFAULT 0,
    wins               INT DEFAULT 0,
    losses             INT DEFAULT 0,
    win_rate           DECIMAL(5,2) DEFAULT 0.0,
    total_pnl          DECIMAL(12,2) DEFAULT 0.0,
    max_dd             DECIMAL(6,2) DEFAULT 0.0,
    avg_rr             DECIMAL(6,2) DEFAULT 0.0,
    generated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(client_id, report_date)
);

CREATE INDEX idx_daily_reports_date ON daily_reports(report_date DESC);

-- ============================================================================
-- SYSTEM EVENTS (audit log)
-- ============================================================================
CREATE TABLE IF NOT EXISTS system_events (
    event_id           BIGSERIAL PRIMARY KEY,
    event_type         VARCHAR(32) NOT NULL,
    severity           VARCHAR(16) DEFAULT 'INFO',
    source             VARCHAR(64) DEFAULT 'system',
    message            TEXT,
    metadata           JSONB,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_events_type ON system_events(event_type);
CREATE INDEX idx_events_created ON system_events(created_at DESC);

-- ============================================================================
-- VIEW: Client Performance Summary
-- ============================================================================
CREATE OR REPLACE VIEW v_client_performance AS
SELECT
    c.client_id,
    c.account_currency,
    c.status,
    COUNT(DISTINCT tf.fill_id) AS total_trades,
    COUNT(DISTINCT tf.fill_id) FILTER (WHERE tf.status = 'closed_tp') AS wins,
    COUNT(DISTINCT tf.fill_id) FILTER (WHERE tf.status = 'closed_sl') AS losses,
    CASE
        WHEN COUNT(DISTINCT tf.fill_id) > 0
        THEN ROUND(COUNT(DISTINCT tf.fill_id) FILTER (WHERE tf.status = 'closed_tp')::DECIMAL
             / COUNT(DISTINCT tf.fill_id) * 100, 1)
        ELSE 0.0
    END AS win_rate,
    COALESCE(SUM(tf.pnl), 0) AS total_pnl,
    MAX(c.registered_at) AS last_updated
FROM clients c
LEFT JOIN trade_fills tf ON c.client_id = tf.client_id
GROUP BY c.client_id, c.account_currency, c.status;

-- ============================================================================
-- VIEW: Daily Aggregated Stats
-- ============================================================================
CREATE OR REPLACE VIEW v_daily_aggregate AS
SELECT
    tf.timestamp::DATE AS trade_date,
    COUNT(*) AS total_trades,
    COUNT(*) FILTER (WHERE tf.status = 'closed_tp') AS wins,
    COUNT(*) FILTER (WHERE tf.status = 'closed_sl') AS losses,
    COALESCE(SUM(tf.pnl), 0) AS total_pnl,
    COUNT(DISTINCT tf.client_id) AS active_clients
FROM trade_fills tf
GROUP BY tf.timestamp::DATE
ORDER BY trade_date DESC;

-- ============================================================================
-- FUNCTIONS
-- ============================================================================
CREATE OR REPLACE FUNCTION update_trade_outcome(
    p_ticket BIGINT,
    p_exit_price DECIMAL(12,5),
    p_pnl DECIMAL(12,2)
) RETURNS VOID AS $$
BEGIN
    UPDATE trade_fills
    SET
        exit_price = p_exit_price,
        exit_timestamp = NOW(),
        pnl = p_pnl,
        status = CASE
            WHEN p_pnl >= 0 THEN 'closed_tp'
            ELSE 'closed_sl'
        END
    WHERE ticket = p_ticket AND status = 'open';
END;
$$ LANGUAGE plpgsql;
