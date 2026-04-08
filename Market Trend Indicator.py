import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# Page Config
st.set_page_config(page_title="QTI Market Trend Tool", layout="wide")

# --- QTI LIGHT THEME BRANDING ---
st.markdown("""
    <style>
    .stApp {
        background-color: #FFFFFF;
    }
    .qti-container {
        background-color: #F8F9FA;
        padding: 25px;
        border-radius: 4px;
        border-bottom: 3px solid #212529;
        margin-bottom: 30px;
        box-shadow: 0px 2px 4px rgba(0,0,0,0.05);
    }
    .qti-header {
        font-size: 34px !important;
        font-weight: 900;
        color: #1A1C1E;
        letter-spacing: -0.5px;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    .qti-subtitle {
        font-size: 13px;
        color: #495057;
        text-transform: uppercase;
        font-weight: 700;
        letter-spacing: 2px;
        margin-bottom: 5px;
    }
    [data-testid="stMetricLabel"] {
        color: #212529 !important;
        font-weight: 600 !important;
    }
    </style>
    <div class="qti-container">
        <div class="qti-subtitle">Quantitative Trend Indicators</div>
        <div class="qti-header">QTI | EQUITY INTELLIGENCE</div>
    </div>
    """, unsafe_allow_html=True)

# --- Sidebar Inputs ---
with st.sidebar:
    st.header("Terminal Controls")
    ticker_symbol = st.text_input("Equity Ticker", value="TSLA").upper()
    rvol_threshold = st.slider("RVOL Sensitivity", 1.0, 5.0, 2.0)
    st.divider()
    st.caption("Mode: Light Terminal | Version 2.0.6")


# --- Data Engine ---
@st.cache_data(ttl=60)
def get_market_data(symbol):
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="5d", interval="5m")
    if df.empty: return None

    # VWAP Calculation
    df['TP'] = (df['High'] + df['Low'] + df['Close']) / 3
    df['Cumulative_TPV'] = (df['TP'] * df['Volume']).groupby(df.index.date).cumsum()
    df['Cumulative_Vol'] = df['Volume'].groupby(df.index.date).cumsum()
    df['VWAP'] = df['Cumulative_TPV'] / df['Cumulative_Vol']

    # RVOL Calculation
    df['Time'] = df.index.time
    historical_avg = df.groupby('Time')['Volume'].mean()
    df['RVOL'] = df.apply(lambda row: row['Volume'] / historical_avg[row['Time']], axis=1)

    return df


data = get_market_data(ticker_symbol)

if data is not None:
    latest = data.iloc[-1]

    st.markdown(f"### 🔍 Analysis for Equity: **{ticker_symbol}**")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Current Price", f"${latest['Close']:.2f}")
    col2.metric("Institutional VWAP", f"${latest['VWAP']:.2f}")

    rvol_val = latest['RVOL']
    col3.metric("RVOL Intensity", f"{rvol_val:.2f}x", delta=f"{rvol_val - 1:.2f}", delta_color="normal")

    is_rally = latest['Close'] > latest['VWAP'] and rvol_val > rvol_threshold
    if is_rally:
        col4.success("🚀 RALLY CONFIRMED")
    elif latest['Close'] < latest['VWAP'] and rvol_val > rvol_threshold:
        col4.error("⚠️ DISTRIBUTION DETECTED")
    else:
        col4.info("⚖️ NEUTRAL / CONSOLIDATION")

    # --- MAIN CHART ---
    fig = go.Figure()

    # Price Line
    fig.add_trace(go.Scatter(x=data.index, y=data['Close'], name="Price", line=dict(color='#006D5B', width=2.5)))

    # VWAP Line
    fig.add_trace(go.Scatter(x=data.index, y=data['VWAP'], name="VWAP", line=dict(color='#34495E', dash='dot')))

    # Volume Bars - UPDATED TO RED
    fig.add_trace(go.Bar(
        x=data.index,
        y=data['Volume'],
        name="Volume",
        opacity=0.35,  # Increased opacity for visibility
        yaxis="y2",
        marker_color="#E74C3C"  # Bright Professional Red
    ))

    fig.update_layout(
        template="plotly_white",
        height=500,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", y=1.1, x=0),
        yaxis=dict(showgrid=True, gridcolor='#F0F0F0', title="Price ($)"),
        yaxis2=dict(overlaying="y", side="right", showgrid=False, title="Volume Volume")
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- RAW TAPE DATA (PERMANENT) ---
    st.markdown("---")
    st.subheader("📋 Raw Tape Data")
    tape_df = data[['Close', 'Volume', 'VWAP', 'RVOL']].tail(25).sort_index(ascending=False)
    st.dataframe(
        tape_df.style.format({
            'Close': '{:.2f}',
            'VWAP': '{:.2f}',
            'RVOL': '{:.2f}x',
            'Volume': '{:,}'
        }),
        use_container_width=True
    )

else:
    st.error(f"Ticker {ticker_symbol} not found.")