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
                        
                        t_clean_fixed = t_clean.replace("테이먼트", "테인먼트").replace("엔터테이먼트", "엔터테인먼트").replace("YG", "와이지").replace("yg", "와이지").replace("에스케이", "SK").replace("엘지", "LG")
                        
                        if not t_clean_fixed.isdigit() and df_krx is not None:
                            matched = df_krx[df_krx['Name'].str.upper() == t_clean_fixed.upper()]
                            if matched.empty:
                                matched = df_krx[df_krx['Name'].str.upper().str.contains(t_clean_fixed.upper(), na=False)]
                                
                            if not matched.empty:
                                code_col = next((c for c in ['Symbol', 'Code', 'code'] if c in df_krx.columns), None)
                                if code_col:
                                    raw_code = matched.iloc[0][code_col]
                                    code = str(raw_code).split('.')[0].zfill(6)
                                    mkt_info = str(matched.iloc[0].get('Market', 'KOSPI')).upper()
                                    suffix = ".KS" if "KOSPI" in mkt_info else ".KQ"
                                    tickers_list.append(code + suffix)
                                else:
                                    tickers_list.append(t_clean_fixed + ".KS")
                            else:
                                tickers_list.append(t_clean_fixed + ".KS")
                        else:
                            code_padded = t_clean_fixed.zfill(6) if len(t_clean_fixed) < 6 else t_clean_fixed
                            if df_krx is not None:
                                code_col = next((c for c in ['Symbol', 'Code', 'code'] if c in df_krx.columns), None)
                                if code_col:
                                    matched_code = df_krx[df_krx[code_col].astype(str).str.split('.').str[0].str.zfill(6) == code_padded]
                                    if not matched_code.empty:
                                        mkt_info = str(matched_code.iloc[0].get('Market', 'KOSPI')).upper()
                                        suffix = ".KS" if "KOSPI" in mkt_info else ".KQ"
                                        tickers_list.append(code_padded + suffix)
                                        continue
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
                rsi_threshold = st.slider("돌파 계수 (K)", 0.40, 0.90, 0.50, 0.05, help="수급 강도 결정 계수입니다. 래리 윌리엄스 표준값은 0.50 입니다.")
                ma_short, ma_long, bb_period = 20, 60, 20
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
        
        if strategy == "변동성 돌파 전략 (Volatility Breakout)":
            optimize = False
            wf_test = False
            st.sidebar.caption("💡 변동성 돌파 전략은 고정 상수 K=0.50을 표준으로 삼으므로, 최적화가 비활성화됩니다.")
        else:
            optimize = st.button("⚡ 최적값 자동 탐색", use_container_width=True)
            wf_test = st.button("🔄 워크포워드 테스트", use_container_width=True)

    # ── [전략 분석 공통 연산 영역] ──
    if analyze:
        st.session_state["analyzed"] = True

    analyzed = st.session_state.get("analyzed") and 'tickers' in locals() and tickers

    if analyzed:
        target_name = tickers_raw.strip() if tickers_raw else "선택 종목"
        with st.spinner(f"📡 {target_name}의 마켓 데이터 수집 및 백테스트 분석 진행 중..."):
            df, open_p, high_p, low_p, close_p, volume = load_market_data(tuple(tickers), start_date, end_date, market)

        if df.empty or 'close_p' not in locals() or close_p.empty:
            st.error("❌ 주가 데이터 서버(Yahoo Finance/Naver) 응답이 원활하지 않습니다. 잠시 후 다시 시도해 주세요.")
            st.stop()

        chart_col = df.columns[0]
        fee_pct = st.session_state.get("main_fee_slider", 0.23)

        strategy_pct, weighted_return, signal, rsi, ma_s, ma_l, bb_upper, bb_lower, bb_mid = run_strategy(
            df, strategy, rsi_threshold, ma_short, ma_long, bb_period, fee_pct=fee_pct, open_p=open_p, high_p=high_p, low_p=low_p
        )
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

    # ── [메인 콘텐츠 서브탭 영역] ──
    sub1, sub2, sub3 = st.tabs(["📈 주가 & 신호", "📊 백테스트", "🔍 재무제표 & 뉴스"])

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
                            raw_ticker = ticker.replace(".KS", "")
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
                            <div style='font-size:12px; color:{DIM}; margin-bottom:4px;'>{ticker}</div>
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
                elif strategy == "MACD 전략 (MACD)":
                    reason = "MACD선이 시그널선을 상향 골든크로스 돌파 — 추세 전환, 매수 신호"
                elif strategy == "변동성 돌파 전략 (Volatility Breakout)":
                    reason = f"주가가 가상의 시가 돌파 타겟가(K={rsi_threshold})를 돌파 — 수급 상승, 매수 신호"
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
                    reason = "MACD선이 시그널선 아래 존재 — 추세 하락, 현금 대기"
                elif strategy == "변동성 돌파 전략 (Volatility Breakout)":
                    reason = "당일 돌파 기준선 돌파 실패 — 노이즈 방지, 현금 관망"
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
        
        # 슬라이더 조작에 반응하는 수수료 기반 주가 실시간 재연산 수행
        strategy_pct, weighted_return, signal, rsi, ma_s, ma_l, bb_upper, bb_lower, bb_mid = safe_run_strategy(
            df, strategy, rsi_threshold, ma_short, ma_long, bb_period, fee_pct=fee_pct, open_p=open_p, high_p=high_p, low_p=low_p
        )
        portfolio_strategy = (1 + weighted_return.fillna(0)).cumprod()
        mdd_s = calculate_mdd(portfolio_strategy)
        sharpe_s = calculate_sharpe(weighted_return.dropna())
        cagr_s = calculate_cagr(portfolio_strategy, days)
        strategy_profit = (investment * 10000) * (strategy_pct / 100)
        strategy_final = (investment * 10000) + strategy_profit
        excess = strategy_profit - equal_profit
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
            strategy_pct, weighted_return, signal, rsi, ma_s, ma_l, bb_upper, bb_lower, bb_mid = safe_run_strategy(
                df, strategy, rsi_threshold, ma_short, ma_long, bb_period, fee_pct=fee_pct, open_p=open_p, high_p=high_p, low_p=low_p
            )
            portfolio_strategy = (1 + weighted_return.fillna(0)).cumprod()
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
            
            # 라이브 한글 사명 변환 맵 추출
            name_map = get_krx_name_map()

            holdings_list_data = []
            for col in df.columns:
                col_idx = df.columns.get_loc(col)
                ticker_trade_count = int(trade_count_series.iloc[col_idx]) if isinstance(trade_count_series, pd.Series) else int(trade_count_series)
                
                # 종목 코드를 깔끔한 한글 사명으로 변환 (예: 047810.KS -> 디에이테크놀로지)
                raw_code = col.replace(".KS", "").replace(".KQ", "")
                display_name = name_map.get(raw_code, col)
                
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
                    "종목": display_name, # 코드 대신 수려한 한글 사명 대입
                    "세후 전략수익률": f"{ticker_return_pct:+.2f}%",
                    "예상 순수익금": f"{int(ticker_profit_won):+,}원",
                    "총 거래 횟수": f"{ticker_trade_count}회",
                    "누적 거래비용": f"{int(total_fee_won):,}원 ({total_fee_pct:.2f}%)",
                    "최종 평가자산": f"{int(ticker_final_won):,}원",
                    "현재 포지션": pos_status
                })
                
            holdings_df = pd.DataFrame(holdings_list_data)
            st.dataframe(holdings_df.style.map(color_val, subset=["세후 전략수익률", "예상 순수익금"]), use_container_width=True, hide_index=True)
            period_returns = (df.iloc[-1] / df.iloc[0] - 1) * 100
            volatility = df.pct_change().std() * (252 ** 0.5) * 100
            last_signal = signal.iloc[-1]
            if len(tickers) == 1:
                holdings = pd.DataFrame({
                    "종목": df.columns,
                    "수익률 (%)": period_returns.values.round(2),
                    "변동성 (%)": volatility.values.round(1),
                    "현재 포지션": ["보유중 ✅" if s == 1 else "현금 ❌" for s in last_signal.values]
                })
                st.dataframe(holdings.style.map(color_val, subset=["수익률 (%)"]), use_container_width=True, hide_index=True)
            else:
                weights = 1 / len(tickers)
                holdings = pd.DataFrame({
                    "종목": df.columns,
                    "수익률 (%)": period_returns.values.round(2),
                    "기여도 (pp)": (period_returns.values * weights).round(2),
                    "변동성 (%)": volatility.values.round(1),
                    "현재 포지션": ["보유중 ✅" if s == 1 else "현금 ❌" for s in last_signal.values]
                })
                st.dataframe(holdings.style.map(color_val, subset=["수익률 (%)", "기여도 (pp)"]), use_container_width=True, hide_index=True)

            # 백테스트 저장/비교
            if "backtest_results" not in st.session_state:
                st.session_state.backtest_results = load_backtest()
            col_save, col_clear = st.columns([3, 1])
            with col_save:
                save_label = st.text_input("결과 저장 이름", value=f"{chart_col} {strategy[:3]} {dt.date.today()}", key="save_label")
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

            # 스트레스 테스트 (last_tickers 기반)
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

            # 워크포워드 테스트
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

            # 최적화
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
                    elif strategy == "이동평균선 전략 (Moving Average)":
                        st.success(f"✅ 최적 MA: 단기 **{int(best['단기 MA'])}** / 장기 **{int(best['장기 MA'])}** → 수익률 **{best['수익률 (%)']:+.2f}%**")
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
                    else:
                        st.success(f"✅ 최적값: RSI **{int(best['RSI'])}** / 단기MA **{int(best['단기 MA'])}** / 장기MA **{int(best['장기 MA'])}** → 수익률 **{best['수익률 (%)']:+.2f}%**")
                    st.dataframe(result_df.sort_values("수익률 (%)", ascending=False).head(10).style.map(color_val, subset=["수익률 (%)"]), use_container_width=True, hide_index=True)
                st.warning("⚠️ 과최적화 주의!")