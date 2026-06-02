# ============================================================================
# Hydra Admin Dashboard — Streamlit Web UI
# ============================================================================
# Renamed from HERMES → Hydra for standalone copy-trade distribution
# Source: Qwen Architecture Proposal 2026-06-02
#
# Real-time admin dashboard showing:
# - Overall system status and signal dispatch metrics
# - Client list and per-client performance
# - Signal dispatch history
# - Daily/weekly P&L aggregation
# - Live client registration activity

import os
import sys
import json
import yaml
import asyncio
from datetime import datetime, timedelta
from typing import Optional

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# ============================================================================
# Page Configuration
# ============================================================================
st.set_page_config(
    page_title="Hydra Admin Dashboard",
    page_icon="🪬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# Load Config
# ============================================================================
@st.cache_resource
def load_config():
    config_path = os.getenv("HYDRA_CONFIG", "config.yaml")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    return {}

config = load_config()

# ============================================================================
# CSS Styling
# ============================================================================
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-top: 0;
    }
    .metric-card {
        background: #1e1e2e;
        border-radius: 10px;
        padding: 1.5rem;
        border: 1px solid #333;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #888;
    }
    .status-active {
        color: #00ff88;
    }
    .status-paused {
        color: #ffaa00;
    }
    .status-suspended {
        color: #ff4444;
    }
    .stApp {
        background: #0e1117;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# Mock Data (replace with real API/DB calls in production)
# ============================================================================
def get_mock_stats():
    return {
        "total_clients": 12,
        "active_clients": 8,
        "paused_clients": 3,
        "suspended_clients": 1,
        "total_signals": 247,
        "signals_today": 18,
        "clients_by_currency": {"USD": 7, "USC": 5},
        "uptime_seconds": 86400
    }

def get_mock_clients():
    return [
        {"client_id": f"CLIENT_{i:03d}", "status": "ACTIVE" if i < 8 else ("PAUSED" if i < 11 else "SUSPENDED"),
         "account_currency": "USD" if i % 2 == 0 else "USC",
         "account_number": f"{1000000 + i}",
         "lot_multiplier": 1.0 if i % 2 == 0 else 100.0,
         "risk_percent": 1.0, "max_lot_cap": 5.0,
         "telegram_chat_id": 10000000 + i}
        for i in range(12)
    ]

def get_mock_signals():
    signals = []
    for i in range(50):
        signals.append({
            "signal_id": f"sig_{i:04d}",
            "timestamp": (datetime.utcnow() - timedelta(hours=i*2)).isoformat(),
            "symbol": ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"][i % 4],
            "direction": ["BUY", "SELL"][i % 2],
            "priority": ["NORMAL", "URGENT", "EMERGENCY"][i % 3],
            "dispatched_to": [5, 8, 12][i % 3],
            "source": ["SMC_GRID", "JUDAS_SWING", "ICT_SMC"][i % 3]
        })
    return signals

# ============================================================================
# Sidebar
# ============================================================================
st.sidebar.image("https://img.icons8.com/fluency/96/hydra.png", width=64)
st.sidebar.markdown("## 🪬 Hydra Control")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    ["📊 Dashboard", "👥 Clients", "📡 Signals", "📈 Performance", "⚙️ Settings"],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Version:** 1.0.0")
st.sidebar.markdown(f"**Server:** {config.get('server', {}).get('host', '0.0.0.0')}:{config.get('server', {}).get('port', 8788)}")

# ============================================================================
# Dashboard Page
# ============================================================================
if page == "📊 Dashboard":
    st.markdown('<p class="main-header">🪬 Hydra Trading System</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Signal Distribution Admin Dashboard — Real-time Overview</p>', unsafe_allow_html=True)
    st.markdown("---")

    stats = get_mock_stats()
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("👥 Active Clients", stats["active_clients"],
                  f"{stats['total_clients']} total")
    with col2:
        st.metric("📡 Signals Today", stats["signals_today"],
                  f"{stats['total_signals']} lifetime")
    with col3:
        st.metric("💵 USD Clients", stats["clients_by_currency"]["USD"])
    with col4:
        st.metric("💴 USC Clients", stats["clients_by_currency"]["USC"])

    st.markdown("### 🟢 System Health")
    health_col1, health_col2, health_col3 = st.columns(3)
    with health_col1:
        st.markdown("**Server Status:** ✅ Running")
    with health_col2:
        st.markdown(f"**Uptime:** {stats['uptime_seconds'] // 3600}h {(stats['uptime_seconds'] % 3600) // 60}m")
    with health_col3:
        st.markdown(f"**DB Connection:** {'✅ Connected' if config.get('database', {}).get('url') else '⚠️ Memory-only'}")

    # Signal activity chart
    st.markdown("### 📊 Signal Activity (Last 24h)")
    hours = list(range(24))
    signal_counts = [abs(h - 12) + 2 for h in hours]  # Mock bell curve

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[f"{h:02d}:00" for h in hours],
        y=signal_counts,
        marker_color='#00d4aa',
        name='Signals'
    ))
    fig.update_layout(
        template='plotly_dark',
        xaxis_title="Hour",
        yaxis_title="Signal Count",
        height=300,
        margin=dict(l=20, r=20, t=20, b=20)
    )
    st.plotly_chart(fig, use_container_width=True)

    # Client currency distribution
    st.markdown("### 💰 Client Currency Distribution")
    curr_col1, curr_col2 = st.columns(2)
    with curr_col1:
        fig_pie = go.Figure(data=[go.Pie(
            labels=['USD', 'USC'],
            values=[stats['clients_by_currency']['USD'], stats['clients_by_currency']['USC']],
            marker_colors=['#00d4aa', '#ff8c00'],
            textinfo='label+percent'
        )])
        fig_pie.update_layout(template='plotly_dark', height=300, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_pie, use_container_width=True)

    with curr_col2:
        st.markdown("**💡 Account Types**")
        st.markdown("""
        - **USD Standard**: Lot multiplier 1.0x (Standard accounts)
        - **USC Cent**: Lot multiplier 100x (Cent accounts)
        - Master signal 0.01 lot → USC Slave gets 1.00 lot auto
        """)

