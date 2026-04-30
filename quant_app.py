import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Quant Trading Analyzer", page_icon="📈", layout="wide")

st.title("📈 퀀트 트레이딩 분석기 (Quant Trading Analyzer)")
st.markdown("RSI 및 이동평균 전략을 활용한 포트폴리오 분석 도구")
st.divider()

with st.sidebar:
    st.header("⚙️ Settings")
    tickers_input = st.text_input("Tickers (comma separated)", "005930.KS, 000660.KS, 373220.KS")
    start_date = st.date_input("Start date", value=pd.to_datetime("2023-01-01"))
    end_date = st.date_input("End date", value=pd.to_datetime("2025-01-01"))
    strategy = st.selectbox("전략 선택 (Strategy)", ["RSI 전략 (RSI)", "이동평균선 전략 (Moving Average)", "복합 전략 (Combined)"])

    if strategy == "RSI 전략 (RSI)":
        rsi_threshold = st.slider("RSI 기준값 (RSI Threshold)", 10, 70, 40)
        ma_short, ma_long = 20, 60
    elif strategy == "이동평균선 전략 (Moving Average)":
        ma_short = st.slider("단기 이동평균 (Short MA)", 5, 60, 20)
        ma_long = st.slider("장기 이동평균 (Long MA)", 20, 120, 60)
        rsi_threshold = 40
    else:
        rsi_threshold = st.slider("RSI 기준값 (RSI Threshold)", 10, 70, 40)
        ma_short = st.slider("단기 이동평균 (Short MA)", 5, 60, 20)
        ma_long = st.slider("장기 이동평균 (Long MA)", 20, 120, 60)

    analyze = st.button("🔍 분석 시작 (Analyze)", use_container_width=True)

# 전략 설명
if strategy == "RSI 전략 (RSI)":
    st.info("""
    **RSI 전략 (Relative Strength Index, 상대강도지수)**
    
    📌 RSI란? 주가가 최근에 얼마나 많이 올랐는지를 0~100 사이 숫자로 표현한 지표예요.
    
    - RSI가 낮을수록 → 너무 많이 떨어진 상태 → **매수 신호**
    - RSI가 높을수록 → 너무 많이 오른 상태 → **매도 신호**
    
    📌 RSI Threshold(기준값)란? 매수 신호를 발생시키는 RSI 기준선이에요.
    - 기준값 40 → RSI가 40 이하일 때 매수
    - 기준값을 높이면 매수 기회가 많아지고, 낮추면 매수 기회가 줄어요.
    """)
elif strategy == "이동평균선 전략 (Moving Average)":
    st.info("""
    **이동평균선 전략 (Moving Average, MA)**
    
    📌 이동평균선(MA)이란? 특정 기간 동안의 주가 평균을 선으로 이은 거예요.
    
    - **단기 MA(Short MA)** → 최근 단기간의 평균 (빠르게 반응)
    - **장기 MA(Long MA)** → 더 긴 기간의 평균 (느리게 반응)
    
    📌 전략 원리:
    - 단기 MA > 장기 MA → 상승 추세 → **매수 신호** 📈 (골든크로스)
    - 단기 MA < 장기 MA → 하락 추세 → **매도 신호** 📉 (데드크로스)
    """)
else:
    st.info("""
    **복합 전략 (Combined Strategy)**
    
    📌 RSI 전략 + 이동평균선 전략을 동시에 사용해요.
    
    - RSI가 기준값 이하 **AND** 단기 MA > 장기 MA → **매수 신호**
    - 두 조건을 동시에 만족해야 하므로 매수 타이밍이 까다롭지만 더 정확해요.
    
    💡 상승 추세인데 과매도 상태인 종목을 찾는 전략이에요!
    """)

st.divider()

if analyze:
    tickers = [t.strip() for t in tickers_input.split(",")]

    with st.spinner("데이터 불러오는 중... (Loading data...)"):
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
    ma_s = df.rolling(ma_short).mean()
    ma_l = df.rolling(ma_long).mean()

    if strategy == "RSI 전략 (RSI)":
        signal = (rsi < rsi_threshold).astype(int)
    elif strategy == "이동평균선 전략 (Moving Average)":
        signal = (ma_s > ma_l).astype(int)
    else:
        signal = ((rsi < rsi_threshold) & (ma_s > ma_l)).astype(int)

    signal_count = signal.sum(axis=1).replace(0, 1)
    returns = df.pct_change()
    weighted_return = (returns * signal.shift(1)).sum(axis=1) / signal_count.shift(1)
    equal_return = returns.mean(axis=1)

    portfolio_strategy = (1 + weighted_return).cumprod()
    portfolio_equal = (1 + equal_return).cumprod()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("균등 포트폴리오 (Equal Portfolio)", f"{(portfolio_equal.iloc[-1] - 1) * 100:.2f}%")
    with col2:
        st.metric(f"{strategy}", f"{(portfolio_strategy.iloc[-1] - 1) * 100:.2f}%",
                  delta=f"{((portfolio_strategy.iloc[-1] - portfolio_equal.iloc[-1]) * 100):.2f}%")

    st.divider()

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(portfolio_equal, label="Equal Portfolio", alpha=0.7)
    ax.plot(portfolio_strategy, label=strategy, linewidth=2)
    ax.set_title(f"Portfolio - {strategy}")
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative Return")
    ax.legend()
    ax.grid(True)
    st.pyplot(fig)