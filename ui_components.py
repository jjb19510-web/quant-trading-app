import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from design import theme, components

# ── 색상 테마 ──
ACCENT = "#3b82f6"
RED = "#ef4444"
GREEN = "#34d399"
CANDLE_UP = "#ef4444"
CANDLE_DOWN = "#3b82f6"
DIM = "#9ca3af"
TEXT = "#e2e8f0"
SURFACE_1 = "#0f1117"
SURFACE_2 = "#13161f"
SURFACE_3 = "#1a1f2e"
LINE = "#1e2330"
BG = "#080a0f"


def apply_custom_css():
    st.markdown(theme.get_global_css(), unsafe_allow_html=True)
    st.markdown(components.get_component_css(), unsafe_allow_html=True)
    st.markdown(f"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600&display=swap');

      .stApp {{ background: {BG}; color: {TEXT}; font-family: 'Inter', sans-serif; }}
      section[data-testid="stSidebar"] {{ background: {SURFACE_1}; border-right: 1px solid {LINE}; }}
      section[data-testid="stSidebar"] * {{ color: {TEXT}; }}
      h1, h2, h3, h4 {{ letter-spacing: -0.02em; }}
      .block-container {{ padding-top: 5rem; padding-bottom: 3rem; max-width: 1400px; }}

      /* ── 상단 요약 카드 ── */
      .qf-summary-grid {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 10px;
        margin-bottom: 24px;
      }}
      .qf-summary-card {{
        background: {SURFACE_1};
        border: 0.5px solid {LINE};
        border-radius: 12px;
        padding: 16px 20px; /* 내부 여백 통일 */
        box-shadow: 0 4px 24px rgba(0,0,0,0.4);
      }}
      .qf-summary-card.highlight {{
        border-color: rgba(239,68,68,0.3);
        background: linear-gradient(135deg, {SURFACE_1} 60%, rgba(239,68,68,0.04));
      }}
      .qf-eyebrow {{
        font-size: 11px;
        color: {DIM};
        text-transform: uppercase;
        letter-spacing: 0.07em;
        margin-bottom: 6px;
        font-weight: 500;
      }}
      .qf-title {{
        font-size: 24px;
        font-weight: 600;
        margin: 0 0 4px 0;
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: -0.02em;
      }}
      .qf-badge {{
        display: inline-block;
        font-size: 11px;
        font-family: 'JetBrains Mono', monospace;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 20px;
        margin-top: 4px;
      }}
      .qf-badge.pos {{ background: rgba(239,68,68,0.12); color: {CANDLE_UP}; }}
      .qf-badge.neg {{ background: rgba(59,130,246,0.12); color: {CANDLE_DOWN}; }}
      .qf-badge.dim {{ background: rgba(107,114,128,0.12); color: {DIM}; }}

      /* ── KPI 스트립 ── */
      .qf-kpi-grid {{
        display: grid;
        grid-template-columns: 1.4fr repeat(5, 1fr);
        gap: 0;
        background: {LINE};
        border: 0.5px solid {LINE};
        border-radius: 10px;
        overflow: hidden;
        margin: 0 0 16px;
      }}
      .qf-kpi {{
        background: {SURFACE_1};
        padding: 12px 14px;
        border-right: 0.5px solid {LINE};
      }}
      .qf-kpi:last-child {{ border-right: none; }}
      .qf-kpi.big {{ background: {SURFACE_2}; }}
      .qf-kpi-label {{
        font-size: 10px;
        color: {DIM};
        text-transform: uppercase;
        letter-spacing: 0.07em;
        font-weight: 500;
      }}
      .qf-kpi-klabel {{
        font-size: 10px;
        color: #3d4459;
        margin-top: 1px;
        display: block;
      }}
      .qf-kpi-value {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 17px;
        font-weight: 600;
        letter-spacing: -0.02em;
        margin-top: 5px;
      }}
      .qf-kpi.big .qf-kpi-value {{
        font-size: 24px;
        color: {CANDLE_UP};
      }}
      .qf-kpi-delta {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 10.5px;
        color: {DIM};
        margin-top: 3px;
      }}
      .qf-kpi-delta.pos {{ color: {CANDLE_UP}; }}
      .qf-kpi-delta.neg {{ color: {CANDLE_DOWN}; }}

      /* ── 섹션 카드 ── */
      .qf-card {{
        background: {SURFACE_1};
        border: 0.5px solid {LINE};
        border-radius: 12px;
        padding: 16px 20px; /* 내부 여백 통일 */
        margin-bottom: 28px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.4);
      }}
      .qf-card h3 {{
        margin: 0 0 2px;
        font-size: 13px;
        font-weight: 600;
        color: {TEXT};
      }}
      .qf-card .qf-sub {{
        font-size: 11px;
        color: {DIM};
        margin-bottom: 10px;
      }}

      /* ── 주문 버튼 ── */
      div[data-testid="column"] button[kind="primary"] {{
        background: rgba(52,211,153,0.1) !important;
        border: 0.5px solid rgba(52,211,153,0.3) !important;
        color: {GREEN} !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
      }}
      div[data-testid="column"] button[kind="secondary"] {{
        background: rgba(239,68,68,0.1) !important;
        border: 0.5px solid rgba(239,68,68,0.3) !important;
        color: {RED} !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
      }}

      /* ── 경고 배지 ── */
      .qf-warn {{
        font-size: 11px;
        color: #f59e0b;
        background: rgba(245,158,11,0.08);
        border: 0.5px solid rgba(245,158,11,0.2);
        border-radius: 6px;
        padding: 5px 10px;
        margin-bottom: 10px;
        display: inline-block;
      }}

      .pos {{ color: {CANDLE_UP}; }}
      .neg {{ color: {CANDLE_DOWN}; }}
      div[data-testid="stDataFrame"] {{ background: {SURFACE_1}; border-radius: 8px; }}
      div[data-testid="stTextInput"] input {{ border: 1px solid {LINE} !important; background: {SURFACE_2} !important; }}
      div[data-testid="stTabs"] button {{ font-size: 11px !important; padding: 6px 8px !important; }}

      /* ── 토스형 뉴스 카드 커스텀 컴포넌트 (물리적 분리 및 인터랙션 주입) ── */
      .qf-news-card {{
        background: {SURFACE_2} !important; /* SURFACE_1 배경 위에서 완전히 분리되도록 어두운 톤 적용 */
        border: 1.2px solid {LINE} !important; /* 테두리를 조금 더 뚜렷하게 조정 */
        border-radius: 10px !important;
        padding: 14px 18px !important;
        margin-bottom: 12px !important; /* 간격을 넓혀 독립된 개별 카드로 분리 */
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important; /* 부드러운 유기적 물리 효과 */
        display: block !important;
        text-decoration: none !important;
      }}
      .qf-news-card:hover {{
        transform: translateY(-3px) !important; /* 마우스 오버 시 위로 공중 부양 */
        border-color: {ACCENT} !important; /* 테두리 발광 피드백 */
        background: {SURFACE_3} !important; /* 배경색을 한 단계 밝혀 초점 집중 */
        box-shadow: 0 6px 16px rgba(59, 130, 246, 0.12) !important; /* 은은한 푸른 광원 그림자 효과 */
      }}div[data-testid="stDataFrame"] {{ background: {SURFACE_1}; border-radius: 8px; }}
      div[data-testid="stTextInput"] input {{ border: 1px solid {LINE} !important; background: {SURFACE_2} !important; }}
      div[data-testid="stTabs"] button {{ font-size: 11px !important; padding: 6px 8px !important; }}

      /* ── 토스형 뉴스 카드 커스텀 컴포넌트 (물리적 분리 및 인터랙션 주입) ── */
      .qf-news-card {{
        background: {SURFACE_2} !important; /* SURFACE_1 배경 위에서 완전히 분리되도록 어두운 톤 적용 */
        border: 1.2px solid {LINE} !important; /* 테두리를 조금 더 뚜렷하게 조정 */
        border-radius: 10px !important;
        padding: 14px 18px !important;
        margin-bottom: 12px !important; /* 간격을 넓혀 독립된 개별 카드로 분리 */
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important; /* 부드러운 유기적 물리 효과 */
        display: block !important;
        text-decoration: none !important;
      }}
      .qf-news-card:hover {{
        transform: translateY(-3px) !important; /* 마우스 오버 시 위로 공중 부양 */
        border-color: {ACCENT} !important; /* 테두리 발광 피드백 */
        background: {SURFACE_3} !important; /* 배경색을 한 단계 밝혀 초점 집중 */
        box-shadow: 0 6px 16px rgba(59, 130, 246, 0.12) !important; /* 은은한 푸른 광원 그림자 효과 */
      }}

      /* ── 모바일 반응형 미디어 쿼리 추가 (f-string 더블 중괄호 처리) ── */
      @media (max-width: 768px) {{
        .qf-summary-grid, .qf-kpi-grid, .qf-toss-grid {{
          grid-template-columns: 1fr !important; /* 모바일에서 찌그러지지 않고 세로로 정렬 */
          gap: 12px;
        }}
        .qf-kpi {{
          border-right: none !important;
          border-bottom: 0.5px solid {LINE};
        }}
      }}
    /* ── 토스형 뉴스 카드 커스텀 컴포넌트 ── */
      .qf-news-card {{
        background: {SURFACE_2} !important; /* SURFACE_1 배경 위에서 완전히 분리되도록 어두운 톤 적용 */
        border: 1.2px solid {LINE} !important; /* 테두리를 조금 더 뚜렷하게 조정 */
        border-radius: 10px !important;
        padding: 14px 18px !important;
        margin-bottom: 12px !important; /* 간격을 넓혀 독립된 개별 카드로 분리 */
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important; /* 부드러운 유기적 물리 효과 */
        display: block !important;
        text-decoration: none !important;
      }}
      .qf-news-card:hover {{
        transform: translateY(-3px) !important; /* 마우스 오버 시 위로 공중 부양 */
        border-color: {ACCENT} !important; /* 테두리 발광 피드백 */
        background: {SURFACE_3} !important; /* 배경색을 한 단계 밝혀 초점 집중 */
        box-shadow: 0 6px 16px rgba(59, 130, 246, 0.12) !important; /* 은은한 푸른 광원 그림자 효과 */
      }}
    </style>
    """, unsafe_allow_html=True)


def render_summary_cards(invested, profit, profit_pct, final_val, excess):
    """상단 4개 요약 카드"""
    profit_badge_cls = "pos" if profit >= 0 else "neg"
    profit_sign = "▲" if profit >= 0 else "▼"
    excess_color = CANDLE_UP if excess >= 0 else DIM

    st.markdown(f"""
    <div class="qf-summary-grid">
      <div class="qf-summary-card">
        <div class="qf-eyebrow">투입금액</div>
        <div class="qf-title" style="color:{TEXT};">{invested:,.0f}만원</div>
      </div>
      <div class="qf-summary-card highlight">
        <div class="qf-eyebrow">전략 수익금</div>
        <div class="qf-title" style="color:{CANDLE_UP if profit >= 0 else CANDLE_DOWN};">
          {'+' if profit >= 0 else ''}{profit:,.0f}만원
        </div>
        <span class="qf-badge {profit_badge_cls}">{profit_sign} {profit_pct:+.2f}%</span>
      </div>
      <div class="qf-summary-card">
        <div class="qf-eyebrow">전략 최종금액</div>
        <div class="qf-title" style="color:{TEXT};">{final_val:,.0f}만원</div>
      </div>
      <div class="qf-summary-card">
        <div class="qf-eyebrow">균등 대비 초과수익</div>
        <div class="qf-title" style="color:{excess_color};">
          {'+' if excess >= 0 else ''}{excess:,.0f}만원
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)


