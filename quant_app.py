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
    init_session_state, load_market_data, load_krx_listing, get_krx_name_map
)
from dashboard import render_dashboard
from portfolio import render_portfolio

# ── [안전 우회 컴파일 엔진] strategies.py 파일의 인자 수집 규격을 자동 판별하여 수수료 및 돌파전략 수동 보정 계산 수행 ──
def safe_run_strategy(df, strategy, rsi_threshold, ma_short, ma_long, bb_period, fee_pct=0.0, open_p=None, high_p=None, low_p=None):
    import inspect
    import pandas as pd
    sig_params = inspect.signature(run_strategy).parameters
    
    # 1. 실제 수용하는 인자만 동적으로 추출하여 안전하게 호출 구성 (unexpected keyword argument 방어)
    kwargs = {}
    if "fee_pct" in sig_params: kwargs["fee_pct"] = fee_pct
    if "open_p" in sig_params: kwargs["open_p"] = open_p
    if "high_p" in sig_params: kwargs["high_p"] = high_p
    if "low_p" in sig_params: kwargs["low_p"] = low_p
    
    # 서버에 변동성 돌파 로직 수식이 누락된 롤백 상태인 경우 자체 백업 연산 작동
    run_custom_vb_backup = (strategy == "변동성 돌파 전략 (Volatility Breakout)" and "open_p" not in sig_params)
    
    if not run_custom_vb_backup:
        total_return, weighted_return, signal, rsi, ma_s, ma_l, bb_upper, bb_lower, bb_mid = run_strategy(
            df, strategy, rsi_threshold, ma_short, ma_long, bb_period, **kwargs
        )
    else:
        # ── [변동성 돌파 자체 백업 연산 엔진] ──
        rsi = df.apply(lambda x: pd.Series(0.0, index=df.index))
        ma_s = df.rolling(ma_short).mean()
        ma_l = df.rolling(ma_long).mean()
        bb_upper = df.rolling(bb_period).mean()
        bb_lower = bb_upper
        bb_mid = bb_upper

        op = open_p.to_frame() if isinstance(open_p, pd.Series) else open_p
        hp = high_p.to_frame() if isinstance(high_p, pd.Series) else high_p
        lp = low_p.to_frame() if isinstance(low_p, pd.Series) else low_p
        
        yesterday_range = hp.shift(1) - lp.shift(1)
        target_price = op + yesterday_range * rsi_threshold
        signal = (hp > target_price).astype(int)
        
        signal_count = signal.sum(axis=1).replace(0, 1)
        returns = df.pct_change()
        daily_fees = signal.diff().abs().fillna(0) * (fee_pct / 100 / 2)
        weighted_return = (returns * signal.shift(1) - daily_fees).sum(axis=1) / signal_count.shift(1)
        portfolio = (1 + weighted_return.fillna(0)).cumprod()
        total_return = (portfolio.iloc[-1] - 1) * 100

    # 2. 수수료 기능 동기화 지연 시 수동 우회 보정 차감 적용
    if "fee_pct" not in sig_params and fee_pct > 0 and not run_custom_vb_backup:
        signal_count = signal.sum(axis=1).replace(0, 1)
        returns = df.pct_change()
        daily_fees = signal.diff().abs().fillna(0) * (fee_pct / 100 / 2)
        weighted_return = (returns * signal.shift(1) - daily_fees).sum(axis=1) / signal_count.shift(1)
        portfolio = (1 + weighted_return.fillna(0)).cumprod()
        total_return = (portfolio.iloc[-1] - 1) * 100
        
    return total_return, weighted_return, signal, rsi, ma_s, ma_l, bb_upper, bb_lower, bb_mid


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

def get_kis_token():
    try:
        token = get_access_token()
        st.session_state["kis_token"] = token
        return token
    except:
        return None

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 대시보드", "🔍 분석", "💼 포트폴리오", "📋 리포트", "🔬 심층분석"])

with tab1:
    render_dashboard()

