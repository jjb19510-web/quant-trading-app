import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import datetime as dt
import json
import os
import requests

from strategies import calculate_mdd, calculate_sharpe, calculate_cagr, run_strategy
from optimization import optimize_parameters, walk_forward_test
from ui_components import (
    apply_custom_css, card, render_kpi_strip, render_strategy_expander,
    render_summary_cards, color_val,
    ACCENT, RED, GREEN, CANDLE_UP, CANDLE_DOWN,
    DIM, TEXT, SURFACE_1, SURFACE_2, LINE, BG
)
from charts import (
    make_candlestick_fig, make_return_chart,
    make_drawdown_chart, make_monthly_bar_chart, make_pie_chart
)
from data_utils import (
    load_watchlist, save_watchlist, load_notes, save_notes,
    load_sectors, save_sectors, load_backtest, save_backtest,
    init_session_state
)
from dashboard import render_dashboard
from portfolio import render_portfolio

try:
    from broker import get_access_token, get_current_price as kis_get_price, get_balance, buy_order, sell_order
    KIS_AVAILABLE = True
except:
    KIS_AVAILABLE = False

st.set_page_config(page_title="Quantfolio", page_icon="📈", layout="wide")
apply_custom_css()

end_date = pd.to_datetime("today").date()
start_date = (pd.to_datetime("today") - pd.DateOffset(years=1)).date()

init_session_state()

@st.cache_data(ttl=86400)
def get_krx_name_map():
    try:
        import FinanceDataReader as fdr
        df = fdr.StockListing('KRX')
        code_col = next((c for c in ['Symbol', 'Code'] if c in df.columns), None)
        name_col = next((c for c in ['Name'] if c in df.columns), None)
        if code_col and name_col:
            return dict(zip(df[code_col].astype(str).str.split('.').str[0].str.zfill(6), df[name_col]))
    except:
        pass
    return {}

# ── [고성능 캐싱 기반 듀얼 주가 수집 엔진] ──
@st.cache_data(ttl=600) # 10분간 메모리에 주가를 보관하여 중복 호출 및 서버 차단 원천 해결
def load_market_data(tickers, start_date, end_date, market):
    try:
        ohlc = yf.download(tickers, start=str(start_date), end=str(end_date), progress=False)
        df = ohlc["Close"] if isinstance(ohlc, pd.DataFrame) and "Close" in ohlc else pd.DataFrame()
    except:
        df = pd.DataFrame()
        ohlc = pd.DataFrame()

    if (df.empty or df.isna().all().all()) and market == "한국주식 (KS)":
        try:
            import FinanceDataReader as fdr
            # .KS와 .KQ 확장자를 모두 호환하여 공백 처리
            clean_tickers = [t.replace(".KS", "").replace(".KQ", "") for t in tickers]
            if len(clean_tickers) == 1:
                df_fdr = fdr.DataReader(clean_tickers[0], start_date, end_date)
                if not df_fdr.empty:
                    df = pd.DataFrame({tickers[0]: df_fdr["Close"]})
                    open_p = df_fdr["Open"]
                    high_p = df_fdr["High"]
                    low_p = df_fdr["Low"]
                    close_p = df_fdr["Close"]
                    volume = df_fdr["Volume"]
                    return df, open_p, high_p, low_p, close_p, volume
            else:
                dfs = []
                for ct, t in zip(clean_tickers, tickers):
                    temp_df = fdr.DataReader(ct, start_date, end_date)[["Close"]]
                    temp_df.columns = [t]
                    dfs.append(temp_df)
                df = pd.concat(dfs, axis=1).dropna()
                chart_col = df.columns[0]
                chart_raw = chart_col.replace(".KS", "")
                df_fdr_single = fdr.DataReader(chart_raw, start_date, end_date)
                open_p = df_fdr_single["Open"]
                high_p = df_fdr_single["High"]
                low_p = df_fdr_single["Low"]
                close_p = df_fdr_single["Close"]
                volume = df_fdr_single["Volume"]
                return df, open_p, high_p, low_p, close_p, volume
        except:
            pass

    if not df.empty:
        df.columns = [str(c) for c in df.columns]
        chart_col = df.columns[0]
        if len(tickers) == 1:
            open_p = ohlc["Open"].squeeze() if "Open" in ohlc else pd.Series()
            high_p = ohlc["High"].squeeze() if "High" in ohlc else pd.Series()
            low_p = ohlc["Low"].squeeze() if "Low" in ohlc else pd.Series()
            close_p = ohlc["Close"].squeeze() if "Close" in ohlc else pd.Series()
            volume = ohlc["Volume"].squeeze() if "Volume" in ohlc else pd.Series()
        else:
            open_p = ohlc["Open"][chart_col] if isinstance(ohlc["Open"], pd.DataFrame) else ohlc["Open"]
            high_p = ohlc["High"][chart_col] if isinstance(ohlc["High"], pd.DataFrame) else ohlc["High"]
            low_p = ohlc["Low"][chart_col] if isinstance(ohlc["Low"], pd.DataFrame) else ohlc["Low"]
            close_p = df[chart_col]
            volume = ohlc["Volume"][chart_col] if isinstance(ohlc["Volume"], pd.DataFrame) else ohlc["Volume"]
        return df, open_p, high_p, low_p, close_p, volume

    return pd.DataFrame(), pd.Series(), pd.Series(), pd.Series(), pd.Series(), pd.Series()


