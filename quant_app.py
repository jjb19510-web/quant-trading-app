import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime as dt

st.set_page_config(page_title="Quantfolio — Backtest Lab", page_icon="📈", layout="wide")

ACCENT = "#3b82f6"
RED = "#ef4444"
GREEN = "#4ade80"
DIM = "#6b7385"
TEXT = "#e6e9ef"
SURFACE_1 = "#11151c"
SURFACE_2 = "#161b25"
SURFACE_3 = "#1d2330"
LINE = "#232a38"
BG = "#0b0e14"

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600&display=swap');
  .stApp {{ background: {BG}; color: {TEXT}; font-family: 'Inter', sans-serif; }}
  section[data-testid="stSidebar"] {{ background: {SURFACE_1}; border-right: 1px solid {LINE}; }}
  section[data-testid="stSidebar"] * {{ color: {TEXT}; }}
  h1, h2, h3, h4 {{ letter-spacing: -0.02em; }}
  .block-container {{ padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1400px; }}
  .qf-eyebrow {{ font-size: 11px; color: {DIM}; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 4px; }}
  .qf-title {{ font-size: 26px; font-weight: 600; margin: 0 0 4px 0; }}
  .qf-meta {{ font-size: 12px; color: {DIM}; font-family: 'JetBrains Mono', monospace; }}
  .qf-kpi-grid {{
    display: grid; grid-template-columns: 1.4fr repeat(5, 1fr);
    gap: 1px; background: {LINE}; border: 1px solid {LINE};
    border-radius: 8px; overflow: hidden; margin: 12px 0 18px;
  }}
  .qf-kpi {{ background: {SURFACE_1}; padding: 12px 14px; }}
  .qf-kpi.big {{ background: {SURFACE_2}; }}
  .qf-kpi-label {{ font-size: 10.5px; color: {DIM}; text-transform: uppercase; letter-spacing: 0.06em; font-weight: 500; }}
  .qf-kpi-klabel {{ font-size: 10px; color: #4d5567; margin-top: 1px; display: block; }}
  .qf-kpi-value {{ font-family: 'JetBrains Mono', monospace; font-size: 18px; font-weight: 600; letter-spacing: -0.02em; margin-top: 4px; }}
  .qf-kpi.big .qf-kpi-value {{ font-size: 26px; color: {GREEN}; }}
  .qf-kpi-delta {{ font-family: 'JetBrains Mono', monospace; font-size: 10.5px; color: {DIM}; margin-top: 2px; }}
  .qf-kpi-delta.pos {{ color: {GREEN}; }}
  .qf-kpi-delta.neg {{ color: {RED}; }}
  .qf-card {{ background: {SURFACE_1}; border: 1px solid {LINE}; border-radius: 8px; padding: 16px 18px; margin-bottom: 16px; }}
  .qf-card h3 {{ margin: 0 0 2px; font-size: 13px; font-weight: 600; }}
  .qf-card .qf-sub {{ font-size: 11px; color: {DIM}; margin-bottom: 10px; }}
  .pos {{ color: {GREEN}; }}
  .neg {{ color: {RED}; }}
  div[data-testid="stDataFrame"] {{ background: {SURFACE_1}; border-radius: 8px; }}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("<div style='font-size:18px; font-weight:600; margin-bottom:16px;'>⚙️ Settings</div>", unsafe_allow_html=True)

    market = st.selectbox("시장 선택 (Market)", ["한국주식 (KS)", "미국주식 (US)"])

    if market == "한국주식 (KS)":
        st.caption("예시: 005930, 000660, 373220")
        tickers_raw = st.text_input("종목 코드 입력 (쉼표로 구분)", "")
        tickers = [t.strip() + ".KS" for t in tickers_raw.split(",") if t.strip()]
    else:
        st.caption("예시: AAPL, TSLA, NVDA")
        tickers_raw = st.text_input("티커 입력 (쉼표로 구분)", "")
        tickers = [t.strip() for t in tickers_raw.split(",") if t.strip()]

    start_date = st.date_input("Start date", value=pd.to_datetime("2023-01-01"))
    end_date = st.date_input("End date", value=pd.to_datetime("2025-01-01"))

    strategy = st.selectbox("전략 선택 (Strategy)", [
        "RSI 전략 (RSI)",
        "이동평균선 전략 (Moving Average)",
        "볼린저 밴드 전략 (Bollinger Bands)",
        "복합 전략 (Combined)"
    ])

    if strategy == "RSI 전략 (RSI)":
        rsi_threshold = st.slider("RSI 기준값", 10, 70, 40)
        ma_short, ma_long, bb_period = 20, 60, 20
    elif strategy == "이동평균선 전략 (Moving Average)":
        ma_short = st.slider("단기 MA", 5, 60, 20)
        ma_long = st.slider("장기 MA", 20, 120, 60)
        rsi_threshold, bb_period = 40, 20
    elif strategy == "볼린저 밴드 전략 (Bollinger Bands)":
        bb_period = st.slider("BB 기간", 5, 60, 20)
        rsi_threshold, ma_short, ma_long = 40, 20, 60
    else:
        rsi_threshold = st.slider("RSI 기준값", 10, 70, 40)
        ma_short = st.slider("단기 MA", 5, 60, 20)
        ma_long = st.slider("장기 MA", 20, 120, 60)
        bb_period = 20

    analyze = st.button("🔍 분석 시작", use_container_width=True)

with st.expander("📖 전략 & 용어 설명 보기", expanded=False):
    if strategy == "RSI 전략 (RSI)":
        st.info("""
        **RSI 전략 (Relative Strength Index, 상대강도지수)**
        - RSI가 낮을수록 → 너무 많이 떨어진 상태 → **매수 신호**
        - RSI Threshold(기준값) 이하일 때 매수
        """)
    elif strategy == "이동평균선 전략 (Moving Average)":
        st.info("""
        **이동평균선 전략 (Moving Average, MA)**
        - 단기 MA > 장기 MA → **매수 신호** 📈 (골든크로스)
        - 단기 MA < 장기 MA → **매도 신호** 📉 (데드크로스)
        """)
    elif strategy == "볼린저 밴드 전략 (Bollinger Bands)":
        st.info("""
        **볼린저 밴드 전략 (Bollinger Bands)**
        - 주가가 하단 밴드 아래로 떨어지면 → **매수 신호** 📈
        - 주가가 상단 밴드 위로 올라가면 → **매도 신호** 📉
        """)
    else:
        st.info("""
        **복합 전략 (Combined Strategy)**
        - RSI가 기준값 이하 **AND** 단기 MA > 장기 MA → **매수 신호**
        """)
    st.info("""
    **균등 포트폴리오 (Equal Portfolio)**
    - 전략 없이 모든 종목에 똑같은 비율로 투자하는 기준선이에요.
    - 전략 수익률 > 균등 → **전략이 효과 있음** ✅
    """)

if analyze:
    if not tickers:
        st.warning("종목을 입력해주세요!")
    else:
        with st.spinner("데이터 불러오는 중..."):
            df = yf.download(tickers, start=start_date, end=end_date)["Close"]

        if isinstance(df, pd.Series):
            df = df.to_frame()

        df.columns = [str(c) for c in df.columns]
        chart_col = df.columns[0]

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
            return ma + (std * 2), ma - (std * 2), ma

        def calculate_mdd(portfolio):
            peak = portfolio.cummax()
            return ((portfolio - peak) / peak).min() * 100

        def calculate_sharpe(returns):
            return (returns.mean() / returns.std()) * (252 ** 0.5)

        def calculate_cagr(portfolio, days):
            return ((portfolio.iloc[-1] / portfolio.iloc[0]) ** (365 / days) - 1) * 100

        def style_fig(fig, height=400):
            fig.update_layout(
                height=height,
                margin=dict(l=8, r=20, t=8, b=28),
                paper_bgcolor=SURFACE_1,
                plot_bgcolor=SURFACE_1,
                font=dict(family="Inter, sans-serif", color=TEXT, size=11),
                showlegend=True,
                hovermode="x unified",
                legend=dict(bgcolor=SURFACE_2, bordercolor=LINE, font=dict(size=10)),
                xaxis=dict(
                    rangeslider=dict(visible=False),
                    rangeselector=dict(
                        buttons=[
                            dict(count=1, label="1M", step="month", stepmode="backward"),
                            dict(count=3, label="3M", step="month", stepmode="backward"),
                            dict(count=6, label="6M", step="month", stepmode="backward"),
                            dict(count=1, label="1Y", step="year", stepmode="backward"),
                            dict(step="all", label="ALL")
                        ],
                        bgcolor=SURFACE_2,
                        activecolor=ACCENT,
                        font=dict(color=TEXT, size=10)
                    )
                )
            )
            fig.update_xaxes(gridcolor="#1c222e", linecolor=LINE, zeroline=False, tickfont=dict(color=DIM))
            fig.update_yaxes(gridcolor="#1c222e", linecolor=LINE, zeroline=False, tickfont=dict(color=DIM))
            return fig

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

        # 매수/매도 시점 계산
        sig = signal.iloc[:, 0]
        buy_idx = sig[(sig == 1) & (sig.shift(1) == 0)].index
        sell_idx = sig[(sig == 0) & (sig.shift(1) == 1)].index

        signal_count = signal.sum(axis=1).replace(0, 1)
        returns = df.pct_change()
        weighted_return = (returns * signal.shift(1)).sum(axis=1) / signal_count.shift(1)
        equal_return = returns.mean(axis=1)

        portfolio_strategy = (1 + weighted_return).cumprod()
        portfolio_equal = (1 + equal_return).cumprod()

        days = max((df.index[-1] - df.index[0]).days, 1)

        equal_pct = (portfolio_equal.iloc[-1] - 1) * 100
        strategy_pct = (portfolio_strategy.iloc[-1] - 1) * 100
        mdd_s = calculate_mdd(portfolio_strategy)
        mdd_e = calculate_mdd(portfolio_equal)
        sharpe_s = calculate_sharpe(weighted_return.dropna())
        sharpe_e = calculate_sharpe(equal_return.dropna())
        cagr_s = calculate_cagr(portfolio_strategy, days)
        cagr_e = calculate_cagr(portfolio_equal, days)

        left, right = st.columns([3, 2])
        with left:
            st.markdown(
                f"<div class='qf-eyebrow'>{strategy} · {len(tickers)} tickers</div>"
                f"<h1 class='qf-title'>📈 퀀트 트레이딩 분석기</h1>",
                unsafe_allow_html=True
            )
        with right:
            st.markdown(
                f"<div class='qf-meta' style='text-align:right; padding-top:18px;'>"
                f"🟢 Run · {dt.datetime.now():%Y-%m-%d %H:%M}</div>",
                unsafe_allow_html=True
            )

        def kpi_html(label, klabel, value, delta=None, big=False, positive=True):
            cls = "qf-kpi big" if big else "qf-kpi"
            delta_html = ""
            if delta:
                d_cls = "pos" if positive else "neg"
                delta_html = f"<div class='qf-kpi-delta {d_cls}'>{delta}</div>"
            return (
                f"<div class='{cls}'>"
                f"<div class='qf-kpi-label'>{label}<span class='qf-kpi-klabel'>{klabel}</span></div>"
                f"<div class='qf-kpi-value'>{value}</div>{delta_html}</div>"
            )

        kpis = (
            kpi_html("Total Return", "총 수익률",
                     f"{strategy_pct:+.2f}%",
                     f"vs {equal_pct:+.2f}% equal",
                     big=True, positive=strategy_pct >= equal_pct)
            + kpi_html("CAGR", "연복리수익률", f"{cagr_s:.1f}%",
                       f"{cagr_s - cagr_e:+.1f}pp",
                       positive=cagr_s >= cagr_e)
            + kpi_html("Sharpe", "샤프지수", f"{sharpe_s:.2f}",
                       f"{sharpe_s - sharpe_e:+.2f}",
                       positive=sharpe_s >= sharpe_e)
            + kpi_html("Max DD", "최대낙폭", f"{mdd_s:.1f}%",
                       f"vs {mdd_e:.1f}%",
                       positive=mdd_s >= mdd_e)
            + kpi_html("Equal Return", "균등수익률", f"{equal_pct:+.2f}%")
            + kpi_html("Equal Sharpe", "균등샤프", f"{sharpe_e:.2f}")
        )
        st.markdown(f"<div class='qf-kpi-grid'>{kpis}</div>", unsafe_allow_html=True)

        st.markdown(f"<div class='qf-card'><h3>📈 전략 지표 그래프</h3><div class='qf-sub'>{chart_col} 기준 · ▲매수 ▼매도 시점 표시</div></div>", unsafe_allow_html=True)

        if strategy == "이동평균선 전략 (Moving Average)":
            fig1 = go.Figure()
            fig1.add_trace(go.Scatter(x=df.index, y=df[chart_col], name="주가", line=dict(color=TEXT, width=1)))
            fig1.add_trace(go.Scatter(x=ma_s.index, y=ma_s[chart_col], name=f"MA{ma_short}", line=dict(color="orange", width=1.5)))
            fig1.add_trace(go.Scatter(x=ma_l.index, y=ma_l[chart_col], name=f"MA{ma_long}", line=dict(color=ACCENT, width=1.5)))
            fig1.add_trace(go.Scatter(x=buy_idx, y=df.loc[buy_idx, chart_col], mode="markers", name="매수▲", marker=dict(symbol="triangle-up", size=10, color=GREEN)))
            fig1.add_trace(go.Scatter(x=sell_idx, y=df.loc[sell_idx, chart_col], mode="markers", name="매도▼", marker=dict(symbol="triangle-down", size=10, color=RED)))
            st.plotly_chart(style_fig(fig1, 400), use_container_width=True)

        elif strategy == "RSI 전략 (RSI)":
            fig1 = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
            fig1.add_trace(go.Scatter(x=df.index, y=df[chart_col], name="주가", line=dict(color=TEXT, width=1)), row=1, col=1)
            fig1.add_trace(go.Scatter(x=buy_idx, y=df.loc[buy_idx, chart_col], mode="markers", name="매수▲", marker=dict(symbol="triangle-up", size=10, color=GREEN)), row=1, col=1)
            fig1.add_trace(go.Scatter(x=sell_idx, y=df.loc[sell_idx, chart_col], mode="markers", name="매도▼", marker=dict(symbol="triangle-down", size=10, color=RED)), row=1, col=1)
            fig1.add_trace(go.Scatter(x=rsi.index, y=rsi[chart_col], name="RSI", line=dict(color=ACCENT, width=1.5)), row=2, col=1)
            fig1.add_hline(y=rsi_threshold, line_dash="dash", line_color=RED, row=2, col=1)
            st.plotly_chart(style_fig(fig1, 500), use_container_width=True)

        elif strategy == "볼린저 밴드 전략 (Bollinger Bands)":
            fig1 = go.Figure()
            fig1.add_trace(go.Scatter(x=df.index, y=df[chart_col], name="주가", line=dict(color=TEXT, width=1)))
            fig1.add_trace(go.Scatter(x=bb_upper.index, y=bb_upper[chart_col], name="상단밴드", line=dict(color=RED, width=1, dash="dash")))
            fig1.add_trace(go.Scatter(x=bb_mid.index, y=bb_mid[chart_col], name="중간선", line=dict(color="yellow", width=1)))
            fig1.add_trace(go.Scatter(x=bb_lower.index, y=bb_lower[chart_col], name="하단밴드", line=dict(color=GREEN, width=1, dash="dash"), fill="tonexty", fillcolor="rgba(74,222,128,0.05)"))
            fig1.add_trace(go.Scatter(x=buy_idx, y=df.loc[buy_idx, chart_col], mode="markers", name="매수▲", marker=dict(symbol="triangle-up", size=10, color=GREEN)))
            fig1.add_trace(go.Scatter(x=sell_idx, y=df.loc[sell_idx, chart_col], mode="markers", name="매도▼", marker=dict(symbol="triangle-down", size=10, color=RED)))
            st.plotly_chart(style_fig(fig1, 400), use_container_width=True)

        elif strategy == "복합 전략 (Combined)":
            fig1 = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
            fig1.add_trace(go.Scatter(x=df.index, y=df[chart_col], name="주가", line=dict(color=TEXT, width=1)), row=1, col=1)
            fig1.add_trace(go.Scatter(x=ma_s.index, y=ma_s[chart_col], name=f"MA{ma_short}", line=dict(color="orange", width=1.5)), row=1, col=1)
            fig1.add_trace(go.Scatter(x=ma_l.index, y=ma_l[chart_col], name=f"MA{ma_long}", line=dict(color=ACCENT, width=1.5)), row=1, col=1)
            fig1.add_trace(go.Scatter(x=buy_idx, y=df.loc[buy_idx, chart_col], mode="markers", name="매수▲", marker=dict(symbol="triangle-up", size=10, color=GREEN)), row=1, col=1)
            fig1.add_trace(go.Scatter(x=sell_idx, y=df.loc[sell_idx, chart_col], mode="markers", name="매도▼", marker=dict(symbol="triangle-down", size=10, color=RED)), row=1, col=1)
            fig1.add_trace(go.Scatter(x=rsi.index, y=rsi[chart_col], name="RSI", line=dict(color=ACCENT, width=1.5)), row=2, col=1)
            fig1.add_hline(y=rsi_threshold, line_dash="dash", line_color=RED, row=2, col=1)
            st.plotly_chart(style_fig(fig1, 500), use_container_width=True)

        st.markdown(f"<div class='qf-card'><h3>💰 수익률 비교</h3><div class='qf-sub'>누적 수익률 (%) · 드래그로 확대 가능</div></div>", unsafe_allow_html=True)
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=portfolio_equal.index,
            y=((portfolio_equal - 1) * 100),
            name="균등 포트폴리오",
            line=dict(color=RED, width=2),
            hovertemplate="%{x}<br>수익률: %{y:.2f}%<extra></extra>"
        ))
        fig2.add_trace(go.Scatter(
            x=portfolio_strategy.index,
            y=((portfolio_strategy - 1) * 100),
            name="전략 포트폴리오",
            line=dict(color=ACCENT, width=2),
            hovertemplate="%{x}<br>수익률: %{y:.2f}%<extra></extra>"
        ))
        fig2.add_hline(y=0, line=dict(color=DIM, width=1, dash="dot"), opacity=0.4)
        st.plotly_chart(style_fig(fig2, 400), use_container_width=True)

        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown(f"<div class='qf-card'><h3>📉 낙폭 (Drawdown)</h3><div class='qf-sub'>고점 대비 하락폭 · 전략 기준</div></div>", unsafe_allow_html=True)
            peak = portfolio_strategy.cummax()
            drawdown = (portfolio_strategy - peak) / peak * 100
            fig_dd = go.Figure()
            fig_dd.add_trace(go.Scatter(
                x=drawdown.index, y=drawdown.values,
                fill="tozeroy", line=dict(color=RED, width=1.5),
                fillcolor="rgba(239,68,68,0.18)", name="Drawdown",
                hovertemplate="%{x}<br>낙폭: %{y:.2f}%<extra></extra>"
            ))
            fig_dd.update_layout(
                height=300,
                margin=dict(l=8, r=20, t=8, b=28),
                paper_bgcolor=SURFACE_1,
                plot_bgcolor=SURFACE_1,
                font=dict(family="Inter, sans-serif", color=TEXT, size=11),
                showlegend=False,
                hovermode="x unified"
            )
            fig_dd.update_xaxes(gridcolor="#1c222e", linecolor=LINE, zeroline=False, tickfont=dict(color=DIM))
            fig_dd.update_yaxes(gridcolor="#1c222e", linecolor=LINE, zeroline=False, tickfont=dict(color=DIM))
            st.plotly_chart(fig_dd, use_container_width=True)

        with col2:
            st.markdown(f"<div class='qf-card'><h3>📅 월별 수익률 히트맵</h3><div class='qf-sub'>전략 월별 수익률 (%) · 초록=수익 빨강=손실</div></div>", unsafe_allow_html=True)
            monthly = weighted_return.resample("ME").apply(lambda x: (1 + x).prod() - 1) * 100
            monthly_df = monthly.to_frame("return")
            monthly_df["year"] = monthly_df.index.year
            monthly_df["month"] = monthly_df.index.month
            pivot = monthly_df.pivot(index="year", columns="month", values="return")

            fig_h = go.Figure(go.Heatmap(
                z=pivot.values,
                x=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],
                y=pivot.index.astype(str),
                colorscale=[[0, RED], [0.5, SURFACE_3], [1, GREEN]],
                zmid=0,
                text=[[f"{v:+.1f}" if not pd.isna(v) else "" for v in row] for row in pivot.values],
                texttemplate="%{text}",
                textfont=dict(family="JetBrains Mono", size=10, color=TEXT),
                colorbar=dict(thickness=8, len=0.8, tickfont=dict(color=DIM, size=9))
            ))
            fig_h.update_layout(
                height=300,
                margin=dict(l=8, r=40, t=8, b=28),
                paper_bgcolor=SURFACE_1,
                plot_bgcolor=SURFACE_1,
                font=dict(family="Inter, sans-serif", color=TEXT, size=11),
            )
            fig_h.update_xaxes(tickfont=dict(color=DIM))
            fig_h.update_yaxes(tickfont=dict(color=DIM))
            st.plotly_chart(fig_h, use_container_width=True)

        st.caption(f"Data: yfinance · {df.index[0].date()} → {df.index[-1].date()} · {len(df)} trading days")