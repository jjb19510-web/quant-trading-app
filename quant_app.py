import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

# 페이지 설정
st.set_page_config(page_title="퀀트 트레이딩 분석기", page_icon="📈", layout="wide")

st.title("📈 퀀트 트레이딩 분석기")
st.markdown("RSI 전략을 활용한 포트폴리오 분석 도구")
st.divider()

# 사이드바로 입력창 이동
with st.sidebar:
    st.header("⚙️ 설정")
    tickers_input = st.text_input("종목 티커 (쉼표로 구분)", "005930.KS, 000660.KS, 373220.KS")
    start_date = st.date_input("시작일", value=pd.to_datetime("2023-01-01"))
    end_date = st.date_input("종료일", value=pd.to_datetime("2025-01-01"))
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
    signal = (rsi < rsi_threshold).astype(int)
    signal_count = signal.sum(axis=1).replace(0, 1)

    returns = df.pct_change()
    weighted_return = (returns * signal.shift(1)).sum(axis=1) / signal_count.shift(1)
    equal_return = returns.mean(axis=1)

    portfolio_rsi = (1 + weighted_return).cumprod()
    portfolio_equal = (1 + equal_return).cumprod()

    # 수익률 카드
    col1, col2 = st.columns(2)
    with col1:
        st.metric("균등 포트폴리오", f"{(portfolio_equal.iloc[-1] - 1) * 100:.2f}%")
    with col2:
        st.metric("RSI 포트폴리오", f"{(portfolio_rsi.iloc[-1] - 1) * 100:.2f}%",
                  delta=f"{((portfolio_rsi.iloc[-1] - portfolio_equal.iloc[-1]) * 100):.2f}%")

    st.divider()

    # 그래프
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(portfolio_equal, label="Equal Portfolio", alpha=0.7)
    ax.plot(portfolio_rsi, label="RSI Portfolio", linewidth=2)
    ax.set_title("Portfolio - RSI Strategy")
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative Return")
    ax.legend()
    ax.grid(True)
    st.pyplot(fig)