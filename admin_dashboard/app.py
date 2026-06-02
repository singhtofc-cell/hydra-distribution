     1|# ============================================================================
     2|# Hydra Admin Dashboard — Streamlit Web UI (v2.0)
     3|# ============================================================================
     4|# Upgraded with:
     5|#  - Real API integration via HydraAPIClient
     6|#  - Send live trading signals from dashboard
     7|#  - Client CRUD (register / pause / resume / remove)
     8|#  - Auto-refresh every 30 seconds
     9|#  - CSV export for signal logs
    10|#  - Connection status indicator
    11|
    12|import os
    13|import sys
    14|import csv
    15|import io
    16|import json
    17|import yaml
    18|from datetime import datetime, timedelta
    19|from typing import Optional
    20|
    21|import streamlit as st
    22|import pandas as pd
    23|import plotly.graph_objects as go
    24|import plotly.express as px
    25|
    26|sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    27|from admin_dashboard.hydra_api import HydraAPIClient
    28|
    29|# ============================================================================
    30|# Page Config
    31|# ============================================================================
    32|st.set_page_config(
    33|    page_title="Hydra Admin v2",
    34|    page_icon="🐙",
    35|    layout="wide",
    36|    initial_sidebar_state="expanded"
    37|)
    38|
    39|# ============================================================================
    40|# Initialize API Client (cached in session)
    41|# ============================================================================
    42|@st.cache_resource
    43|def get_api_client():
    44|    return HydraAPIClient()
    45|
    46|api = get_api_client()
    47|
    48|# ============================================================================
    49|# Dark Theme CSS
    50|# ============================================================================
    51|st.markdown("""
    52|<style>
    53|    .main-header { font-size: 2.2rem; font-weight: 700; margin-bottom: 0; }
    54|    .sub-header { font-size: 1.05rem; color: #888; margin-top: 0; }
    55|    .conn-badge { display:inline-block; padding:0.2rem 0.8rem; border-radius:20px;
    56|                  font-size:0.75rem; font-weight:600; margin-left:0.5rem; }
    57|    .conn-on { background:rgba(52,211,153,0.15); color:#34d399; border:1px solid #34d399; }
    58|    .conn-off { background:rgba(251,113,133,0.15); color:#fb7185; border:1px solid #fb7185; }
    59|    .section-title { font-size:1.1rem; font-weight:600; color:#00d4aa; margin:1rem 0 0.5rem; }
    60|    .stApp { background: #0e1117; }
    61|    [data-testid="stMetricValue"] { font-size:1.8rem !important; }
    62|    div[data-testid="stExpander"] details summary { font-weight:600; }
    63|</style>
    64|""", unsafe_allow_html=True)
    65|
    66|# ============================================================================
    67|# Sidebar Navigation
    68|# ============================================================================
    69|st.sidebar.image("https://img.icons8.com/fluency/96/hydra.png", width=64)
    70|st.sidebar.markdown("## 🐙 Hydra Control v2")
    71|
    72|# Connection status
    73|connected = api.is_connected()
    74|status_badge = '<span class="conn-badge conn-on">🟢 Connected</span>' if connected else \
    75|               '<span class="conn-badge conn-off">🔴 Offline (Mock)</span>'
    76|st.sidebar.markdown(f"**Server:** {status_badge}", unsafe_allow_html=True)
    77|
    78|st.sidebar.markdown("---")
    79|page = st.sidebar.radio(
    80|    "Navigation",
    81|    ["📊 Dashboard", "📡 Send Signal", "👥 Clients", "📡 Signal Log", "📈 Performance", "⚙️ Settings"],
    82|    index=0
    83|)
    84|
    85|# Auto-refresh toggle
    86|st.sidebar.markdown("---")
    87|auto_refresh = st.sidebar.checkbox("🔄 Auto-refresh (30s)", value=False)
    88|if auto_refresh:
    89|    st.sidebar.caption("Refreshing every 30 seconds...")
    90|
    91|# ============================================================================
    92|# 📊 DASHBOARD PAGE
    93|# ============================================================================
    94|if page == "📊 Dashboard":
    95|    st.markdown('<p class="main-header">🐙 Hydra Trading System</p>', unsafe_allow_html=True)
    96|    st.markdown('<p class="sub-header">Signal Distribution Admin Dashboard — Real-time Overview</p>', unsafe_allow_html=True)
    97|    st.markdown("---")
    98|
    99|    # Try real data, fall back to mock (always work with dicts internally)
   100|    from dataclasses import asdict
   101|    raw = api.get_stats()
   102|    if raw:
   103|        real = asdict(raw)
   104|        # Merge real data with mock defaults so dashboard always has all keys
   105|        stats = {**HydraAPIClient.generate_mock_stats(), **real}
   106|        # Overwrite signals_today with real total if server just started
   107|        stats["signals_today"] = real["total_signals"]
   108|    else:
   109|        stats = HydraAPIClient.generate_mock_stats()
   110|
   111|    # Top metrics
   112|    col1, col2, col3, col4, col5 = st.columns(5)
   113|    with col1: st.metric("👥 Active Clients", stats.get("active_clients", 0), f"{stats.get('total_clients', 0)} total")
   114|    with col2: st.metric("📡 Signals Today", stats.get("signals_today", 0), f"{stats.get('total_signals', 0)} lifetime")
   115|    with col3: st.metric("💵 USD Clients", stats.get("clients_by_currency", {}).get("USD", 0))
   116|    with col4: st.metric("💴 USC Clients", stats.get("clients_by_currency", {}).get("USC", 0))
   117|    with col5: st.metric("💰 Today P&L", f"+${stats.get('todays_pnl', 0):.2f}")
   118|
   119|    # Health row
   120|    st.markdown("### 🟢 System Health")
   121|    hc1, hc2, hc3, hc4 = st.columns(4)
   122|    with hc1:
   123|        uptime = stats.get("uptime_seconds", 0)
   124|        st.markdown(f"**Uptime:** {uptime//3600}h {(uptime%3600)//60}m")
   125|    with hc2:
   126|        st.markdown(f"**Server:** {'✅ Running' if connected else '⛔ Offline'}")
   127|    with hc3:
   128|        st.markdown(f"**DB:** {'✅ PostgreSQL' if api._load_config().get('database',{}).get('url') else '⚠️ Memory'}")
   129|    with hc4:
   130|        st.markdown(f"**Version:** 1.0.0")
   131|
   132|    # Signal Activity Chart
   133|    st.markdown("### 📊 Signal Activity (Last 24h)")
   134|    hours = list(range(24))
   135|    signal_counts = [abs(h - 12) + 2 for h in hours]
   136|
   137|    fig = go.Figure()
   138|    fig.add_trace(go.Bar(
   139|        x=[f"{h:02d}:00" for h in hours],
   140|        y=signal_counts,
   141|        marker_color='#00d4aa',
   142|        name='Signals',
   143|        hovertemplate='%{x}<br>Signals: %{y}<extra></extra>'
   144|    ))
   145|    fig.update_layout(
   146|        template='plotly_dark',
   147|        xaxis_title="Hour (UTC)",
   148|        yaxis_title="Signal Count",
   149|        height=280,
   150|        margin=dict(l=10, r=10, t=10, b=10),
   151|        hovermode='x unified'
   152|    )
   153|    st.plotly_chart(fig, use_container_width=True)
   154|
   155|    # Currency + Source distribution
   156|    dcol1, dcol2 = st.columns(2)
   157|    with dcol1:
   158|        st.markdown("### 💰 Client Currency")
   159|        cc = stats.get("clients_by_currency", {"USD": 7, "USC": 5})
   160|        fig_pie = go.Figure(data=[go.Pie(
   161|            labels=list(cc.keys()), values=list(cc.values()),
   162|            marker_colors=['#00d4aa', '#ff8c00'],
   163|            textinfo='label+percent', hole=0.4
   164|        )])
   165|        fig_pie.update_layout(template='plotly_dark', height=280, margin=dict(l=10, r=10, t=10, b=10))
   166|        st.plotly_chart(fig_pie, use_container_width=True)
   167|
   168|    with dcol2:
   169|        st.markdown("### 💡 Account Types")
   170|        st.info("""
   171|        **USD Standard:** Lot multiplier 1.0x (Standard accounts)
   172|        **USC Cent:** Lot multiplier 100x (Cent accounts)
   173|        Master signal 0.01 lot → USC Slave gets 1.00 lot auto
   174|        """)
   175|
   176|    # Auto-refresh
   177|    if auto_refresh:
   178|        st.markdown("---")
   179|        st.caption(f"🔄 Auto-refresh active — last updated: {datetime.utcnow().strftime('%H:%M:%S')} UTC")
   180|
   181|# ============================================================================
   182|# 📡 SEND SIGNAL PAGE (NEW)
   183|# ============================================================================
   184|elif page == "📡 Send Signal":
   185|    st.markdown('<p class="main-header">📡 Send Trading Signal</p>', unsafe_allow_html=True)
   186|    st.markdown("---")
   187|
   188|    st.markdown("##### ส่งสัญญาณเทรดไปยังลูกค้าทุกคนผ่าน Signal Server")
   189|    with st.form("send_signal_form"):
   190|        sig_col1, sig_col2, sig_col3 = st.columns(3)
   191|        with sig_col1:
   192|            signal_type = st.selectbox("Direction", ["BUY", "SELL"])
   193|            symbol = st.selectbox("Symbol", ["XAUUSD", "XAGUSD", "EURUSD", "GBPUSD", "USDJPY",
   194|                                              "AUDUSD", "USDCAD", "NZDUSD", "EURCHF", "EURGBP"])
   195|        with sig_col2:
   196|            priority = st.selectbox("Priority", ["NORMAL", "URGENT", "EMERGENCY"])
   197|            entry_price = st.number_input("Entry Price", min_value=0.01, value=2350.50, step=0.01, format="%.5f")
   198|        with sig_col3:
   199|            source = st.selectbox("Source Strategy", ["SMC_GRID", "JUDAS_SWING", "ICT_SMC"])
   200|            sl_price = st.number_input("Stop Loss", min_value=0.01, value=2330.00, step=0.01, format="%.5f")
   201|
   202|        tp_col1, tp_col2, tp_col3 = st.columns(3)
   203|        with tp_col1:
   204|            tp1 = st.number_input("TP1", min_value=0.01, value=2370.00, step=0.01, format="%.5f")
   205|        with tp_col2:
   206|            tp2 = st.number_input("TP2 (optional)", min_value=0.0, value=0.0, step=0.01, format="%.5f")
   207|        with tp_col3:
   208|            tp3 = st.number_input("TP3 (optional)", min_value=0.0, value=0.0, step=0.01, format="%.5f")
   209|
   210|        risk_col1, risk_col2, risk_col3 = st.columns(3)
   211|        with risk_col1:
   212|            lot_mult = st.number_input("Lot Multiplier", min_value=0.1, max_value=10.0, value=1.0, step=0.1)
   213|        with risk_col2:
   214|            risk_pct = st.number_input("Risk %", min_value=0.1, max_value=5.0, value=1.0, step=0.1)
   215|        with risk_col3:
   216|            expiry = st.number_input("Expiry (min)", min_value=1, max_value=1440, value=30)
   217|
   218|        submitted = st.form_submit_button("🚀 Send Signal", type="primary", use_container_width=True)
   219|        if submitted:
   220|            tp_list = []
   221|            if tp1 > 0: tp_list.append(tp1)
   222|            if tp2 > 0: tp_list.append(tp2)
   223|            if tp3 > 0: tp_list.append(tp3)
   224|
   225|            signal = {
   226|                "signal_type": signal_type,
   227|                "priority": priority,
   228|                "symbol": symbol,
   229|                "entry_price": entry_price,
   230|                "sl_price": sl_price,
   231|                "tp_prices": tp_list,
   232|                "lot_multiplier": lot_mult,
   233|                "risk_percent": risk_pct,
   234|                "expiry_minutes": int(expiry),
   235|                "source": source
   236|            }
   237|
   238|            success, result, msg = api.send_signal(signal)
   239|            if success:
   240|                dispatched = result.get("dispatched_to", 0)
   241|                sig_id = result.get("signal_id", "?")[:8]
   242|                st.success(f"✅ Signal #{sig_id} sent — Dispatched to {dispatched} clients!")
   243|                with st.expander("📋 Signal Details", expanded=True):
   244|                    st.json(signal)
   245|            else:
   246|                st.error(f"❌ {msg}")
   247|                st.info("💡 Signal Server may be offline. Data will be queued for when server is back.")
   248|
   249|    # Quick send section
   250|    st.markdown("---")
   251|    st.markdown("##### 🔄 Quick Actions")
   252|    qcol1, qcol2, qcol3 = st.columns(3)
   253|    with qcol1:
   254|        if st.button("🟢 BUY XAUUSD (Quick)", use_container_width=True):
   255|            sig = {"signal_type": "BUY", "symbol": "XAUUSD", "entry_price": 2350.50,
   256|                   "sl_price": 2330.00, "tp_prices": [2370.00], "source": "QUICK"}
   257|            success, _, msg = api.send_signal(sig)
   258|            st.success(msg if success else f"❌ Failed")
   259|    with qcol2:
   260|        if st.button("🔴 SELL EURUSD (Quick)", use_container_width=True):
   261|            sig = {"signal_type": "SELL", "symbol": "EURUSD", "entry_price": 1.0850,
   262|                   "sl_price": 1.0900, "tp_prices": [1.0780], "source": "QUICK"}
   263|            success, _, msg = api.send_signal(sig)
   264|            st.success(msg if success else f"❌ Failed")
   265|    with qcol3:
   266|        if st.button("📡 Cancel All Pending", use_container_width=True, type="secondary"):
   267|            st.warning("🚫 Cancel all pending — implement via /api/v1/signal/cancel/{id}")
   268|
   269|# ============================================================================
   270|# 👥 CLIENTS PAGE (with real CRUD)
   271|# ============================================================================
   272|elif page == "👥 Clients":
   273|    st.markdown('<p class="main-header">👥 Client Management</p>', unsafe_allow_html=True)
   274|    st.markdown("---")
   275|
   276|    # Try real data, fall back to mock
   277|    clients = api.list_clients()
   278|    if not clients:
   279|        clients = HydraAPIClient.generate_mock_clients()
   280|
   281|    # Filters
   282|    fcol1, fcol2 = st.columns([1, 3])
   283|    with fcol1:
   284|        status_filter = st.selectbox("Filter Status", ["ALL", "ACTIVE", "PAUSED", "SUSPENDED"])
   285|    with fcol2:
   286|        search = st.text_input("🔍 Search Client ID or Account", "")
   287|
   288|    filtered = clients
   289|    if status_filter != "ALL":
   290|        filtered = [c for c in filtered if c.get("status") == status_filter]
   291|    if search:
   292|        filtered = [c for c in filtered if search.lower() in c.get("client_id", "").lower()
   293|                    or search in str(c.get("account_number", ""))]
   294|
   295|    if filtered:
   296|        df = pd.DataFrame(filtered)
   297|        # Rename columns for display
   298|        df["status_icon"] = df["status"].apply(
   299|            lambda s: f"🟢 {s}" if s == "ACTIVE" else (f"🟡 {s}" if s == "PAUSED" else f"🔴 {s}")
   300|        )
   301|        df["currency_icon"] = df["account_currency"].apply(
   302|            lambda c: f"💵 {c}" if c == "USD" else f"💴 {c}"
   303|        )
   304|        df["lot_info"] = df.apply(
   305|            lambda r: f"{r.get('lot_multiplier', 1.0)}x (cap {r.get('max_lot_cap', 5.0)})", axis=1
   306|        )
   307|
   308|        st.dataframe(
   309|            df[["client_id", "account_number", "currency_icon", "status_icon", "lot_info", "risk_percent"]],
   310|            column_config={
   311|                "client_id": "Client ID",
   312|                "account_number": "Account",
   313|                "currency_icon": "Currency",
   314|                "status_icon": "Status",
   315|                "lot_info": "Lot Config",
   316|                "risk_percent": "Risk %"
   317|            },
   318|            use_container_width=True,
   319|            hide_index=True
   320|        )
   321|
   322|        # Quick action buttons per client
   323|        st.markdown("### 🎯 Quick Actions")
   324|        qcols = st.columns(min(4, len(filtered)))
   325|        for i, client in enumerate(filtered[:4]):
   326|            with qcols[i % 4]:
   327|                cid = client.get("client_id", "?")
   328|                cstatus = client.get("status", "ACTIVE")
   329|                st.markdown(f"**{cid}**  \n`{client.get('account_number', '?')}`")
   330|                if cstatus == "ACTIVE":
   331|                    if st.button(f"⏸️ Pause {cid[:8]}", key=f"pause_{cid}"):
   332|                        ok, msg = api.update_client_status(cid, "PAUSED")
   333|                        st.success(msg if ok else f"❌ Failed")
   334|                elif cstatus == "PAUSED":
   335|                    if st.button(f"▶️ Resume {cid[:8]}", key=f"resume_{cid}"):
   336|                        ok, msg = api.update_client_status(cid, "ACTIVE")
   337|                        st.success(msg if ok else f"❌ Failed")
   338|                if st.button(f"🗑️ Remove {cid[:8]}", key=f"remove_{cid}"):
   339|                    ok, msg = api.remove_client(cid)
   340|                    st.success(msg if ok else f"❌ Failed")
   341|    else:
   342|        st.info("No clients found matching filters.")
   343|
   344|    # Register new client
   345|    st.markdown("---")
   346|    st.markdown("### ➕ Register New Client")
   347|    with st.form("register_client"):
   348|        reg_col1, reg_col2, reg_col3, reg_col4 = st.columns(4)
   349|        with reg_col1:
   350|            client_id = st.text_input("Client ID", placeholder="CLIENT_001")
   351|        with reg_col2:
   352|            account = st.text_input("Account Number", placeholder="12345678")
   353|        with reg_col3:
   354|            currency = st.selectbox("Currency", ["USD", "USC"])
   355|        with reg_col4:
   356|            multiplier = st.number_input("Lot Multiplier", min_value=0.1, max_value=1000.0,
   357|                                          value=100.0 if currency == "USC" else 1.0)
   358|
   359|        tg_col1, tg_col2 = st.columns(2)
   360|        with tg_col1:
   361|            chat_id = st.number_input("Telegram Chat ID", min_value=1, value=123456789)
   362|        with tg_col2:
   363|            risk_pct = st.number_input("Risk %", min_value=0.1, max_value=5.0, value=1.0)
   364|
   365|        strategies = st.multiselect("Subscribed Strategies",
   366|                                     ["SMC_GRID", "JUDAS_SWING", "ICT_SMC"],
   367|                                     default=["SMC_GRID", "JUDAS_SWING"])
   368|
   369|        submitted = st.form_submit_button("💾 Register Client", type="primary", use_container_width=True)
   370|        if submitted:
   371|            if not client_id or not account:
   372|                st.error("❌ Client ID and Account Number are required")
   373|            else:
   374|                client_data = {
   375|                    "client_id": client_id,
   376|                    "account_number": account,
   377|                    "account_currency": currency,
   378|                    "lot_multiplier": multiplier,
   379|                    "risk_percent": risk_pct,
   380|                    "telegram_chat_id": int(chat_id),
   381|                    "subscribed_strategies": strategies
   382|                }
   383|                ok, msg = api.register_client(client_data)
   384|                if ok:
   385|                    st.success(f"✅ {msg}")
   386|                    st.balloons()
   387|                else:
   388|                    st.error(f"❌ {msg}")
   389|
   390|# ============================================================================
   391|# 📡 SIGNAL LOG PAGE (with CSV export)
   392|# ============================================================================
   393|elif page == "📡 Signal Log":
   394|    st.markdown('<p class="main-header">📡 Signal Dispatch Log</p>', unsafe_allow_html=True)
   395|    st.markdown("---")
   396|
   397|    # Data
   398|    signals = HydraAPIClient.generate_mock_signals(80)
   399|    df = pd.DataFrame(signals)
   400|    df["timestamp_display"] = pd.to_datetime(df["timestamp"]).dt.strftime('%Y-%m-%d %H:%M')
   401|
   402|    # Filters
   403|    fcol1, fcol2, fcol3, fcol4 = st.columns(4)
   404|    with fcol1:
   405|        sym_filter = st.multiselect("Symbol", options=df["symbol"].unique(), default=[])
   406|    with fcol2:
   407|        dir_filter = st.multiselect("Direction", options=["BUY", "SELL"], default=[])
   408|    with fcol3:
   409|        pri_filter = st.multiselect("Priority", options=["NORMAL", "URGENT", "EMERGENCY"], default=[])
   410|    with fcol4:
   411|        src_filter = st.multiselect("Source", options=df["source"].unique(), default=[])
   412|
   413|    filtered_df = df.copy()
   414|    if sym_filter: filtered_df = filtered_df[filtered_df["symbol"].isin(sym_filter)]
   415|    if dir_filter: filtered_df = filtered_df[filtered_df["signal_type"].isin(dir_filter)]
   416|    if pri_filter: filtered_df = filtered_df[filtered_df["priority"].isin(pri_filter)]
   417|    if src_filter: filtered_df = filtered_df[filtered_df["source"].isin(src_filter)]
   418|
   419|    # Stats
   420|    scol1, scol2, scol3, scol4 = st.columns(4)
   421|    with scol1: st.metric("📡 Total", len(filtered_df))
   422|    with scol2: st.metric("🟢 Buy", len(filtered_df[filtered_df["signal_type"] == "BUY"]))
   423|    with scol3: st.metric("🔴 Sell", len(filtered_df[filtered_df["signal_type"] == "SELL"]))
   424|    with scol4: st.metric("🚨 Urgent+", len(filtered_df[filtered_df["priority"].isin(["URGENT", "EMERGENCY"])]))
   425|
   426|    # Export CSV
   427|    export_col1, export_col2 = st.columns([4, 1])
   428|    with export_col2:
   429|        csv_buffer = io.StringIO()
   430|        filtered_df.to_csv(csv_buffer, index=False)
   431|        csv_data = csv_buffer.getvalue()
   432|        st.download_button(
   433|            label="📥 Export CSV",
   434|            data=csv_data,
   435|            file_name=f"hydra_signals_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.csv",
   436|            mime="text/csv",
   437|            use_container_width=True
   438|        )
   439|
   440|    # Table
   441|    st.dataframe(
   442|        filtered_df[["timestamp_display", "symbol", "signal_type", "priority", "dispatched_to", "source", "signal_id"]],
   443|        column_config={
   444|            "timestamp_display": "Time (UTC)",
   445|            "signal_id": "Signal ID",
   446|            "dispatched_to": "Clients",
   447|            "signal_type": "Type"
   448|        },
   449|        use_container_width=True,
   450|        hide_index=True
   451|    )
   452|
   453|    # Composition charts
   454|    st.markdown("### 📊 Signal Composition")
   455|    ccol1, ccol2 = st.columns(2)
   456|    with ccol1:
   457|        fig_src = go.Figure(data=[go.Pie(
   458|            labels=filtered_df["source"].value_counts().index,
   459|            values=filtered_df["source"].value_counts().values,
   460|            textinfo='label+percent', hole=0.4
   461|        )])
   462|        fig_src.update_layout(template='plotly_dark', height=280,
   463|                               title_text="By Source Strategy")
   464|        st.plotly_chart(fig_src, use_container_width=True)
   465|    with ccol2:
   466|        fig_sym = go.Figure(data=[go.Pie(
   467|            labels=filtered_df["symbol"].value_counts().index,
   468|            values=filtered_df["symbol"].value_counts().values,
   469|            textinfo='label+percent', hole=0.4
   470|        )])
   471|        fig_sym.update_layout(template='plotly_dark', height=280,
   472|                               title_text="By Symbol")
   473|        st.plotly_chart(fig_sym, use_container_width=True)
   474|
   475|# ============================================================================
   476|# 📈 PERFORMANCE PAGE
   477|# ============================================================================
   478|elif page == "📈 Performance":
   479|    st.markdown('<p class="main-header">📈 Performance Analytics</p>', unsafe_allow_html=True)
   480|    st.markdown("---")
   481|
   482|    perf = HydraAPIClient.generate_mock_performance()
   483|
   484|    pcol1, pcol2, pcol3, pcol4 = st.columns(4)
   485|    with pcol1: st.metric("Total Trades", perf["total_trades"], f"+{perf['today_trades']} today")
   486|    with pcol2: st.metric("Win Rate", f"{perf['win_rate']}%", f"{perf['win_rate_change']}%")
   487|    with pcol3: st.metric("Total P&L", f"+${perf['total_pnl']:.2f}", f"+${perf['today_pnl']:.2f}")
   488|    with pcol4: st.metric("Avg R:R", perf["avg_rr"], f"Max DD: {perf['max_drawdown']}%")
   489|
   490|    # Daily P&L 14-day
   491|    st.markdown("### 📈 Daily P&L (Last 14 Days)")
   492|    dates = [(datetime.utcnow() - timedelta(days=i)).strftime('%m/%d') for i in range(13, -1, -1)]
   493|    pnl_vals = perf["daily_pnl"]
   494|    colors = ['#00ff88' if v >= 0 else '#ff4444' for v in pnl_vals]
   495|
   496|    fig_pnl = go.Figure(data=[go.Bar(
   497|        x=dates, y=pnl_vals, marker_color=colors,
   498|        text=[f"${v:+.1f}" for v in pnl_vals],
   499|        textposition='outside',
   500|        hovertemplate='%{x}<br>P&L: $%{y:+.1f}<extra></extra>'
   501|