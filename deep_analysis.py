import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import datetime as dt
from data_utils import load_krx_listing, get_krx_name_map
from ui_components import card, ACCENT, CANDLE_UP, CANDLE_DOWN, DIM, TEXT, SURFACE_1, SURFACE_2, LINE, BG


@st.cache_data(ttl=600)
def load_ticker_data(ticker):
    hist = yf.download(ticker, period="1y", progress=False)
    return hist

@st.cache_data(ttl=600)
def load_ticker_info(ticker):
    import time
    t = yf.Ticker(ticker)
    try:
        info = t.info
    except:
        info = {}
    time.sleep(1)
    try:
        financials = t.financials
    except:
        financials = None
    return info, financials

@st.cache_data(ttl=600)
def load_competitor_info(ct):
    import time
    time.sleep(0.5)
    try:
        return yf.Ticker(ct).info
    except:
        return {}

def render_deep_analysis(KIS_AVAILABLE, get_kis_token):

    st.markdown(
        "<div style='font-size:22px; font-weight:700; margin-bottom:4px;'>🔬 종목 심층분석</div>"
        f"<div style='font-size:12px; color:{DIM}; margin-bottom:24px;'>재무 · 기술적 분석 · 수급 히스토리 · 경쟁사 비교 · AI 투자의견</div>",
        unsafe_allow_html=True
    )

    # ── 종목 입력 ──
    col_input, col_btn = st.columns([4, 1])
    with col_input:
        ticker_input = st.text_input("종목명 또는 코드 입력", placeholder="예: 삼성전자, 005930, AAPL", key="deep_ticker_input")
    with col_btn:
        st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
        analyze_btn = st.button("🔬 심층분석 시작", use_container_width=True)

    if not ticker_input or not analyze_btn:
        st.info("종목명 또는 코드를 입력하고 심층분석 시작 버튼을 눌러주세요.")
        return

    # ── 티커 변환 ──
    df_krx = load_krx_listing()
    name_map = get_krx_name_map()
    ticker = ticker_input.strip()
    is_korean = True

    if not ticker.endswith(".KS") and not ticker.endswith(".KQ") and not ticker.isupper():
        if df_krx is not None:
            code_col = next((c for c in ['Symbol', 'Code', 'code'] if c in df_krx.columns), None)
            if code_col:
                matched = df_krx[df_krx['Name'].str.upper() == ticker.upper()]
                if matched.empty:
                    matched = df_krx[df_krx['Name'].str.upper().str.contains(ticker.upper(), na=False)]
                if not matched.empty:
                    raw_code = str(matched.iloc[0][code_col]).split('.')[0].zfill(6)
                    mkt = str(matched.iloc[0].get('Market', 'KOSPI')).upper()
                    suffix = ".KS" if "KOSPI" in mkt else ".KQ"
                    ticker = raw_code + suffix
    elif ticker.isdigit():
        ticker = ticker.zfill(6) + ".KS"

    if ticker.endswith(".KS") or ticker.endswith(".KQ"):
        raw_ticker = ticker.replace(".KS", "").replace(".KQ", "")
        is_korean = True
    else:
        raw_ticker = ticker
        is_korean = False

    display_name = name_map.get(raw_ticker, ticker_input)

    with st.spinner(f"{display_name} 데이터 분석 중..."):
        hist = load_ticker_data(ticker)
        if hist.empty:
            st.error("주가 데이터를 불러오지 못했어요. 종목코드를 확인해주세요.")
            return

        close = hist["Close"].squeeze()
        high = hist["High"].squeeze()
        low = hist["Low"].squeeze()
        volume = hist["Volume"].squeeze()
        open_p = hist["Open"].squeeze()

    curr_price = float(close.iloc[-1])
    prev_price = float(close.iloc[-2])
    chg = curr_price - prev_price
    chg_pct = chg / prev_price * 100
    chg_color = CANDLE_UP if chg >= 0 else CANDLE_DOWN
    chg_arrow = "▲" if chg >= 0 else "▼"

    st.markdown(f"""
    <div style='background:{SURFACE_2}; border:0.5px solid {LINE}; border-radius:12px; padding:18px; margin-bottom:20px;'>
        <div style='font-size:13px; color:{DIM}; margin-bottom:4px;'>{raw_ticker}</div>
        <div style='font-size:22px; font-weight:700; margin-bottom:4px;'>{display_name}</div>
        <div style='font-family:JetBrains Mono; font-size:28px; font-weight:700;'>{curr_price:,.0f}원
            <span style='font-size:15px; color:{chg_color}; margin-left:8px;'>{chg_arrow} {chg:+,.0f}원 ({chg_pct:+.2f}%)</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ══════════════════════════════════════════
    # 1. 재무제표 분석
    # ══════════════════════════════════════════
    card("📊 재무제표 분석", "매출/영업이익 추이 (이중 축) · PER/PBR 밸류에이션")

    try:
        info, financials = load_ticker_info(ticker)

        if financials is not None and not financials.empty:
            rev_row = next((r for r in ["Total Revenue", "Revenue"] if r in financials.index), None)
            op_row = next((r for r in ["Operating Income", "EBIT"] if r in financials.index), None)

            if rev_row or op_row:
                fig_fin = go.Figure()
                cols_fin = financials.columns[:4]
                years = [str(c.year) for c in cols_fin][::-1]

                def auto_unit(max_eok):
                    if abs(max_eok) >= 10000:
                        return "조원", 10000
                    return "억원", 1

                rev_unit, rev_div = "억원", 1
                op_unit, op_div = "억원", 1

                if rev_row:
                    rev_eok = [round(float(financials.loc[rev_row, c]) / 1e8, 1) for c in cols_fin][::-1]
                    rev_unit, rev_div = auto_unit(max(abs(v) for v in rev_eok))
                    rev_vals = [round(v / rev_div, 2) for v in rev_eok]
                    rev_hover = [f"{v:,.2f}{rev_unit}" if rev_unit == "조원" else f"{v:,.0f}{rev_unit}" for v in rev_vals]
                    fig_fin.add_trace(go.Bar(
                        x=years, y=rev_vals,
                        name=f"매출액({rev_unit})",
                        marker_color=ACCENT, opacity=0.6,
                        yaxis="y1",
                        hovertemplate="<b>%{x}년 매출액</b><br>%{customdata}<extra></extra>",
                        customdata=rev_hover
                    ))

                if op_row:
                    op_eok = [round(float(financials.loc[op_row, c]) / 1e8, 1) for c in cols_fin][::-1]
                    op_unit, op_div = auto_unit(max(abs(v) for v in op_eok))
                    op_vals = [round(v / op_div, 2) for v in op_eok]
                    op_hover = [f"{v:,.2f}{op_unit}" if op_unit == "조원" else f"{v:,.0f}{op_unit}" for v in op_vals]
                    # 영업이익은 꺾은선 + 마커로 표시 (막대 겹침 방지)
                    fig_fin.add_trace(go.Scatter(
                        x=years, y=op_vals,
                        name=f"영업이익({op_unit})",
                        mode="lines+markers+text",
                        line=dict(color=CANDLE_UP, width=2.5),
                        marker=dict(size=8, color=CANDLE_UP),
                        text=op_hover,
                        textposition="top center",
                        textfont=dict(color=CANDLE_UP, size=11),
                        yaxis="y2",
                        hovertemplate="<b>%{x}년 영업이익</b><br>%{customdata}<extra></extra>",
                        customdata=op_hover
                    ))

                fig_fin.update_layout(
                    barmode="group", height=340,
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color=TEXT, size=11),
                    margin=dict(l=60, r=60, t=30, b=20),
                    legend=dict(orientation="h", y=1.12),
                    xaxis=dict(gridcolor="rgba(0,0,0,0)"),
                    yaxis=dict(
                        tickfont=dict(color=ACCENT),
                        gridcolor=LINE,
                        tickformat=",",
                        ticksuffix=rev_unit,
                        side="left",
                        showgrid=True
                    ),
                    yaxis2=dict(
                        tickfont=dict(color=CANDLE_UP),
                        gridcolor="rgba(0,0,0,0)",
                        tickformat=",",
                        ticksuffix=op_unit,
                        side="right",
                        overlaying="y",
                        showgrid=False
                    )
                )
                st.plotly_chart(fig_fin, use_container_width=True, config={"displayModeBar": False})

        # 밸류에이션
        per = info.get("trailingPE") or info.get("forwardPE")
        pbr = info.get("priceToBook")
        roe = info.get("returnOnEquity")
        eps = info.get("trailingEps")
        mkt_cap = info.get("marketCap")
        div_yield = info.get("dividendYield")

        if is_korean:
            try:
                nv_url = f"https://m.stock.naver.com/api/stock/{raw_ticker}/integration"
                nv_res = requests.get(nv_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
                nv_data = nv_res.json()
                total_infos = nv_data.get("totalInfos", [])

                def clean_val(val_str):
                    return val_str.replace("원","").replace("%","").replace("배","").replace("x","").replace(",","").strip()

                for info_item in total_infos:
                    k = str(info_item.get("key", "")).upper()
                    c = str(info_item.get("code", "")).lower()
                    v = str(info_item.get("value", "")).strip()
                    if not v or v == "-":
                        continue
                    val_clean = clean_val(v)
                    try:
                        if c == "per" or k == "PER":
                            if not per:
                                per = float(val_clean)
                        elif c == "pbr" or k == "PBR":
                            if not pbr:
                                pbr = float(val_clean)
                        elif c == "eps" or k == "EPS":
                            if not eps:
                                eps = float(val_clean)
                        elif c == "bps" or k == "BPS":
                            pass  # 사용 안함
                        elif c == "roe" or k == "ROE":
                            if not roe:
                                roe = float(val_clean) / 100
                        elif c == "dividendyield" or k == "배당수익률":
                            if not div_yield:
                                div_yield = float(val_clean) / 100
                        elif c == "marketvalue" or k == "시가총액":
                            if not mkt_cap:
                                # 순수 숫자(백만원 단위)로 오는 경우
                                try:
                                    mkt_cap = float(val_clean) * 1e6
                                except:
                                    pass
                    except:
                        pass

                # 시가총액이 여전히 없으면 현재가 * 상장주식수로 계산
                if not mkt_cap:
                    shares = info.get("sharesOutstanding") or info.get("impliedSharesOutstanding")
                    if shares:
                        mkt_cap = curr_price * shares

            except:
                pass

        v1, v2, v3, v4, v5, v6 = st.columns(6)
        for col, label, value in [
            (v1, "PER", f"{per:.1f}배" if per else "N/A"),
            (v2, "PBR", f"{pbr:.1f}배" if pbr else "N/A"),
            (v3, "ROE", f"{roe*100:.1f}%" if roe else "N/A"),
            (v4, "EPS", f"{int(eps):,}원" if eps else "N/A"),
            (v5, "시가총액", f"{mkt_cap/1e12:.1f}조" if mkt_cap else "N/A"),
            (v6, "배당수익률", f"{div_yield*100:.2f}%" if div_yield else "N/A"),
        ]:
            with col:
                st.markdown(f"""
                <div style='background:{SURFACE_2}; border:0.5px solid {LINE}; border-radius:10px; padding:12px; text-align:center; margin-bottom:8px;'>
                    <div style='font-size:10px; color:{DIM}; margin-bottom:4px;'>{label}</div>
                    <div style='font-size:14px; font-weight:700; font-family:JetBrains Mono;'>{value}</div>
                </div>
                """, unsafe_allow_html=True)

    except Exception as e:
        st.info(f"재무 데이터 조회 실패: {e}")

    st.markdown("---")

    # ══════════════════════════════════════════
    # 2. 기술적 분석
    # ══════════════════════════════════════════
    card("📈 기술적 분석", "추세 · 모멘텀 · 변동성 · 거래량 종합 진단")

    try:
        # 기본 지표
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi_val = float(rsi.iloc[-1])

        ma20 = close.rolling(20).mean()
        ma60 = close.rolling(60).mean()
        ma120 = close.rolling(120).mean()

        bb_mid = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        bb_upper = bb_mid + 2 * bb_std
        bb_lower = bb_mid - 2 * bb_std

        high_52 = float(high.max())
        low_52 = float(low.min())
        pos_52 = (curr_price - low_52) / (high_52 - low_52) * 100 if high_52 != low_52 else 50

        # 거래량 분석
        vol_ma20 = volume.rolling(20).mean()
        vol_ratio = float(volume.iloc[-1]) / float(vol_ma20.iloc[-1]) if float(vol_ma20.iloc[-1]) > 0 else 1

        # 추세 판단
        ma20_val = float(ma20.iloc[-1])
        ma60_val = float(ma60.iloc[-1])
        ma120_val = float(ma120.iloc[-1])

        if curr_price > ma20_val > ma60_val > ma120_val:
            trend = "강한 상승추세 📈"
            trend_color = CANDLE_UP
        elif curr_price > ma20_val and ma20_val > ma60_val:
            trend = "상승추세 🟢"
            trend_color = CANDLE_UP
        elif curr_price < ma20_val < ma60_val < ma120_val:
            trend = "강한 하락추세 📉"
            trend_color = CANDLE_DOWN
        elif curr_price < ma20_val and ma20_val < ma60_val:
            trend = "하락추세 🔴"
            trend_color = CANDLE_DOWN
        else:
            trend = "횡보/혼조 ⚖️"
            trend_color = "#f59e0b"

        # RSI 상태
        if rsi_val < 30:
            rsi_label = "과매도 — 반등 가능성"
            rsi_color = CANDLE_UP
        elif rsi_val > 70:
            rsi_label = "과매수 — 조정 주의"
            rsi_color = CANDLE_DOWN
        elif rsi_val > 55:
            rsi_label = "강세 구간"
            rsi_color = "#22c55e"
        elif rsi_val < 45:
            rsi_label = "약세 구간"
            rsi_color = "#ef4444"
        else:
            rsi_label = "중립"
            rsi_color = "#f59e0b"

        # 볼린저밴드 위치
        bb_upper_val = float(bb_upper.iloc[-1])
        bb_lower_val = float(bb_lower.iloc[-1])
        bb_pct = (curr_price - bb_lower_val) / (bb_upper_val - bb_lower_val) * 100 if bb_upper_val != bb_lower_val else 50

        if bb_pct > 85:
            bb_label = "상단 돌파 (과열 주의)"
            bb_color = CANDLE_DOWN
        elif bb_pct > 60:
            bb_label = "상단 근접 (강세)"
            bb_color = "#22c55e"
        elif bb_pct < 15:
            bb_label = "하단 이탈 (과매도)"
            bb_color = CANDLE_UP
        elif bb_pct < 40:
            bb_label = "하단 근접 (약세)"
            bb_color = "#ef4444"
        else:
            bb_label = "중간 구간 (중립)"
            bb_color = "#f59e0b"

        # 지지선/저항선 (최근 60일 기준)
        recent_high = float(high.iloc[-60:].max())
        recent_low = float(low.iloc[-60:].min())
        support = float(low.iloc[-60:].nsmallest(5).mean())
        resistance = float(high.iloc[-60:].nlargest(5).mean())

        # 거래량 상태
        if vol_ratio > 2.0:
            vol_label = f"폭발적 거래량 ({vol_ratio:.1f}배)"
            vol_color = CANDLE_UP
        elif vol_ratio > 1.3:
            vol_label = f"거래량 증가 ({vol_ratio:.1f}배)"
            vol_color = "#22c55e"
        elif vol_ratio < 0.5:
            vol_label = f"거래량 급감 ({vol_ratio:.1f}배)"
            vol_color = "#6b7280"
        else:
            vol_label = f"평균 수준 ({vol_ratio:.1f}배)"
            vol_color = "#f59e0b"

        # 종합 진단
        score = 0
        if curr_price > ma20_val: score += 1
        if curr_price > ma60_val: score += 1
        if ma20_val > ma60_val: score += 1
        if rsi_val > 50: score += 1
        if bb_pct > 50: score += 1
        if vol_ratio > 1.0: score += 1

        if score >= 5:
            diagnosis = "매우 강세 — 모멘텀 유효"
            diag_color = CANDLE_UP
        elif score >= 4:
            diagnosis = "강세 — 추세 유지 중"
            diag_color = "#22c55e"
        elif score >= 3:
            diagnosis = "중립 — 방향성 탐색"
            diag_color = "#f59e0b"
        elif score >= 2:
            diagnosis = "약세 — 추세 약화"
            diag_color = "#ef4444"
        else:
            diagnosis = "매우 약세 — 하락 압력"
            diag_color = CANDLE_DOWN

        # 종합 진단 배너
        st.markdown(f"""
        <div style='background:{diag_color}15; border:1px solid {diag_color}40; border-radius:10px; padding:14px 18px; margin-bottom:16px; display:flex; justify-content:space-between; align-items:center;'>
            <div>
                <div style='font-size:11px; color:{DIM}; margin-bottom:4px;'>기술적 종합 진단</div>
                <div style='font-size:16px; font-weight:700; color:{diag_color};'>{diagnosis}</div>
            </div>
            <div style='text-align:right;'>
                <div style='font-size:11px; color:{DIM}; margin-bottom:4px;'>종합 점수</div>
                <div style='font-size:20px; font-weight:700; color:{diag_color};'>{score}/6</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 지표 카드 2행
        r1c1, r1c2, r1c3 = st.columns(3)
        r2c1, r2c2, r2c3 = st.columns(3)

        for col, label, value, sub, color in [
            (r1c1, "추세", trend, f"MA20: {ma20_val:,.0f}원", trend_color),
            (r1c2, f"RSI (14): {rsi_val:.1f}", rsi_label, f"과매도<30 | 과매수>70", rsi_color),
            (r1c3, "볼린저밴드", bb_label, f"위치: {bb_pct:.0f}% | 밴드폭: {bb_upper_val-bb_lower_val:,.0f}원", bb_color),
            (r2c1, "52주 위치", f"{pos_52:.1f}%", f"고가: {high_52:,.0f} / 저가: {low_52:,.0f}", "#a855f7"),
            (r2c2, "거래량", vol_label, f"오늘: {int(volume.iloc[-1]):,}주", vol_color),
            (r2c3, "지지/저항", f"{support:,.0f} / {resistance:,.0f}", "최근 60일 기준 (지지/저항)", "#6b7280"),
        ]:
            with col:
                st.markdown(f"""
                <div style='background:{SURFACE_2}; border:0.5px solid {LINE}; border-radius:10px; padding:12px; margin-bottom:8px;'>
                    <div style='font-size:10px; color:{DIM}; margin-bottom:4px;'>{label}</div>
                    <div style='font-size:13px; font-weight:700; color:{color};'>{value}</div>
                    <div style='font-size:10px; color:{DIM}; margin-top:3px;'>{sub}</div>
                </div>
                """, unsafe_allow_html=True)

        # 차트 (주가 + 거래량)
        fig_tech = go.Figure()

        # 볼린저밴드
        fig_tech.add_trace(go.Scatter(
            x=close.index[-60:], y=bb_upper.iloc[-60:],
            name="BB상단", line=dict(color="#ef4444", width=1, dash="dash"), opacity=0.5
        ))
        fig_tech.add_trace(go.Scatter(
            x=close.index[-60:], y=bb_lower.iloc[-60:],
            name="BB하단", line=dict(color="#3b82f6", width=1, dash="dash"), opacity=0.5,
            fill="tonexty", fillcolor="rgba(99,102,241,0.05)"
        ))

        # 주가/이동평균
        fig_tech.add_trace(go.Scatter(
            x=close.index[-60:], y=ma120.iloc[-60:],
            name="MA120", line=dict(color="#6b7280", width=1)
        ))
        fig_tech.add_trace(go.Scatter(
            x=close.index[-60:], y=ma60.iloc[-60:],
            name="MA60", line=dict(color="#a855f7", width=1.2)
        ))
        fig_tech.add_trace(go.Scatter(
            x=close.index[-60:], y=ma20.iloc[-60:],
            name="MA20", line=dict(color="orange", width=1.2)
        ))
        fig_tech.add_trace(go.Scatter(
            x=close.index[-60:], y=close.iloc[-60:],
            name="주가", line=dict(color=ACCENT, width=2)
        ))

        # 거래량 (보조 y축)
        vol_colors = [CANDLE_UP if float(close.iloc[i]) >= float(close.iloc[i-1]) else CANDLE_DOWN
                      for i in range(len(close.iloc[-60:]))]
        fig_tech.add_trace(go.Bar(
            x=volume.index[-60:], y=volume.iloc[-60:],
            name="거래량", yaxis="y2",
            marker_color=vol_colors, opacity=0.4
        ))

        fig_tech.update_layout(
            height=360,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT, size=11),
            margin=dict(l=0, r=60, t=30, b=20),
            legend=dict(orientation="h", y=1.12),
            yaxis=dict(gridcolor=LINE, tickformat=",", ticksuffix="원", side="left"),
            yaxis2=dict(
                overlaying="y", side="right",
                showgrid=False, tickformat=",",
                title=dict(text="거래량", font=dict(color="#6b7280")),
                tickfont=dict(color="#6b7280")
            ),
            xaxis=dict(gridcolor=LINE)
        )
        st.plotly_chart(fig_tech, use_container_width=True, config={"displayModeBar": False})

    except Exception as e:
        st.info(f"기술적 분석 실패: {e}")

    st.markdown("---")

    # ══════════════════════════════════════════
    # 3. 외국인/기관 수급 히스토리 (30일)
    # ══════════════════════════════════════════
    card("💰 외국인/기관 수급 히스토리", "최근 30일 순매수 추이 (KIS API · 장 마감 후 당일 반영)")

    if KIS_AVAILABLE and is_korean:
        try:
            from broker import get_stock_investor
            kis_token = get_kis_token()
            if kis_token:
                inv_data = get_stock_investor(raw_ticker, kis_token)
                if inv_data.get("rt_cd") == "0" and inv_data.get("output"):
                    output = inv_data["output"][:30]
                    dates = [o["stck_bsop_date"] for o in output][::-1]
                    dates_fmt = [f"{d[4:6]}/{d[6:8]}" for d in dates]
                    frgn_vals = [round(int(o.get("frgn_ntby_tr_pbmn", 0)) / 100, 1) for o in output][::-1]
                    orgn_vals = [round(int(o.get("orgn_ntby_tr_pbmn", 0)) / 100, 1) for o in output][::-1]

                    fig_supply = go.Figure()
                    fig_supply.add_trace(go.Bar(
                        x=dates_fmt, y=frgn_vals, name="외국인",
                        marker_color=[CANDLE_UP if v >= 0 else CANDLE_DOWN for v in frgn_vals],
                        opacity=0.85,
                        hovertemplate="<b>%{x} 외국인</b><br>%{customdata:,}억원<extra></extra>",
                        customdata=frgn_vals
                    ))
                    fig_supply.add_trace(go.Bar(
                        x=dates_fmt, y=orgn_vals, name="기관",
                        marker_color=["rgba(168,85,247,0.8)" if v >= 0 else "rgba(99,102,241,0.6)" for v in orgn_vals],
                        opacity=0.85,
                        hovertemplate="<b>%{x} 기관</b><br>%{customdata:,}억원<extra></extra>",
                        customdata=orgn_vals
                    ))
                    fig_supply.add_hline(y=0, line=dict(color=DIM, width=1, dash="dot"))
                    fig_supply.update_layout(
                        barmode="group", height=320,
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color=TEXT, size=11),
                        margin=dict(l=0, r=0, t=30, b=20),
                        legend=dict(orientation="h", y=1.12),
                        yaxis=dict(gridcolor=LINE, tickformat=",", ticksuffix="억"),
                        xaxis=dict(gridcolor=LINE)
                    )
                    st.plotly_chart(fig_supply, use_container_width=True, config={"displayModeBar": False})

                    frgn_5d = sum(frgn_vals[-5:])
                    orgn_5d = sum(orgn_vals[-5:])
                    frgn_30d = sum(frgn_vals)
                    orgn_30d = sum(orgn_vals)

                    s1, s2, s3, s4 = st.columns(4)
                    for col, label, val in [
                        (s1, "외국인 5일 누적", frgn_5d),
                        (s2, "기관 5일 누적", orgn_5d),
                        (s3, "외국인 30일 누적", frgn_30d),
                        (s4, "기관 30일 누적", orgn_30d),
                    ]:
                        with col:
                            color = CANDLE_UP if val >= 0 else CANDLE_DOWN
                            arrow = "▲" if val >= 0 else "▼"
                            st.markdown(f"""
                            <div style='background:{SURFACE_2}; border:0.5px solid {LINE}; border-radius:10px; padding:12px; text-align:center;'>
                                <div style='font-size:10px; color:{DIM}; margin-bottom:4px;'>{label}</div>
                                <div style='font-size:13px; font-weight:700; color:{color}; font-family:JetBrains Mono;'>{arrow} {abs(val):,.1f}억원</div>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.info("수급 데이터를 불러오지 못했어요.")
        except Exception as e:
            st.info(f"수급 히스토리 조회 실패: {e}")
    else:
        st.info("수급 히스토리는 한국 주식만 지원합니다.")

    st.markdown("---")

    # ══════════════════════════════════════════
    # 4. 경쟁사 비교
    # ══════════════════════════════════════════
    card("🏢 경쟁사 비교", "동종업계 PER/PBR/ROE 비교")

    try:
        t_info = info
        sector = t_info.get("sector", "")

        competitors_map = {
            "Technology": ["005930.KS", "000660.KS", "035420.KS", "066570.KS"],
            "Consumer Cyclical": ["005380.KS", "000270.KS", "012330.KS", "011210.KS"],
            "Financial Services": ["105560.KS", "055550.KS", "086790.KS", "139130.KS"],
            "Industrials": ["042660.KS", "009540.KS", "011200.KS", "047050.KS"],
            "Healthcare": ["068270.KS", "207940.KS", "128940.KS", "145720.KS"],
            "Basic Materials": ["051910.KS", "011790.KS", "010120.KS", "002380.KS"],
        }

        comp_tickers = competitors_map.get(sector, [])
        if ticker not in comp_tickers:
            comp_tickers = [ticker] + comp_tickers[:3]
        else:
            comp_tickers = [ticker] + [t for t in comp_tickers if t != ticker][:3]

        comp_data = []
        for ct in comp_tickers:
            try:
                ci = load_competitor_info(ct)
                ct_raw = ct.replace(".KS", "").replace(".KQ", "")
                is_target = ct == ticker
                comp_data.append({
                    "종목": f"★ {name_map.get(ct_raw, ct_raw)}" if is_target else name_map.get(ct_raw, ct_raw),
                    "현재가": f"{int(ci.get('currentPrice', ci.get('regularMarketPrice', 0))):,}원" if ci.get('currentPrice') or ci.get('regularMarketPrice') else "N/A",
                    "PER": f"{ci.get('trailingPE', 0):.1f}배" if ci.get('trailingPE') else "N/A",
                    "PBR": f"{ci.get('priceToBook', 0):.1f}배" if ci.get('priceToBook') else "N/A",
                    "ROE": f"{ci.get('returnOnEquity', 0)*100:.1f}%" if ci.get('returnOnEquity') else "N/A",
                    "시가총액": f"{ci.get('marketCap', 0)/1e12:.1f}조" if ci.get('marketCap') else "N/A",
                })
            except:
                pass

        if comp_data:
            st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)
        else:
            st.info("경쟁사 데이터를 불러오지 못했어요.")
    except Exception as e:
        st.info(f"경쟁사 비교 실패: {e}")

    st.markdown("---")

    # ══════════════════════════════════════════
    # 5. AI 종합 투자의견
    # ══════════════════════════════════════════
    card("🤖 AI 종합 투자의견", "재무·기술적·수급 데이터 기반 AI 분석 (참고용)")

    if st.button("🤖 AI 투자의견 생성", use_container_width=True, key="ai_opinion_btn"):
        with st.spinner("AI가 종목을 심층 분석하는 중..."):
            try:
                curr_per = per if per else "N/A"
                curr_pbr = pbr if pbr else "N/A"
                curr_roe = f"{roe*100:.1f}%" if roe else "N/A"

                prompt = f"""당신은 국내 최고 수준의 증권사 리서치센터 수석 애널리스트입니다.
아래 데이터를 바탕으로 {display_name}({raw_ticker})에 대한 전문 투자 리포트를 작성해주세요.

[기본 정보]
- 현재가: {curr_price:,.0f}원
- PER: {curr_per}
- PBR: {curr_pbr}
- ROE: {curr_roe}

[기술적 분석]
- RSI(14): {rsi_val:.1f} ({rsi_label})
- 추세: {trend}
- 볼린저밴드: {bb_label} (위치: {bb_pct:.0f}%)
- 52주 위치: {pos_52:.1f}%
- 52주 고가: {high_52:,.0f}원 / 저가: {low_52:,.0f}원
- 거래량: {vol_label}
- 지지선: {support:,.0f}원 / 저항선: {resistance:,.0f}원
- 기술적 종합점수: {score}/6 ({diagnosis})

[작성 규칙]
1. 반드시 한국어로만 작성
2. 수치 근거를 반드시 포함
3. 단기(1개월)/중기(3개월)/장기(6개월) 관점 구분
4. 투자의견은 반드시 매수/중립/매도 중 하나로 명시
5. 목표주가는 현재가 기준 상승/하락 여력(%)도 함께 제시
6. 지지선/저항선 기반 매수 구간 및 손절선 제시

아래 형식으로 정확히 작성:

【투자의견】 매수 / 중립 / 매도 (하나만)
【목표주가】 X,XXX원 (현재가 대비 +X%)
【매수 적정 구간】 X,XXX원 ~ X,XXX원
【손절 기준선】 X,XXX원 (현재가 대비 -X%)

【핵심 투자포인트】
1. (포인트 1 — 수치 근거 포함)
2. (포인트 2 — 수치 근거 포함)
3. (포인트 3 — 수치 근거 포함)

【주요 리스크】
1. (리스크 1)
2. (리스크 2)

【단기/중기/장기 전망】
- 단기(1개월):
- 중기(3개월):
- 장기(6개월):

【결론】
(2~3줄 종합 코멘트)

⚠️ 본 분석은 AI가 생성한 참고 자료이며, 실제 투자 결정은 본인의 판단과 책임 하에 이루어져야 합니다."""

                openai_key = st.secrets.get("OPENAI_API_KEY", "")
                ai_res = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {openai_key}"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 1200
                    }
                )
                ai_data = ai_res.json()
                if "choices" not in ai_data:
                    raise Exception(str(ai_data))
                opinion = ai_data["choices"][0]["message"]["content"]
                st.session_state["ai_opinion"] = opinion
                st.session_state["ai_opinion_ticker"] = display_name

            except Exception as e:
                st.error(f"AI 분석 실패: {e}")

    if st.session_state.get("ai_opinion") and st.session_state.get("ai_opinion_ticker") == display_name:
        opinion_text = st.session_state["ai_opinion"]

        if "매수" in opinion_text[:100]:
            badge_color = CANDLE_UP
            badge_text = "매수"
        elif "매도" in opinion_text[:100]:
            badge_color = CANDLE_DOWN
            badge_text = "매도"
        else:
            badge_color = "#f59e0b"
            badge_text = "중립"

        st.markdown(f"""
        <div style='background:{SURFACE_2}; border:0.5px solid {LINE}; border-radius:12px; padding:20px; margin-top:12px;'>
            <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;'>
                <div style='font-size:14px; font-weight:700;'>🤖 {display_name} AI 투자의견</div>
                <span style='background:{badge_color}22; border:0.5px solid {badge_color}; border-radius:20px; padding:4px 14px; font-size:13px; font-weight:700; color:{badge_color};'>{badge_text}</span>
            </div>
            <div style='font-size:13px; line-height:2.0; white-space:pre-line; color:{TEXT};'>{opinion_text}</div>
        </div>
        """, unsafe_allow_html=True)