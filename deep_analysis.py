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
    return yf.download(ticker, period="1y", progress=False)


@st.cache_data(ttl=600)
def load_ticker_financials(ticker):
    import time
    try:
        f = yf.Ticker(ticker).financials
        time.sleep(0.3)
        return f
    except:
        return None


@st.cache_data(ttl=300)
def load_naver_info(raw_ticker):
    """네이버 모바일 API — quant_app.py SUB3와 동일한 파싱 로직"""
    result = {"per": "N/A", "pbr": "N/A", "roe": "N/A", "eps": "N/A",
              "div_yield": "N/A", "mkt_str": "N/A", "price": None}

    # 1. DART에서 ROE 먼저 시도 (quant_app.py SUB3와 동일)
    try:
        from dart_utils import get_dart_roe
        roe_val = get_dart_roe(raw_ticker)
        if roe_val is not None:
            result["roe"] = f"{roe_val:.1f}%"
    except: pass

    # 2. 네이버 API로 나머지 항목 + ROE 보완
    try:
        url = f"https://m.stock.naver.com/api/stock/{raw_ticker}/integration"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        data = res.json()

        def clean_val(val_str):
            return val_str.replace("원","").replace("%","").replace("배","").replace("x","").replace(",","").strip()

        for info in data.get("totalInfos", []):
            k = str(info.get("key","")).upper()
            c = str(info.get("code","")).lower()
            v = str(info.get("value","")).strip()
            if not v or v == "-": continue
            val_clean = clean_val(v)
            try:
                if c == "per" or k == "PER":
                    if result["per"] == "N/A": result["per"] = f"{float(val_clean):.1f}배"
                elif c == "pbr" or k == "PBR":
                    if result["pbr"] == "N/A": result["pbr"] = f"{float(val_clean):.1f}배"
                elif c == "eps" or k == "EPS":
                    if result["eps"] == "N/A": result["eps"] = f"{int(float(val_clean)):,}원"
                elif c == "roe" or k == "ROE":
                    if result["roe"] == "N/A": result["roe"] = f"{float(val_clean):.1f}%"
                elif c == "dividendyield" or k == "배당수익률":
                    if result["div_yield"] == "N/A": result["div_yield"] = f"{float(val_clean):.2f}%"
                elif c == "marketvalue" or k == "시가총액":
                    result["mkt_str"] = v
            except: pass
    except: pass
    return result