# ── [고성능 캐싱 기반 듀얼 주가 수집 엔진] ──
@st.cache_data(ttl=600) # 10분간 메모리에 주가를 보관하여 중복 호출 및 서버 차단 원천 해결
def load_market_data(tickers, start_date, end_date, market):
    try:
        ohlc = yf.download(tickers, start=str(start_date), end=str(end_date), progress=False)
        df = ohlc["Close"] if isinstance(ohlc, pd.DataFrame) and "Close" in ohlc else pd.DataFrame()
    except:
        df = pd.DataFrame()
        ohlc = pd.DataFrame()

    if (df.empty or df.isna().all().all()) and market == "한국주식 (KS)":
        try:
            import FinanceDataReader as fdr
            clean_tickers = [t.replace(".KS", "") for t in tickers]
            if len(clean_tickers) == 1:
                df_fdr = fdr.DataReader(clean_tickers[0], start_date, end_date)
                if not df_fdr.empty:
                    df = pd.DataFrame({tickers[0]: df_fdr["Close"]})
                    open_p = df_fdr["Open"]
                    high_p = df_fdr["High"]
                    low_p = df_fdr["Low"]
                    close_p = df_fdr["Close"]
                    volume = df_fdr["Volume"]
                    return df, open_p, high_p, low_p, close_p, volume
            else:
                dfs = []
                for ct, t in zip(clean_tickers, tickers):
                    temp_df = fdr.DataReader(ct, start_date, end_date)[["Close"]]
                    temp_df.columns = [t]
                    dfs.append(temp_df)
                df = pd.concat(dfs, axis=1).dropna()
                chart_col = df.columns[0]
                chart_raw = chart_col.replace(".KS", "")
                df_fdr_single = fdr.DataReader(chart_raw, start_date, end_date)
                open_p = df_fdr_single["Open"]
                high_p = df_fdr_single["High"]
                low_p = df_fdr_single["Low"]
                close_p = df_fdr_single["Close"]
                volume = df_fdr_single["Volume"]
                return df, open_p, high_p, low_p, close_p, volume
        except:
            pass

    if not df.empty:
        df.columns = [str(c) for c in df.columns]
        chart_col = df.columns[0]
        if len(tickers) == 1:
            open_p = ohlc["Open"].squeeze() if "Open" in ohlc else pd.Series()
            high_p = ohlc["High"].squeeze() if "High" in ohlc else pd.Series()
            low_p = ohlc["Low"].squeeze() if "Low" in ohlc else pd.Series()
            close_p = ohlc["Close"].squeeze() if "Close" in ohlc else pd.Series()
            volume = ohlc["Volume"].squeeze() if "Volume" in ohlc else pd.Series()
        else:
            open_p = ohlc["Open"][chart_col] if isinstance(ohlc["Open"], pd.DataFrame) else ohlc["Open"]
            high_p = ohlc["High"][chart_col] if isinstance(ohlc["High"], pd.DataFrame) else ohlc["High"]
            low_p = ohlc["Low"][chart_col] if isinstance(ohlc["Low"], pd.DataFrame) else ohlc["Low"]
            close_p = df[chart_col]
            volume = ohlc["Volume"][chart_col] if isinstance(ohlc["Volume"], pd.DataFrame) else ohlc["Volume"]
        return df, open_p, high_p, low_p, close_p, volume

    return pd.DataFrame(), pd.Series(), pd.Series(), pd.Series(), pd.Series(), pd.Series()


@st.cache_data(ttl=3600)
def get_kis_token():
    try:
        return get_access_token()
    except:
        return None

tab1, tab2, tab3 = st.tabs(["📊 대시보드", "🔍 분석", "💼 포트폴리오"])

with tab1:
    render_dashboard()

