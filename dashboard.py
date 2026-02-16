"""
=========================================================
    STREAMLIT DASHBOARD UNTUK MULTI-AGENT BOT
    Menampilkan equity curve, leaderboard, sentimen, dll.
    Berdasarkan trade-app [citation:4] dan NOFX [citation:3]
=========================================================
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import sqlite3
from datetime import datetime, timedelta
import time

# Konfigurasi halaman
st.set_page_config(
    page_title="Multi-Agent Trading Dashboard",
    page_icon="📊",
    layout="wide"
)

# Koneksi ke database yang sama dengan bot
@st.cache_resource
def get_db_connection():
    return sqlite3.connect('trading_history.db', check_same_thread=False)

conn = get_db_connection()

# =================== FUNGSI LOAD DATA ===================
@st.cache_data(ttl=10)  # refresh setiap 10 detik
def load_trades():
    query = """
    SELECT id, timestamp, symbol, action, entry, sl, tp, exit_price, profit, 
           reason, agent_name, confidence
    FROM trades 
    ORDER BY timestamp DESC 
    LIMIT 100
    """
    return pd.read_sql_query(query, conn)

@st.cache_data(ttl=60)
def load_agent_performance():
    query = """
    SELECT agent_name, 
           COUNT(*) as total_trades,
           SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as wins,
           SUM(profit) as total_profit,
           AVG(profit) as avg_profit,
           AVG(confidence) as avg_confidence
    FROM trades 
    WHERE profit IS NOT NULL
    GROUP BY agent_name
    """
    return pd.read_sql_query(query, conn)

@st.cache_data(ttl=300)
def load_sentiment_history():
    query = """
    SELECT timestamp, sentiment_score, sentiment_signal, 
           fundamental_score, fundamental_signal
    FROM market_sentiment 
    ORDER BY timestamp DESC 
    LIMIT 50
    """
    return pd.read_sql_query(query, conn)

def get_equity_curve():
    query = """
    SELECT timestamp, 
           SUM(profit) OVER (ORDER BY timestamp) as cumulative_profit
    FROM trades 
    WHERE profit IS NOT NULL
    ORDER BY timestamp
    """
    return pd.read_sql_query(query, conn)

# =================== SIDEBAR ===================
st.sidebar.title("🤖 Multi-Agent Dashboard")
st.sidebar.markdown("---")

# Auto-refresh toggle
auto_refresh = st.sidebar.checkbox("Auto Refresh (10 detik)", value=True)
refresh_interval = 10

if auto_refresh:
    time.sleep(1)
    st.rerun()

# Filter tanggal
st.sidebar.subheader("Filter Tanggal")
date_range = st.sidebar.date_input(
    "Rentang",
    [datetime.now() - timedelta(days=7), datetime.now()]
)

# Pilih agen
st.sidebar.subheader("Filter Agen")
agent_list = pd.read_sql_query("SELECT DISTINCT agent_name FROM trades WHERE agent_name IS NOT NULL", conn)
agent_options = ['Semua'] + agent_list['agent_name'].tolist()
selected_agent = st.sidebar.selectbox("Pilih Agen", agent_options)

st.sidebar.markdown("---")
st.sidebar.info(
    "Dashboard ini terhubung ke database bot trading. "
    "Data diperbarui setiap 10 detik."
)

# =================== MAIN DASHBOARD ===================
st.title("📊 Multi-Agent Trading Bot Dashboard")
st.markdown("---")

# Load data
trades_df = load_trades()
agent_perf = load_agent_performance()
sentiment_df = load_sentiment_history()
equity_df = get_equity_curve()

# =================== METRIK UTAMA ===================
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_trades = len(trades_df[trades_df['action'].isin(['BUY', 'SELL'])])
    st.metric("Total Trades", total_trades)

with col2:
    if not trades_df.empty and 'profit' in trades_df.columns:
        total_profit = trades_df['profit'].sum()
        st.metric("Total Profit/Loss", f"Rp{total_profit:,.0f}")
    else:
        st.metric("Total Profit/Loss", "Rp0")

with col3:
    if not agent_perf.empty:
        total_wins = agent_perf['wins'].sum()
        win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
        st.metric("Win Rate", f"{win_rate:.1f}%")
    else:
        st.metric("Win Rate", "0%")

with col4:
    if not sentiment_df.empty:
        latest_sentiment = sentiment_df.iloc[0]['sentiment_signal']
        st.metric("Sentimen Terkini", latest_sentiment)
    else:
        st.metric("Sentimen Terkini", "N/A")

st.markdown("---")

# =================== DUA KOLOM UTAMA ===================
left_col, right_col = st.columns(2)

with left_col:
    st.subheader("📈 Equity Curve")
    
    if not equity_df.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=equity_df['timestamp'],
            y=equity_df['cumulative_profit'],
            mode='lines',
            name='Equity',
            line=dict(color='gold', width=2)
        ))
        fig.update_layout(
            height=400,
            margin=dict(l=0, r=0, t=20, b=20),
            yaxis_title="Profit (Rp)",
            xaxis_title="Waktu"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Belum ada data equity")

with right_col:
    st.subheader("🏆 Agent Leaderboard")
    
    if not agent_perf.empty:
        # Hitung win rate
        agent_perf['win_rate'] = (agent_perf['wins'] / agent_perf['total_trades'] * 100).fillna(0)
        agent_perf = agent_perf.sort_values('total_profit', ascending=False)
        
        fig = go.Figure(data=[
            go.Bar(
                name='Total Profit',
                x=agent_perf['agent_name'],
                y=agent_perf['total_profit'],
                marker_color='lightgreen'
            ),
            go.Bar(
                name='Win Rate (%)',
                x=agent_perf['agent_name'],
                y=agent_perf['win_rate'],
                marker_color='gold',
                yaxis='y2'
            )
        ])
        
        fig.update_layout(
            height=400,
            yaxis=dict(title="Total Profit (Rp)"),
            yaxis2=dict(
                title="Win Rate (%)",
                overlaying='y',
                side='right',
                range=[0, 100]
            ),
            barmode='group',
            margin=dict(l=0, r=0, t=20, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Belum ada data performa agent")

st.markdown("---")

# =================== SENTIMEN DAN FUNDAMENTAL ===================
st.subheader("📰 Sentimen & Fundamental Pasar")

sent_col1, sent_col2 = st.columns(2)

with sent_col1:
    if not sentiment_df.empty:
        sentiment_df['timestamp'] = pd.to_datetime(sentiment_df['timestamp'])
        sentiment_df = sentiment_df.sort_values('timestamp')
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=sentiment_df['timestamp'],
            y=sentiment_df['sentiment_score'],
            mode='lines+markers',
            name='Sentiment Score',
            line=dict(color='orange', width=2)
        ))
        fig.update_layout(
            height=300,
            title="Sentiment Score (0-100)",
            yaxis_range=[0, 100],
            margin=dict(l=0, r=0, t=30, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Belum ada data sentimen")

with sent_col2:
    if not sentiment_df.empty:
        # Map signal ke angka untuk visualisasi
        signal_map = {'BULLISH': 1, 'NEUTRAL': 0, 'BEARISH': -1}
        sentiment_df['signal_value'] = sentiment_df['sentiment_signal'].map(signal_map).fillna(0)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=sentiment_df['timestamp'],
            y=sentiment_df['signal_value'],
            mode='lines+markers',
            name='Signal',
            line=dict(color='blue', width=2)
        ))
        fig.update_layout(
            height=300,
            title="Sentiment Signal (BULLISH=1, NEUTRAL=0, BEARISH=-1)",
            yaxis_range=[-1.5, 1.5],
            margin=dict(l=0, r=0, t=30, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Belum ada data signal")

st.markdown("---")

# =================== TRADE HISTORY ===================
st.subheader("📜 Trade History")

# Filter berdasarkan agen
if selected_agent != 'Semua':
    filtered_trades = trades_df[trades_df['agent_name'] == selected_agent]
else:
    filtered_trades = trades_df

# Tampilkan tabel
if not filtered_trades.empty:
    # Format kolom untuk tampilan
    display_cols = ['timestamp', 'action', 'entry', 'sl', 'tp', 'exit_price', 'profit', 'agent_name', 'confidence']
    display_df = filtered_trades[display_cols].copy()
    
    # Format angka
    display_df['entry'] = display_df['entry'].round(2)
    display_df['sl'] = display_df['sl'].round(2)
    display_df['tp'] = display_df['tp'].round(2)
    display_df['exit_price'] = display_df['exit_price'].round(2)
    display_df['profit'] = display_df['profit'].round(0)
    display_df['confidence'] = display_df['confidence'].round(2)
    
    # Warna berdasarkan profit
    def color_profit(val):
        color = 'green' if val > 0 else 'red' if val < 0 else 'black'
        return f'color: {color}'
    
    st.dataframe(
        display_df.style.applymap(color_profit, subset=['profit']),
        use_container_width=True,
        height=400
    )
else:
    st.info("Belum ada data trade")

st.markdown("---")

# =================== AI DECISION LOGS ===================
st.subheader("🧠 AI Decision Logs")

if not filtered_trades.empty and 'reason' in filtered_trades.columns:
    # Tampilkan 5 trade terakhir dengan reasoning
    for idx, row in filtered_trades.head(5).iterrows():
        with st.expander(f"{row['timestamp']} - {row['action']} by {row['agent_name']} (Conf: {row['confidence']:.2f})"):
            st.write(f"**Reason:** {row.get('reason', 'No reason provided')}")
            if pd.notna(row.get('reflection')):
                st.write(f"**Reflection:** {row['reflection']}")
else:
    st.info("Belum ada decision logs")

# Footer
st.markdown("---")
st.caption(f"Dashboard diperbarui: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Multi-Agent Bot V2")