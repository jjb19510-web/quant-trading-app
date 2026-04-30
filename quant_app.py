import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="퀀트 트레이딩 분석기", page_icon="📈", layout="wide")

st.title("📈 퀀트 트레이딩 분석기")
st.markdown("RSI 및 이동평균 전략을 활용한 포트폴리오 분석 도구")
st.divider()

with st.sidebar:
    st.header("⚙️ 설정")
    tickers_input = st.text_input("종목 티커 (쉼표로 구분)", "005930.KS, 000660.KS, 373220.KS")
    start_date = st.date_input("시작일", value=pd.to_datetime("2023-01-01"))
    end_date = st.date_input("종료일", value=pd.to_datetime("2025-01-01"))
    strategy = st.selectbox("전략 선택", ["RSI", "이동평균", "복합"])
    rsi_threshold = st.slider("RSI 기준값", 10, 70, 40)
    analyze = st.button("🔍 분석 시작", use_container_width=True)

if analyze:
    tickers = [t.strip() for t in tickers_input.split(",")]

    with st.spinner("데이터 불러오는 중..."):
        df = yf.download(tickers, start=start_date, end=end_date)["Close"]

    def calculate_rsi(data, period=14):
        delta = data.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    rsi = df.apply(calculate_rsi)
    ma20 = df.rolling(20).mean()
    ma60 = df.rolling(60).mean()

    if strategy == "RSI":
        signal = (rsi < rsi_threshold).astype(int)
    elif strategy == "이동평균":
        signal = (ma20 > ma60).astype(int)
    else:  # 복합
        signal = ((rsi < rsi_threshold) & (ma20 > ma60)).astype(int)

    signal_count = signal.sum(axis=1).replace(0, 1)
    returns = df.pct_change()
    weighted_return = (returns * signal.shift(1)).sum(axis=1) / signal_count.shift(1)
    equal_return = returns.mean(axis=1)

    portfolio_strategy = (1 + weighted_return).cumprod()
    portfolio_equal = (1 + equal_return).cumprod()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("균등 포트폴리오", f"{(portfolio_equal.iloc[-1] - 1) * 100:.2f}%")
    with col2:
        st.metric(f"{strategy} 전략", f"{(portfolio_strategy.iloc[-1] - 1) * 100:.2f}%",
                  delta=f"{((portfolio_strategy.iloc[-1] - portfolio_equal.iloc[-1]) * 100):.2f}%")

    st.divider()

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(portfolio_equal, label="Equal Portfolio", alpha=0.7)
    ax.plot(portfolio_strategy, label=f"{strategy} Strategy", linewidth=2)
    ax.set_title(f"Portfolio - {strategy} Strategy")
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative Return")
    ax.legend()
    ax.grid(True)
    st.pyplot(fig)