with tab2:
    with st.sidebar:
        st.markdown("<div style='font-size:18px; font-weight:600; margin-bottom:16px;'>⚙️ Settings</div>", unsafe_allow_html=True)

        # ── 계좌 현황 ──
        if KIS_AVAILABLE:
            with st.expander("💼 계좌 현황", expanded=True):
                kis_token = get_kis_token()
                if kis_token:
                    balance_data = get_balance(kis_token)
                    if balance_data.get("rt_cd") == "0":
                        output2 = balance_data.get("output2", [{}])[0]
                        total_eval = int(output2.get("scts_evlu_amt", 0))
                        total_profit = int(output2.get("evlu_pfls_smtl_amt", 0))
                        cash = int(output2.get("dnca_tot_amt", 0))
                        st.markdown(f"""
                        <div style='background:#0f1117; border:0.5px solid #1e2330; border-radius:12px; padding:12px 14px; margin-bottom:12px;'>
                            <div style='font-size:11px; color:#6b7280; margin-bottom:6px;'>총 평가금액</div>
                            <div style='font-size:18px; font-weight:600; font-family:JetBrains Mono;'>{total_eval:,}원</div>
                            <div style='font-size:12px; color:{"#ef4444" if total_profit >= 0 else "#3b82f6"}; margin-top:2px;'>
                                {"▲" if total_profit >= 0 else "▼"} {total_profit:+,}원
                            </div>
                            <div style='font-size:11px; color:#6b7280; margin-top:4px;'>예수금 {cash:,}원</div>
                        </div>
                        """, unsafe_allow_html=True)
                        holdings_list = balance_data.get("output1", [])
                        if holdings_list:
                            hdf = pd.DataFrame([{
                                "종목": h.get("prdt_name", ""),
                                "수량": int(h.get("hldg_qty", 0)),
                                "현재가": f"{int(h.get('prpr', 0)):,}",
                                "평균단가": f"{float(h.get('pchs_avg_pric', 0)):,.0f}",
                                "평가손익": f"{float(h.get('evlu_pfls_amt', 0)):+,.0f}"
                            } for h in holdings_list if int(h.get("hldg_qty", 0)) > 0])
                            if not hdf.empty:
                                st.dataframe(hdf, use_container_width=True, hide_index=True)

        # ── 종목 검색 ──
        with st.expander("🔍 종목 검색", expanded=True):
            market = st.selectbox("시장 선택", ["한국주식 (KS)", "미국주식 (US)"])

            if market == "한국주식 (KS)":
                st.caption("예시: 삼성전자, 에코프로, 005930")
                default_ticker = st.session_state.get("selected_ticker", "")
                tickers_raw = st.text_input("종목명 또는 코드 (쉼표로 구분)", value=default_ticker)

                tickers_list = []
                if tickers_raw.strip():
                    try:
                        df_krx = pd.read_csv("https://raw.githubusercontent.com/corazzon/finance-data-analysis/main/krx.csv")
                    except:
                        try:
                            import FinanceDataReader as fdr
                            df_krx = fdr.StockListing('KRX')
                        except:
                            df_krx = None

                    for t in tickers_raw.split(","):
                        t_clean = t.strip()
                        if not t_clean:
                            continue
                        
                        # 종목명(한글) 입력 시 코스피(.KS) / 코스닥(.KQ) 자동 분류 판별
                        if not t_clean.isdigit() and df_krx is not None:
                            matched = df_krx[df_krx['Name'].str.upper() == t_clean.upper()]
                            if not matched.empty:
                                code_col = next((c for c in ['Symbol', 'Code', 'code'] if c in df_krx.columns), None)
                                if code_col:
                                    raw_code = matched.iloc[0][code_col]
                                    code = str(raw_code).split('.')[0].zfill(6)
                                    
                                    # 시장 정보 추출 (KOSPI -> .KS, KOSDAQ/KONEX -> .KQ)
                                    mkt_info = str(matched.iloc[0].get('Market', 'KOSPI')).upper()
                                    suffix = ".KS" if "KOSPI" in mkt_info else ".KQ"
                                    tickers_list.append(code + suffix)
                                else:
                                    tickers_list.append(t_clean + ".KS")
                            else:
                                # KRX 검색 실패시 FinanceDataReader로 직접 검색
                                try:
                                    import FinanceDataReader as fdr
                                    krx_all = fdr.StockListing('KRX')
                                    name_col = next((c for c in ['Name'] if c in krx_all.columns), None)
                                    code_col2 = next((c for c in ['Symbol', 'Code'] if c in krx_all.columns), None)
                                    if name_col and code_col2:
                                        matched2 = krx_all[krx_all[name_col].str.upper() == t_clean.upper()]
                                        if not matched2.empty:
                                            raw_code2 = matched2.iloc[0][code_col2]
                                            code2 = str(raw_code2).split('.')[0].zfill(6)
                                            mkt2 = str(matched2.iloc[0].get('Market', 'KOSPI')).upper()
                                            suffix2 = ".KS" if "KOSPI" in mkt2 else ".KQ"
                                            tickers_list.append(code2 + suffix2)
                                            continue
                                except:
                                    pass
                                tickers_list.append(t_clean + ".KS")
                        else:
                            # 6자리 숫자로 입력 시 상장사 정보에서 시장 판별 후 알맞은 심볼 부착
                            code_padded = t_clean.zfill(6) if len(t_clean) < 6 else t_clean
                            if df_krx is not None:
                                code_col = next((c for c in ['Symbol', 'Code', 'code'] if c in df_krx.columns), None)
                                if code_col:
                                    try:
                                        matched_code = df_krx[df_krx[code_col].astype(str).str.split('.').str[0].str.zfill(6) == code_padded]
                                        if not matched_code.empty:
                                            mkt_info = str(matched_code.iloc[0].get('Market', 'KOSPI')).upper()
                                            suffix = ".KS" if "KOSPI" in mkt_info else ".KQ"
                                            tickers_list.append(code_padded + suffix)
                                            continue
                                    except:
                                        pass
                            tickers_list.append(code_padded + ".KS")

                tickers = tickers_list
                if tickers:
                    st.session_state["last_tickers"] = tickers
            else:
                st.caption("예시: AAPL, TSLA, NVDA")
                default_ticker = st.session_state.get("selected_ticker", "")
                tickers_raw = st.text_input("티커 입력 (쉼표로 구분)", value=default_ticker)
                tickers = [t.strip() for t in tickers_raw.split(",") if t.strip()]
                if tickers:
                    st.session_state["last_tickers"] = tickers

            if tickers_raw.strip():
                if st.button("⭐ 관심종목 추가", use_container_width=True):
                    new_items = [t.strip() for t in tickers_raw.split(",") if t.strip()]
                    for item in new_items:
                        if item not in st.session_state.watchlist:
                            st.session_state.watchlist.append(item)
                    save_watchlist(st.session_state.watchlist)
                    st.rerun()

        # ── 관심종목 ──
        if st.session_state.watchlist:
            with st.expander("⭐ 관심종목", expanded=True):
                name_map = get_krx_name_map()
                for witem in st.session_state.watchlist:
                    col_w, col_d = st.columns([4, 1])
                    with col_w:
                        display_name = name_map.get(witem, witem)
                        if st.button(f"{display_name} ({witem})", key=f"wl_{witem}", use_container_width=True):
                            st.session_state["selected_ticker"] = witem
                            st.session_state["note_ticker"] = witem
                    with col_d:
                        if st.button("✕", key=f"del_{witem}"):
                            st.session_state.watchlist.remove(witem)
                            save_watchlist(st.session_state.watchlist)
                            st.rerun()

                if "note_ticker" in st.session_state:
                    nt = st.session_state.note_ticker
                    st.markdown(f"<div style='font-size:12px; font-weight:600; margin:8px 0 4px;'>📝 {nt} 메모</div>", unsafe_allow_html=True)
                    note_text = st.text_area("", value=st.session_state.notes.get(nt, ""), height=80, key=f"note_{nt}", label_visibility="collapsed")
                    if st.button("💾 저장", key=f"save_note_{nt}", use_container_width=True):
                        st.session_state.notes[nt] = note_text
                        save_notes(st.session_state.notes)
                        st.success("저장됐어요!")

        # ── 전략 설정 ──
        with st.expander("📐 전략 설정", expanded=True):
            strategy = st.selectbox("전략 선택", [
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

        # ── 목표가 · 손절가 · 투입금액 ──
        with st.expander("🎯 목표가 · 손절가 · 투입금액", expanded=False):
            target_pct = st.number_input("목표 수익률 (%)", min_value=1, max_value=200, value=20, step=5)
            stop_pct = st.number_input("손절 라인 (%)", min_value=1, max_value=50, value=10, step=1)
            investment = st.number_input("투입금액 (만원)", min_value=0, value=1000, step=100)
            st.caption(f"= {investment:,}만원 ({investment * 10000:,}원)")

        # ── 섹터 관리 ──
        with st.expander("📂 섹터 관리", expanded=False):
            sector_name = st.text_input("섹터 이름", placeholder="예: 반도체", key="sector_name_input")
            sector_tickers_input = st.text_input("종목 코드 (쉼표로 구분)", placeholder="예: 005930, 000660", key="sector_tickers_input")
            if st.button("➕ 섹터 추가", use_container_width=True):
                if sector_name and sector_tickers_input:
                    tickers_list = [t.strip() for t in sector_tickers_input.split(",") if t.strip()]
                    st.session_state.sectors[sector_name] = tickers_list
                    save_sectors(st.session_state.sectors)
                    st.success(f"{sector_name} 섹터 저장됐어요!")
            if st.session_state.sectors:
                for sname in list(st.session_state.sectors.keys()):
                    col_s, col_sd = st.columns([4, 1])
                    with col_s:
                        st.caption(f"📁 {sname}: {', '.join(st.session_state.sectors[sname])}")
                    with col_sd:
                        if st.button("✕", key=f"del_sector_{sname}"):
                            del st.session_state.sectors[sname]
                            save_sectors(st.session_state.sectors)
                            st.rerun()

        st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
        analyze = st.button("🔍 분석 시작", use_container_width=True)
        optimize = st.button("⚡ 최적값 자동 탐색", use_container_width=True)
        wf_test = st.button("🔄 워크포워드 테스트", use_container_width=True)

    # ── [전략 분석 공통 연산 영역] (서브탭 분할을 위한 최적 계산부) ──
    if analyze:
        st.session_state["analyzed"] = True

    if 'tickers' in locals() and tickers:
        st.session_state["last_tickers"] = tickers
    tickers = st.session_state.get("last_tickers", [])
    analyzed = st.session_state.get("analyzed") and bool(tickers)

    if analyzed:
        with st.spinner("데이터 분석 준비 중..."):
            # .KS 실패시 .KQ로 자동 재시도
            ohlc = yf.download(tickers, start=start_date, end=end_date)
            df_check = ohlc["Close"] if isinstance(ohlc, pd.DataFrame) and "Close" in ohlc else pd.DataFrame()
            if df_check.empty or df_check.isna().all().all():
                tickers = [t.replace(".KS", ".KQ") if t.endswith(".KS") else t for t in tickers]
                st.session_state["last_tickers"] = tickers
                ohlc = yf.download(tickers, start=start_date, end=end_date)
            df = ohlc["Close"] if isinstance(ohlc, pd.DataFrame) and "Close" in ohlc else pd.DataFrame()
            if isinstance(df, pd.Series):
                df = df.to_frame()
            
            # ── [듀얼 엔진 백업] yfinance 장애 발생 시, 한국주식은 FinanceDataReader(네이버)로 자동 우회 수집 ──
            if (df.empty or df.isna().all().all()) and market == "한국주식 (KS)":
                try:
                    import FinanceDataReader as fdr
                    clean_tickers = [t.replace(".KS", "") for t in tickers]
                    if len(clean_tickers) == 1:
                        df_fdr = fdr.DataReader(clean_tickers[0], start_date, end_date)
                        if not df_fdr.empty:
                            df = pd.DataFrame({tickers[0]: df_fdr["Close"]})
                            open_p = df_fdr["Open"]
                            high_p = df_fdr["High"]
                            low_p = df_fdr["Low"]
                            close_p = df_fdr["Close"]
                            volume = df_fdr["Volume"]
                    else:
                        dfs = []
                        for ct, t in zip(clean_tickers, tickers):
                            temp_df = fdr.DataReader(ct, start_date, end_date)[["Close"]]
                            temp_df.columns = [t]
                            dfs.append(temp_df)
                        df = pd.concat(dfs, axis=1).dropna()
                        chart_col = df.columns[0]
                        chart_raw = chart_col.replace(".KS", "")
                        df_fdr_single = fdr.DataReader(chart_raw, start_date, end_date)
                        open_p = df_fdr_single["Open"]
                        high_p = df_fdr_single["High"]
                        low_p = df_fdr_single["Low"]
                        close_p = df_fdr_single["Close"]
                        volume = df_fdr_single["Volume"]
                except:
                    pass

            # ── yfinance가 정상 작동했을 때의 기존 컬럼/단일가 분리 파싱 ──
            if not df.empty and 'close_p' not in locals():
                df.columns = [str(c) for c in df.columns]
                chart_col = df.columns[0]
                if len(tickers) == 1:
                    ticker_ohlc = yf.download(tickers[0], start=start_date, end=end_date)
                    open_p = ticker_ohlc["Open"].squeeze()
                    high_p = ticker_ohlc["High"].squeeze()
                    low_p = ticker_ohlc["Low"].squeeze()
                    close_p = ticker_ohlc["Close"].squeeze()
                    volume = ticker_ohlc["Volume"].squeeze()
                else:
                    open_p = ohlc["Open"][chart_col] if isinstance(ohlc["Open"], pd.DataFrame) else ohlc["Open"]
                    high_p = ohlc["High"][chart_col] if isinstance(ohlc["High"], pd.DataFrame) else ohlc["High"]
                    low_p = ohlc["Low"][chart_col] if isinstance(ohlc["Low"], pd.DataFrame) else ohlc["Low"]
                    close_p = df[chart_col]
                    volume = ohlc["Volume"][chart_col] if isinstance(ohlc["Volume"], pd.DataFrame) else ohlc["Volume"]

        # ── [예외 처리] 듀얼 백업 수집까지 최종 실패했을 때에만 안전하게 정지 ──
        if df.empty or 'close_p' not in locals() or close_p.empty:
            st.error("❌ 주가 데이터 서버(Yahoo Finance/Naver) 응답이 원활하지 않습니다. 잠시 후 다시 시도해 주세요.")
            st.stop()

        # 메인 화면 슬라이더 값을 세션 상태에서 선감지하여 연동 (기본값 0.23% 세팅)
        fee_pct = st.session_state.get("main_fee_slider", 0.23)

        strategy_pct, weighted_return, signal, rsi, ma_s, ma_l, bb_upper, bb_lower, bb_mid = run_strategy(
            df, strategy, rsi_threshold, ma_short, ma_long, bb_period, fee_pct=fee_pct
        )
        # 서브탭 메시지 출력에 필요한 최근 신호 및 RSI 지표 미리 연산
        last_sig = signal.iloc[-1].values[0]
        last_rsi = rsi[chart_col].iloc[-1] if isinstance(rsi, pd.DataFrame) else rsi.iloc[-1]

        sig = signal.iloc[:, 0]
        buy_idx = sig[(sig == 1) & (sig.shift(1) == 0)].index
        sell_idx = sig[(sig == 0) & (sig.shift(1) == 1)].index
        equal_return = df.pct_change().mean(axis=1)
        portfolio_strategy = (1 + weighted_return).cumprod()
        portfolio_equal = (1 + equal_return).cumprod()
        days = max((df.index[-1] - df.index[0]).days, 1)
        equal_pct = (portfolio_equal.iloc[-1] - 1) * 100
        mdd_s = calculate_mdd(portfolio_strategy)
        mdd_e = calculate_mdd(portfolio_equal)
        sharpe_s = calculate_sharpe(weighted_return.dropna())
        sharpe_e = calculate_sharpe(equal_return.dropna())
        cagr_s = calculate_cagr(portfolio_strategy, days)
        cagr_e = calculate_cagr(portfolio_equal, days)
        invest_won = investment * 10000
        strategy_profit = invest_won * (strategy_pct / 100)
        strategy_final = invest_won + strategy_profit
        equal_profit = invest_won * (equal_pct / 100)
        excess = strategy_profit - equal_profit

    # ── [메인 콘텐츠 서브탭 영역] ──
    sub1, sub2, sub3 = st.tabs(["📈 주가 & 신호", "📊 백테스트", "🔍 재무 & 뉴스"])

    # ── SUB 1 : 주가 & 신호 ──
    with sub1:
        if st.session_state.watchlist:
            @st.cache_data(ttl=300)
            def get_today_signals(watchlist, strategy_name, rsi_thr, ma_s, ma_l, bb_p):
                buy_list, sell_list = [], []
                for item in watchlist:
                    ticker = item + ".KS" if not item.endswith(".KS") else item
                    try:
                        df_w = yf.download(ticker, period="6mo", progress=False)["Close"]
                        if isinstance(df_w, pd.Series):
                            df_w = df_w.to_frame()
                        df_w.columns = [ticker]
                        _, _, sig, _, _, _, _, _, _ = run_strategy(df_w, strategy_name, rsi_thr, ma_s, ma_l, bb_p)
                        last = sig.iloc[-1].values[0]
                        prev = sig.iloc[-2].values[0]
                        if last == 1 and prev == 0:
                            buy_list.append(item)
                        elif last == 0 and prev == 1:
                            sell_list.append(item)
                    except:
                        pass
                return buy_list, sell_list

            buy_signals, sell_signals = get_today_signals(
                tuple(st.session_state.watchlist), strategy, rsi_threshold, ma_short, ma_long, bb_period
            )
            card("🔔 오늘 신호 현황", f"{strategy} 기준")
            if buy_signals:
                st.success(f"🟢 매수 신호: {', '.join(buy_signals)}")
            elif sell_signals:
                st.warning(f"🔴 매도 신호: {', '.join(sell_signals)}")
            else:
                st.info("오늘 신호 없음 — 관망")

        if not analyzed:
            st.info("사이드바에서 종목을 입력하고 🔍 분석 시작 버튼을 눌러주세요!")
        else:
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

            card("💹 현재가", "실시간 주가 · KIS API 기준" if KIS_AVAILABLE else "주가 · yfinance 기준")
            price_cols = st.columns(len(tickers))
            kis_token = get_kis_token() if KIS_AVAILABLE else None
            for i, ticker in enumerate(tickers):
                with price_cols[i]:
                    price_data = None
                    if KIS_AVAILABLE and kis_token and market == "한국주식 (KS)":
                        try:
                            raw_ticker = ticker.replace(".KS", "").replace(".KQ", "")
                            price_data = kis_get_price(raw_ticker, kis_token)
                        except:
                            pass
                    if not price_data:
                        try:
                            hist = yf.Ticker(ticker).history(period="2d")
                            if len(hist) >= 2:
                                current = hist["Close"].iloc[-1]
                                prev = hist["Close"].iloc[-2]
                                change = current - prev
                                change_pct = (change / prev) * 100
                                price_data = {"current": current, "change": change, "change_pct": change_pct}
                        except:
                            pass
                    if price_data:
                        current = price_data["current"]
                        change = price_data["change"]
                        change_pct = price_data["change_pct"]
                        color = CANDLE_UP if change >= 0 else CANDLE_DOWN
                        arrow = "▲" if change >= 0 else "▼"
                        st.markdown(f"""
                        <div style='background:{SURFACE_2}; border:0.5px solid {LINE}; border-radius:12px; padding:14px 18px; margin-bottom:8px;'>
                            <div style='font-size:16px; font-weight:600; color:{TEXT}; margin-bottom:4px;'>{name_map.get(ticker.replace(".KS","").replace(".KQ",""), ticker)}</div>
                            <div style='font-family:JetBrains Mono; font-size:22px; font-weight:600;'>{current:,.0f}</div>
                            <div style='font-family:JetBrains Mono; font-size:12px; color:{color}; margin-top:2px;'>{arrow} {change:+,.0f} ({change_pct:+.2f}%)</div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style='background:{SURFACE_2}; border:0.5px solid {LINE}; border-radius:12px; padding:14px 18px; margin-bottom:8px;'>
                            <div style='font-size:12px; color:{DIM};'>{ticker}</div>
                            <div style='font-size:14px; color:{DIM};'>조회 실패</div>
                        </div>
                        """, unsafe_allow_html=True)

            render_summary_cards(
                invested=investment,
                profit=strategy_profit / 10000,
                profit_pct=strategy_pct,
                final_val=strategy_final / 10000,
                excess=excess / 10000
            )

            current_pct = strategy_pct
            target_remaining = target_pct - current_pct
            t1, t2 = st.columns(2)
            with t1:
                if current_pct >= target_pct:
                    st.success(f"🎯 목표 수익률 달성! (+{target_pct}%)")
                else:
                    st.info(f"🎯 목표까지 {target_remaining:.1f}% 남음 (목표 +{target_pct}%)")
            with t2:
                if current_pct <= -stop_pct:
                    st.error(f"🛑 손절 라인 도달! (-{stop_pct}%)")
                else:
                    st.info(f"🛡 손절까지 {current_pct + stop_pct:.1f}% 여유 (손절 -{stop_pct}%)")

            # 현재 포지션 메시지
            if last_sig == 1:
                if strategy == "RSI 전략 (RSI)":
                    reason = f"RSI {last_rsi:.1f} — 과매도 구간 진입, 매수 신호"
                elif strategy == "이동평균선 전략 (Moving Average)":
                    reason = "단기 MA가 장기 MA 위 — 골든크로스, 매수 신호"
                elif strategy == "볼린저 밴드 전략 (Bollinger Bands)":
                    reason = "주가가 볼린저 하단 밴드 아래 — 매수 신호"
                else:
                    reason = f"RSI {last_rsi:.1f} + 골든크로스 동시 충족 — 강한 매수 신호"
                st.success(f"🟢 현재 포지션: 매수 · {reason}")
            else:
                if strategy == "RSI 전략 (RSI)":
                    reason = f"RSI {last_rsi:.1f} — 과매도 구간 아님, 현금 대기"
                elif strategy == "이동평균선 전략 (Moving Average)":
                    reason = "단기 MA가 장기 MA 아래 — 데드크로스, 현금 대기"
                elif strategy == "볼린저 밴드 전략 (Bollinger Bands)":
                    reason = "주가가 볼린저 하단 밴드 위 — 현금 대기"
                else:
                    reason = "매수 조건 미충족 — 현금 대기"
                st.warning(f"⚪ 현재 포지션: 현금 · {reason}")

            # 전략 지표 그래프
            card("📈 전략 지표 그래프", f"{chart_col} · 상승 🔴 하락 🔵 · ▲매수 ▼매도")
            rsi_chart = rsi[chart_col] if isinstance(rsi, pd.DataFrame) else rsi
            if strategy == "이동평균선 전략 (Moving Average)":
                extra = [
                    go.Scatter(x=ma_s.index, y=ma_s[chart_col], name=f"MA{ma_short}", line=dict(color="orange", width=1.2)),
                    go.Scatter(x=ma_l.index, y=ma_l[chart_col], name=f"MA{ma_long}", line=dict(color=ACCENT, width=1.2)),
                ]
                fig1 = make_candlestick_fig(close_p, open_p, high_p, low_p, volume=volume, extra_traces=extra, buy_idx=buy_idx, sell_idx=sell_idx, chart_col=chart_col)
            elif strategy == "RSI 전략 (RSI)":
                fig1 = make_candlestick_fig(close_p, open_p, high_p, low_p, volume=volume, has_rsi=True, rsi_data=rsi_chart, rsi_threshold=rsi_threshold, buy_idx=buy_idx, sell_idx=sell_idx, chart_col=chart_col)
            elif strategy == "볼린저 밴드 전략 (Bollinger Bands)":
                extra = [
                    go.Scatter(x=bb_upper.index, y=bb_upper[chart_col], name="상단밴드", line=dict(color=CANDLE_UP, width=1, dash="dash")),
                    go.Scatter(x=bb_mid.index, y=bb_mid[chart_col], name="중간선", line=dict(color="yellow", width=1)),
                    go.Scatter(x=bb_lower.index, y=bb_lower[chart_col], name="하단밴드", line=dict(color=GREEN, width=1, dash="dash")),
                ]
                fig1 = make_candlestick_fig(close_p, open_p, high_p, low_p, volume=volume, extra_trades=extra, buy_idx=buy_idx, sell_idx=sell_idx, chart_col=chart_col)
            else:
                extra = [
                    go.Scatter(x=ma_s.index, y=ma_s[chart_col], name=f"MA{ma_short}", line=dict(color="orange", width=1.2)),
                    go.Scatter(x=ma_l.index, y=ma_l[chart_col], name=f"MA{ma_long}", line=dict(color=ACCENT, width=1.2)),
                ]
                fig1 = make_candlestick_fig(close_p, open_p, high_p, low_p, volume=volume, has_rsi=True, rsi_data=rsi_chart, rsi_threshold=rsi_threshold, extra_traces=extra, buy_idx=buy_idx, sell_idx=sell_idx, chart_col=chart_col)

            st.plotly_chart(fig1, use_container_width=True, config={"displayModeBar": False, "scrollZoom": True})

    # ── SUB 2 : 백테스트 성과 ──
    with sub2:
        if not analyzed:
            st.info("사이드바에서 종목을 입력하고 🔍 분석 시작 버튼을 눌러주세요!")
        else:
            # 1. 백테스트 탭 내부로 수수료 슬라이더 배치 (가시성 및 직관성 극대화!)
            fee_pct = st.slider(
                "💸 거래 비용 설정 (왕복 수수료 + 매도세금) (%)", 
                min_value=0.00, 
                max_value=1.50, 
                value=0.23, 
                step=0.01,
                key="main_fee_slider",
                help="왕복 1회 매매 시 발생하는 수수료와 거래세의 합계입니다. 국내 주식의 표준 권장 비용은 0.23% 입니다."
            )
            
            # 슬라이더 조작에 반응하는 수수료 기반 주가 재연산 수행
            strategy_pct, weighted_return, signal, rsi, ma_s, ma_l, bb_upper, bb_lower, bb_mid = run_strategy(
                df, strategy, rsi_threshold, ma_short, ma_long, bb_period, fee_pct=fee_pct
            )
            portfolio_strategy = (1 + weighted_return).cumprod()
            mdd_s = calculate_mdd(portfolio_strategy)
            sharpe_s = calculate_sharpe(weighted_return.dropna())
            cagr_s = calculate_cagr(portfolio_strategy, days)
            strategy_profit = (investment * 10000) * (strategy_pct / 100)
            strategy_final = (investment * 10000) + strategy_profit
            excess = strategy_profit - equal_profit
            
            # 수수료가 실시간 반영된 KPI 지표 및 설명서 출력
            render_kpi_strip(strategy_pct, equal_pct, cagr_s, cagr_e, sharpe_s, sharpe_e, mdd_s, mdd_e)
            render_strategy_expander(strategy)

            # 수수료가 실시간 반영된 누적 수익률 비교 차트
            card("💰 수익률 비교", "누적 수익률 (%)")
            st.plotly_chart(make_return_chart(portfolio_equal, portfolio_strategy, strategy), use_container_width=True, config={"displayModeBar": False, "scrollZoom": True})

            # 수수료가 실시간 반영된 낙폭 및 월별 수익률 차트
            col1, col2 = st.columns([1, 1])
            with col1:
                card("📉 자산 낙폭 (Drawdown)", "자산이 역대 최고점에서 얼마나 떨어졌었는지 보여주는 위기 고통 지표예요.")
                st.markdown("""
                <div style='background: rgba(239,68,68,0.03); border: 0.5px solid rgba(239,68,68,0.2); border-radius: 8px; padding: 10px 14px; margin-bottom: 12px; font-size: 11.5px; color: #9ca3af;'>
                  💡 <b>0%는 자산이 역대 최고점(무손실)</b>인 상태를 뜻합니다. 가장 밑바닥 계곡이 <b>역사상 가장 크게 돈을 잃었던 순간(MDD)</b>입니다.
                </div>
                """, unsafe_allow_html=True)
                st.plotly_chart(make_drawdown_chart(portfolio_strategy), use_container_width=True, config={"displayModeBar": False, "scrollZoom": True})
            with col2:
                card("📅 월별 수익률", "막대가 위로 → 수익 🔴 · 아래로 → 손실 🔵")
                st.plotly_chart(make_monthly_bar_chart(weighted_return), use_container_width=True, config={"displayModeBar": False})

            # 2. 종목별 상세 성과 매트릭스 테이블 생성 (세후 순수익금 및 총 거래비용 산출)
            card("📊 종목별 세부 성과 (수수료/순수익금 시뮬레이션)", "실전 세금/수수료를 감안한 세후 순수익금과 성과를 정밀 분석합니다.")
            volatility = df.pct_change().std() * (252 ** 0.5) * 100
            last_signal = signal.iloc[-1]
            
            # 총 매매 거래 횟수 연산 (signal.diff().abs()가 1인 영업일 합산)
            trade_count_series = signal.diff().abs().fillna(0).sum()
            invest_won = investment * 10000
            
            holdings_list_data = []
            for col in df.columns:
                col_idx = df.columns.get_loc(col)
                ticker_trade_count = int(trade_count_series.iloc[col_idx]) if isinstance(trade_count_series, pd.Series) else int(trade_count_series)
                
                # 총 납부 거래세 및 수수료 % 계산 (왕복 거래비용 / 2 * 거래 횟수)
                total_fee_pct = ticker_trade_count * (fee_pct / 2)
                
                # 포트폴리오 동일가중치 투자금 분할 계산
                allocated_invest = invest_won / len(tickers)
                total_fee_won = allocated_invest * (total_fee_pct / 100)
                
                # 수수료 차감 후 예상 순수익금 및 평가금 산출
                if len(tickers) == 1:
                    ticker_return_pct = strategy_pct
                    ticker_profit_won = strategy_profit
                    ticker_final_won = strategy_final
                else:
                    ticker_return_pct = (portfolio_strategy.iloc[-1] - 1) * 100
                    ticker_profit_won = allocated_invest * (ticker_return_pct / 100)
                    ticker_final_won = allocated_invest + ticker_profit_won
                
                pos_status = "보유중 ✅" if (last_signal.iloc[col_idx] == 1 if isinstance(last_signal, pd.Series) else last_signal == 1) else "현금 ❌"
                
                holdings_list_data.append({
                    "종목": col,
                    "세후 전략수익률": f"{ticker_return_pct:+.2f}%",
                    "예상 순수익금": f"{int(ticker_profit_won):+,}원",
                    "총 거래 횟수": f"{ticker_trade_count}회",
                    "누적 거래비용": f"{int(total_fee_won):,}원 ({total_fee_pct:.2f}%)",
                    "최종 평가자산": f"{int(ticker_final_won):,}원",
                    "현재 포지션": pos_status
                })
                
            holdings_df = pd.DataFrame(holdings_list_data)
            st.dataframe(holdings_df.style.map(color_val, subset=["세후 전략수익률", "예상 순수익금"]), use_container_width=True, hide_index=True)

    # ── SUB 3 : 재무 & 뉴스 ──
    with sub3:
        if not analyzed:
            st.info("사이드바에서 종목을 입력하고 🔍 분석 시작 버튼을 눌러주세요!")
        else:
            card("📊 재무제표", "ROE · PER · PBR · 시가총액 · 52주 범위 (DART 공식 기준)")
            try:
                import FinanceDataReader as fdr
                raw_ticker = chart_col.replace(".KS", "").replace(".KQ", "")
                try:
                    fi = pd.read_csv("https://raw.githubusercontent.com/corazzon/finance-data-analysis/main/krx.csv")
                except:
                    fi = fdr.StockListing('KRX')

                code_col = next((c for c in ['Symbol', 'Code', 'code'] if c in fi.columns), None)
                row = fi[fi[code_col].astype(str).str.split('.').str[0].str.zfill(6) == raw_ticker] if code_col else pd.DataFrame()

                if not row.empty:
                    mkt = row.iloc[0].get('Marcap', 0)
                    mkt_str = f"{int(mkt)/1e12:.1f}조" if mkt else 'N/A'
                    high52 = row.iloc[0].get('High', 'N/A')
                    low52 = row.iloc[0].get('Low', 'N/A')
                    curr_p = float(close_p.iloc[-1]) if not close_p.empty else 0

                    from dart_utils import get_dart_roe, get_dart_per_pbr
                    roe = get_dart_roe(raw_ticker)
                    roe_str = f"{roe:.1f}%" if roe is not None else "N/A"
                    dart_per, dart_pbr = get_dart_per_pbr(raw_ticker, curr_p)
                    per = f"{dart_per:.1f}배" if dart_per is not None else "N/A"
                    pbr = f"{dart_pbr:.1f}배" if dart_pbr is not None else "N/A"
                    
                    # 토스증권 스타일 패칭을 위한 데이터 초기화
                    eps, bps, div_yield, div_payout, div_per_share = "N/A", "N/A", "N/A", "N/A", "N/A"
                    
                    # 네이버 통합 API 조회를 통한 가치평가 및 배당 데이터 보완 수집
                    try:
                        nv_url = f"https://m.stock.naver.com/api/stock/{raw_ticker}/integration"
                        nv_res = requests.get(nv_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
                        nv_data = nv_res.json()
                        total_infos = nv_data.get("totalInfos", [])
                        # 수집된 원본 데이터에 이미 기호가 붙어있을 때를 대비해 완전히 기호를 씻어주는 클렌징 헬퍼 함수
                        def clean_val(val_str):
                            return val_str.replace("원", "").replace("%", "").replace("배", "").replace("x", "").replace(",", "").strip()

                        for info in total_infos:
                            k = str(info.get("key", "")).upper()
                            c = str(info.get("code", "")).lower()
                            v = str(info.get("value", "")).strip()
                            if not v or v == "-":
                                continue
                            
                            val_clean = clean_val(v)
                            
                            # 정확히 일치하는(==) 키워드로 파싱하여 데이터 중복 및 기호 중첩 차단
                            if c == "per" or k == "PER":
                                if per == "N/A":
                                    try: per = f"{float(val_clean):.1f}배"
                                    except: per = f"{v}배" if "배" not in v else v
                            elif c == "pbr" or k == "PBR":
                                if pbr == "N/A":
                                    try: pbr = f"{float(val_clean):.1f}배"
                                    except: pbr = f"{v}배" if "배" not in v else v
                            elif c == "eps" or k == "EPS":
                                try: eps = f"{int(float(val_clean)):,}원"
                                except: eps = f"{v}원" if "원" not in v else v
                            elif c == "bps" or k == "BPS":
                                try: bps = f"{int(float(val_clean)):,}원"
                                except: bps = f"{v}원" if "원" not in v else v
                            elif c == "roe" or k == "ROE":
                                if roe_str == "N/A":
                                    try: roe_str = f"{float(val_clean):.1f}%"
                                    except: roe_str = f"{v}%" if "%" not in v else v
                            elif c == "dividendyield" or k == "배당수익률":
                                try: div_yield = f"{float(val_clean):.2f}%"
                                except: div_yield = f"{v}%" if "%" not in v else v
                            elif c in ["dividend", "dps"] or k == "주당배당금":
                                try: div_per_share = f"{int(float(val_clean)):,}원"
                                except: div_per_share = f"{v}원" if "원" not in v else v
                            elif c in ["payoutratio", "dividendpayoutratio"] or "배당성향" in k:
                                try: div_payout = f"{float(val_clean):.1f}%"
                                except: div_payout = f"{v}%" if "%" not in v else v
                            elif c == "marketvalue" or k == "시가총액":
                                mkt_str = v # 네이버 실시간 시총 (예: 10조 1,234억원)으로 즉시 대체 주입
                    except:
                        pass

                    # ── [토스증권 투자지표 스타일 컴포넌트 렌더링] ──
                    st.markdown(f"""
                    <div class="qf-toss-grid" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; background: #0f1117; padding: 18px; border-radius: 14px; border: 0.5px solid #1e2330;">
                      
                      <!-- 가치평가 -->
                      <div style="background: #13161f; padding: 16px; border-radius: 12px; border: 0.5px solid #1e2330;">
                        <div style="font-size: 13.5px; font-weight: 600; color: #9ca3af; margin-bottom: 12px;">가치평가</div>
                        <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 0.5px solid #1e2330;">
                          <span style="color: #6b7280; font-size: 13px;">시가총액</span>
                          <span style="color: #e2e8f0; font-size: 13px; font-weight: 600; font-family: 'JetBrains Mono';">{mkt_str}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 0.5px solid #1e2330;">
                          <span style="color: #6b7280; font-size: 13px;">PER</span>
                          <span style="color: #e2e8f0; font-size: 13px; font-weight: 600; font-family: 'JetBrains Mono';">{per}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding: 10px 0;">
                          <span style="color: #6b7280; font-size: 13px;">PBR</span>
                          <span style="color: #e2e8f0; font-size: 13px; font-weight: 600; font-family: 'JetBrains Mono';">{pbr}</span>
                        </div>
                      </div>
                      
                      <!-- 수익성 -->
                      <div style="background: #13161f; padding: 16px; border-radius: 12px; border: 0.5px solid #1e2330;">
                        <div style="font-size: 13.5px; font-weight: 600; color: #9ca3af; margin-bottom: 12px;">수익</div>
                        <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 0.5px solid #1e2330;">
                          <span style="color: #6b7280; font-size: 13px;">EPS</span>
                          <span style="color: #e2e8f0; font-size: 13px; font-weight: 600; font-family: 'JetBrains Mono';">{eps}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 0.5px solid #1e2330;">
                          <span style="color: #6b7280; font-size: 13px;">BPS</span>
                          <span style="color: #e2e8f0; font-size: 13px; font-weight: 600; font-family: 'JetBrains Mono';">{bps}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding: 10px 0;">
                          <span style="color: #6b7280; font-size: 13px;">ROE</span>
                          <span style="color: #e2e8f0; font-size: 13px; font-weight: 600; font-family: 'JetBrains Mono';">{roe_str}</span>
                        </div>
                      </div>
                      
                      <!-- 배당 정보 -->
                      <div style="background: #13161f; padding: 16px; border-radius: 12px; border: 0.5px solid #1e2330;">
                        <div style="font-size: 13.5px; font-weight: 600; color: #9ca3af; margin-bottom: 12px;">배당 (최근 12개월)</div>
                        <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 0.5px solid #1e2330;">
                          <span style="color: #6b7280; font-size: 13px;">배당수익률</span>
                          <span style="color: #e2e8f0; font-size: 13px; font-weight: 600; font-family: 'JetBrains Mono';">{div_yield}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 0.5px solid #1e2330;">
                          <span style="color: #6b7280; font-size: 13px;">주당 배당금</span>
                          <span style="color: #e2e8f0; font-size: 13px; font-weight: 600; font-family: 'JetBrains Mono';">{div_per_share}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding: 10px 0;">
                          <span style="color: #6b7280; font-size: 13px;">배당성향</span>
                          <span style="color: #e2e8f0; font-size: 13px; font-weight: 600; font-family: 'JetBrains Mono';">{div_payout}</span>
                        </div>
                      </div>
                      
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info("재무 데이터를 찾을 수 없어요.")
            except Exception as e:
                st.error(f"재무 데이터 오류: {e}")

            card("📰 관련 뉴스", f"{chart_col} 최신 뉴스")
            try:
                naver_id = st.secrets.get("NAVER_CLIENT_ID", "")
                naver_secret = st.secrets.get("NAVER_CLIENT_SECRET", "")
                query = chart_col.replace(".KS", "").replace(".KQ", "")
                url = f"https://openapi.naver.com/v1/search/news.json?query={query}&display=5&sort=date"
                res = requests.get(url, headers={"X-Naver-Client-Id": naver_id, "X-Naver-Client-Secret": naver_secret}, timeout=5)
                items = res.json().get("items", [])
                if items:
                    for item in items:
                        title = item["title"].replace("<b>", "").replace("</b>", "")
                        link = item["link"]
                        date = item["pubDate"][:16]
                        # 카드 전체 영역이 링크가 되도록 <a> 태그를 부모로 배치하고 간격을 명확히 함
                        st.markdown(f"""
                        <a href='{link}' target='_blank' class='qf-news-card'>
                            <div style='color:{TEXT}; font-size:13.5px; font-weight:500; line-height:1.45;'>{title}</div>
                            <div style='font-size:11.5px; color:{DIM}; margin-top:8px;'>{date}</div>
                        </a>
                        """, unsafe_allow_html=True)
                else:
                    st.info("뉴스를 불러오지 못했어요.")
            except:
                st.info("뉴스를 불러오지 못했어요.")

            st.caption(f"Data: yfinance · {df.index[0].date()} → {df.index[-1].date()} · {len(df)} trading days")

with tab3:
    render_portfolio(KIS_AVAILABLE, get_kis_token, get_balance if KIS_AVAILABLE else lambda x: {})