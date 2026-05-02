import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Quant Trading Analyzer", page_icon="📈", layout="wide")

st.title("📈 퀀트 트레이딩 분석기 (Quant Trading Analyzer)")
st.markdown("RSI 및 이동평균 전략을 활용한 포트폴리오 분석 도구")
st.divider()

with st.sidebar:
    st.header("⚙️ Settings")
    
    market = st.selectbox("시장 선택 (Market)", ["한국주식 (KS)", "미국주식 (US)"])
    
    if market == "한국주식 (KS)":
        st.caption("예시: 005930, 000660, 373220")
        tickers_raw = st.text_input("종목 코드 입력 (쉼표로 구분)", "")
        tickers = [t.strip() + ".KS" for t in tickers_raw.split(",") if t.strip()]
    else:
        st.caption("예시: AAPL, TSLA, NVDA")
        tickers_raw = st.text_input("티커 입력 (쉼표로 구분)", "")
        tickers = [t.strip() for t in tickers_raw.split(",") if t.strip()]

    start_date = st.date_input("Start date", value=pd.to_datetime("2024-01-01"))
    end_date = st.date_input("End date", value=pd.to_datetime("2026-01-01"))
    strategy = st.selectbox("전략 선택 (Strategy)", [
        "RSI 전략 (RSI)",
        "이동평균선 전략 (Moving Average)",
        "볼린저 밴드 전략 (Bollinger Bands)",
        "복합 전략 (Combined)"
    ])

    if strategy == "RSI 전략 (RSI)":
        rsi_threshold = st.slider("RSI 기준값 (RSI Threshold)", 10, 70, 40)
        ma_short, ma_long = 20, 60
        bb_period = 20
    elif strategy == "이동평균선 전략 (Moving Average)":
        ma_short = st.slider("단기 이동평균 (Short MA)", 5, 60, 20)
        ma_long = st.slider("장기 이동평균 (Long MA)", 20, 120, 60)
        rsi_threshold = 40
        bb_period = 20
    elif strategy == "볼린저 밴드 전략 (Bollinger Bands)":
        bb_period = st.slider("볼린저 밴드 기간 (Period)", 5, 60, 20)
        rsi_threshold = 40
        ma_short, ma_long = 20, 60
    else:
        rsi_threshold = st.slider("RSI 기준값 (RSI Threshold)", 10, 70, 40)
        ma_short = st.slider("단기 이동평균 (Short MA)", 5, 60, 20)
        ma_long = st.slider("장기 이동평균 (Long MA)", 20, 120, 60)
        bb_period = 20

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
elif strategy == "볼린저 밴드 전략 (Bollinger Bands)":
    st.info("""
    **볼린저 밴드 전략 (Bollinger Bands)**
    
    📌 볼린저 밴드란? 이동평균선 위아래로 밴드(띠)를 만들어서 주가가 그 범위를 벗어나면 신호를 주는 지표예요.
    
    3개의 선으로 구성돼요:
    - **중간선** → 20일 이동평균선
    - **상단 밴드** → 중간선 + (표준편차 × 2)
    - **하단 밴드** → 중간선 - (표준편차 × 2)
    
    📌 전략 원리:
    - 주가가 **하단 밴드 아래**로 떨어지면 → **매수 신호** 📈
    - 주가가 **상단 밴드 위**로 올라가면 → **매도 신호** 📉
    """)
