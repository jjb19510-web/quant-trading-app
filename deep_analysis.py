import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import datetime as dt
from data_utils import load_krx_listing, get_krx_name_map
from ui_components import card, ACCENT, CANDLE_UP, CANDLE_DOWN, DIM, TEXT, SURFACE_1, SURFACE_2, LINE, BG
from design.components import hero_card, ai_insight_card, kpi_card, status_badge, score_card


@st.cache_data(ttl=600)
def load_ticker_data(ticker):
    try:
        hist = yf.download(ticker, period="1y", progress=False)
        if not hist.empty:
            return hist
    except:
        pass

    # yfinance 실패 시 FinanceDataReader 폴백 (최근 상장 종목 등)
    if ticker.endswith(".KS") or ticker.endswith(".KQ"):
        try:
            import FinanceDataReader as fdr
            import datetime as dt_module
            raw_code = ticker.replace(".KS", "").replace(".KQ", "")
            end_date = dt_module.datetime.now().strftime("%Y-%m-%d")
            start_date = (dt_module.datetime.now() - dt_module.timedelta(days=365)).strftime("%Y-%m-%d")
            df_fdr = fdr.DataReader(raw_code, start_date, end_date)
            if not df_fdr.empty:
                # yfinance와 동일한 컬럼 구조로 변환
                df_fdr = df_fdr.rename(columns={
                    "Open": "Open", "High": "High", "Low": "Low",
                    "Close": "Close", "Volume": "Volume"
                })
                return df_fdr[["Open", "High", "Low", "Close", "Volume"]]
        except:
            pass

    return pd.DataFrame()


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
        from dart_utils import get_dart_roe, get_dart_per_pbr
        roe_val = get_dart_roe(raw_ticker)
        if roe_val is not None:
            result["roe"] = f"{roe_val:.1f}%"
        # PER/PBR도 DART에서 보완
        if result["per"] == "N/A" or result["pbr"] == "N/A":
            dart_per, dart_pbr = get_dart_per_pbr(raw_ticker, 0)
            if dart_per and result["per"] == "N/A":
                result["per"] = f"{dart_per:.1f}배"
            if dart_pbr and result["pbr"] == "N/A":
                result["pbr"] = f"{dart_pbr:.1f}배"
    except Exception as e:
        print(f"dart_utils 오류: {e}")

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
                elif c == "dividendyieldratio" or c == "dividendyield" or k == "배당수익률":
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

    if analyze_btn and ticker_input:
        st.session_state["deep_ticker"] = ticker_input
    
    if not st.session_state.get("deep_ticker"):
        st.info("종목명 또는 코드를 입력하고 심층분석 시작 버튼을 눌러주세요.")
        return
    
    ticker_input = st.session_state["deep_ticker"]

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

    # ── 종목명/코드 → 정식 티커 변환 (분석 탭과 동일 로직) ──
    if ticker.endswith(".KS") or ticker.endswith(".KQ"):
        raw_ticker = ticker.replace(".KS", "").replace(".KQ", "")
        is_korean = True
    elif ticker.isdigit():
        # 숫자 코드만 입력된 경우 → 한국 종목
        raw_ticker = ticker.zfill(6)
        is_korean = True
        suffix = ".KS"
        if df_krx is not None:
            code_col = next((c for c in ['Symbol', 'Code', 'code'] if c in df_krx.columns), None)
            if code_col:
                try:
                    matched = df_krx[df_krx[code_col].astype(str).str.split('.').str[0].str.zfill(6) == raw_ticker]
                    if not matched.empty:
                        mkt = str(matched.iloc[0].get('Market', 'KOSPI')).upper()
                        suffix = ".KS" if "KOSPI" in mkt else ".KQ"
                except:
                    pass
        ticker = raw_ticker + suffix
    else:
        # 종목명(한글/영문) 입력 → KRX 리스트에서 검색
        matched_code = None
        matched_suffix = ".KS"

        # 1. 수동 매핑 우선 확인 (대소문자 무관)
        try:
            from data_utils import MANUAL_STOCK_MAP
            for map_name, (map_code, map_mkt) in MANUAL_STOCK_MAP.items():
                if map_name.upper() == ticker.upper():
                    matched_code = map_code
                    matched_suffix = ".KS" if "KOSPI" in map_mkt.upper() else ".KQ"
                    break
        except:
            pass

        # 2. KRX 리스트에서 검색
        if matched_code is None and df_krx is not None:
            name_col = next((c for c in ['Name'] if c in df_krx.columns), None)
            code_col = next((c for c in ['Symbol', 'Code', 'code'] if c in df_krx.columns), None)
            if name_col and code_col:
                # 정확히 일치 (대소문자 무관)
                m = df_krx[df_krx[name_col].astype(str).str.upper() == ticker.upper()]
                if m.empty:
                    # 부분 일치
                    m = df_krx[df_krx[name_col].astype(str).str.upper().str.contains(ticker.upper(), na=False)]
                if not m.empty:
                    raw_code = str(m.iloc[0][code_col]).split('.')[0].zfill(6)
                    matched_code = raw_code
                    mkt = str(m.iloc[0].get('Market', 'KOSPI')).upper()
                    matched_suffix = ".KS" if "KOSPI" in mkt else ".KQ"

        # 3. FinanceDataReader 폴백
        if matched_code is None:
            try:
                import FinanceDataReader as fdr
                krx_all = fdr.StockListing('KRX')
                name_col2 = next((c for c in ['Name'] if c in krx_all.columns), None)
                code_col2 = next((c for c in ['Symbol', 'Code'] if c in krx_all.columns), None)
                if name_col2 and code_col2:
                    m2 = krx_all[krx_all[name_col2].astype(str).str.upper() == ticker.upper()]
                    if m2.empty:
                        m2 = krx_all[krx_all[name_col2].astype(str).str.upper().str.contains(ticker.upper(), na=False)]
                    if not m2.empty:
                        raw_code2 = str(m2.iloc[0][code_col2]).split('.')[0].zfill(6)
                        matched_code = raw_code2
                        mkt2 = str(m2.iloc[0].get('Market', 'KOSPI')).upper()
                        matched_suffix = ".KS" if "KOSPI" in mkt2 else ".KQ"
            except:
                pass

        if matched_code:
            raw_ticker = matched_code
            ticker = matched_code + matched_suffix
            is_korean = True
        else:
            # 한국 종목으로 못 찾으면 미국 주식(영문 티커)으로 간주
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
        open_p = hist["Open"].squeeze()

    # ── 장중 분봉 데이터 자동 전환 ──
    import datetime as dt_now
    kst_now = dt_now.datetime.now(dt_now.timezone(dt_now.timedelta(hours=9)))
    market_open = kst_now.replace(hour=9, minute=0, second=0, microsecond=0)
    market_close = kst_now.replace(hour=15, minute=30, second=0, microsecond=0)
    is_market_open = kst_now.weekday() < 5 and market_open <= kst_now <= market_close

    minute_hist = None
    if is_market_open and is_korean and KIS_AVAILABLE:
        try:
            from broker import get_access_token, get_minute_chart
            import pandas as pd
            kis_token = get_kis_token()
            if kis_token:
                minute_hist = get_minute_chart(raw_ticker, kis_token, interval="5")
                if minute_hist is None or minute_hist.empty:
                    st.warning(f"⚠️ 분봉 데이터 없음 (종목코드: {raw_ticker}) — 일봉으로 대체")
        except Exception as e:
            st.warning(f"⚠️ 분봉 조회 실패: {e} — 일봉으로 대체")

    # 장중이면 분봉 데이터로 기술적 분석, 아니면 일봉 유지
    if minute_hist is not None and not minute_hist.empty and len(minute_hist) >= 20:
        import pandas as pd
        minute_hist = minute_hist.sort_values("time").reset_index(drop=True)
        # X축 시간 라벨 생성 (YYYYMMDDHHMMSS → HH:MM)
        def parse_time_label(t):
            try:
                t = str(t)
                if len(t) >= 12:
                    return t[8:10] + ":" + t[10:12]
                elif len(t) >= 6:
                    return t[:2] + ":" + t[2:4]
                return t
            except:
                return str(t)
        time_labels = [parse_time_label(t) for t in minute_hist["time"]]
        import pandas as pd
        close = pd.Series(minute_hist["close"].values, index=time_labels, name="Close")
        high = pd.Series(minute_hist["high"].values, index=time_labels, name="High")
        low = pd.Series(minute_hist["low"].values, index=time_labels, name="Low")
        volume = pd.Series(minute_hist["volume"].values, index=time_labels, name="Volume")
        open_p = pd.Series(minute_hist["open"].values, index=time_labels, name="Open")
        data_label = "📡 장중 5분봉 기준 (실시간)"
    else:
        data_label = "📅 전일 종가 기준"

    curr_price = float(close.iloc[-1])
    prev_price = float(close.iloc[-2])
    chg = curr_price - prev_price
    chg_pct = chg / prev_price * 100
    chg_color = CANDLE_UP if chg >= 0 else CANDLE_DOWN
    chg_arrow = "▲" if chg >= 0 else "▼"

    # KIS API로 실시간 현재가 보완 (한국 주식만)
    if KIS_AVAILABLE and is_korean:
        try:
            from broker import get_access_token, get_current_price as kis_get_price
            kis_token = get_kis_token()
            if kis_token:
                price_data = kis_get_price(raw_ticker, kis_token)
                if price_data:
                    curr_price = price_data["current"]
                    chg = price_data["change"]
                    chg_pct = price_data["change_pct"]
                    chg_color = CANDLE_UP if chg >= 0 else CANDLE_DOWN
                    chg_arrow = "▲" if chg >= 0 else "▼"
        except:
            pass

    stock_status = "buy" if chg > 0 else ("warning" if chg < 0 else "neutral")
    stock_delta_html = f"<span style='color:{chg_color};'>{chg_arrow} {chg:+,.0f}원 ({chg_pct:+.2f}%)</span> · <span style='color:{DIM};'>{data_label}</span>"
    st.markdown(
        hero_card(
            title=f"{display_name} ({raw_ticker})",
            value=f"{curr_price:,.0f}원",
            subtitle=stock_delta_html,
            status=stock_status
        ),
        unsafe_allow_html=True
    )

    # ── Quantfolio Score™ (Phase 5-1B) ──
    try:
        from score_engine import calculate_quantfolio_score
        score_result = calculate_quantfolio_score(close=close, high=high, low=low, volume=volume)
        score_sub_components = [
            ("Trend", score_result["components"]["trend"]),
            ("Momentum", score_result["components"]["momentum"]),
            ("Volume", score_result["components"]["volume"]),
            ("Risk", score_result["components"]["risk"]),
        ]
        st.markdown(
            score_card(
                score=score_result["score"],
                grade=score_result["grade"],
                status=score_result["status"],
                label=score_result["label"],
                components=score_sub_components,
                summary=score_result["summary"],
            ),
            unsafe_allow_html=True
        )
    except Exception as e:
        st.caption(f"Quantfolio Score 계산 불가 ({e})")

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
                value_html = f"<span style='font-family:JetBrains Mono; font-size:15px;'>{value}</span>"
                st.markdown(kpi_card(title=label, value=value_html), unsafe_allow_html=True)

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

        def _tech_status(c):
            if c in (CANDLE_UP, "#22c55e"):
                return "buy"
            elif c in (CANDLE_DOWN, "#ef4444"):
                return "warning"
            else:
                return "neutral"

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
                value_html = f"<span style='color:{color}; font-size:15px; font-weight:600;'>{value}</span>"
                st.markdown(kpi_card(title=label, value=value_html, delta=sub, status=_tech_status(color)), unsafe_allow_html=True)

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

        # ── AI 기술적 종합 판단 (자동 생성) ──
        try:
            openai_key = st.secrets.get("OPENAI_API_KEY", "")
            if openai_key:
                with st.spinner("AI 기술적 분석 중..."):
                    tech_prompt = f"""당신은 증권사 기술적 분석 전문 애널리스트입니다.
아래 기술적 지표를 바탕으로 {display_name}({raw_ticker})의 단기 기술적 판단을 내려주세요.

[기술적 지표]
- 현재가: {curr_price:,.0f}원
- RSI(14): {rsi_val:.1f} — {rsi_label}
- 추세: {trend}
- 볼린저밴드: {bb_label} (위치: {bb_pct:.0f}%)
- 52주 위치: {pos_52:.1f}% (고가: {high_52:,.0f}원 / 저가: {low_52:,.0f}원)
- 거래량: {vol_label}
- 지지선: {support:,.0f}원 / 저항선: {resistance:,.0f}원
- 종합 점수: {score}/6 ({diagnosis})

[출력 형식 — 반드시 아래 형식 그대로]

【기술적 판단】 매수 / 중립 / 매도 중 하나만

【한줄 요약】
(현재 차트 상황을 1문장으로 — 핵심 지표 2개 이상 언급)

【매수 관점】
- (강점 1)
- (강점 2)

【주의 관점】
- (리스크 1)
- (리스크 2)

【단기 행동 가이드】
- 매수 타이밍: (언제 어떤 조건에서 매수할지)
- 목표 구간: (단기 목표가 또는 저항선 기준)
- 손절 기준: (어떤 조건에서 손절할지)

⚠️ 기술적 분석은 참고용이며 투자 책임은 본인에게 있습니다."""

                    ai_res = requests.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={"Content-Type": "application/json", "Authorization": f"Bearer {openai_key}"},
                        json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": tech_prompt}], "max_tokens": 600}
                    )
                    tech_opinion = ai_res.json()["choices"][0]["message"]["content"]
                    st.markdown(ai_insight_card(title="AI Technical Insight", content=f"<div style='white-space:pre-line;'>{tech_opinion}</div>", confidence=None, status="neutral"), unsafe_allow_html=True)
        except Exception as e:
            pass

    except Exception as e:
        st.info(f"기술적 분석 실패: {e}")

    st.markdown("---")

    # ══════════════════════════════════════════
    # 🎯 변동성 돌파 목표가
    # ══════════════════════════════════════════
    card("🎯 변동성 돌파 목표가", "전일 변동폭 기준 오늘 돌파 기준가 자동 계산")

    st.markdown(f"""
    <div style='background:{SURFACE_1}; border-left:4px solid {ACCENT}; border-radius:0 8px 8px 0; padding:14px 18px; margin-bottom:16px; font-size:13px; line-height:1.8; color:{TEXT};'>
        <b>💡 변동성 돌파 전략이란?</b><br>
        어제 주가가 크게 움직였으면 오늘도 비슷하게 움직일 가능성이 높아요.<br>
        오늘 시장이 열리면 주가를 지켜보다가, <b>돌파 기준가를 넘어서는 순간 매수</b>하고 <b>당일 종가에 매도</b>하는 단타 전략이에요.<br><br>
        <b>계산법:</b> 오늘 시가 + (전일 고가 - 전일 저가) × K값<br>
        <b>K값이 낮을수록</b> 기준가가 낮아서 자주 돌파되고, <b>K값이 높을수록</b> 확실할 때만 진입해요.
    </div>
    """, unsafe_allow_html=True)

    try:
        today_open = float(open_p.iloc[-1])
        prev_high = float(high.iloc[-2])
        prev_low = float(low.iloc[-2])
        prev_close = float(close.iloc[-2])
        prev_range = prev_high - prev_low

        vb_targets = {}
        for k in [0.3, 0.4, 0.5, 0.6]:
            vb_targets[k] = today_open + prev_range * k

        # 현재가가 어떤 K값을 돌파했는지
        breached = [k for k, t in vb_targets.items() if curr_price >= t]
        not_breached = [k for k, t in vb_targets.items() if curr_price < t]

        # 안내 배너
        if breached:
            next_k = not_breached[0] if not_breached else None
            st.markdown(f"""
            <div style='background:#22c55e15; border:1px solid #22c55e40; border-radius:10px; padding:16px 18px; margin-bottom:14px;'>
                <div style='font-size:13px; color:#22c55e; font-weight:700; margin-bottom:6px;'>✅ 돌파 성공 — 단타 진입 신호!</div>
                <div style='font-size:13px; color:{TEXT}; margin-bottom:4px;'>
                    현재가 <b>{curr_price:,.0f}원</b>이 K={max(breached)} 기준가 <b>{vb_targets[max(breached)]:,.0f}원</b>을 넘었어요.
                </div>
                <div style='font-size:12px; color:{DIM}; margin-top:6px;'>
                    📌 지금 매수 후 오늘 장 마감 전(15:20~15:30)에 매도하는 전략을 고려해보세요.
                </div>
                {f"<div style='font-size:12px; color:{DIM}; margin-top:4px;'>다음 목표가(저항): K={next_k} 기준가 {vb_targets[next_k]:,.0f}원</div>" if next_k else ""}
            </div>
            """, unsafe_allow_html=True)
        else:
            nearest_k = min(not_breached)
            nearest_target = vb_targets[nearest_k]
            gap_pct = (nearest_target - curr_price) / curr_price * 100
            st.markdown(f"""
            <div style='background:#f59e0b15; border:1px solid #f59e0b40; border-radius:10px; padding:16px 18px; margin-bottom:14px;'>
                <div style='font-size:13px; color:#f59e0b; font-weight:700; margin-bottom:6px;'>⏳ 아직 대기 중 — 돌파 전</div>
                <div style='font-size:13px; color:{TEXT}; margin-bottom:4px;'>
                    가장 가까운 돌파 기준가는 K={nearest_k}일 때 <b>{nearest_target:,.0f}원</b>이에요.
                </div>
                <div style='font-size:12px; color:{DIM}; margin-top:6px;'>
                    📌 현재가({curr_price:,.0f}원)에서 <b>+{gap_pct:.2f}%</b>만 더 오르면 단타 진입 신호가 발생해요.<br>
                    장중에 이 가격을 돌파하는지 지켜보세요!
                </div>
            </div>
            """, unsafe_allow_html=True)

        k_desc = {0.3: "보수적 진입", 0.4: "안정적 진입", 0.5: "표준 진입", 0.6: "확실한 진입"}
        k_cols = st.columns(4)
        for i, (k, target) in enumerate(vb_targets.items()):
            is_breached = curr_price >= target
            gap = (target - curr_price) / curr_price * 100
            color = "#22c55e" if is_breached else "#6b7280"
            bg = "#22c55e15" if is_breached else SURFACE_2
            border = "#22c55e40" if is_breached else LINE
            with k_cols[i]:
                st.markdown(f"""
                <div style='background:{bg}; border:0.5px solid {border}; border-radius:10px; padding:12px; text-align:center;'>
                    <div style='font-size:10px; color:{DIM}; margin-bottom:2px;'>{k_desc[k]}</div>
                    <div style='font-size:11px; color:{DIM}; margin-bottom:4px;'>K = {k}</div>
                    <div style='font-size:16px; font-weight:700; font-family:JetBrains Mono; color:{color};'>{target:,.0f}원</div>
                    <div style='font-size:11px; color:{color}; margin-top:4px;'>{'✅ 돌파 완료!' if is_breached else f'현재가 대비 +{gap:.2f}%'}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style='background:{SURFACE_1}; border-radius:8px; padding:10px 16px; margin-top:10px; font-size:12px; color:{DIM}; line-height:1.7;'>
            💡 <b>어떤 K값을 써야 할까요?</b> 처음이라면 <b>K=0.5(표준)</b>를 추천해요.
            K값이 낮을수록 진입 기회가 많지만 가짜 신호도 많고, 높을수록 신호는 적지만 신뢰도가 높아요.
        </div>
        """, unsafe_allow_html=True)

        # 전일 데이터 요약
        st.markdown(f"""
        <div style='background:{SURFACE_2}; border:0.5px solid {LINE}; border-radius:8px; padding:12px 16px; margin-top:10px; display:flex; gap:24px;'>
            <span style='font-size:12px; color:{DIM};'>오늘 시가 <b style='color:{TEXT};'>{today_open:,.0f}원</b></span>
            <span style='font-size:12px; color:{DIM};'>전일 고가 <b style='color:{TEXT};'>{prev_high:,.0f}원</b></span>
            <span style='font-size:12px; color:{DIM};'>전일 저가 <b style='color:{TEXT};'>{prev_low:,.0f}원</b></span>
            <span style='font-size:12px; color:{DIM};'>전일 변동폭 <b style='color:{TEXT};'>{prev_range:,.0f}원</b></span>
        </div>
        """, unsafe_allow_html=True)

    except Exception as e:
        st.info(f"변동성 돌파 계산 실패: {e}")

    st.markdown("---")

    # ══════════════════════════════════════════
    # ✅ 단타 체크리스트
    # ══════════════════════════════════════════
    card("✅ 단타 체크리스트", "조건 충족 여부 자동 점검 · 진입 추천 / 보류 / 위험 판단")

    try:
        checks = [
            {
                "name": "거래량 모멘텀",
                "pass": vol_ratio >= 1.3,
                "detail": f"오늘 거래량 평균 대비 {vol_ratio:.1f}배 {'✓ 활발' if vol_ratio >= 1.3 else '✗ 부족'}",
                "why": "단타는 거래량이 살아있어야 빠른 매도가 가능해요"
            },
            {
                "name": "RSI 진입 구간",
                "pass": 30 <= rsi_val <= 60,
                "detail": f"RSI {rsi_val:.1f} — {'✓ 진입 가능 구간 (30~60)' if 30 <= rsi_val <= 60 else ('✗ 과매수 (60 초과), 고점 매수 위험' if rsi_val > 60 else '✗ 과매도 (30 미만), 추가 하락 가능')}",
                "why": "RSI 30~60이 단타 진입 최적 구간이에요"
            },
            {
                "name": "볼린저밴드 위치",
                "pass": bb_pct <= 70,
                "detail": f"밴드 위치 {bb_pct:.0f}% — {'✓ 적정 구간' if bb_pct <= 70 else '✗ 상단 과열 (70% 초과), 눌림 가능성'}",
                "why": "밴드 상단(70% 이상)은 단기 과열 구간이라 단타 진입 시 리스크가 높아요"
            },
            {
                "name": "추세 방향",
                "pass": "상승" in trend,
                "detail": f"{trend} — {'✓ 추세 방향 유리' if '상승' in trend else '✗ 역추세 단타, 리스크 높음'}",
                "why": "추세를 따라가는 단타가 역추세보다 성공률이 높아요"
            },
            {
                "name": "52주 위치",
                "pass": pos_52 <= 85,
                "detail": f"52주 위치 {pos_52:.1f}% — {'✓ 신고가 부담 없음' if pos_52 <= 85 else '✗ 신고가 근접 (85% 초과), 차익실현 매물 주의'}",
                "why": "52주 신고가 근처는 차익실현 매물이 많아 단타 목표가 달성이 어려워요"
            },
            {
                "name": "기술적 종합 점수",
                "pass": score >= 4,
                "detail": f"종합 {score}/6점 — {'✓ 진입 적합' if score >= 4 else '✗ 진입 조건 부족'}",
                "why": "6개 지표 중 4개 이상 충족해야 단타 성공률이 높아요"
            },
        ]

        passed = sum(1 for c in checks if c["pass"])
        total = len(checks)

        if passed >= 5:
            verdict = "진입 추천"
            verdict_color = "#22c55e"
            verdict_bg = "#22c55e15"
            verdict_border = "#22c55e40"
            verdict_icon = "🟢"
            verdict_desc = "대부분의 단타 조건을 충족했어요. 계산기에서 수익/손실 배율 확인 후 진입하세요."
        elif passed >= 4:
            verdict = "조건부 진입"
            verdict_color = "#f59e0b"
            verdict_bg = "#f59e0b15"
            verdict_border = "#f59e0b40"
            verdict_icon = "🟡"
            verdict_desc = "일부 조건이 미충족이에요. 미충족 항목을 확인하고 리스크를 인지한 후 진입하세요."
        elif passed >= 3:
            verdict = "보류 권장"
            verdict_color = "#f59e0b"
            verdict_bg = "#f59e0b10"
            verdict_border = "#f59e0b30"
            verdict_icon = "🟠"
            verdict_desc = "절반 이상의 조건이 미충족이에요. 더 좋은 타이밍을 기다리는 게 유리해요."
        else:
            verdict = "진입 위험"
            verdict_color = "#ef4444"
            verdict_bg = "#ef444415"
            verdict_border = "#ef444440"
            verdict_icon = "🔴"
            verdict_desc = "대부분의 단타 조건을 충족하지 못했어요. 이 종목은 오늘 단타를 피하세요."

        # 종합 판단 배너
        verdict_status_map = {
            "진입 추천": "buy",
            "조건부 진입": "neutral",
            "보류 권장": "warning",
            "진입 위험": "risk",
        }
        verdict_value_html = f"<span style='color:{verdict_color}; font-size:20px;'>{verdict_icon} {verdict}</span>"
        st.markdown(
            hero_card(
                title=f"단타 종합 판단 ({passed}/{total} 충족)",
                value=verdict_value_html,
                subtitle=verdict_desc,
                status=verdict_status_map.get(verdict, "neutral")
            ),
            unsafe_allow_html=True
        )

        # 체크리스트 항목
        for i in range(0, len(checks), 2):
            cols = st.columns(2)
            for j, col in enumerate(cols):
                if i + j < len(checks):
                    c = checks[i + j]
                    c_color = "#22c55e" if c["pass"] else "#ef4444"
                    c_bg = "#22c55e10" if c["pass"] else "#ef444410"
                    c_border = "#22c55e30" if c["pass"] else "#ef444430"
                    c_icon = "✅" if c["pass"] else "❌"
                    c_status = "buy" if c["pass"] else "warning"
                    with col:
                        st.markdown(f"""
                        <div style='background:{c_bg}; border:0.5px solid {c_border}; border-radius:10px; padding:12px; margin-bottom:8px;'>
                            <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;'>
                                <span style='font-size:12px; font-weight:600; color:{c_color};'>{c_icon} {c["name"]}</span>
                                {status_badge(c_status)}
                            </div>
                            <div style='font-size:12px; color:{DIM}; margin-bottom:4px;'>{c["detail"]}</div>
                            <div style='font-size:11px; color:#6b7280; border-top:0.5px solid {c_border}; padding-top:6px; margin-top:6px;'>💡 {c["why"]}</div>
                        </div>
                        """, unsafe_allow_html=True)

    except Exception as e:
        st.info(f"체크리스트 생성 실패: {e}")

    st.markdown("---")

    # ══════════════════════════════════════════
    # 💰 단타 매매 계산기
    # ══════════════════════════════════════════
    card("💰 단타 매매 계산기", "기술적 분석 기반 지지선/저항선 자동 적용 · 수수료 포함 세후 수익/손실")

    import streamlit.components.v1 as components
    calc_html = f"""
    <style>
      * {{ box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
      body {{ background: transparent; margin: 0; padding: 0; color: #e2e8f0; }}
      .grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px; }}
      .grid3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-bottom: 14px; }}
      label {{ font-size: 11px; color: #9ca3af; display: block; margin-bottom: 4px; }}
      input {{ width: 100%; padding: 8px 10px; background: #1e2330; border: 0.5px solid #2d3748; border-radius: 8px; color: #e2e8f0; font-size: 13px; font-family: 'JetBrains Mono', monospace; }}
      input:focus {{ outline: none; border-color: #6366f1; }}
      .card {{ background: #13161f; border: 0.5px solid #1e2330; border-radius: 10px; padding: 14px; text-align: center; }}
      .card .label {{ font-size: 11px; color: #9ca3af; margin-bottom: 4px; }}
      .card .value {{ font-size: 20px; font-weight: 700; font-family: 'JetBrains Mono', monospace; }}
      .card .sub {{ font-size: 11px; color: #9ca3af; margin-top: 4px; }}
      .profit {{ background: #22c55e15; border: 1px solid #22c55e40; border-radius: 12px; padding: 14px; }}
      .loss {{ background: #ef444415; border: 1px solid #ef444440; border-radius: 12px; padding: 14px; }}
      .row {{ display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 6px; }}
      .row .k {{ color: #9ca3af; }}
      .row .v {{ color: #e2e8f0; }}
      .divider {{ border-top: 0.5px solid rgba(255,255,255,0.1); margin: 8px 0; padding-top: 8px; display: flex; justify-content: space-between; }}
      .section-title {{ font-size: 12px; font-weight: 600; margin-bottom: 10px; }}
    </style>

    <div class="grid3">
      <div>
        <label>매수가 (원)</label>
        <input type="number" id="buy_price" value="{int(curr_price)}" step="100" oninput="calc()">
      </div>
      <div>
        <label>목표가 (원)</label>
        <input type="number" id="target" value="{int(resistance)}" step="100" oninput="calc()">
      </div>
      <div>
        <label>손절가 (원)</label>
        <input type="number" id="stop" value="{int(support)}" step="100" oninput="calc()">
      </div>
    </div>

    <div class="grid3">
      <div>
        <label>투입금액 (만원)</label>
        <input type="number" id="invest" value="1000" step="100" oninput="calc()">
      </div>
      <div>
        <label>매수 수수료 (%)</label>
        <input type="number" id="buy_fee" value="0.015" step="0.001" oninput="calc()">
      </div>
      <div>
        <label>매도 수수료+세금 (%)</label>
        <input type="number" id="sell_fee" value="0.265" step="0.001" oninput="calc()">
      </div>
    </div>

    <div class="grid3" id="summary_cards"></div>

    <div class="grid2" id="result_cards" style="margin-top: 4px;"></div>

    <script>
    function fmt(n) {{ return Math.round(n).toLocaleString('ko-KR'); }}
    function fmtP(n) {{ return parseFloat(n).toFixed(2); }}

    function calc() {{
      const buy = parseFloat(document.getElementById('buy_price').value) || 0;
      const invest_man = parseFloat(document.getElementById('invest').value) || 0;
      const target = parseFloat(document.getElementById('target').value) || 0;
      const stop = parseFloat(document.getElementById('stop').value) || 0;
      const buy_fee_pct = parseFloat(document.getElementById('buy_fee').value) || 0;
      const sell_fee_pct = parseFloat(document.getElementById('sell_fee').value) || 0;

      if (!buy || !invest_man) return;

      const invest = invest_man * 10000;
      const qty = Math.floor(invest / (buy * (1 + buy_fee_pct / 100)));
      const actual_buy = qty * buy;
      const buy_fee_won = actual_buy * buy_fee_pct / 100;
      const total_cost = actual_buy + buy_fee_won;
      const bep = buy * (1 + buy_fee_pct / 100) / (1 - sell_fee_pct / 100);

      const target_sell = qty * target;
      const target_fee = target_sell * sell_fee_pct / 100;
      const target_net = target_sell - target_fee - total_cost;
      const target_pct = (target - buy) / buy * 100;
      const target_net_pct = target_net / total_cost * 100;

      const stop_sell = qty * stop;
      const stop_fee = stop_sell * sell_fee_pct / 100;
      const stop_net = stop_sell - stop_fee - total_cost;
      const stop_pct = (stop - buy) / buy * 100;
      const stop_net_pct = stop_net / total_cost * 100;

      const rr = stop_net !== 0 ? Math.abs(target_net / stop_net) : 0;
      const rr_color = rr >= 2 ? '#22c55e' : rr >= 1.5 ? '#f59e0b' : '#ef4444';
      const rr_bg = rr >= 2 ? '#22c55e15' : rr >= 1.5 ? '#f59e0b15' : '#ef444415';
      const rr_border = rr >= 2 ? '#22c55e40' : rr >= 1.5 ? '#f59e0b40' : '#ef444440';
      const rr_label = rr >= 2 ? '✅ 양호 (2.0 이상)' : rr >= 1.5 ? '⚠️ 보통 (1.5~2.0)' : '❌ 불량 (1.5 미만)';

      document.getElementById('summary_cards').innerHTML = `
        <div class="card">
          <div class="label">매수 수량</div>
          <div class="value">${{fmt(qty)}}주</div>
          <div class="sub">실투입 ${{fmt(total_cost/10000)}}만원</div>
        </div>
        <div class="card">
          <div class="label">손익분기점</div>
          <div class="value">${{fmt(bep)}}원</div>
          <div class="sub">수수료 포함 실제 BEP</div>
        </div>
        <div class="card" style="background:${{rr_bg}}; border: 1px solid ${{rr_border}};">
          <div class="label" style="color:${{rr_color}};">수익/손실 배율</div>
          <div class="value" style="color:${{rr_color}};">손절 1 → 수익 ${{fmtP(rr)}}</div>
          <div class="sub" style="color:${{rr_color}};">${{rr_label}}</div>
        </div>
      `;

      document.getElementById('result_cards').innerHTML = `
        <div class="profit">
          <div class="section-title" style="color:#22c55e;">🎯 목표가 도달 시</div>
          <div class="row"><span class="k">목표가</span><span class="v">${{fmt(target)}}원 (+${{fmtP(target_pct)}}%)</span></div>
          <div class="row"><span class="k">매도 수수료+세금</span><span style="color:#ef4444;">-${{fmt(target_fee)}}원</span></div>
          <div class="row"><span class="k">매도 총액</span><span class="v">${{fmt(target_sell)}}원</span></div>
          <div class="divider">
            <span style="font-weight:600; font-size:13px;">세후 순수익</span>
            <span style="color:#22c55e; font-weight:700; font-size:15px; font-family:'JetBrains Mono',monospace;">+${{fmt(target_net)}}원 (+${{fmtP(target_net_pct)}}%)</span>
          </div>
        </div>
        <div class="loss">
          <div class="section-title" style="color:#ef4444;">🛑 손절가 도달 시</div>
          <div class="row"><span class="k">손절가</span><span class="v">${{fmt(stop)}}원 (${{fmtP(stop_pct)}}%)</span></div>
          <div class="row"><span class="k">매도 수수료+세금</span><span style="color:#ef4444;">-${{fmt(stop_fee)}}원</span></div>
          <div class="row"><span class="k">매도 총액</span><span class="v">${{fmt(stop_sell)}}원</span></div>
          <div class="divider">
            <span style="font-weight:600; font-size:13px;">세후 손실</span>
            <span style="color:#ef4444; font-weight:700; font-size:15px; font-family:'JetBrains Mono',monospace;">${{fmt(stop_net)}}원 (${{fmtP(stop_net_pct)}}%)</span>
          </div>
        </div>
      `;

      // 매도 전략 3단계
      const s1 = Math.round(buy * 1.03);
      const s2 = Math.round(buy * 1.05);
      const s3 = target || Math.round(buy * 1.08);
      const auto_stop = Math.round(buy * 0.97);

      const s1_pnl = ((s1 - buy) * qty * (1 - sell_fee_pct/100) - buy_fee_won).toFixed(0);
      const s2_pnl = ((s2 - buy) * qty * (1 - sell_fee_pct/100) - buy_fee_won).toFixed(0);
      const s3_pnl = ((s3 - buy) * qty * (1 - sell_fee_pct/100) - buy_fee_won).toFixed(0);

      document.getElementById('sell_strategy').innerHTML = `
        <div style='background:#13161f; border:0.5px solid #2d3748; border-radius:12px; padding:16px; margin-top:12px;'>
          <div style='font-size:12px; font-weight:700; color:#e2e8f0; margin-bottom:12px;'>📋 AI 추천 분할 매도 전략</div>
          <div style='display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin-bottom:10px;'>
            <div style='background:#22c55e15; border:0.5px solid #22c55e40; border-radius:8px; padding:10px; text-align:center;'>
              <div style='font-size:10px; color:#22c55e; margin-bottom:4px;'>1단계 (+3%)</div>
              <div style='font-size:14px; font-weight:700; color:#22c55e; font-family:JetBrains Mono;'>${{fmt(s1)}}원</div>
              <div style='font-size:10px; color:#9ca3af; margin-top:4px;'>30% 매도</div>
              <div style='font-size:11px; color:#22c55e; margin-top:2px;'>+${{fmt(Math.round(s1_pnl * 0.3))}}원</div>
            </div>
            <div style='background:#22c55e15; border:0.5px solid #22c55e40; border-radius:8px; padding:10px; text-align:center;'>
              <div style='font-size:10px; color:#22c55e; margin-bottom:4px;'>2단계 (+5%)</div>
              <div style='font-size:14px; font-weight:700; color:#22c55e; font-family:JetBrains Mono;'>${{fmt(s2)}}원</div>
              <div style='font-size:10px; color:#9ca3af; margin-top:4px;'>50% 매도</div>
              <div style='font-size:11px; color:#22c55e; margin-top:2px;'>+${{fmt(Math.round(s2_pnl * 0.5))}}원</div>
            </div>
            <div style='background:#6366f115; border:0.5px solid #6366f140; border-radius:8px; padding:10px; text-align:center;'>
              <div style='font-size:10px; color:#818cf8; margin-bottom:4px;'>3단계 (목표가)</div>
              <div style='font-size:14px; font-weight:700; color:#818cf8; font-family:JetBrains Mono;'>${{fmt(s3)}}원</div>
              <div style='font-size:10px; color:#9ca3af; margin-top:4px;'>잔여 전량</div>
              <div style='font-size:11px; color:#818cf8; margin-top:2px;'>+${{fmt(Math.round(s3_pnl * 0.2))}}원</div>
            </div>
          </div>
          <div style='display:flex; gap:8px;'>
            <div style='flex:1; background:#ef444415; border:0.5px solid #ef444440; border-radius:8px; padding:10px; text-align:center;'>
              <div style='font-size:10px; color:#ef4444; margin-bottom:4px;'>🛑 자동 손절 (-3%)</div>
              <div style='font-size:14px; font-weight:700; color:#ef4444; font-family:JetBrains Mono;'>${{fmt(auto_stop)}}원</div>
            </div>
            <div style='flex:1; background:#ef444415; border:0.5px solid #ef444440; border-radius:8px; padding:10px; text-align:center;'>
              <div style='font-size:10px; color:#ef4444; margin-bottom:4px;'>⏰ 시간 손절</div>
              <div style='font-size:14px; font-weight:700; color:#ef4444; font-family:JetBrains Mono;'>14:30</div>
            </div>
          </div>
        </div>
      `;
    }}
    calc();
    </script>
    """
    components.html(calc_html, height=520, scrolling=False)

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

                    # 누적 계산은 30일치 전체 데이터를 유지하되, 차트용 데이터만 최근 5영업일(일주일)로 슬라이싱
                    dates_chart = dates_fmt[-10:]
                    frgn_chart = frgn_vals[-10:]
                    orgn_chart = orgn_vals[-10:]

                    fig_sup = go.Figure()
                    
                    # 외국인 바 (고정 레드)
                    fig_sup.add_trace(go.Bar(
                        x=dates_chart, y=frgn_chart, name="외국인",
                        marker_color="#ef4444",
                        opacity=0.85,
                        hovertemplate="<b>%{x} 외국인</b><br>%{y:,.1f}억원<extra></extra>"
                    ))
                    
                    # 기관 바 (고정 파랑)
                    fig_sup.add_trace(go.Bar(
                        x=dates_chart, y=orgn_chart, name="기관",
                        marker_color="#190be3",
                        opacity=0.85,
                        hovertemplate="<b>%{x} 기관</b><br>%{y:,.1f}억원<extra></extra>"
                    ))
                    
                    fig_sup.add_hline(y=0, line=dict(color=DIM, width=1, dash="dot"))
                    fig_sup.update_layout(
                        barmode="group", 
                        bargap=0.35,       # 5일만 표현하므로 그룹 간 간격을 널찍하게 확보
                        bargroupgap=0.08,   # 외국인/기관 막대 사이의 간격
                        height=300,
                        paper_bgcolor="rgba(0,0,0,0)", 
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color=TEXT, size=11), 
                        margin=dict(l=0, r=0, t=30, b=20),
                        legend=dict(orientation="h", y=1.12),
                        yaxis=dict(gridcolor=LINE, tickformat=",", ticksuffix="억"),
                        xaxis=dict(gridcolor=LINE)
                    )
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
        st.session_state["ai_opinion_requested"] = True

    if st.session_state.get("ai_opinion_requested") and not st.session_state.get("ai_opinion"):
        st.session_state["ai_opinion_requested"] = False
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
        st.markdown(ai_insight_card(title="AI Investment Opinion", content=f"<div style='white-space:pre-line;'>{opinion_text}</div>", confidence=None, status="neutral"), unsafe_allow_html=True)