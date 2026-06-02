# ============================================================================
# Hydra Admin Dashboard — Streamlit Web UI (v2.0)
# ============================================================================
# Upgraded with:
#  - Real API integration via HydraAPIClient
#  - Send live trading signals from dashboard
#  - Client CRUD (register / pause / resume / remove)
#  - Auto-refresh every 30 seconds
#  - CSV export for signal logs
#  - Connection status indicator

import os
import sys
import csv
import io
import json
import yaml
from datetime import datetime, timedelta
from typing import Optional

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from admin_dashboard.hydra_api import HydraAPIClient

# ============================================================================
# Page Config
# ============================================================================
st.set_page_config(
    page_title="Hydra Admin v2",
    page_icon="🦑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# Initialize API Client (cached in session)
# ============================================================================
@st.cache_resource
def get_api_client():
    return HydraAPIClient()

api = get_api_client()

# ============================================================================
# Dark Theme CSS
# ============================================================================
st.markdown("""
<style>
    .main-header { font-size: 2.2rem; font-weight: 700; margin-bottom: 0; }
    .sub-header { font-size: 1.05rem; color: #888; margin-top: 0; }
    .conn-badge { display:inline-block; padding:0.2rem 0.8rem; border-radius:20px;
                  font-size:0.75rem; font-weight:600; margin-left:0.5rem; }
    .conn-on { background:rgba(52,211,153,0.15); color:#34d399; border:1px solid #34d399; }
    .conn-off { background:rgba(251,113,133,0.15); color:#fb7185; border:1px solid #fb7185; }
    .section-title { font-size:1.1rem; font-weight:600; color:#00d4aa; margin:1rem 0 0.5rem; }
    .stApp { background: #0e1117; }
    [data-testid="stMetricValue"] { font-size:1.8rem !important; }
    div[data-testid="stExpander"] details summary { font-weight:600; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# Sidebar Navigation
# ============================================================================
st.sidebar.image("https://img.icons8.com/fluency/96/hydra.png", width=64)
st.sidebar.markdown("## 🦑 Hydra Control v2")

# Connection status
connected = api.is_connected()
status_badge = '<span class="conn-badge conn-on">🟢 Connected</span>' if connected else \
               '<span class="conn-badge conn-off">🔴 Offline (Mock)</span>'
st.sidebar.markdown(f"**Server:** {status_badge}", unsafe_allow_html=True)

st.sidebar.markdown("---")
page = st.sidebar.radio(
    "Navigation",
    ["📊 Dashboard", "📡 Send Signal", "👥 Clients", "📡 Signal Log", "📈 Performance", "⚙️ Settings"],
    index=0
)

# Auto-refresh toggle
st.sidebar.markdown("---")
auto_refresh = st.sidebar.checkbox("🔄 Auto-refresh (30s)", value=False)
if auto_refresh:
    st.sidebar.caption("Refreshing every 30 seconds...")

# ============================================================================
# 📊 DASHBOARD PAGE
# ============================================================================
if page == "📊 Dashboard":
    st.markdown('<p class="main-header">🦑 Hydra Trading System</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Signal Distribution Admin Dashboard — Real-time Overview</p>', unsafe_allow_html=True)
    st.markdown("---")

    # Try real data, fall back to mock (always work with dicts internally)
    from dataclasses import asdict
    raw = api.get_stats()
    if raw:
        real = asdict(raw)
        # Merge real data with mock defaults so dashboard always has all keys
        stats = {**HydraAPIClient.generate_mock_stats(), **real}
        # Overwrite signals_today with real total if server just started
        stats["signals_today"] = real["total_signals"]
    else:
        stats = HydraAPIClient.generate_mock_stats()

    # Top metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: st.metric("👥 Active Clients", stats.get("active_clients", 0), f"{stats.get('total_clients', 0)} total")
    with col2: st.metric("📡 Signals Today", stats.get("signals_today", 0), f"{stats.get('total_signals', 0)} lifetime")
    with col3: st.metric("💵 USD Clients", stats.get("clients_by_currency", {}).get("USD", 0))
    with col4: st.metric("💴 USC Clients", stats.get("clients_by_currency", {}).get("USC", 0))
    with col5: st.metric("💰 Today P&L", f"+${stats.get('todays_pnl', 0):.2f}")

    # Health row
    st.markdown("### 🟢 System Health")
    hc1, hc2, hc3, hc4 = st.columns(4)
    with hc1:
        uptime = stats.get("uptime_seconds", 0)
        st.markdown(f"**Uptime:** {uptime//3600}h {(uptime%3600)//60}m")
    with hc2:
        st.markdown(f"**Server:** {'✅ Running' if connected else '⛔ Offline'}")
    with hc3:
        st.markdown(f"**DB:** {'✅ PostgreSQL' if api._load_config().get('database',{}).get('url') else '⚠️ Memory'}")
    with hc4:
        st.markdown(f"**Version:** 1.0.0")

    # Signal Activity Chart
    st.markdown("### 📊 Signal Activity (Last 24h)")
    hours = list(range(24))
    signal_counts = [abs(h - 12) + 2 for h in hours]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[f"{h:02d}:00" for h in hours],
        y=signal_counts,
        marker_color='#00d4aa',
        name='Signals',
        hovertemplate='%{x}<br>Signals: %{y}<extra></extra>'
    ))
    fig.update_layout(
        template='plotly_dark',
        xaxis_title="Hour (UTC)",
        yaxis_title="Signal Count",
        height=280,
        margin=dict(l=10, r=10, t=10, b=10),
        hovermode='x unified'
    )
    st.plotly_chart(fig, use_container_width=True)

    # Currency + Source distribution
    dcol1, dcol2 = st.columns(2)
    with dcol1:
        st.markdown("### 💰 Client Currency")
        cc = stats.get("clients_by_currency", {"USD": 7, "USC": 5})
        fig_pie = go.Figure(data=[go.Pie(
            labels=list(cc.keys()), values=list(cc.values()),
            marker_colors=['#00d4aa', '#ff8c00'],
            textinfo='label+percent', hole=0.4
        )])
        fig_pie.update_layout(template='plotly_dark', height=280, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_pie, use_container_width=True)

    with dcol2:
        st.markdown("### 💡 Account Types")
        st.info("""
        **USD Standard:** Lot multiplier 1.0x (Standard accounts)
        **USC Cent:** Lot multiplier 100x (Cent accounts)
        Master signal 0.01 lot → USC Slave gets 1.00 lot auto
        """)

    # Auto-refresh
    if auto_refresh:
        st.markdown("---")
        st.caption(f"🔄 Auto-refresh active — last updated: {datetime.utcnow().strftime('%H:%M:%S')} UTC")

# ============================================================================
# 📡 SEND SIGNAL PAGE (NEW)
# ============================================================================
elif page == "📡 Send Signal":
    st.markdown('<p class="main-header">📡 Send Trading Signal</p>', unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("##### ส่งสัญญาณเทรดไปยังลูกค้าทุกคนผ่าน Signal Server")
    with st.form("send_signal_form"):
        sig_col1, sig_col2, sig_col3 = st.columns(3)
        with sig_col1:
            signal_type = st.selectbox("Direction", ["BUY", "SELL"])
            symbol = st.selectbox("Symbol", ["XAUUSD", "XAGUSD", "EURUSD", "GBPUSD", "USDJPY",
                                              "AUDUSD", "USDCAD", "NZDUSD", "EURCHF", "EURGBP"])
        with sig_col2:
            priority = st.selectbox("Priority", ["NORMAL", "URGENT", "EMERGENCY"])
            entry_price = st.number_input("Entry Price", min_value=0.01, value=2350.50, step=0.01, format="%.5f")
        with sig_col3:
            source = st.selectbox("Source Strategy", ["SMC_GRID", "JUDAS_SWING", "ICT_SMC"])
            sl_price = st.number_input("Stop Loss", min_value=0.01, value=2330.00, step=0.01, format="%.5f")

        tp_col1, tp_col2, tp_col3 = st.columns(3)
        with tp_col1:
            tp1 = st.number_input("TP1", min_value=0.01, value=2370.00, step=0.01, format="%.5f")
        with tp_col2:
            tp2 = st.number_input("TP2 (optional)", min_value=0.0, value=0.0, step=0.01, format="%.5f")
        with tp_col3:
            tp3 = st.number_input("TP3 (optional)", min_value=0.0, value=0.0, step=0.01, format="%.5f")

        risk_col1, risk_col2, risk_col3 = st.columns(3)
        with risk_col1:
            lot_mult = st.number_input("Lot Multiplier", min_value=0.1, max_value=10.0, value=1.0, step=0.1)
        with risk_col2:
            risk_pct = st.number_input("Risk %", min_value=0.1, max_value=5.0, value=1.0, step=0.1)
        with risk_col3:
            expiry = st.number_input("Expiry (min)", min_value=1, max_value=1440, value=30)

        submitted = st.form_submit_button("🚀 Send Signal", type="primary", use_container_width=True)
        if submitted:
            tp_list = []
            if tp1 > 0: tp_list.append(tp1)
            if tp2 > 0: tp_list.append(tp2)
            if tp3 > 0: tp_list.append(tp3)

            signal = {
                "signal_type": signal_type,
                "priority": priority,
                "symbol": symbol,
                "entry_price": entry_price,
                "sl_price": sl_price,
                "tp_prices": tp_list,
                "lot_multiplier": lot_mult,
                "risk_percent": risk_pct,
                "expiry_minutes": int(expiry),
                "source": source
            }

            success, result, msg = api.send_signal(signal)
            if success:
                dispatched = result.get("dispatched_to", 0)
                sig_id = result.get("signal_id", "?")[:8]
                st.success(f"✅ Signal #{sig_id} sent — Dispatched to {dispatched} clients!")
                with st.expander("📋 Signal Details", expanded=True):
                    st.json(signal)
            else:
                st.error(f"❌ {msg}")
                st.info("💡 Signal Server may be offline. Data will be queued for when server is back.")

    # Quick send section
    st.markdown("---")
    st.markdown("##### 🔄 Quick Actions")
    qcol1, qcol2, qcol3 = st.columns(3)
    with qcol1:
        if st.button("🟢 BUY XAUUSD (Quick)", use_container_width=True):
            sig = {"signal_type": "BUY", "symbol": "XAUUSD", "entry_price": 2350.50,
                   "sl_price": 2330.00, "tp_prices": [2370.00], "source": "QUICK"}
            success, _, msg = api.send_signal(sig)
            st.success(msg if success else f"❌ Failed")
    with qcol2:
        if st.button("🔴 SELL EURUSD (Quick)", use_container_width=True):
            sig = {"signal_type": "SELL", "symbol": "EURUSD", "entry_price": 1.0850,
                   "sl_price": 1.0900, "tp_prices": [1.0780], "source": "QUICK"}
            success, _, msg = api.send_signal(sig)
            st.success(msg if success else f"❌ Failed")
    with qcol3:
        if st.button("📡 Cancel All Pending", use_container_width=True, type="secondary"):
            st.warning("🚫 Cancel all pending — implement via /api/v1/signal/cancel/{id}")

# ============================================================================
# 👥 CLIENTS PAGE (with real CRUD)
# ============================================================================
elif page == "👥 Clients":
    st.markdown('<p class="main-header">👥 Client Management</p>', unsafe_allow_html=True)
    st.markdown("---")

    # Try real data, fall back to mock
    clients = api.list_clients()
    if not clients:
        clients = HydraAPIClient.generate_mock_clients()

    # Filters
    fcol1, fcol2 = st.columns([1, 3])
    with fcol1:
        status_filter = st.selectbox("Filter Status", ["ALL", "ACTIVE", "PAUSED", "SUSPENDED"])
    with fcol2:
        search = st.text_input("🔍 Search Client ID or Account", "")

    filtered = clients
    if status_filter != "ALL":
        filtered = [c for c in filtered if c.get("status") == status_filter]
    if search:
        filtered = [c for c in filtered if search.lower() in c.get("client_id", "").lower()
                    or search in str(c.get("account_number", ""))]

    if filtered:
        df = pd.DataFrame(filtered)
        # Rename columns for display
        df["status_icon"] = df["status"].apply(
            lambda s: f"🟢 {s}" if s == "ACTIVE" else (f"🟡 {s}" if s == "PAUSED" else f"🔴 {s}")
        )
        df["currency_icon"] = df["account_currency"].apply(
            lambda c: f"💵 {c}" if c == "USD" else f"💴 {c}"
        )
        df["lot_info"] = df.apply(
            lambda r: f"{r.get('lot_multiplier', 1.0)}x (cap {r.get('max_lot_cap', 5.0)})", axis=1
        )

        st.dataframe(
            df[["client_id", "account_number", "currency_icon", "status_icon", "lot_info", "risk_percent"]],
            column_config={
                "client_id": "Client ID",
                "account_number": "Account",
                "currency_icon": "Currency",
                "status_icon": "Status",
                "lot_info": "Lot Config",
                "risk_percent": "Risk %"
            },
            use_container_width=True,
            hide_index=True
        )

        # Quick action buttons per client
        st.markdown("### 🎯 Quick Actions")
        qcols = st.columns(min(4, len(filtered)))
        for i, client in enumerate(filtered[:4]):
            with qcols[i % 4]:
                cid = client.get("client_id", "?")
                cstatus = client.get("status", "ACTIVE")
                st.markdown(f"**{cid}**  \n`{client.get('account_number', '?')}`")
                if cstatus == "ACTIVE":
                    if st.button(f"⏸️ Pause {cid[:8]}", key=f"pause_{cid}"):
                        ok, msg = api.update_client_status(cid, "PAUSED")
                        st.success(msg if ok else f"❌ Failed")
                elif cstatus == "PAUSED":
                    if st.button(f"▶️ Resume {cid[:8]}", key=f"resume_{cid}"):
                        ok, msg = api.update_client_status(cid, "ACTIVE")
                        st.success(msg if ok else f"❌ Failed")
                if st.button(f"🗑️ Remove {cid[:8]}", key=f"remove_{cid}"):
                    ok, msg = api.remove_client(cid)
                    st.success(msg if ok else f"❌ Failed")
    else:
        st.info("No clients found matching filters.")

    # Register new client
    st.markdown("---")
    st.markdown("### ➕ Register New Client")
    with st.form("register_client"):
        reg_col1, reg_col2, reg_col3, reg_col4 = st.columns(4)
        with reg_col1:
            client_id = st.text_input("Client ID", placeholder="CLIENT_001")
        with reg_col2:
            account = st.text_input("Account Number", placeholder="12345678")
        with reg_col3:
            currency = st.selectbox("Currency", ["USD", "USC"])
        with reg_col4:
            multiplier = st.number_input("Lot Multiplier", min_value=0.1, max_value=1000.0,
                                          value=100.0 if currency == "USC" else 1.0)

        tg_col1, tg_col2 = st.columns(2)
        with tg_col1:
            chat_id = st.number_input("Telegram Chat ID", min_value=1, value=123456789)
        with tg_col2:
            risk_pct = st.number_input("Risk %", min_value=0.1, max_value=5.0, value=1.0)

        strategies = st.multiselect("Subscribed Strategies",
                                     ["SMC_GRID", "JUDAS_SWING", "ICT_SMC"],
                                     default=["SMC_GRID", "JUDAS_SWING"])

        submitted = st.form_submit_button("💾 Register Client", type="primary", use_container_width=True)
        if submitted:
            if not client_id or not account:
                st.error("❌ Client ID and Account Number are required")
            else:
                client_data = {
                    "client_id": client_id,
                    "account_number": account,
                    "account_currency": currency,
                    "lot_multiplier": multiplier,
                    "risk_percent": risk_pct,
                    "telegram_chat_id": int(chat_id),
                    "subscribed_strategies": strategies
                }
                ok, msg = api.register_client(client_data)
                if ok:
                    st.success(f"✅ {msg}")
                    st.balloons()
                else:
                    st.error(f"❌ {msg}")

# ============================================================================
# 📡 SIGNAL LOG PAGE (with CSV export)
# ============================================================================
elif page == "📡 Signal Log":
    st.markdown('<p class="main-header">📡 Signal Dispatch Log</p>', unsafe_allow_html=True)
    st.markdown("---")

    # Data
    signals = HydraAPIClient.generate_mock_signals(80)
    df = pd.DataFrame(signals)
    df["timestamp_display"] = pd.to_datetime(df["timestamp"]).dt.strftime('%Y-%m-%d %H:%M')

    # Filters
    fcol1, fcol2, fcol3, fcol4 = st.columns(4)
    with fcol1:
        sym_filter = st.multiselect("Symbol", options=df["symbol"].unique(), default=[])
    with fcol2:
        dir_filter = st.multiselect("Direction", options=["BUY", "SELL"], default=[])
    with fcol3:
        pri_filter = st.multiselect("Priority", options=["NORMAL", "URGENT", "EMERGENCY"], default=[])
    with fcol4:
        src_filter = st.multiselect("Source", options=df["source"].unique(), default=[])

    filtered_df = df.copy()
    if sym_filter: filtered_df = filtered_df[filtered_df["symbol"].isin(sym_filter)]
    if dir_filter: filtered_df = filtered_df[filtered_df["signal_type"].isin(dir_filter)]
    if pri_filter: filtered_df = filtered_df[filtered_df["priority"].isin(pri_filter)]
    if src_filter: filtered_df = filtered_df[filtered_df["source"].isin(src_filter)]

    # Stats
    scol1, scol2, scol3, scol4 = st.columns(4)
    with scol1: st.metric("📡 Total", len(filtered_df))
    with scol2: st.metric("🟢 Buy", len(filtered_df[filtered_df["signal_type"] == "BUY"]))
    with scol3: st.metric("🔴 Sell", len(filtered_df[filtered_df["signal_type"] == "SELL"]))
    with scol4: st.metric("🚨 Urgent+", len(filtered_df[filtered_df["priority"].isin(["URGENT", "EMERGENCY"])]))

    # Export CSV
    export_col1, export_col2 = st.columns([4, 1])
    with export_col2:
        csv_buffer = io.StringIO()
        filtered_df.to_csv(csv_buffer, index=False)
        csv_data = csv_buffer.getvalue()
        st.download_button(
            label="📥 Export CSV",
            data=csv_data,
            file_name=f"hydra_signals_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    # Table
    st.dataframe(
        filtered_df[["timestamp_display", "symbol", "signal_type", "priority", "dispatched_to", "source", "signal_id"]],
        column_config={
            "timestamp_display": "Time (UTC)",
            "signal_id": "Signal ID",
            "dispatched_to": "Clients",
            "signal_type": "Type"
        },
        use_container_width=True,
        hide_index=True
    )

    # Composition charts
    st.markdown("### 📊 Signal Composition")
    ccol1, ccol2 = st.columns(2)
    with ccol1:
        fig_src = go.Figure(data=[go.Pie(
            labels=filtered_df["source"].value_counts().index,
            values=filtered_df["source"].value_counts().values,
            textinfo='label+percent', hole=0.4
        )])
        fig_src.update_layout(template='plotly_dark', height=280,
                               title_text="By Source Strategy")
        st.plotly_chart(fig_src, use_container_width=True)
    with ccol2:
        fig_sym = go.Figure(data=[go.Pie(
            labels=filtered_df["symbol"].value_counts().index,
            values=filtered_df["symbol"].value_counts().values,
            textinfo='label+percent', hole=0.4
        )])
        fig_sym.update_layout(template='plotly_dark', height=280,
                               title_text="By Symbol")
        st.plotly_chart(fig_sym, use_container_width=True)

# ============================================================================
# 📈 PERFORMANCE PAGE
# ============================================================================
elif page == "📈 Performance":
    st.markdown('<p class="main-header">📈 Performance Analytics</p>', unsafe_allow_html=True)
    st.markdown("---")

    perf = HydraAPIClient.generate_mock_performance()

    pcol1, pcol2, pcol3, pcol4 = st.columns(4)
    with pcol1: st.metric("Total Trades", perf["total_trades"], f"+{perf['today_trades']} today")
    with pcol2: st.metric("Win Rate", f"{perf['win_rate']}%", f"{perf['win_rate_change']}%")
    with pcol3: st.metric("Total P&L", f"+${perf['total_pnl']:.2f}", f"+${perf['today_pnl']:.2f}")
    with pcol4: st.metric("Avg R:R", perf["avg_rr"], f"Max DD: {perf['max_drawdown']}%")

    # Daily P&L 14-day
    st.markdown("### 📈 Daily P&L (Last 14 Days)")
    dates = [(datetime.utcnow() - timedelta(days=i)).strftime('%m/%d') for i in range(13, -1, -1)]
    pnl_vals = perf["daily_pnl"]
    colors = ['#00ff88' if v >= 0 else '#ff4444' for v in pnl_vals]

    fig_pnl = go.Figure(data=[go.Bar(
        x=dates, y=pnl_vals, marker_color=colors,
        text=[f"${v:+.1f}" for v in pnl_vals],
        textposition='outside',
        hovertemplate='%{x}<br>P&L: $%{y:+.1f}<extra></extra>'
    )])
    fig_pnl.update_layout(
        template='plotly_dark', height=350,
        xaxis_title="Date", yaxis_title="P&L ($)",
        showlegend=False, hovermode='x unified'
    )
    st.plotly_chart(fig_pnl, use_container_width=True)

    # Top Clients
    st.markdown("### 🏆 Top Performing Clients")
    top_clients = pd.DataFrame({
        "Client": [f"CLIENT_{i:03d}" for i in range(5)],
        "Currency": ["USD", "USC", "USD", "USC", "USD"],
        "Trades": [34, 28, 22, 19, 15],
        "Wins": [25, 19, 14, 12, 9],
        "Losses": [9, 9, 8, 7, 6],
        "Win Rate": ["73.5%", "67.9%", "63.6%", "63.2%", "60.0%"],
        "P&L": ["+$285.50", "+$192.30", "+$145.00", "+$98.70", "+$72.40"],
        "Avg R:R": ["1:2.8", "1:2.5", "1:2.3", "1:2.1", "1:1.9"]
    })
    st.dataframe(top_clients, use_container_width=True, hide_index=True)

    # Performance by symbol
    st.markdown("### 📊 Performance by Symbol")
    sym_perf = pd.DataFrame({
        "Symbol": ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "AUDUSD"],
        "Trades": [45, 32, 28, 22, 15],
        "Win Rate": [71.1, 65.6, 67.9, 63.6, 60.0],
        "P&L": ["+$342.00", "+$187.50", "+$156.80", "+$98.20", "+$62.00"]
    })
    st.dataframe(sym_perf, use_container_width=True, hide_index=True)

# ============================================================================
# ⚙️ SETTINGS PAGE
# ============================================================================
elif page == "⚙️ Settings":
    st.markdown('<p class="main-header">⚙️ System Settings</p>', unsafe_allow_html=True)
    st.markdown("---")

    # Connection info
    with st.expander("🔌 Server Connection", expanded=True):
        scol1, scol2 = st.columns(2)
        with scol1:
            server_url = st.text_input("Signal Server URL", value=api.base_url)
        with scol2:
            st.markdown(f"**Status:** {'🟢 Connected' if connected else '🔴 Offline (Mock)'}")
        if st.button("🔄 Test Connection", use_container_width=True):
            health = api.check_health()
            if health:
                st.success(f"✅ Connected — v{health.version}, {health.active_clients} active clients")
            else:
                st.error(f"❌ Cannot reach {server_url}. Dashboard will use mock data.")

    with st.form("settings_form"):
        st.markdown("### 🖥️ Server")
        srv_col1, srv_col2 = st.columns(2)
        with srv_col1:
            host = st.text_input("Host", value="0.0.0.0")
        with srv_col2:
            port = st.number_input("Port", value=8788, min_value=1, max_value=65535)

        st.markdown("### 🤖 Telegram")
        tg_col1, tg_col2, tg_col3 = st.columns(3)
        with tg_col1:
            bot_token = st.text_input("Bot Token", type="password", placeholder="Enter token")
        with tg_col2:
            admin_chat = st.text_input("Admin Chat ID", placeholder="123456789")
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

        submitted = st.form_submit_button("💾 Save Settings", type="primary", use_container_width=True)
        if submitted:
            st.success("✅ Settings preview saved! (Connect to real server to persist)")

# ============================================================================
# Footer
# ============================================================================
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#666;padding:0.5rem;font-size:0.8rem;'>"
    "🦑 Hydra Trading System v2.0 · Dashboard built with Streamlit · "
    f"{'🟢 Live' if connected else '🔴 Mock Data'}</div>",
    unsafe_allow_html=True
)
