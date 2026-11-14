import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Page Configuration
st.set_page_config(page_title="Stock Price Trend Analyzer", page_icon="📈", layout="wide")
st.title("📈 Stock Price Trend Analyzer")
st.markdown("Analyze historical price action, Moving Averages, and RSI trends in real time.")

# Sidebar Controls
st.sidebar.header("Configuration")
ticker = st.sidebar.text_input("Enter Stock Ticker (e.g., AAPL, MSFT, RELIANCE.NS)", value="AAPL").strip().upper()
period = st.sidebar.selectbox("Select Timeframe", ["3mo", "6mo", "1y", "2y", "5y"], index=2)
sma_short = st.sidebar.slider("Short-Term SMA (Days)", 5, 50, 20)
sma_long = st.sidebar.slider("Long-Term SMA (Days)", 20, 200, 50)

# Fetch Data (Optimized for Streamlit Cloud)
@st.cache_data(ttl=3600)
def load_data(symbol, time_period):
    df = yf.download(symbol, period=time_period, progress=False)
    # Flatten multi-level columns if returned by newer yfinance versions
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

if not ticker:
    st.warning("Please enter a valid stock ticker symbol in the sidebar.")
else:
    try:
        df = load_data(ticker, period)

        if df.empty or len(df) < 2:
            st.error(f"No data found for ticker '{ticker}'. For Indian stocks, add '.NS' (e.g., TCS.NS or RELIANCE.NS).")
        else:
            # Calculate Technical Indicators
            df[f"SMA_{sma_short}"] = df["Close"].rolling(window=sma_short).mean()
            df[f"SMA_{sma_long}"] = df["Close"].rolling(window=sma_long).mean()

            # Calculate RSI (14-day)
            delta = df["Close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df["RSI"] = 100 - (100 / (1 + rs))

            # Top Key Metrics
            latest_close = float(df["Close"].iloc[-1])
            prev_close = float(df["Close"].iloc[-2])
            price_change = latest_close - prev_close
            pct_change = (price_change / prev_close) * 100
            currency = "INR" if ticker.endswith((".NS", ".BO")) else "USD"

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Current Price", f"{latest_close:.2f} {currency}", f"{price_change:.2f} ({pct_change:.2f}%)")
            col2.metric("Period High", f"{float(df['High'].max()):.2f} {currency}")
            col3.metric("Period Low", f"{float(df['Low'].min()):.2f} {currency}")
            col4.metric("Current RSI (14)", f"{float(df['RSI'].iloc[-1]):.1f}")

            # Trend Signal Banner
            latest_short = df[f"SMA_{sma_short}"].iloc[-1]
            latest_long = df[f"SMA_{sma_long}"].iloc[-1]
            if pd.notna(latest_short) and pd.notna(latest_long):
                if latest_short > latest_long:
                    st.success(f"**Bullish Trend Signal:** {sma_short}-day SMA ({latest_short:.2f}) is trading above the {sma_long}-day SMA ({latest_long:.2f}).")
                else:
                    st.warning(f"**Bearish Trend Signal:** {sma_short}-day SMA ({latest_short:.2f}) is trading below the {sma_long}-day SMA ({latest_long:.2f}).")

            # Interactive Plotly Chart (Candlestick + SMA + RSI)
            fig = make_subplots(
                rows=2, cols=1, shared_xaxes=True,
                vertical_spacing=0.08, row_heights=[0.7, 0.3],
                subplot_titles=(f"{ticker} Price & Moving Averages", "Relative Strength Index (RSI)")
            )

            # Candlestick Trace
            fig.add_trace(go.Candlestick(
                x=df.index, open=df["Open"], high=df["High"],
                low=df["Low"], close=df["Close"], name="Price"
            ), row=1, col=1)

            # Moving Averages
            fig.add_trace(go.Scatter(
                x=df.index, y=df[f"SMA_{sma_short}"],
                line=dict(color="orange", width=1.5), name=f"SMA {sma_short}"
            ), row=1, col=1)

            fig.add_trace(go.Scatter(
                x=df.index, y=df[f"SMA_{sma_long}"],
                line=dict(color="cyan", width=1.5), name=f"SMA {sma_long}"
            ), row=1, col=1)

            # RSI Trace
            fig.add_trace(go.Scatter(
                x=df.index, y=df["RSI"],
                line=dict(color="purple", width=1.5), name="RSI (14)"
            ), row=2, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

            fig.update_layout(height=650, xaxis_rangeslider_visible=False, template="plotly_dark")
            st.plotly_chart(fig, width="stretch")

            # Raw Data & CSV Export
            with st.expander("View Historical Data & Download CSV"):
                st.dataframe(df.tail(20))
                csv = df.to_csv().encode("utf-8")
                st.download_button("Download Full Data as CSV", data=csv, file_name=f"{ticker}_trend_data.csv", mime="text/csv")

    except Exception as e:
        st.error(f"An error occurred while fetching data: {e}")