else:
    st.info("""
    **복합 전략 (Combined Strategy)**
    
    📌 RSI 전략 + 이동평균선 전략을 동시에 사용해요.
    
    - RSI가 기준값 이하 **AND** 단기 MA > 장기 MA → **매수 신호**
    - 두 조건을 동시에 만족해야 하므로 더 정확해요.
    """)

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
    if not tickers:
        st.warning("종목을 입력해주세요!")
    else:
        with st.spinner("데이터 불러오는 중..."):
            df = yf.download(tickers, start=start_date, end=end_date)["Close"]

        if isinstance(df, pd.Series):
            df = df.to_frame()

        def calculate_rsi(data, period=14):
            delta = data.diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(period).mean()
            avg_loss = loss.rolling(period).mean()
            rs = avg_gain / avg_loss
            return 100 - (100 / (1 + rs))

        def calculate_bb(data, period=20):
            ma = data.rolling(period).mean()
            std = data.rolling(period).std()
            upper = ma + (std * 2)
            lower = ma - (std * 2)
            return upper, lower, ma

        def calculate_mdd(portfolio):
            peak = portfolio.cummax()
            drawdown = (portfolio - peak) / peak
            return drawdown.min() * 100

        def calculate_sharpe(returns):
            return (returns.mean() / returns.std()) * (252 ** 0.5)

        rsi = df.apply(calculate_rsi)
        ma_s = df.rolling(ma_short).mean()
        ma_l = df.rolling(ma_long).mean()
        bb_upper, bb_lower, bb_mid = calculate_bb(df, bb_period)

        if strategy == "RSI 전략 (RSI)":
            signal = (rsi < rsi_threshold).astype(int)
        elif strategy == "이동평균선 전략 (Moving Average)":
            signal = (ma_s > ma_l).astype(int)
        elif strategy == "볼린저 밴드 전략 (Bollinger Bands)":
            signal = (df < bb_lower).astype(int)
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

        mdd_equal = calculate_mdd(portfolio_equal)
        mdd_strategy = calculate_mdd(portfolio_strategy)
        sharpe_equal = calculate_sharpe(equal_return.dropna())
        sharpe_strategy = calculate_sharpe(weighted_return.dropna())

        st.subheader("📊 성과 지표")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("균등 수익률", f"{equal_pct:.2f}%")
        with col2:
            st.metric("전략 수익률", f"{strategy_pct:.2f}%", delta=f"{diff_pct:.2f}%")

        col3, col4, col5, col6 = st.columns(4)
        with col3:
            st.metric("균등 MDD", f"{mdd_equal:.2f}%")
        with col4:
            st.metric("전략 MDD", f"{mdd_strategy:.2f}%")
        with col5:
            st.metric("균등 샤프지수", f"{sharpe_equal:.2f}")
        with col6:
            st.metric("전략 샤프지수", f"{sharpe_strategy:.2f}")

        st.divider()

        # 전략별 지표 그래프
        st.subheader("📈 전략 지표 그래프")
        ticker_for_chart = tickers[0]

        if strategy == "이동평균선 전략 (Moving Average)":
            fig1 = go.Figure()
            fig1.add_trace(go.Scatter(
                x=df.index, y=df[ticker_for_chart],
                name="주가", line=dict(color="white", width=1)
            ))
            fig1.add_trace(go.Scatter(
                x=ma_s.index, y=ma_s[ticker_for_chart],
                name=f"MA{ma_short}", line=dict(color="orange", width=1.5)
            ))
            fig1.add_trace(go.Scatter(
                x=ma_l.index, y=ma_l[ticker_for_chart],
                name=f"MA{ma_long}", line=dict(color="royalblue", width=1.5)
            ))
            fig1.update_layout(
                title=f"{ticker_for_chart} - 이동평균선",
                template="plotly_dark", height=400,
                hovermode="x unified"
            )
            st.plotly_chart(fig1, use_container_width=True)

        elif strategy == "RSI 전략 (RSI)":
            fig1 = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                  row_heights=[0.7, 0.3])
            fig1.add_trace(go.Scatter(
                x=df.index, y=df[ticker_for_chart],
                name="주가", line=dict(color="white", width=1)
            ), row=1, col=1)
            fig1.add_trace(go.Scatter(
                x=rsi.index, y=rsi[ticker_for_chart],
                name="RSI", line=dict(color="orange", width=1.5)
            ), row=2, col=1)
            fig1.add_hline(y=rsi_threshold, line_dash="dash",
                           line_color="red", row=2, col=1)
            fig1.update_layout(
                title=f"{ticker_for_chart} - RSI",
                template="plotly_dark", height=500,
                hovermode="x unified"
            )
            st.plotly_chart(fig1, use_container_width=True)

        elif strategy == "볼린저 밴드 전략 (Bollinger Bands)":
            fig1 = go.Figure()
            fig1.add_trace(go.Scatter(
                x=df.index, y=df[ticker_for_chart],
                name="주가", line=dict(color="white", width=1)
            ))
            fig1.add_trace(go.Scatter(
                x=bb_upper.index, y=bb_upper[ticker_for_chart],
                name="상단 밴드", line=dict(color="red", width=1, dash="dash")
            ))
            fig1.add_trace(go.Scatter(
                x=bb_mid.index, y=bb_mid[ticker_for_chart],
                name="중간선", line=dict(color="yellow", width=1)
            ))
            fig1.add_trace(go.Scatter(
                x=bb_lower.index, y=bb_lower[ticker_for_chart],
                name="하단 밴드", line=dict(color="green", width=1, dash="dash"),
                fill="tonexty", fillcolor="rgba(0,255,0,0.05)"
            ))
            fig1.update_layout(
                title=f"{ticker_for_chart} - 볼린저 밴드",
                template="plotly_dark", height=400,
                hovermode="x unified"
            )
            st.plotly_chart(fig1, use_container_width=True)

        elif strategy == "복합 전략 (Combined)":
            fig1 = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                  row_heights=[0.7, 0.3])
            fig1.add_trace(go.Scatter(
                x=df.index, y=df[ticker_for_chart],
                name="주가", line=dict(color="white", width=1)
            ), row=1, col=1)
            fig1.add_trace(go.Scatter(
                x=ma_s.index, y=ma_s[ticker_for_chart],
                name=f"MA{ma_short}", line=dict(color="orange", width=1.5)
            ), row=1, col=1)
            fig1.add_trace(go.Scatter(
                x=ma_l.index, y=ma_l[ticker_for_chart],
                name=f"MA{ma_long}", line=dict(color="royalblue", width=1.5)
            ), row=1, col=1)
            fig1.add_trace(go.Scatter(
                x=rsi.index, y=rsi[ticker_for_chart],
                name="RSI", line=dict(color="purple", width=1.5)
            ), row=2, col=1)
            fig1.add_hline(y=rsi_threshold, line_dash="dash",
                           line_color="red", row=2, col=1)
            fig1.update_layout(
                title=f"{ticker_for_chart} - 복합 전략",
                template="plotly_dark", height=500,
                hovermode="x unified"
            )
            st.plotly_chart(fig1, use_container_width=True)

        st.divider()

        # 수익률 비교 그래프
        st.subheader("💰 수익률 비교 그래프")
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=portfolio_equal.index,
            y=((portfolio_equal - 1) * 100),
            name="Equal Portfolio",
            line=dict(color="royalblue", width=2),
            hovertemplate="%{x}<br>수익률: %{y:.2f}%<extra></extra>"
        ))
        fig2.add_trace(go.Scatter(
            x=portfolio_strategy.index,
            y=((portfolio_strategy - 1) * 100),
            name=strategy,
            line=dict(color="orangered", width=2),
            hovertemplate="%{x}<br>수익률: %{y:.2f}%<extra></extra>"
        ))
        fig2.update_layout(
            title=f"포트폴리오 수익률 비교 - {strategy}",
            xaxis_title="날짜",
            yaxis_title="수익률 (%)",
            hovermode="x unified",
            template="plotly_dark",
            height=500
        )
        fig2.add_hline(y=0, line_dash="dash", line_color="gray")
        st.plotly_chart(fig2, use_container_width=True)