_EMOJI_TO_ICON = {
    "🤖": "ai",
    "📊": "market",
    "💼": "portfolio",
    "🔍": "search",
    "📋": "report",
    "🔬": "analysis",
    "⚙️": "settings",
    "⚠️": "warning",
    "📈": "trade",
}


def card(title, sub=""):
    display_title = title
    for emoji, icon_key in _EMOJI_TO_ICON.items():
        if title.startswith(emoji):
            display_title = components.qf_icon(icon_key) + title[len(emoji):]
            break
    st.markdown(
        f"<div class='qf-card'><h3>{display_title}</h3><div class='qf-sub'>{sub}</div></div>",
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
        f"<div class='qf-kpi-label'>{label}"
        f"<span class='qf-kpi-klabel'>{klabel}</span></div>"
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
        font=dict(family="Inter, sans-serif", color=TEXT, size=11.5), # 차트 기본 폰트 크기 미세 상향
        showlegend=True,
        hovermode="x unified",
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(0,0,0,0)",
            font=dict(size=11), # 범례 글꼴 크기 상향
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",  # 좌측 시간 선택 버튼과 겹치지 않도록 우측 정렬로 패치
            x=1
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
                font=dict(color=TEXT, size=11), # 기간 선택 버튼 글꼴 크기 상향
                bordercolor=LINE
            ),
            showgrid=True,
            gridcolor="rgba(255,255,255,0.03)",
            linecolor=LINE,
            zeroline=False,
            tickfont=dict(color="#9ca3af", size=11), # 축 눈금 가독성(대비/크기) 개선
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.03)",
            linecolor=LINE,
            zeroline=False,
            tickfont=dict(color="#9ca3af", size=11), # 축 눈금 가독성(대비/크기) 개선
            side="right",
        )
    )
    return fig