def render_deep_analysis(KIS_AVAILABLE, get_kis_token):

    st.markdown(
        "<div style='font-size:22px; font-weight:700; margin-bottom:4px;'>🔬 종목 심층분석</div>"
        f"<div style='font-size:12px; color:{DIM}; margin-bottom:24px;'>재무 · 기술적 분석 · 수급 히스토리 · 경쟁사 비교 · AI 투자의견</div>",
        unsafe_allow_html=True
    )

    col_input, col_btn = st.columns([4, 1])
    with col_input:
        ticker_input = st.text_input("종목명 또는 코드 입력", placeholder="예: 삼성전자, 005930, AAPL", key="deep_ticker_input")
    with col_btn:
        st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
        analyze_btn = st.button("🔬 심층분석 시작", use_container_width=True)

    if not ticker_input or not analyze_btn:
        st.info("종목명 또는 코드를 입력하고 심층분석 시작 버튼을 눌러주세요.")
        return

    df_krx = load_krx_listing()
    name_map = get_krx_name_map()
    ticker = ticker_input.strip()
    is_korean = True

    if not ticker.endswith(".KS") and not ticker.endswith(".KQ") and not ticker.isupper():
        if df_krx is not None:
            code_col = next((c for c in ['Symbol','Code','code'] if c in df_krx.columns), None)
            if code_col:
                matched = df_krx[df_krx['Name'].str.upper() == ticker.upper()]
                if matched.empty:
                    matched = df_krx[df_krx['Name'].str.upper().str.contains(ticker.upper(), na=False)]
                if not matched.empty:
                    raw_code = str(matched.iloc[0][code_col]).split('.')[0].zfill(6)
                    mkt = str(matched.iloc[0].get('Market','KOSPI')).upper()
                    ticker = raw_code + (".KS" if "KOSPI" in mkt else ".KQ")
    elif ticker.isdigit():
        ticker = ticker.zfill(6) + ".KS"

    if ticker.endswith(".KS") or ticker.endswith(".KQ"):
        raw_ticker = ticker.replace(".KS","").replace(".KQ","")
        is_korean = True
    else:
        raw_ticker = ticker
        is_korean = False

    display_name = name_map.get(raw_ticker, ticker_input)

    with st.spinner(f"{display_name} 데이터 분석 중..."):
        hist = load_ticker_data(ticker)
        if hist.empty:
            st.error("주가 데이터를 불러오지 못했어요.")
            return
        close = hist["Close"].squeeze()
        high = hist["High"].squeeze()
        low = hist["Low"].squeeze()
        volume = hist["Volume"].squeeze()

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
    card("📊 재무제표 분석", "매출(막대)/영업이익(꺾은선) 추이 · PER/PBR 밸류에이션")

    try:
        financials = load_ticker_financials(ticker)

        if financials is not None and not financials.empty:
            rev_row = next((r for r in ["Total Revenue","Revenue"] if r in financials.index), None)
            ni_row = next((r for r in ["Net Income","Net Income Common Stockholders"] if r in financials.index), None)

            if rev_row or ni_row:
                def auto_unit(max_eok):
                    return ("조원", 10000) if abs(max_eok) >= 10000 else ("억원", 1)

                # 최대 5년치
                cols_fin = financials.columns[:5]
                years = [f"{c.year}년" for c in cols_fin][::-1]

                rev_eok, ni_eok = [], []
                if rev_row:
                    rev_eok = [round(float(financials.loc[rev_row, c]) / 1e8, 1) for c in cols_fin][::-1]
                if ni_row:
                    ni_eok = [round(float(financials.loc[ni_row, c]) / 1e8, 1) for c in cols_fin][::-1]

                # 단위 결정
                max_val = max([abs(v) for v in rev_eok + ni_eok] or [1])
                unit, div = auto_unit(max_val)

                rev_vals = [round(v / div, 2) for v in rev_eok] if rev_eok else []
                ni_vals = [round(v / div, 2) for v in ni_eok] if ni_eok else []

                # 순이익률 계산
                margin_vals = []
                if rev_eok and ni_eok:
                    for r, n in zip(rev_eok, ni_eok):
                        margin_vals.append(round(n / r * 100, 2) if r != 0 else 0)

                # 순이익 성장률
                growth_vals = []
                if ni_eok:
                    for i in range(len(ni_eok)):
                        if i == 0 or ni_eok[i-1] == 0:
                            growth_vals.append(None)
                        else:
                            growth_vals.append(round((ni_eok[i] - ni_eok[i-1]) / abs(ni_eok[i-1]) * 100, 2))

                # 차트
                fig_fin = go.Figure()

                if rev_vals:
                    fig_fin.add_trace(go.Bar(
                        x=years, y=rev_vals, name=f"매출({unit})",
                        marker_color="#3b82f6", opacity=0.7, yaxis="y1",
                        hovertemplate=f"<b>%{{x}} 매출</b><br>%{{y:,.2f}}{unit}<extra></extra>"
                    ))
                if ni_vals:
                    fig_fin.add_trace(go.Bar(
                        x=years, y=ni_vals, name=f"순이익({unit})",
                        marker_color="#60a5fa", opacity=0.85, yaxis="y1",
                        hovertemplate=f"<b>%{{x}} 순이익</b><br>%{{y:,.2f}}{unit}<extra></extra>"
                    ))
                if margin_vals:
                    fig_fin.add_trace(go.Scatter(
                        x=years, y=margin_vals, name="순이익률(%)",
                        mode="lines+markers",
                        line=dict(color="#f59e0b", width=2.5),
                        marker=dict(size=7, color="#f59e0b"),
                        yaxis="y2",
                        hovertemplate="<b>%{x} 순이익률</b><br>%{y:.2f}%<extra></extra>"
                    ))

                fig_fin.update_layout(
                    barmode="group", height=320,
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color=TEXT, size=11),
                    margin=dict(l=50, r=60, t=30, b=20),
                    legend=dict(orientation="h", y=1.12),
                    xaxis=dict(gridcolor="rgba(0,0,0,0)"),
                    yaxis=dict(tickfont=dict(color="#3b82f6"), gridcolor=LINE, tickformat=",", ticksuffix=unit, side="left"),
                    yaxis2=dict(tickfont=dict(color="#f59e0b"), gridcolor="rgba(0,0,0,0)", tickformat=".1f", ticksuffix="%", side="right", overlaying="y", showgrid=False)
                )
                st.plotly_chart(fig_fin, use_container_width=True, config={"displayModeBar": False})

                # 요약 테이블
                table_data = {"항목": ["매출", "순이익", "순이익률", "순이익 성장률"]}
                for i, y in enumerate(years):
                    col_data = []
                    col_data.append(f"{rev_vals[i]:,.1f}{unit}" if rev_vals and i < len(rev_vals) else "N/A")
                    col_data.append(f"{ni_vals[i]:,.1f}{unit}" if ni_vals and i < len(ni_vals) else "N/A")
                    col_data.append(f"{margin_vals[i]:.2f}%" if margin_vals and i < len(margin_vals) else "N/A")
                    g = growth_vals[i] if growth_vals and i < len(growth_vals) else None
                    col_data.append(f"{g:+.2f}%" if g is not None else "-")
                    table_data[y] = col_data

                df_table = pd.DataFrame(table_data)
                st.dataframe(df_table, use_container_width=True, hide_index=True)

        # 밸류에이션 — 네이버 API (quant_app.py SUB3와 동일)
        nv = load_naver_info(raw_ticker) if is_korean else {}

        v1, v2, v3, v4, v5, v6 = st.columns(6)
        for col, label, value in [
            (v1, "PER", nv.get("per","N/A")),
            (v2, "PBR", nv.get("pbr","N/A")),
            (v3, "ROE", nv.get("roe","N/A")),
            (v4, "EPS", nv.get("eps","N/A")),
            (v5, "시가총액", nv.get("mkt_str","N/A")),
            (v6, "배당수익률", nv.get("div_yield","N/A")),
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

    rsi_val = 50.0
    rsi_label = "중립"
    trend = "횡보/혼조 ⚖️"
    bb_pct = 50.0
    bb_label = "중간 구간 (중립)"
    pos_52 = 50.0
    high_52 = curr_price
    low_52 = curr_price
    support = curr_price
    resistance = curr_price
    vol_label = "평균"
    score = 3
    diagnosis = "중립 — 방향성 탐색"
    diag_color = "#f59e0b"
    ma20 = close.rolling(20).mean()
    ma60 = close.rolling(60).mean()
    ma120 = close.rolling(120).mean()
    bb_upper = close.rolling(20).mean() + 2 * close.rolling(20).std()
    bb_lower = close.rolling(20).mean() - 2 * close.rolling(20).std()

    try:
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + gain / loss))
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

        vol_ma20 = volume.rolling(20).mean()
        vol_ratio = float(volume.iloc[-1]) / float(vol_ma20.iloc[-1]) if float(vol_ma20.iloc[-1]) > 0 else 1

        ma20_val = float(ma20.iloc[-1])
        ma60_val = float(ma60.iloc[-1])
        ma120_val = float(ma120.iloc[-1])
        bb_upper_val = float(bb_upper.iloc[-1])
        bb_lower_val = float(bb_lower.iloc[-1])
        bb_pct = (curr_price - bb_lower_val) / (bb_upper_val - bb_lower_val) * 100 if bb_upper_val != bb_lower_val else 50

        support = float(low.iloc[-60:].nsmallest(5).mean())
        resistance = float(high.iloc[-60:].nlargest(5).mean())

        if curr_price > ma20_val > ma60_val > ma120_val: trend, trend_color = "강한 상승추세 📈", CANDLE_UP
        elif curr_price > ma20_val and ma20_val > ma60_val: trend, trend_color = "상승추세 🟢", CANDLE_UP
        elif curr_price < ma20_val < ma60_val < ma120_val: trend, trend_color = "강한 하락추세 📉", CANDLE_DOWN
        elif curr_price < ma20_val and ma20_val < ma60_val: trend, trend_color = "하락추세 🔴", CANDLE_DOWN
        else: trend, trend_color = "횡보/혼조 ⚖️", "#f59e0b"

        if rsi_val < 30: rsi_label, rsi_color = "과매도 — 반등 가능성", CANDLE_UP
        elif rsi_val > 70: rsi_label, rsi_color = "과매수 — 조정 주의", CANDLE_DOWN
        elif rsi_val > 55: rsi_label, rsi_color = "강세 구간", "#22c55e"
        elif rsi_val < 45: rsi_label, rsi_color = "약세 구간", "#ef4444"
        else: rsi_label, rsi_color = "중립", "#f59e0b"

        if bb_pct > 85: bb_label, bb_color = "상단 돌파 (과열)", CANDLE_DOWN
        elif bb_pct > 60: bb_label, bb_color = "상단 근접 (강세)", "#22c55e"
        elif bb_pct < 15: bb_label, bb_color = "하단 이탈 (과매도)", CANDLE_UP
        elif bb_pct < 40: bb_label, bb_color = "하단 근접 (약세)", "#ef4444"
        else: bb_label, bb_color = "중간 구간 (중립)", "#f59e0b"

        if vol_ratio > 2.0: vol_label, vol_color = f"폭발적 ({vol_ratio:.1f}배)", CANDLE_UP
        elif vol_ratio > 1.3: vol_label, vol_color = f"증가 ({vol_ratio:.1f}배)", "#22c55e"
        elif vol_ratio < 0.5: vol_label, vol_color = f"급감 ({vol_ratio:.1f}배)", "#6b7280"
        else: vol_label, vol_color = f"평균 ({vol_ratio:.1f}배)", "#f59e0b"

        score = sum([curr_price > ma20_val, curr_price > ma60_val, ma20_val > ma60_val,
                     rsi_val > 50, bb_pct > 50, vol_ratio > 1.0])

        if score >= 5: diagnosis, diag_color = "매우 강세 — 모멘텀 유효", CANDLE_UP
        elif score >= 4: diagnosis, diag_color = "강세 — 추세 유지 중", "#22c55e"
        elif score >= 3: diagnosis, diag_color = "중립 — 방향성 탐색", "#f59e0b"
        elif score >= 2: diagnosis, diag_color = "약세 — 추세 약화", "#ef4444"
        else: diagnosis, diag_color = "매우 약세 — 하락 압력", CANDLE_DOWN

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

        r1c1, r1c2, r1c3 = st.columns(3)
        r2c1, r2c2, r2c3 = st.columns(3)
        for col, label, value, sub, color in [
            (r1c1, "추세", trend, f"MA20: {float(ma20.iloc[-1]):,.0f}원", trend_color),
            (r1c2, f"RSI (14): {rsi_val:.1f}", rsi_label, "과매도<30 | 과매수>70", rsi_color),
            (r1c3, "볼린저밴드", bb_label, f"위치: {bb_pct:.0f}%", bb_color),
            (r2c1, "52주 위치", f"{pos_52:.1f}%", f"고가: {high_52:,.0f} / 저가: {low_52:,.0f}", "#a855f7"),
            (r2c2, "거래량", vol_label, f"오늘: {int(volume.iloc[-1]):,}주", vol_color),
            (r2c3, "지지/저항", f"{support:,.0f} / {resistance:,.0f}", "최근 60일 기준", "#6b7280"),
        ]:
            with col:
                st.markdown(f"""
                <div style='background:{SURFACE_2}; border:0.5px solid {LINE}; border-radius:10px; padding:12px; margin-bottom:8px;'>
                    <div style='font-size:10px; color:{DIM}; margin-bottom:4px;'>{label}</div>
                    <div style='font-size:13px; font-weight:700; color:{color};'>{value}</div>
                    <div style='font-size:10px; color:{DIM}; margin-top:3px;'>{sub}</div>
                </div>
                """, unsafe_allow_html=True)

        fig_tech = go.Figure()
        fig_tech.add_trace(go.Scatter(x=close.index[-60:], y=bb_upper.iloc[-60:], name="BB상단", line=dict(color="#ef4444", width=1, dash="dash"), opacity=0.5))
        fig_tech.add_trace(go.Scatter(x=close.index[-60:], y=bb_lower.iloc[-60:], name="BB하단", line=dict(color="#3b82f6", width=1, dash="dash"), opacity=0.5, fill="tonexty", fillcolor="rgba(99,102,241,0.05)"))
        fig_tech.add_trace(go.Scatter(x=close.index[-60:], y=ma120.iloc[-60:], name="MA120", line=dict(color="#6b7280", width=1)))
        fig_tech.add_trace(go.Scatter(x=close.index[-60:], y=ma60.iloc[-60:], name="MA60", line=dict(color="#a855f7", width=1.2)))
        fig_tech.add_trace(go.Scatter(x=close.index[-60:], y=ma20.iloc[-60:], name="MA20", line=dict(color="orange", width=1.2)))
        fig_tech.add_trace(go.Scatter(x=close.index[-60:], y=close.iloc[-60:], name="주가", line=dict(color=ACCENT, width=2)))
        close_arr = list(close.iloc[-60:])
        vol_colors = [CANDLE_UP if i == 0 or close_arr[i] >= close_arr[i-1] else CANDLE_DOWN for i in range(len(close_arr))]
        fig_tech.add_trace(go.Bar(x=volume.index[-60:], y=volume.iloc[-60:], name="거래량", yaxis="y2", marker_color=vol_colors, opacity=0.4))
        fig_tech.update_layout(
            height=360, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT, size=11), margin=dict(l=0, r=60, t=30, b=20),
            legend=dict(orientation="h", y=1.12),
            yaxis=dict(gridcolor=LINE, tickformat=",", ticksuffix="원"),
            yaxis2=dict(overlaying="y", side="right", showgrid=False, tickformat=","),
            xaxis=dict(gridcolor=LINE)
        )
        st.plotly_chart(fig_tech, use_container_width=True, config={"displayModeBar": False})

    except Exception as e:
        st.info(f"기술적 분석 실패: {e}")

    st.markdown("---")

    # ══════════════════════════════════════════
    # 3. 수급 히스토리
    # ══════════════════════════════════════════
    card("💰 외국인/기관 수급 히스토리", "최근 30일 순매수 추이 (KIS API)")

    if KIS_AVAILABLE and is_korean:
        try:
            from broker import get_stock_investor
            kis_token = get_kis_token()
            if kis_token:
                inv_data = get_stock_investor(raw_ticker, kis_token)
                if inv_data.get("rt_cd") == "0" and inv_data.get("output"):
                    output = inv_data["output"][:30]
                    dates_fmt = [f"{o['stck_bsop_date'][4:6]}/{o['stck_bsop_date'][6:8]}" for o in output][::-1]
                    def safe_int(val):
                        try: return int(str(val).strip()) if str(val).strip() else 0
                        except: return 0

                    frgn_vals = [round(safe_int(o.get("frgn_ntby_tr_pbmn",0))/100, 1) for o in output][::-1]
                    orgn_vals = [round(safe_int(o.get("orgn_ntby_tr_pbmn",0))/100, 1) for o in output][::-1]

                    fig_sup = go.Figure()
                    fig_sup.add_trace(go.Bar(x=dates_fmt, y=frgn_vals, name="외국인",
                        marker_color=[CANDLE_UP if v>=0 else CANDLE_DOWN for v in frgn_vals], opacity=0.85,
                        hovertemplate="<b>%{x} 외국인</b><br>%{customdata:,}억원<extra></extra>", customdata=frgn_vals))
                    fig_sup.add_trace(go.Bar(x=dates_fmt, y=orgn_vals, name="기관",
                        marker_color=["rgba(168,85,247,0.8)" if v>=0 else "rgba(99,102,241,0.6)" for v in orgn_vals], opacity=0.85,
                        hovertemplate="<b>%{x} 기관</b><br>%{customdata:,}억원<extra></extra>", customdata=orgn_vals))
                    fig_sup.add_hline(y=0, line=dict(color=DIM, width=1, dash="dot"))
                    fig_sup.update_layout(barmode="group", height=300,
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color=TEXT, size=11), margin=dict(l=0,r=0,t=30,b=20),
                        legend=dict(orientation="h", y=1.12),
                        yaxis=dict(gridcolor=LINE, tickformat=",", ticksuffix="억"),
                        xaxis=dict(gridcolor=LINE))
                    st.plotly_chart(fig_sup, use_container_width=True, config={"displayModeBar": False})

                    s1, s2, s3, s4 = st.columns(4)
                    for col, label, val in [(s1,"외국인 5일",sum(frgn_vals[-5:])),(s2,"기관 5일",sum(orgn_vals[-5:])),(s3,"외국인 30일",sum(frgn_vals)),(s4,"기관 30일",sum(orgn_vals))]:
                        with col:
                            c2 = CANDLE_UP if val>=0 else CANDLE_DOWN
                            st.markdown(f"<div style='background:{SURFACE_2};border:0.5px solid {LINE};border-radius:10px;padding:12px;text-align:center;'><div style='font-size:10px;color:{DIM};margin-bottom:4px;'>{label} 누적</div><div style='font-size:13px;font-weight:700;color:{c2};font-family:JetBrains Mono;'>{'▲' if val>=0 else '▼'} {abs(val):,.1f}억원</div></div>", unsafe_allow_html=True)
                else:
                    st.info("수급 데이터를 불러오지 못했어요.")
        except Exception as e:
            st.info(f"수급 히스토리 조회 실패: {e}")
    else:
        st.info("수급 히스토리는 한국 주식만 지원합니다.")

    st.markdown("---")

    # ══════════════════════════════════════════
    # 4. 경쟁사 비교 — 네이버 API로 통일
    # ══════════════════════════════════════════
    card("🏢 경쟁사 비교", "동종업계 PER/PBR/ROE 비교")

    try:
        competitors_map = {
            "005930": ["000660","035420","066570","034220"],
            "000660": ["005930","035420","034220","058470"],
            "005380": ["000270","012330","011210","064960"],
            "035420": ["035720","259960","263750","251270"],
            "051910": ["006400","096770","010950","298000"],
            "068270": ["207940","128940","145720","196170"],
            "105560": ["055550","086790","139130","316140"],
            "035720": ["035420","259960","263750","251270"],
            "006400": ["051910","096770","010950","298000"],
        }
        comp_codes = competitors_map.get(raw_ticker, [])
        all_codes = [raw_ticker] + comp_codes[:4]

        comp_data = []
        for code in all_codes:
            nv_info = load_naver_info(code)
            is_target = code == raw_ticker
            comp_data.append({
                "종목": f"★ {name_map.get(code, code)}" if is_target else name_map.get(code, code),
                "PER": nv_info.get("per","N/A"),
                "PBR": nv_info.get("pbr","N/A"),
                "ROE": nv_info.get("roe","N/A"),
                "시가총액": nv_info.get("mkt_str","N/A"),
            })

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
    card("🤖 AI 종합 투자의견", "재무·기술적·수급 데이터 기반 (참고용)")

    if st.button("🤖 AI 투자의견 생성", use_container_width=True, key="ai_opinion_btn"):
        with st.spinner("AI가 종목을 심층 분석하는 중..."):
            try:
                nv = load_naver_info(raw_ticker) if is_korean else {}
                prompt = f"""당신은 국내 최고 수준의 증권사 리서치센터 수석 애널리스트입니다.
아래 데이터를 바탕으로 {display_name}({raw_ticker})에 대한 전문 투자 리포트를 작성해주세요.

[기본 정보]
- 현재가: {curr_price:,.0f}원
- PER: {nv.get('per','N/A')} / PBR: {nv.get('pbr','N/A')} / ROE: {nv.get('roe','N/A')}
- 시가총액: {nv.get('mkt_str','N/A')}

[기술적 분석]
- RSI(14): {rsi_val:.1f} ({rsi_label})
- 추세: {trend}
- 볼린저밴드: {bb_label} (위치: {bb_pct:.0f}%)
- 52주 위치: {pos_52:.1f}% (고가: {high_52:,.0f}원 / 저가: {low_52:,.0f}원)
- 거래량: {vol_label}
- 지지선: {support:,.0f}원 / 저항선: {resistance:,.0f}원
- 기술적 종합점수: {score}/6 ({diagnosis})

[작성 규칙]
1. 반드시 한국어로만 작성, 수치 근거 필수 포함
2. 투자의견은 매수/중립/매도 중 하나로 명시
3. 목표주가와 상승여력(%) 제시
4. 지지선/저항선 기반 매수 구간 및 손절선 제시

아래 형식으로 작성:

【투자의견】 매수 / 중립 / 매도
【목표주가】 X,XXX원 (현재가 대비 +X%)
【매수 적정 구간】 X,XXX원 ~ X,XXX원
【손절 기준선】 X,XXX원 (현재가 대비 -X%)

【핵심 투자포인트】
1.
2.
3.

【주요 리스크】
1.
2.

【단기/중기/장기 전망】
- 단기(1개월):
- 중기(3개월):
- 장기(6개월):

【결론】

⚠️ 본 분석은 AI 참고 자료이며 투자 책임은 본인에게 있습니다."""

                openai_key = st.secrets.get("OPENAI_API_KEY","")
                ai_res = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Content-Type":"application/json","Authorization":f"Bearer {openai_key}"},
                    json={"model":"gpt-4o-mini","messages":[{"role":"user","content":prompt}],"max_tokens":1200}
                )
                ai_data = ai_res.json()
                if "choices" not in ai_data: raise Exception(str(ai_data))
                opinion = ai_data["choices"][0]["message"]["content"]
                st.session_state["ai_opinion"] = opinion
                st.session_state["ai_opinion_ticker"] = display_name
            except Exception as e:
                st.error(f"AI 분석 실패: {e}")

    if st.session_state.get("ai_opinion") and st.session_state.get("ai_opinion_ticker") == display_name:
        opinion_text = st.session_state["ai_opinion"]
        badge_color = CANDLE_UP if "매수" in opinion_text[:100] else (CANDLE_DOWN if "매도" in opinion_text[:100] else "#f59e0b")
        badge_text = "매수" if "매수" in opinion_text[:100] else ("매도" if "매도" in opinion_text[:100] else "중립")
        st.markdown(f"""
        <div style='background:{SURFACE_2}; border:0.5px solid {LINE}; border-radius:12px; padding:20px; margin-top:12px;'>
            <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;'>
                <div style='font-size:14px; font-weight:700;'>🤖 {display_name} AI 투자의견</div>
                <span style='background:{badge_color}22; border:0.5px solid {badge_color}; border-radius:20px; padding:4px 14px; font-size:13px; font-weight:700; color:{badge_color};'>{badge_text}</span>
            </div>
            <div style='font-size:13px; line-height:2.0; white-space:pre-line; color:{TEXT};'>{opinion_text}</div>
        </div>
        """, unsafe_allow_html=True)