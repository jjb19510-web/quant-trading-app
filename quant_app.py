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

@st.cache_data(ttl=3600)
def get_kis_token():
    try:
        return get_access_token()
    except:
        return None

tab1, tab2, tab3 = st.tabs(["📊 대시보드", "🔍 분석", "💼 포트폴리오"])

# ════════════════════════════════
# 탭 1 — 대시보드
# ════════════════════════════════
with tab1:
    render_dashboard()

# ════════════════════════════════
# 탭 2 — 분석
# ════════════════════════════════
with tab2:
    with st.sidebar:
        st.markdown("<div style='font-size:18px; font-weight:600; margin-bottom:16px;'>⚙️ Settings</div>", unsafe_allow_html=True)

        if KIS_AVAILABLE:
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
                        <div style='font-size:11px; color:#6b7280; margin-bottom:6px;'>💼 계좌 현황</div>
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
            st.divider()

        market = st.selectbox("시장 선택 (Market)", ["한국주식 (KS)", "미국주식 (US)"])

        if st.session_state.watchlist:
            st.markdown("<div style='font-size:12px; color:#6b7280; margin-bottom:6px;'>⭐ 관심종목</div>", unsafe_allow_html=True)
            for witem in st.session_state.watchlist:
                col_w, col_d = st.columns([4, 1])
                with col_w:
                    if st.button(witem, key=f"wl_{witem}", use_container_width=True):
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
            st.divider()

        if market == "한국주식 (KS)":
            st.markdown("<div style='font-size:13px; font-weight:600; margin-bottom:4px;'>🔍 종목 검색</div>", unsafe_allow_html=True)
            st.caption("예시: 005930, 000660, 373220")
            default_ticker = st.session_state.get("selected_ticker", "")
            tickers_raw = st.text_input("종목명 또는 코드 입력 (쉼표로 구분)", value=default_ticker)
            tickers = [t.strip() + ".KS" for t in tickers_raw.split(",") if t.strip()]
        else:
            st.markdown("<div style='font-size:13px; font-weight:600; margin-bottom:4px;'>🔍 종목 검색</div>", unsafe_allow_html=True)
            st.caption("예시: AAPL, TSLA, NVDA")
            default_ticker = st.session_state.get("selected_ticker", "")
            tickers_raw = st.text_input("티커 입력 (쉼표로 구분)", value=default_ticker)
            tickers = [t.strip() for t in tickers_raw.split(",") if t.strip()]

        if tickers_raw.strip():
            if st.button("⭐ 관심종목 추가", use_container_width=True):
                new_items = [t.strip() for t in tickers_raw.split(",") if t.strip()]
                for item in new_items:
                    if item not in st.session_state.watchlist:
                        st.session_state.watchlist.append(item)
                save_watchlist(st.session_state.watchlist)
                st.rerun()

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

        st.divider()
        st.markdown("<div style='font-size:13px; font-weight:600; margin-bottom:8px;'>🎯 목표가 · 손절가</div>", unsafe_allow_html=True)
        target_pct = st.number_input("목표 수익률 (%)", min_value=1, max_value=200, value=20, step=5)
        stop_pct = st.number_input("손절 라인 (%)", min_value=1, max_value=50, value=10, step=1)
        st.divider()
        st.markdown("<div style='font-size:13px; font-weight:600; margin-bottom:8px;'>💰 투입금액 설정</div>", unsafe_allow_html=True)
        investment = st.number_input("투입금액 (만원)", min_value=0, value=1000, step=100)
        st.caption(f"= {investment:,}만원 ({investment * 10000:,}원)")

        st.divider()
        st.markdown("<div style='font-size:13px; font-weight:600; margin-bottom:8px;'>📂 섹터 관리</div>", unsafe_allow_html=True)
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

        analyze = st.button("🔍 분석 시작", use_container_width=True)
        optimize = st.button("⚡ 최적값 자동 탐색", use_container_width=True)
        wf_test = st.button("🔄 워크포워드 테스트", use_container_width=True)

    # ── 오늘 신호 현황 ──
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

    if wf_test:
        if not tickers:
            st.warning("종목을 입력해주세요!")
        else:
            with st.spinner("데이터 불러오는 중..."):
                df = yf.download(tickers, start=start_date, end=end_date)["Close"]
            if isinstance(df, pd.Series):
                df = df.to_frame()
            df.columns = [str(c) for c in df.columns]
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
        if not tickers:
            st.warning("종목을 입력해주세요!")
        else:
            with st.spinner("데이터 불러오는 중..."):
                df = yf.download(tickers, start=start_date, end=end_date)["Close"]
            if isinstance(df, pd.Series):
                df = df.to_frame()
            df.columns = [str(c) for c in df.columns]
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

    if analyze:
        if not tickers:
            st.warning("종목을 입력해주세요!")
        else:
            with st.spinner("데이터 불러오는 중..."):
                ohlc = yf.download(tickers, start=start_date, end=end_date)
                df = ohlc["Close"]
                if isinstance(df, pd.Series):
                    df = df.to_frame()
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

            strategy_pct, weighted_return, signal, rsi, ma_s, ma_l, bb_upper, bb_lower, bb_mid = run_strategy(
                df, strategy, rsi_threshold, ma_short, ma_long, bb_period
            )
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

            render_kpi_strip(strategy_pct, equal_pct, cagr_s, cagr_e, sharpe_s, sharpe_e, mdd_s, mdd_e)
            render_strategy_expander(strategy)

            last_sig = signal.iloc[-1].values[0]
            last_rsi = rsi[chart_col].iloc[-1] if isinstance(rsi, pd.DataFrame) else rsi.iloc[-1]
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

            # ── 스트레스 테스트 ──
            with st.expander("🚨 스트레스 테스트 — 과거 위기 시뮬레이션", expanded=False):
                SCENARIOS = {
                    "코로나 폭락": ("2020-02-01", "2020-03-31"),
                    "금리인상 쇼크": ("2022-01-01", "2022-10-31"),
                    "미중 무역전쟁": ("2018-06-01", "2018-12-31"),
                    "글로벌 금융위기": ("2008-09-01", "2009-03-31"),
                    "미국-이란 전쟁": ("2026-02-28", "2026-04-30"),
                }
                selected = st.multiselect(
                    "시나리오 선택",
                    options=list(SCENARIOS.keys()),
                    default=[]
                )
                if selected and tickers:
                    stress_results = []
                    for scenario in selected:
                        s_start, s_end = SCENARIOS[scenario]
                        try:
                            s_df = yf.download(tickers, start=s_start, end=s_end, progress=False)["Close"]
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
                elif not tickers:
                    st.info("사이드바에서 종목을 먼저 입력해주세요!")

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
            card("💰 수익률 비교", "누적 수익률 (%)")
            st.plotly_chart(make_return_chart(portfolio_equal, portfolio_strategy, strategy), use_container_width=True, config={"displayModeBar": False, "scrollZoom": True})

            col1, col2 = st.columns([1, 1])
            with col1:
                card("📉 낙폭 (Drawdown)", "고점 대비 하락폭")
                st.plotly_chart(make_drawdown_chart(portfolio_strategy), use_container_width=True, config={"displayModeBar": False, "scrollZoom": True})
            with col2:
                card("📅 월별 수익률", "막대가 위로 → 수익 🔴 · 아래로 → 손실 🔵")
                st.plotly_chart(make_monthly_bar_chart(weighted_return), use_container_width=True, config={"displayModeBar": False})

            card("📊 종목별 성과", "기간 수익률 및 현재 포지션")
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

            card("📊 재무 지표", "PER · PBR · 시가총액 · 52주 범위")
            try:
                import FinanceDataReader as fdr
                raw_ticker = chart_col.replace(".KS", "").replace(".KQ", "")
                fi = fdr.StockListing('KRX')
                row = fi[fi['Code'] == raw_ticker]
                if not row.empty:
                    mkt = row.iloc[0].get('Marcap', 0)
                    mkt_str = f"{int(mkt)/1e12:.1f}조" if mkt else 'N/A'
                    high52 = row.iloc[0].get('High', 'N/A')
                    low52 = row.iloc[0].get('Low', 'N/A')
                    per, pbr = 'N/A', 'N/A'
                    try:
                        nv_url = f"https://m.stock.naver.com/api/stock/{raw_ticker}/investment"
                        nv_res = requests.get(nv_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
                        nv_data = nv_res.json()
                        per_val = nv_data.get("per", None)
                        pbr_val = nv_data.get("pbr", None)
                        if per_val: per = f"{float(per_val):.1f}x"
                        if pbr_val: pbr = f"{float(pbr_val):.1f}x"
                    except:
                        pass
                    f1, f2, f3, f4, f5 = st.columns(5)
                    with f1:
                        st.metric("PER", per, help="주가수익비율 — 낮을수록 저평가")
                    with f2:
                        st.metric("PBR", pbr, help="주가순자산비율")
                    with f3:
                        st.metric("시가총액", mkt_str)
                    with f4:
                        st.metric("52주 고가", f"{int(high52):,}원" if high52 != 'N/A' else 'N/A')
                    with f5:
                        st.metric("52주 저가", f"{int(low52):,}원" if low52 != 'N/A' else 'N/A')
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
                        <div style='background:{SURFACE_1}; border:0.5px solid {LINE}; border-radius:10px; padding:12px 14px; margin-bottom:8px;'>
                            <a href='{link}' target='_blank' style='color:{TEXT}; text-decoration:none; font-size:13px; font-weight:500;'>{title}</a>
                            <div style='font-size:11px; color:{DIM}; margin-top:4px;'>{date}</div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("뉴스를 불러오지 못했어요.")
            except:
                st.info("뉴스를 불러오지 못했어요.")

            st.caption(f"Data: yfinance · {df.index[0].date()} → {df.index[-1].date()} · {len(df)} trading days")

# ════════════════════════════════
# 탭 3 — 포트폴리오
# ════════════════════════════════
with tab3:
    render_portfolio(KIS_AVAILABLE, get_kis_token, get_balance if KIS_AVAILABLE else lambda x: {})