# ============================================================================
# Clients Page
# ============================================================================
elif page == "👥 Clients":
    st.markdown('<p class="main-header">👥 Client Management</p>', unsafe_allow_html=True)
    st.markdown("---")

    clients = get_mock_clients()

    # Filter
    status_filter = st.selectbox("Filter by Status", ["ALL", "ACTIVE", "PAUSED", "SUSPENDED"])
    if status_filter != "ALL":
        clients = [c for c in clients if c["status"] == status_filter]

    # Client table
    df = pd.DataFrame(clients)
    df["status_display"] = df["status"].apply(
        lambda s: f"🟢 {s}" if s == "ACTIVE" else (f"🟡 {s}" if s == "PAUSED" else f"🔴 {s}")
    )
    df["currency_display"] = df["account_currency"].apply(
        lambda c: f"💵 {c}" if c == "USD" else f"💴 {c}"
    )
    df["lot_info"] = df.apply(
        lambda r: f"{r['lot_multiplier']}x (cap {r['max_lot_cap']})", axis=1
    )

    st.dataframe(
        df[["client_id", "account_number", "currency_display", "status_display", "lot_info", "risk_percent"]],
        column_config={
            "client_id": "Client ID",
            "account_number": "Account",
            "currency_display": "Currency",
            "status_display": "Status",
            "lot_info": "Lot Config",
            "risk_percent": "Risk %"
        },
        use_container_width=True,
        hide_index=True
    )

    st.markdown("### ➕ Register New Client")
    with st.form("register_client"):
        reg_col1, reg_col2, reg_col3, reg_col4 = st.columns(4)
        with reg_col1:
            client_id = st.text_input("Client ID")
        with reg_col2:
            account = st.text_input("Account Number")
        with reg_col3:
            currency = st.selectbox("Currency", ["USD", "USC"])
        with reg_col4:
            multiplier = st.number_input("Lot Multiplier", min_value=0.1, max_value=1000.0, value=1.0)

        submitted = st.form_submit_button("Register Client", type="primary")
        if submitted:
            st.success(f"✅ Client {client_id} registered! (Mock — implement DB connection)")

# ============================================================================
# Signals Page
# ============================================================================
elif page == "📡 Signals":
    st.markdown('<p class="main-header">📡 Signal Dispatch Log</p>', unsafe_allow_html=True)
    st.markdown("---")

    signals = get_mock_signals()
    df_signals = pd.DataFrame(signals)
    df_signals["timestamp_display"] = pd.to_datetime(df_signals["timestamp"]).dt.strftime('%Y-%m-%d %H:%M')

    # Filter
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        symbol_filter = st.multiselect("Symbol", options=df_signals["symbol"].unique(), default=[])
    with filter_col2:
        direction_filter = st.multiselect("Direction", options=["BUY", "SELL"], default=[])
    with filter_col3:
        priority_filter = st.multiselect("Priority", options=["NORMAL", "URGENT", "EMERGENCY"], default=[])

    if symbol_filter:
        df_signals = df_signals[df_signals["symbol"].isin(symbol_filter)]
    if direction_filter:
        df_signals = df_signals[df_signals["direction"].isin(direction_filter)]
    if priority_filter:
        df_signals = df_signals[df_signals["priority"].isin(priority_filter)]

    st.dataframe(
        df_signals[["timestamp_display", "symbol", "direction", "priority", "dispatched_to", "source", "signal_id"]],
        column_config={
            "timestamp_display": "Time",
            "signal_id": "Signal ID",
            "dispatched_to": "Clients"
        },
        use_container_width=True,
        hide_index=True
    )

    # Signal composition
    st.markdown("### 📊 Signal Composition")
    fig_pie_signals = go.Figure(data=[go.Pie(
        labels=df_signals["source"].value_counts().index,
        values=df_signals["source"].value_counts().values,
        textinfo='label+percent'
    )])
    fig_pie_signals.update_layout(template='plotly_dark', height=300)
    st.plotly_chart(fig_pie_signals, use_container_width=True)

