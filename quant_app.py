import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Quant Trading Analyzer", page_icon="📈", layout="wide")

st.title("📈 Quant Trading Analyzer (퀀트 트레이딩 분석기)")
st.markdown("RSI 및 이동평균 전략을 활용한 포트폴리오 분석 도구")
st.divider()

with st.sidebar:
    st.header("⚙️ Settings")
    tickers_input = st.text_input("Tickers (comma separated)", "005930.KS, 000660.KS, 373220.KS")
    start_date = st.date_input("Start date", value=pd.to_datetime("2023-01-01"))
    end_date = st.date_input("End date", value=pd.to_datetime("2025-01-01"))
    strategy = st.selectbox("전략 선택 (Strategy)", ["RSI 전략 (RSI)", "이동평균선 전략 (Moving Average)", "복합 전략 (Combined)"])

    if strategy == "RSI (RSI 전략)":
        rsi_threshold = st.slider("RSI 기준값 (RSI Threshold)", 10, 70, 40)
        ma_short, ma_long = 20, 60
    elif strategy == "Moving Average (이동평균선 전략)":
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
    """)
elif strategy == "이동평균선 전략 (Moving Average)":
    st.info("""
    **이동평균선 전략 (Moving Average, MA)**
    
    📌 이동평균선(MA)이란? 특정 기간 동안의 주가 평균을 선으로 이은 거예요.
    
    - **단기 MA(Short MA)** → 최근 단기간의 평균
    - **장기 MA(Long MA)** → 더 긴 기간의 평균
    
    📌 전략 원리:
    - 단기 MA > 장기 MA → **매수 신호** 📈 (골든크로스)
    - 단기 MA < 장기 MA → **매도 신호** 📉 (데드크로스)
    """)
else:
    st.info("""
    **복합 전략 (Combined Strategy)**
    
    📌 RSI 전략 + 이동평균선 전략을 동시에 사용해요.
    
    - RSI가 기준값 이하 **AND** 단기 MA > 장기 MA → **매수 신호**
    - 두 조건을 동시에 만족해야 하므로 더 정확해요.
    """)

# 균등 포트폴리오 설명 (항상 고정)
st.info("""
**균등 포트폴리오 (Equal Portfolio)란?**

📌 전략 없이 모든 종목에 똑같은 비율로 투자하는 방식이에요.

- 종목이 3개면 → 각각 33%씩 투자
- 아무 전략 없이 그냥 들고 있는 것

📌 왜 보여주냐면?
- 내 전략이 **"아무것도 안 하는 것보다 나은가?"** 를 비교하기 위한 기준선이에요.
- 전략 수익률 > 균등 포트폴리오 → **전략이 효과 있음** ✅
- 전략 수익률 < 균등 포트폴리오 → **그냥 들고 있는 게 나음** ❌
""")

st.divider()

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

    equal_pct = (portfolio_equal.iloc[-1] - 1) * 100
    strategy_pct = (portfolio_strategy.iloc[-1] - 1) * 100
    diff_pct = strategy_pct - equal_pct

    col1, col2 = st.columns(2)
    with col1:
        st.metric("균등 포트폴리오", f"{equal_pct:.2f}%")
    with col2:
        st.metric(f"{strategy}", f"{strategy_pct:.2f}%", delta=f"{diff_pct:.2f}%")

    st.divider()

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=portfolio_equal.index,
        y=((portfolio_equal - 1) * 100),
        name="Equal Portfolio",
        line=dict(color="royalblue", width=2),
        hovertemplate="%{x}<br>수익률: %{y:.2f}%<extra></extra>"
    ))

    fig.add_trace(go.Scatter(
        x=portfolio_strategy.index,
        y=((portfolio_strategy - 1) * 100),
        name=strategy,
        line=dict(color="orangered", width=2),
        hovertemplate="%{x}<br>수익률: %{y:.2f}%<extra></extra>"
    ))

    fig.update_layout(
        title=f"포트폴리오 수익률 비교 - {strategy}",
        xaxis_title="날짜",
        yaxis_title="수익률 (%)",
        hovermode="x unified",
        template="plotly_dark",
        height=500
    )

    fig.add_hline(y=0, line_dash="dash", line_color="gray")

    st.plotly_chart(fig, use_container_width=True)