with tab2:
    with st.sidebar:
        st.markdown("<div style='font-size:18px; font-weight:600; margin-bottom:16px;'>⚙️ Settings</div>", unsafe_allow_html=True)

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

        with st.expander("🔍 종목 검색", expanded=True):
            market = st.selectbox("시장 선택", ["한국주식 (KS)", "미국주식 (US)"])

            if market == "한국주식 (KS)":
                st.caption("예시: 삼성전자, 에코프로, 와이지엔터테이먼트")
                default_ticker = st.session_state.get("selected_ticker", "")
                tickers_raw = st.text_input("종목명 또는 코드 (쉼표로 구분)", value=default_ticker)

                tickers_list = []
                if tickers_raw.strip():
                    df_krx = load_krx_listing()
                    for t in tickers_raw.split(","):
                        t_clean = t.strip()
                        if not t_clean:
                            continue
                        if not t_clean.isdigit() and df_krx is not None:
                            matched = df_krx[df_krx['Name'].str.upper() == t_clean.upper()]
                            if matched.empty:
                                matched = df_krx[df_krx['Name'].str.upper().str.contains(t_clean.upper(), na=False)]
                            if not matched.empty:
                                code_col = next((c for c in ['Symbol', 'Code', 'code'] if c in df_krx.columns), None)
                                if code_col:
                                    raw_code = matched.iloc[0][code_col]
                                    code = str(raw_code).split('.')[0].zfill(6)
                                    mkt_info = str(matched.iloc[0].get('Market', 'KOSPI')).upper()
                                    suffix = ".KS" if "KOSPI" in mkt_info else ".KQ"
                                    tickers_list.append(code + suffix)
                                else:
                                    tickers_list.append(t_clean + ".KS")
                            else:
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

        if st.session_state.get("watchlist"):
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

        with st.expander("📐 전략 설정", expanded=True):
            strategy = st.selectbox("전략 선택", [
                "RSI 전략 (RSI)",
                "이동평균선 전략 (Moving Average)",
                "볼린저 밴드 전략 (Bollinger Bands)",
                "MACD 전략 (MACD)",
                "변동성 돌파 전략 (Volatility Breakout)",
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
            elif strategy == "MACD 전략 (MACD)":
                ma_short = st.slider("단기(Fast) EMA", 5, 40, 12)
                ma_long = st.slider("장기(Slow) EMA", 20, 100, 26)
                rsi_threshold, bb_period = 40, 20
            elif strategy == "변동성 돌파 전략 (Volatility Breakout)":
                rsi_threshold = st.slider("돌파 계수 (K)", 0.40, 0.90, 0.50, 0.05)
                ma_short, ma_long, bb_period = 20, 60, 20
            else:
                rsi_threshold = st.slider("RSI 기준값", 10, 70, 40)
                ma_short = st.slider("단기 MA", 5, 60, 20)
                ma_long = st.slider("장기 MA", 20, 120, 60)
                bb_period = 20

        with st.expander("🎯 목표가 · 손절가 · 투입금액", expanded=False):
            target_pct = st.number_input("목표 수익률 (%)", min_value=1, max_value=200, value=20, step=5)
            stop_pct = st.number_input("손절 라인 (%)", min_value=1, max_value=50, value=10, step=1)
            investment = st.number_input("투입금액 (만원)", min_value=0, value=1000, step=100)
            st.caption(f"= {investment:,}만원 ({investment * 10000:,}원)")

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
        if strategy == "변동성 돌파 전략 (Volatility Breakout)":
            optimize = False
            wf_test = False
        else:
            optimize = st.button("⚡ 최적값 자동 탐색", use_container_width=True)
            wf_test = st.button("🔄 워크포워드 테스트", use_container_width=True)

    # ── 분석 공통 연산 ──
    if analyze:
        st.session_state["analyzed"] = True

    if 'tickers' in locals() and tickers:
        st.session_state["last_tickers"] = tickers
    tickers = st.session_state.get("last_tickers", [])
    analyzed = st.session_state.get("analyzed") and bool(tickers)

    if analyzed:
        with st.spinner("데이터 분석 준비 중..."):
            df, open_p, high_p, low_p, close_p, volume = load_market_data(tuple(tickers), start_date, end_date, market)

        if df.empty or close_p.empty:
            st.error("❌ 주가 데이터를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.")
            st.stop()

        chart_col = df.columns[0]
        fee_pct = st.session_state.get("main_fee_slider", 0.23)

        strategy_pct, weighted_return, signal, rsi, ma_s, ma_l, bb_upper, bb_lower, bb_mid = safe_run_strategy(
            df, strategy, rsi_threshold, ma_short, ma_long, bb_period, fee_pct=fee_pct, open_p=open_p, high_p=high_p, low_p=low_p
        )
        last_sig = signal.iloc[-1].values[0]
        last_rsi = rsi[chart_col].iloc[-1] if isinstance(rsi, pd.DataFrame) else rsi.iloc[-1]

        sig = signal.iloc[:, 0]
        buy_idx = sig[(sig == 1) & (sig.shift(1) == 0)].index
        sell_idx = sig[(sig == 0) & (sig.shift(1) == 1)].index
        equal_return = df.pct_change().mean(axis=1)
        portfolio_strategy = (1 + weighted_return.fillna(0)).cumprod()
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

    # ── 서브탭 ──
    sub1, sub2, sub3 = st.tabs(["📈 주가 & 신호", "📊 백테스트", "🔍 재무제표 & 뉴스"])

    # ── SUB 1 : 주가 & 신호 ──
    with sub1:
        if st.session_state.get("watchlist"):
            @st.cache_data(ttl=300)
            def get_today_signals(watchlist, strategy_name, rsi_thr, ma_s, ma_l, bb_p):
                buy_list, sell_list = [], []
                for item in watchlist:
                    ticker = item + ".KS" if not item.endswith(".KS") and not item.endswith(".KQ") else item
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
            if kis_token:
                st.session_state["kis_token"] = kis_token
            name_map = get_krx_name_map()

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
                    display_name = name_map.get(ticker.replace(".KS","").replace(".KQ",""), ticker)
                    if price_data:
                        current = price_data["current"]
                        change = price_data["change"]
                        change_pct = price_data["change_pct"]
                        color = CANDLE_UP if change >= 0 else CANDLE_DOWN
                        arrow = "▲" if change >= 0 else "▼"
                        st.markdown(f"""
                        <div style='background:{SURFACE_2}; border:0.5px solid {LINE}; border-radius:12px; padding:14px 18px; margin-bottom:8px;'>
                            <div style='font-size:16px; font-weight:600; color:{TEXT}; margin-bottom:4px;'>{display_name}</div>
                            <div style='font-family:JetBrains Mono; font-size:22px; font-weight:600;'>{current:,.0f}</div>
                            <div style='font-family:JetBrains Mono; font-size:12px; color:{color}; margin-top:2px;'>{arrow} {change:+,.0f} ({change_pct:+.2f}%)</div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style='background:{SURFACE_2}; border:0.5px solid {LINE}; border-radius:12px; padding:14px 18px; margin-bottom:8px;'>
                            <div style='font-size:12px; color:{DIM};'>{display_name}</div>
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

            if last_sig == 1:
                if strategy == "RSI 전략 (RSI)":
                    reason = f"RSI {last_rsi:.1f} — 과매도 구간 진입, 매수 신호"
                elif strategy == "이동평균선 전략 (Moving Average)":
                    reason = "단기 MA가 장기 MA 위 — 골든크로스, 매수 신호"
                elif strategy == "볼린저 밴드 전략 (Bollinger Bands)":
                    reason = "주가가 볼린저 하단 밴드 아래 — 매수 신호"
                elif strategy == "MACD 전략 (MACD)":
                    reason = "MACD선이 시그널선 상향 돌파 — 매수 신호"
                elif strategy == "변동성 돌파 전략 (Volatility Breakout)":
                    reason = f"시가 돌파 타겟가(K={rsi_threshold}) 돌파 — 매수 신호"
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
                elif strategy == "MACD 전략 (MACD)":
                    reason = "MACD선이 시그널선 아래 — 현금 대기"
                elif strategy == "변동성 돌파 전략 (Volatility Breakout)":
                    reason = "돌파 기준선 돌파 실패 — 현금 관망"
                else:
                    reason = "매수 조건 미충족 — 현금 대기"
                st.warning(f"⚪ 현재 포지션: 현금 · {reason}")

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

    # ── SUB 2 : 백테스트 ──
    with sub2:
        if not analyzed:
            st.info("사이드바에서 종목을 입력하고 🔍 분석 시작 버튼을 눌러주세요!")
        else:
            fee_pct = st.slider(
                "💸 거래 비용 설정 (왕복 수수료 + 매도세금) (%)",
                min_value=0.00, max_value=1.50, value=0.23, step=0.01,
                key="main_fee_slider",
                help="왕복 1회 매매 시 발생하는 수수료와 거래세의 합계입니다. 국내 주식 표준은 0.23%입니다."
            )
            strategy_pct, weighted_return, signal, rsi, ma_s, ma_l, bb_upper, bb_lower, bb_mid = safe_run_strategy(
                df, strategy, rsi_threshold, ma_short, ma_long, bb_period, fee_pct=fee_pct, open_p=open_p, high_p=high_p, low_p=low_p
            )
            portfolio_strategy = (1 + weighted_return.fillna(0)).cumprod()
            mdd_s = calculate_mdd(portfolio_strategy)
            sharpe_s = calculate_sharpe(weighted_return.dropna())
            cagr_s = calculate_cagr(portfolio_strategy, days)
            strategy_profit = invest_won * (strategy_pct / 100)
            strategy_final = invest_won + strategy_profit
            excess = strategy_profit - equal_profit

            render_kpi_strip(strategy_pct, equal_pct, cagr_s, cagr_e, sharpe_s, sharpe_e, mdd_s, mdd_e)
            render_strategy_expander(strategy)

            card("💰 수익률 비교", "누적 수익률 (%)")
            st.plotly_chart(make_return_chart(portfolio_equal, portfolio_strategy, strategy), use_container_width=True, config={"displayModeBar": False, "scrollZoom": True})

            col1, col2 = st.columns([1, 1])
            with col1:
                card("📉 자산 낙폭 (Drawdown)", "자산이 역대 최고점에서 얼마나 떨어졌었는지 보여주는 지표예요.")
                st.plotly_chart(make_drawdown_chart(portfolio_strategy), use_container_width=True, config={"displayModeBar": False, "scrollZoom": True})
            with col2:
                card("📅 월별 수익률", "막대가 위로 → 수익 🔴 · 아래로 → 손실 🔵")
                st.plotly_chart(make_monthly_bar_chart(weighted_return), use_container_width=True, config={"displayModeBar": False})

            # ── [토스증권형 종목별 실시간 성적표 통합 렌더링 영역] ──
            # ── [종목별 실시간 성적표 - 슬림형 네이티브 성적표 교체] ──
            card("💼 종목별 퀀트 포지션 요약", "전략 시그널 판단과 투입자금 대비 세후 성과를 한눈에 모니터링합니다.")
            
            name_map = get_krx_name_map()
            alloc_won = invest_won / len(tickers) if len(tickers) > 0 else invest_won
            
            scorecard_rows = []
            for ticker in tickers:
                try:
                    t_df = df[[ticker]] if ticker in df.columns else df.iloc[:, [0]]
                    
                    # 5대 필수 지표 연산을 위한 독립 시뮬레이션
                    try:
                        _op = open_p[[ticker]] if open_p is not None and ticker in open_p else None
                        _hp = high_p[[ticker]] if high_p is not None and ticker in high_p else None
                        _lp = low_p[[ticker]] if low_p is not None and ticker in low_p else None
                    except:
                        _op, _hp, _lp = None, None, None
                    t_pct, _, t_sig, _, _, _, _, _, _ = safe_run_strategy(
                        t_df, strategy, rsi_threshold, ma_short, ma_long, bb_period, fee_pct=fee_pct,
                        open_p=_op, high_p=_hp, low_p=_lp
                    )
                    
                    sig_series = t_sig.iloc[:, 0] if isinstance(t_sig, pd.DataFrame) else t_sig
                    close_series = df[ticker] if ticker in df.columns else df.iloc[:, 0]
                    t_last_sig = sig_series.iloc[-1]
                    
                    # 1. 포지션 정보 (이모지 매핑)
                    position_str = "🟢 보유 (BUY)" if t_last_sig == 1 else "⚪ 관망 (WAIT)"
                    
                    curr_p_val = float(close_series.iloc[-1])
                    t_profit_won = float(alloc_won * (t_pct / 100))
                    
                    display_name = name_map.get(ticker.replace('.KS','').replace('.KQ',''), ticker)
                    
                    scorecard_rows.append({
                        "종목명": f"{display_name} ({ticker})",
                        "전략 시그널": position_str,
                        "현재가": curr_p_val,
                        "세후 수익률": float(t_pct),
                        "예상 순수익금": t_profit_won
                    })
                except Exception as ex:
                    display_name = name_map.get(ticker.replace('.KS','').replace('.KQ',''), ticker)
                    scorecard_rows.append({
                        "종목명": f"{display_name} ({ticker})",
                        "전략 시그널": "🚨 연산 오류",
                        "현재가": 0.0,
                        "세후 수익률": 0.0,
                        "예상 순수익금": 0.0
                    })
            
            if scorecard_rows:
                kis_token_for_supply = get_kis_token() if KIS_AVAILABLE else None
                cols = st.columns(min(len(scorecard_rows), 3))
                for idx, row in enumerate(scorecard_rows):
                    with cols[idx % 3]:
                        is_buy = "보유" in row["전략 시그널"]
                        sig_color = "#ef4444" if is_buy else "#6b7280"
                        sig_bg = "rgba(239,68,68,0.08)" if is_buy else "rgba(107,114,128,0.08)"
                        ret_color = "#ef4444" if row["세후 수익률"] >= 0 else "#3b82f6"
                        ret_arrow = "▲" if row["세후 수익률"] >= 0 else "▼"
                        profit_color = "#ef4444" if row["예상 순수익금"] >= 0 else "#3b82f6"

                        # RSI 게이지 계산
                        try:
                            ticker_code = row["종목명"].split("(")[-1].replace(")", "").strip()
                            t_df_rsi = df[[ticker_code]] if ticker_code in df.columns else df.iloc[:, [0]]
                            from strategies import calculate_rsi
                            rsi_series = calculate_rsi(t_df_rsi.iloc[:, 0])
                            rsi_val = float(rsi_series.iloc[-1])
                            rsi_pct = min(max(rsi_val, 0), 100)
                            rsi_color = "#ef4444" if rsi_val < 30 else ("#f59e0b" if rsi_val < 50 else "#3b82f6")
                            rsi_label = "과매도 🔴" if rsi_val < 30 else ("중립 🟡" if rsi_val < 70 else "과매수 🔵")
                        except:
                            rsi_val = 0
                            rsi_pct = 0
                            rsi_color = "#6b7280"
                            rsi_label = "N/A"

                        # 목표가/손절 여유
                        try:
                            curr = row["현재가"]
                            entry_price = curr / (1 + row["세후 수익률"] / 100) if row["세후 수익률"] != -100 else curr
                            target_price_val = entry_price * (1 + target_pct / 100)
                            stop_price_val = entry_price * (1 - stop_pct / 100)
                            to_target = ((target_price_val - curr) / curr * 100) if curr > 0 else 0
                            to_stop = ((curr - stop_price_val) / curr * 100) if curr > 0 else 0
                        except:
                            to_target = 0
                            to_stop = 0

                        st.markdown(f"""
                        <div style='background:#13161f; border:0.5px solid #1e2330; border-radius:14px; padding:18px; margin-bottom:12px; box-shadow:0 4px 24px rgba(0,0,0,0.4);'>
                          
                          <!-- 종목명 & 코드 -->
                          <div style='font-size:15px; font-weight:700; color:#e2e8f0; margin-bottom:2px;'>{row["종목명"].split("(")[0].strip()}</div>
                          <div style='font-size:11px; color:#6b7280; margin-bottom:12px;'>{row["종목명"].split("(")[-1].replace(")", "").strip()}</div>
                          
                          <!-- 전략명 + 시그널 배지 -->
                          <div style='display:flex; gap:6px; flex-wrap:wrap; margin-bottom:14px;'>
                            <div style='display:inline-block; background:rgba(59,130,246,0.08); border:0.5px solid rgba(59,130,246,0.3); border-radius:20px; padding:3px 10px; font-size:11px; font-weight:600; color:#3b82f6;'>
                              {strategy.split("(")[0].strip()}
                            </div>
                            <div style='display:inline-block; background:{sig_bg}; border:0.5px solid {sig_color}; border-radius:20px; padding:3px 10px; font-size:11.5px; font-weight:600; color:{sig_color};'>
                              {row["전략 시그널"]}
                            </div>
                          </div>
                          
                          <!-- 현재가 -->
                          <div style='display:flex; justify-content:space-between; padding:8px 0; border-bottom:0.5px solid #1e2330;'>
                            <span style='color:#6b7280; font-size:12px;'>현재가</span>
                            <span style='color:#e2e8f0; font-size:13px; font-weight:600; font-family:JetBrains Mono;'>{int(row["현재가"]):,}원</span>
                          </div>
                          
                          <!-- 세후 수익률 -->
                          <div style='display:flex; justify-content:space-between; padding:8px 0; border-bottom:0.5px solid #1e2330;'>
                            <span style='color:#6b7280; font-size:12px;'>세후 수익률</span>
                            <span style='color:{ret_color}; font-size:13px; font-weight:600; font-family:JetBrains Mono;'>{ret_arrow} {row["세후 수익률"]:+.2f}%</span>
                          </div>
                          
                          <!-- 예상 순수익금 -->
                          <div style='display:flex; justify-content:space-between; padding:8px 0; border-bottom:0.5px solid #1e2330;'>
                            <span style='color:#6b7280; font-size:12px;'>예상 순수익금</span>
                            <span style='color:{profit_color}; font-size:13px; font-weight:600; font-family:JetBrains Mono;'>{int(row["예상 순수익금"]):+,}원</span>
                          </div>
                          
                          <!-- RSI 게이지 -->
                          <div style='padding:10px 0; border-bottom:0.5px solid #1e2330;'>
                            <div style='display:flex; justify-content:space-between; margin-bottom:6px;'>
                              <span style='color:#6b7280; font-size:12px;'>RSI</span>
                              <span style='color:{rsi_color}; font-size:12px; font-weight:600;'>{rsi_val:.1f} — {rsi_label}</span>
                            </div>
                            <div style='background:#1e2330; border-radius:4px; height:5px; width:100%;'>
                              <div style='background:{rsi_color}; border-radius:4px; height:5px; width:{rsi_pct}%;'></div>
                            </div>
                            <div style='display:flex; justify-content:space-between; margin-top:3px;'>
                              <span style='color:#6b7280; font-size:10px;'>과매도</span>
                              <span style='color:#6b7280; font-size:10px;'>중립</span>
                              <span style='color:#6b7280; font-size:10px;'>과매수</span>
                            </div>
                          </div>
                          
                          <!-- 목표가/손절 -->
                          <div style='display:flex; gap:8px; margin-top:10px; margin-bottom:10px;'>
                            <div style='flex:1; background:rgba(239,68,68,0.06); border:0.5px solid rgba(239,68,68,0.2); border-radius:8px; padding:7px 10px; text-align:center;'>
                              <div style='font-size:10px; color:#9ca3af; margin-bottom:2px;'>🎯 목표까지</div>
                              <div style='font-size:12px; font-weight:600; color:#ef4444;'>{to_target:.1f}%</div>
                            </div>
                            <div style='flex:1; background:rgba(59,130,246,0.06); border:0.5px solid rgba(59,130,246,0.2); border-radius:8px; padding:7px 10px; text-align:center;'>
                              <div style='font-size:10px; color:#9ca3af; margin-bottom:2px;'>🛡 손절여유</div>
                              <div style='font-size:12px; font-weight:600; color:#3b82f6;'>{to_stop:.1f}%</div>
                            </div>
                          </div>
                          
                        </div>
                        """, unsafe_allow_html=True)

                        # ── 외국인/기관 수급 섹션 (KIS API) ──
                        if KIS_AVAILABLE and kis_token_for_supply:
                            try:
                                from broker import get_stock_investor
                                supply_ticker = row["종목명"].split("(")[-1].replace(")", "").strip().replace(".KS", "").replace(".KQ", "")
                                inv_data = get_stock_investor(supply_ticker, kis_token_for_supply)

                                if inv_data.get("rt_cd") == "0" and inv_data.get("output"):
                                    latest = inv_data["output"][0]
                                    date_str = latest.get("stck_bsop_date", "")
                                    date_fmt = f"{date_str[4:6]}/{date_str[6:8]}" if len(date_str) == 8 else date_str

                                    frgn_qty = int(latest.get("frgn_ntby_qty", 0))
                                    orgn_qty = int(latest.get("orgn_ntby_qty", 0))
                                    frgn_amt_eok = int(latest.get("frgn_ntby_tr_pbmn", 0)) / 100  # 백만원 → 억원
                                    orgn_amt_eok = int(latest.get("orgn_ntby_tr_pbmn", 0)) / 100

                                    frgn_color = "#ef4444" if frgn_qty >= 0 else "#3b82f6"
                                    orgn_color = "#ef4444" if orgn_qty >= 0 else "#3b82f6"
                                    frgn_arrow = "▲" if frgn_qty >= 0 else "▼"
                                    orgn_arrow = "▲" if orgn_qty >= 0 else "▼"

                                    # 게이지 바 너비 (최대 ±100억 기준 스케일)
                                    max_scale = 100
                                    frgn_pct = min(abs(frgn_amt_eok) / max_scale * 100, 100)
                                    orgn_pct = min(abs(orgn_amt_eok) / max_scale * 100, 100)

                                    st.markdown(f"""
                                    <div style='background:#0f1117; border:0.5px solid #1e2330; border-radius:10px; padding:12px; margin-top:-2px;'>
                                      <div style='font-size:10px; color:#6b7280; margin-bottom:8px;'>💰 수급 동향 · {date_fmt} 기준</div>
                                      <div style='margin-bottom:8px;'>
                                        <div style='display:flex; justify-content:space-between; margin-bottom:3px;'>
                                          <span style='font-size:11px; color:#9ca3af;'>🌍 외국인</span>
                                          <span style='font-size:11px; font-weight:600; color:{frgn_color};'>{frgn_arrow} {abs(frgn_amt_eok):,.1f}억원</span>
                                        </div>
                                        <div style='background:#1e2330; border-radius:4px; height:5px; width:100%;'>
                                          <div style='background:{frgn_color}; border-radius:4px; height:5px; width:{frgn_pct}%;'></div>
                                        </div>
                                      </div>
                                      <div>
                                        <div style='display:flex; justify-content:space-between; margin-bottom:3px;'>
                                          <span style='font-size:11px; color:#9ca3af;'>🏦 기관</span>
                                          <span style='font-size:11px; font-weight:600; color:{orgn_color};'>{orgn_arrow} {abs(orgn_amt_eok):,.1f}억원</span>
                                        </div>
                                        <div style='background:#1e2330; border-radius:4px; height:5px; width:100%;'>
                                          <div style='background:{orgn_color}; border-radius:4px; height:5px; width:{orgn_pct}%;'></div>
                                        </div>
                                      </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                            except Exception:
                                pass
            # ── [종목별 실시간 성적표 통합 렌더링 끝] ──

            if "backtest_results" not in st.session_state:
                st.session_state.backtest_results = load_backtest()
            col_save, col_clear = st.columns([3, 1])
            with col_save:
                display_name = name_map.get(chart_col.replace(".KS","").replace(".KQ",""), chart_col)
                save_label = st.text_input("결과 저장 이름", value=f"{display_name} {strategy[:3]} {dt.date.today()}", key="save_label")
            with col_clear:
                st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
                if st.button("💾 저장", key="save_backtest"):
                    result_entry = {
                        "이름": save_label, "종목": chart_col, "전략": strategy,
                        "수익률": round(strategy_pct, 2), "샤프": round(sharpe_s, 2),
                        "MDD": round(mdd_s, 2), "날짜": str(dt.date.today())
                    }
                    st.session_state.backtest_results.append(result_entry)
                    save_backtest(st.session_state.backtest_results)
                    st.success("저장됐어요!")
            if st.session_state.backtest_results:
                with st.expander("📋 저장된 백테스트 결과 비교", expanded=False):
                    bt_df = pd.DataFrame(st.session_state.backtest_results)
                    st.dataframe(bt_df, use_container_width=True, hide_index=True)
                    if st.button("🗑 전체 삭제", key="clear_backtest"):
                        st.session_state.backtest_results = []
                        save_backtest([])
                        st.rerun()

            last_tickers = st.session_state.get("last_tickers", [])
            if last_tickers:
                with st.expander("🚨 스트레스 테스트 — 과거 위기 시뮬레이션", expanded=False):
                    SCENARIOS = {
                        "코로나 폭락": ("2020-02-01", "2020-03-31"),
                        "금리인상 쇼크": ("2022-01-01", "2022-10-31"),
                        "미중 무역전쟁": ("2018-06-01", "2018-12-31"),
                        "글로벌 금융위기": ("2008-09-01", "2009-03-31"),
                        "미국-이란 전쟁": ("2026-02-28", "2026-04-30"),
                    }
                    selected = st.multiselect("시나리오 선택", options=list(SCENARIOS.keys()), default=[])
                    if selected:
                        stress_results = []
                        for scenario in selected:
                            s_start, s_end = SCENARIOS[scenario]
                            try:
                                s_df = yf.download(last_tickers, start=s_start, end=s_end, progress=False)["Close"]
                                if isinstance(s_df, pd.Series):
                                    s_df = s_df.to_frame()
                                if len(s_df) >= 2:
                                    s_ret = (s_df.iloc[-1] / s_df.iloc[0] - 1).mean() * 100
                                    stress_results.append({
                                        "시나리오": scenario,
                                        "기간": f"{s_start} ~ {s_end}",
                                        "예상 손익": f"{s_ret:+.1f}%",
                                        "평가": "🟢 선방" if s_ret > -10 else ("🟡 주의" if s_ret > -20 else "🔴 위험"),
                                        "_ret": s_ret
                                    })
                            except:
                                pass
                        if stress_results:
                            st.dataframe(
                                pd.DataFrame([{k: v for k, v in r.items() if k != "_ret"} for r in stress_results]),
                                use_container_width=True, hide_index=True
                            )
                            fig_stress = go.Figure(go.Bar(
                                x=[r["시나리오"] for r in stress_results],
                                y=[r["_ret"] for r in stress_results],
                                marker=dict(color=[CANDLE_UP if r["_ret"] >= 0 else CANDLE_DOWN for r in stress_results], opacity=0.85),
                                text=[f"{r['_ret']:+.1f}%" for r in stress_results],
                                textposition="outside",
                            ))
                            fig_stress.add_hline(y=0, line=dict(color=DIM, width=1, dash="dot"))
                            fig_stress.update_layout(
                                height=300, margin=dict(l=0, r=20, t=8, b=28),
                                paper_bgcolor=BG, plot_bgcolor=BG,
                                font=dict(family="Inter, sans-serif", color=TEXT, size=11),
                                yaxis=dict(ticksuffix="%", side="right"),
                                xaxis=dict(showgrid=False),
                            )
                            st.plotly_chart(fig_stress, use_container_width=True, config={"displayModeBar": False})

            if wf_test:
                card("🔄 워크포워드 테스트 결과", "과거로 최적화 → 미래로 검증 · 반복")
                col_a, col_b = st.columns(2)
                with col_a:
                    train_months = st.slider("학습 기간 (개월)", 12, 36, 24)
                with col_b:
                    test_months = st.slider("검증 기간 (개월)", 3, 12, 6)
                with st.spinner("워크포워드 테스트 진행 중..."):
                    wf_result = walk_forward_test(df, strategy, train_months, test_months)
                if wf_result.empty:
                    st.warning("데이터 기간이 너무 짧아요!")
                else:
                    avg_return = wf_result["검증 수익률 (%)"].mean()
                    positive_count = (wf_result["검증 수익률 (%)"] > 0).sum()
                    total_count = len(wf_result)
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("평균 검증 수익률", f"{avg_return:+.2f}%")
                    with col2:
                        st.metric("수익 구간", f"{positive_count}/{total_count}")
                    with col3:
                        st.metric("승률", f"{positive_count/total_count*100:.1f}%")
                    st.dataframe(wf_result.style.map(color_val, subset=["검증 수익률 (%)"]), use_container_width=True, hide_index=True)
                    fig_wf = go.Figure()
                    fig_wf.add_trace(go.Bar(
                        x=list(range(1, len(wf_result)+1)),
                        y=wf_result["검증 수익률 (%)"],
                        marker=dict(color=[CANDLE_UP if v > 0 else CANDLE_DOWN for v in wf_result["검증 수익률 (%)"]]),
                        text=[f"{v:+.1f}%" for v in wf_result["검증 수익률 (%)"]],
                        textposition="outside"
                    ))
                    fig_wf.add_hline(y=0, line=dict(color=DIM, width=1, dash="dot"))
                    fig_wf.update_layout(height=300, margin=dict(l=8, r=20, t=8, b=28), paper_bgcolor=SURFACE_1, plot_bgcolor=SURFACE_1, font=dict(color=TEXT, size=11))
                    st.plotly_chart(fig_wf, use_container_width=True, config={"displayModeBar": False})
                    st.warning("⚠️ 과거 데이터 기반 테스트예요!")

            if optimize:
                card("⚡ 파라미터 최적화 결과", "과거 데이터 기준 최적값 탐색 · 과최적화 주의!")
                with st.spinner("최적값 탐색 중..."):
                    result_df = optimize_parameters(df, strategy)
                    best = result_df.loc[result_df["수익률 (%)"].idxmax()]
                    if strategy == "RSI 전략 (RSI)":
                        st.success(f"✅ 최적 RSI 기준값: **{int(best['RSI 기준값'])}** → 수익률 **{best['수익률 (%)']:+.2f}%**")
                        fig_opt = go.Figure()
                        fig_opt.add_trace(go.Bar(
                            x=result_df["RSI 기준값"], y=result_df["수익률 (%)"],
                            marker=dict(color=[CANDLE_UP if v == best["RSI 기준값"] else ACCENT for v in result_df["RSI 기준값"]]),
                            text=[f"{v:+.1f}%" for v in result_df["수익률 (%)"]],
                            textposition="outside"
                        ))
                        fig_opt.update_layout(height=300, margin=dict(l=8, r=20, t=8, b=28), paper_bgcolor=SURFACE_1, plot_bgcolor=SURFACE_1, font=dict(color=TEXT, size=11))
                        st.plotly_chart(fig_opt, use_container_width=True, config={"displayModeBar": False})
                    if strategy == "MACD 전략 (MACD)":
                        st.success(f"✅ 최적 MACD: Fast **{int(best['Fast EMA'])}** / Slow **{int(best['Slow EMA'])}** → 수익률 **{best['수익률 (%)']:+.2f}%**")
                    elif strategy == "볼린저 밴드 전략 (Bollinger Bands)":
                        st.success(f"✅ 최적 BB 기간: **{int(best['BB 기간'])}** → 수익률 **{best['수익률 (%)']:+.2f}%**")
                        fig_opt = go.Figure()
                        fig_opt.add_trace(go.Bar(
                            x=result_df["BB 기간"], y=result_df["수익률 (%)"],
                            marker=dict(color=[CANDLE_UP if v == best["BB 기간"] else ACCENT for v in result_df["BB 기간"]]),
                            text=[f"{v:+.1f}%" for v in result_df["수익률 (%)"]],
                            textposition="outside"
                        ))
                        fig_opt.update_layout(height=300, margin=dict(l=8, r=20, t=8, b=28), paper_bgcolor=SURFACE_1, plot_bgcolor=SURFACE_1, font=dict(color=TEXT, size=11))
                        st.plotly_chart(fig_opt, use_container_width=True, config={"displayModeBar": False})
                    elif strategy == "MACD 전략 (MACD)":
                        st.success(f"✅ 최적 MACD: Fast **{int(best['Fast EMA'])}** / Slow **{int(best['Slow EMA'])}** → 수익률 **{best['수익률 (%)']:+.2f}%**")
                    else:
                        st.success(f"✅ 최적값: RSI **{int(best['RSI'])}** / 단기MA **{int(best['단기 MA'])}** / 장기MA **{int(best['장기 MA'])}** → 수익률 **{best['수익률 (%)']:+.2f}%**")
                    st.dataframe(result_df.sort_values("수익률 (%)", ascending=False).head(10).style.map(color_val, subset=["수익률 (%)"]), use_container_width=True, hide_index=True)
                st.warning("⚠️ 과최적화 주의!")

    # ── SUB 3 : 재무 & 뉴스 ──
    with sub3:
        if not analyzed:
            st.info("사이드바에서 종목을 입력하고 🔍 분석 시작 버튼을 눌러주세요!")
        else:
            card("📊 재무제표", "ROE · PER · PBR · 시가총액 · EPS · BPS · 배당 정보 (DART 공식 및 실시간 연동)")
            try:
                raw_ticker = chart_col.replace(".KS", "").replace(".KQ", "")
                fi = load_krx_listing()
                code_col = next((c for c in ['Symbol', 'Code', 'code'] if c in fi.columns), None) if fi is not None else None
                row = fi[fi[code_col].astype(str).str.split('.').str[0].str.zfill(6) == raw_ticker] if code_col and fi is not None else pd.DataFrame()

                if fi is not None and not row.empty:
                    mkt = row.iloc[0].get('Marcap', 0)
                    mkt_str = f"{int(mkt)/1e12:.1f}조" if mkt else 'N/A'
                    curr_p = float(close_p.iloc[-1]) if not close_p.empty else 0

                    from dart_utils import get_dart_roe, get_dart_per_pbr
                    roe = get_dart_roe(raw_ticker)
                    roe_str = f"{roe:.1f}%" if roe is not None else "N/A"
                    dart_per, dart_pbr = get_dart_per_pbr(raw_ticker, curr_p)
                    per = f"{dart_per:.1f}배" if dart_per is not None else "N/A"
                    pbr = f"{dart_pbr:.1f}배" if dart_pbr is not None else "N/A"
                    eps, bps, div_yield, div_payout, div_per_share = "N/A", "N/A", "N/A", "N/A", "N/A"

                    try:
                        nv_url = f"https://m.stock.naver.com/api/stock/{raw_ticker}/integration"
                        nv_res = requests.get(nv_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
                        nv_data = nv_res.json()
                        total_infos = nv_data.get("totalInfos", [])

                        def clean_val(val_str):
                            return val_str.replace("원", "").replace("%", "").replace("배", "").replace("x", "").replace(",", "").strip()

                        for info in total_infos:
                            k = str(info.get("key", "")).upper()
                            c = str(info.get("code", "")).lower()
                            v = str(info.get("value", "")).strip()
                            if not v or v == "-":
                                continue
                            val_clean = clean_val(v)
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
                                mkt_str = v
                    except:
                        pass

                    st.markdown(f"""
                    <div class="qf-toss-grid" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; background: #0f1117; padding: 18px; border-radius: 14px; border: 0.5px solid #1e2330;">
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
with tab4:
    from report import render_report
    render_report()

with tab5:
    from deep_analysis import render_deep_analysis
    render_deep_analysis(KIS_AVAILABLE, get_kis_token)