# ============================================================================
# Performance Page
# ============================================================================
elif page == "📈 Performance":
    st.markdown('<p class="main-header">📈 Performance Analytics</p>', unsafe_allow_html=True)
    st.markdown("---")

    # Mock performance data
    perf_col1, perf_col2, perf_col3, perf_col4 = st.columns(4)
    with perf_col1:
        st.metric("Total Trades", 142, "+12 today")
    with perf_col2:
        st.metric("Win Rate", "67.8%", "+2.1%")
    with perf_col3:
        st.metric("Total P&L", "+$847.50", "+$52.30")
    with perf_col4:
        st.metric("Avg R:R", "1:2.4", "+0.1")

    # Daily P&L chart
    st.markdown("### 📈 Daily P&L (Last 14 Days)")
    dates = [(datetime.utcnow() - timedelta(days=i)).strftime('%m/%d') for i in range(13, -1, -1)]
    pnl_values = [12.5, -8.3, 22.1, 15.0, -3.2, 30.5, 18.7, -5.5, 10.2, 25.8, -12.1, 8.9, 35.2, 5.0]

    colors = ['#00ff88' if v >= 0 else '#ff4444' for v in pnl_values]
    fig_pnl = go.Figure(data=[go.Bar(
        x=dates, y=pnl_values, marker_color=colors,
        text=[f"${v:+.1f}" for v in pnl_values],
        textposition='outside'
    )])
    fig_pnl.update_layout(
        template='plotly_dark',
        height=350,
        xaxis_title="Date",
        yaxis_title="P&L ($)",
        showlegend=False
    )
    st.plotly_chart(fig_pnl, use_container_width=True)

    # Top clients
    st.markdown("### 🏆 Top Performing Clients")
    top_clients = pd.DataFrame({
        "Client": [f"CLIENT_{i:03d}" for i in range(5)],
        "Currency": ["USD", "USC", "USD", "USC", "USD"],
        "Trades": [34, 28, 22, 19, 15],
        "Win Rate": ["72.1%", "68.4%", "65.0%", "63.2%", "60.0%"],
        "P&L": ["+$285.50", "+$192.30", "+$145.00", "+$98.70", "+$72.40"]
    })
    st.dataframe(top_clients, use_container_width=True, hide_index=True)

# ============================================================================
# Settings Page
# ============================================================================
elif page == "⚙️ Settings":
    st.markdown('<p class="main-header">⚙️ System Settings</p>', unsafe_allow_html=True)
    st.markdown("---")

    with st.form("settings_form"):
        st.markdown("### 🖥️ Server")
        srv_col1, srv_col2 = st.columns(2)
        with srv_col1:
            host = st.text_input("Host", value=config.get("server", {}).get("host", "0.0.0.0"))
        with srv_col2:
            port = st.number_input("Port", value=config.get("server", {}).get("port", 8788))

        st.markdown("### 🤖 Telegram")
        tg_col1, tg_col2, tg_col3 = st.columns(3)
        with tg_col1:
            bot_token = st.text_input("Bot Token", type="password",
                                       value=os.getenv("HYDRA_TELEGRAM_BOT_TOKEN", ""))
        with tg_col2:
            admin_chat = st.text_input("Admin Chat ID",
                                        value=str(os.getenv("HYDRA_ADMIN_CHAT_ID", "")))
        with tg_col3:
            poll_interval = st.number_input("Poll Interval (s)", value=30)

        st.markdown("### 📊 Reporting")
        rep_col1, rep_col2 = st.columns(2)
        with rep_col1:
            st.checkbox("Enable Hourly Reports", value=True)
            st.checkbox("Enable Daily Reports", value=True)
        with rep_col2:
            st.checkbox("Enable Weekly Reports", value=True)
            st.checkbox("Enable Admin Summary", value=True)

        st.markdown("### ⚠️ Risk Limits")
        risk_col1, risk_col2, risk_col3 = st.columns(3)
        with risk_col1:
            st.number_input("Max Daily Loss %", value=5.0, min_value=0.1, max_value=50.0)
        with risk_col2:
            st.number_input("Max Drawdown %", value=15.0, min_value=0.1, max_value=100.0)
        with risk_col3:
            st.number_input("Max Slippage (points)", value=30, min_value=1, max_value=500)

        submitted = st.form_submit_button("💾 Save Settings", type="primary")
        if submitted:
            st.success("✅ Settings saved! (Mock — implement config write)")

st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666; padding: 1rem;'>"
    "🪬 Hydra Trading System v1.0 — Signal Distribution Admin Dashboard"
    "</div>",
    unsafe_allow_html=True
)
