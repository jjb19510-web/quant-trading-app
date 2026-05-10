import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# ── 색상 테마 ──
ACCENT = "#3b82f6"
RED = "#ef4444"
GREEN = "#4ade80"
CANDLE_UP = "#ef4444"
CANDLE_DOWN = "#3b82f6"
DIM = "#6b7385"
TEXT = "#e6e9ef"
SURFACE_1 = "#0d0d0f"
SURFACE_2 = "#111318"
SURFACE_3 = "#1d2330"
LINE = "#1c2030"
BG = "#080a0f"


def apply_custom_css():
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
      .qf-kpi.big .qf-kpi-value {{ font-size: 26px; color: {CANDLE_UP}; }}
      .qf-kpi-delta {{ font-family: 'JetBrains Mono', monospace; font-size: 10.5px; color: {DIM}; margin-top: 2px; }}
      .qf-kpi-delta.pos {{ color: {CANDLE_UP}; }}
      .qf-kpi-delta.neg {{ color: {CANDLE_DOWN}; }}
      .qf-card {{ background: {SURFACE_1}; border: 1px solid {LINE}; border-radius: 8px; padding: 16px 18px; margin-bottom: 16px; }}
      .qf-card h3 {{ margin: 0 0 2px; font-size: 13px; font-weight: 600; }}
      .qf-card .qf-sub {{ font-size: 11px; color: {DIM}; margin-bottom: 10px; }}
      .pos {{ color: {CANDLE_UP}; }}
      .neg {{ color: {CANDLE_DOWN}; }}
      div[data-testid="stDataFrame"] {{ background: {SURFACE_1}; border-radius: 8px; }}
    </style>
    """, unsafe_allow_html=True)


def card(title, sub=""):
    st.markdown(f"<div class='qf-card'><h3>{title}</h3><div class='qf-sub'>{sub}</div></div>", unsafe_allow_html=True)


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


def render_kpi_strip(strategy_pct, equal_pct, cagr_s, cagr_e, sharpe_s, sharpe_e, mdd_s, mdd_e):
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


def render_strategy_expander(strategy):
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


def color_val(val):
    try:
        v = float(val)
        if v > 0: return f"color: {CANDLE_UP};"
        if v < 0: return f"color: {CANDLE_DOWN};"
    except:
        return ""
    return ""


def style_fig(fig, height=400):
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=60, t=8, b=28),
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        font=dict(family="Inter, sans-serif", color=TEXT, size=11),
        showlegend=True,
        hovermode="x unified",
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(0,0,0,0)",
            font=dict(size=10),
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0
        ),
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
                bgcolor=SURFACE_1,
                activecolor=ACCENT,
                font=dict(color=TEXT, size=10),
                bordercolor=LINE
            ),
            showgrid=True,
            gridcolor="rgba(255,255,255,0.03)",
            linecolor=LINE,
            zeroline=False,
            tickfont=dict(color=DIM, size=10),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.03)",
            linecolor=LINE,
            zeroline=False,
            tickfont=dict(color=DIM, size=10),
            side="right",
        )
    )
    return fig