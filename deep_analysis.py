import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import datetime as dt
from data_utils import load_krx_listing, get_krx_name_map
from ui_components import card, ACCENT, CANDLE_UP, CANDLE_DOWN, DIM, TEXT, SURFACE_1, SURFACE_2, LINE, BG


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
        hist = yf.download(ticker, period="1y", progress=False)
        if hist.empty:
            st.error("주가 데이터를 불러오지 못했어요. 종목코드를 확인해주세요.")
            return

        close = hist["Close"].squeeze()
        high = hist["High"].squeeze()
        low = hist["Low"].squeeze()
        volume = hist["Volume"].squeeze()
        open_p = hist["Open"].squeeze()

    st.markdown(f"<div style='font-size:18px; font-weight:700; margin:16px 0 4px;'>{display_name} ({raw_ticker})</div>", unsafe_allow_html=True)
    curr_price = float(close.iloc[-1])
    prev_price = float(close.iloc[-2])
    chg = curr_price - prev_price
    chg_pct = chg / prev_price * 100
    chg_color = CANDLE_UP if chg >= 0 else CANDLE_DOWN
    chg_arrow = "▲" if chg >= 0 else "▼"
    st.markdown(f"""
    <div style='font-family:JetBrains Mono; font-size:28px; font-weight:700;'>{curr_price:,.0f}원
        <span style='font-size:16px; color:{chg_color}; margin-left:8px;'>{chg_arrow} {chg:+,.0f} ({chg_pct:+.2f}%)</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ══════════════════════════════════════════
    # 1. 재무제표 분석
    # ══════════════════════════════════════════
    card("📊 재무제표 분석", "매출/영업이익 추이 · PER/PBR 밸류에이션")

    try:
        t = yf.Ticker(ticker)
        info = t.info
        financials = t.financials
        quarterly = t.quarterly_financials

        # 연간 재무 차트
        if financials is not None and not financials.empty:
            rev_row = next((r for r in ["Total Revenue", "Revenue"] if r in financials.index), None)
            op_row = next((r for r in ["Operating Income", "EBIT"] if r in financials.index), None)

            if rev_row or op_row:
                fig_fin = go.Figure()
                years = [str(c.year) for c in financials.columns[:4]][::-1]

                if rev_row:
                    rev_vals = [financials.loc[rev_row, c] / 1e8 for c in financials.columns[:4]][::-1]
                    fig_fin.add_trace(go.Bar(
                        x=years, y=rev_vals, name="매출액(억원)",
                        marker_color=ACCENT, opacity=0.7
                    ))
                if op_row:
                    op_vals = [financials.loc[op_row, c] / 1e8 for c in financials.columns[:4]][::-1]
                    fig_fin.add_trace(go.Bar(
                        x=years, y=op_vals, name="영업이익(억원)",
                        marker_color=CANDLE_UP, opacity=0.9
                    ))

                fig_fin.update_layout(
                    barmode="group", height=300,
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color=TEXT, size=11),
                    margin=dict(l=0, r=0, t=20, b=20),
                    legend=dict(orientation="h", y=1.1),
                    yaxis=dict(gridcolor=LINE)
                )
                st.plotly_chart(fig_fin, use_container_width=True, config={"displayModeBar": False})

        # 밸류에이션 지표
        per = info.get("trailingPE", None)
        pbr = info.get("priceToBook", None)
        roe = info.get("returnOnEquity", None)
        eps = info.get("trailingEps", None)
        mkt_cap = info.get("marketCap", None)
        div_yield = info.get("dividendYield", None)

        v1, v2, v3, v4, v5, v6 = st.columns(6)
        for col, label, value in [
            (v1, "PER", f"{per:.1f}배" if per else "N/A"),
            (v2, "PBR", f"{pbr:.1f}배" if pbr else "N/A"),
            (v3, "ROE", f"{roe*100:.1f}%" if roe else "N/A"),
            (v4, "EPS", f"{eps:,.0f}원" if eps else "N/A"),
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
    card("📈 기술적 분석", "RSI · 이동평균 · 볼린저밴드 · 52주 위치")

    try:
        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi_val = float(rsi.iloc[-1])

        # 이동평균
        ma20 = close.rolling(20).mean()
        ma60 = close.rolling(60).mean()
        ma120 = close.rolling(120).mean()

        # 볼린저밴드
        bb_mid = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        bb_upper = bb_mid + 2 * bb_std
        bb_lower = bb_mid - 2 * bb_std

        # 52주 위치
        high_52 = float(high.rolling(252).max().iloc[-1])
        low_52 = float(low.rolling(252).min().iloc[-1])
        pos_52 = (curr_price - low_52) / (high_52 - low_52) * 100 if high_52 != low_52 else 50

        # RSI 상태
        if rsi_val < 30:
            rsi_label = "과매도 🔴"
            rsi_color = CANDLE_UP
        elif rsi_val > 70:
            rsi_label = "과매수 🔵"
            rsi_color = CANDLE_DOWN
        else:
            rsi_label = "중립 🟡"
            rsi_color = "#f59e0b"

        # MA 상태
        ma_status = "골든크로스 🟢" if float(ma20.iloc[-1]) > float(ma60.iloc[-1]) else "데드크로스 🔴"

        # BB 위치
        bb_pct = (curr_price - float(bb_lower.iloc[-1])) / (float(bb_upper.iloc[-1]) - float(bb_lower.iloc[-1])) * 100
        if bb_pct > 80:
            bb_label = "상단 근접 (과열)"
        elif bb_pct < 20:
            bb_label = "하단 근접 (침체)"
        else:
            bb_label = "중간 구간"

        # 지표 카드
        t1, t2, t3, t4 = st.columns(4)
        for col, label, value, sub in [
            (t1, "RSI (14)", f"{rsi_val:.1f}", rsi_label),
            (t2, "이동평균", ma_status, f"MA20: {float(ma20.iloc[-1]):,.0f}"),
            (t3, "볼린저밴드", bb_label, f"위치: {bb_pct:.0f}%"),
            (t4, "52주 위치", f"{pos_52:.1f}%", f"고가: {high_52:,.0f} / 저가: {low_52:,.0f}"),
        ]:
            with col:
                st.markdown(f"""
                <div style='background:{SURFACE_2}; border:0.5px solid {LINE}; border-radius:10px; padding:12px; margin-bottom:8px;'>
                    <div style='font-size:10px; color:{DIM}; margin-bottom:4px;'>{label}</div>
                    <div style='font-size:14px; font-weight:700;'>{value}</div>
                    <div style='font-size:10px; color:{DIM}; margin-top:2px;'>{sub}</div>
                </div>
                """, unsafe_allow_html=True)

        # 차트
        fig_tech = go.Figure()
        fig_tech.add_trace(go.Scatter(x=close.index[-60:], y=bb_upper.iloc[-60:], name="BB상단", line=dict(color="#ef4444", width=1, dash="dash"), opacity=0.5))
        fig_tech.add_trace(go.Scatter(x=close.index[-60:], y=bb_lower.iloc[-60:], name="BB하단", line=dict(color="#3b82f6", width=1, dash="dash"), opacity=0.5, fill="tonexty", fillcolor="rgba(99,102,241,0.05)"))
        fig_tech.add_trace(go.Scatter(x=close.index[-60:], y=close.iloc[-60:], name="주가", line=dict(color=ACCENT, width=2)))
        fig_tech.add_trace(go.Scatter(x=close.index[-60:], y=ma20.iloc[-60:], name="MA20", line=dict(color="orange", width=1.2)))
        fig_tech.add_trace(go.Scatter(x=close.index[-60:], y=ma60.iloc[-60:], name="MA60", line=dict(color="#a855f7", width=1.2)))
        fig_tech.update_layout(
            height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT, size=11), margin=dict(l=0, r=0, t=20, b=20),
            legend=dict(orientation="h", y=1.1), yaxis=dict(gridcolor=LINE), xaxis=dict(gridcolor=LINE)
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
                    frgn_vals = [int(o.get("frgn_ntby_tr_pbmn", 0)) / 100 for o in output][::-1]
                    orgn_vals = [int(o.get("orgn_ntby_tr_pbmn", 0)) / 100 for o in output][::-1]

                    fig_supply = go.Figure()
                    fig_supply.add_trace(go.Bar(
                        x=dates_fmt, y=frgn_vals, name="외국인(억원)",
                        marker_color=[CANDLE_UP if v >= 0 else CANDLE_DOWN for v in frgn_vals],
                        opacity=0.85
                    ))
                    fig_supply.add_trace(go.Bar(
                        x=dates_fmt, y=orgn_vals, name="기관(억원)",
                        marker_color=["rgba(168,85,247,0.8)" if v >= 0 else "rgba(59,130,246,0.8)" for v in orgn_vals],
                        opacity=0.85
                    ))
                    fig_supply.add_hline(y=0, line=dict(color=DIM, width=1, dash="dot"))
                    fig_supply.update_layout(
                        barmode="group", height=320,
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color=TEXT, size=11),
                        margin=dict(l=0, r=0, t=20, b=20),
                        legend=dict(orientation="h", y=1.1),
                        yaxis=dict(gridcolor=LINE, ticksuffix="억"),
                        xaxis=dict(gridcolor=LINE)
                    )
                    st.plotly_chart(fig_supply, use_container_width=True, config={"displayModeBar": False})

                    # 요약 카드
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
                                <div style='font-size:13px; font-weight:700; color:{color}; font-family:JetBrains Mono;'>{arrow} {abs(val):,.1f}억</div>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.info("수급 데이터를 불러오지 못했어요.")
            else:
                st.info("KIS 토큰을 불러오지 못했어요.")
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
        sector = yf.Ticker(ticker).info.get("sector", "")
        industry = yf.Ticker(ticker).info.get("industry", "")

        # 섹터별 대표 경쟁사 매핑
        competitors_map = {
            "Technology": ["005930.KS", "000660.KS", "035420.KS"],
            "Consumer Cyclical": ["005380.KS", "000270.KS", "012330.KS"],
            "Financial Services": ["105560.KS", "055550.KS", "086790.KS"],
            "Industrials": ["042660.KS", "009540.KS", "011200.KS"],
            "Healthcare": ["068270.KS", "207940.KS", "128940.KS"],
        }

        comp_tickers = competitors_map.get(sector, [])
        if ticker not in comp_tickers:
            comp_tickers = [ticker] + comp_tickers[:3]
        else:
            comp_tickers = [ticker] + [t for t in comp_tickers if t != ticker][:3]

        comp_data = []
        for ct in comp_tickers:
            try:
                ci = yf.Ticker(ct).info
                ct_raw = ct.replace(".KS", "").replace(".KQ", "")
                comp_data.append({
                    "종목": name_map.get(ct_raw, ct_raw),
                    "현재가": f"{ci.get('currentPrice', ci.get('regularMarketPrice', 0)):,.0f}원" if ci.get('currentPrice') else "N/A",
                    "PER": f"{ci.get('trailingPE', 0):.1f}배" if ci.get('trailingPE') else "N/A",
                    "PBR": f"{ci.get('priceToBook', 0):.1f}배" if ci.get('priceToBook') else "N/A",
                    "ROE": f"{ci.get('returnOnEquity', 0)*100:.1f}%" if ci.get('returnOnEquity') else "N/A",
                    "시가총액": f"{ci.get('marketCap', 0)/1e12:.1f}조" if ci.get('marketCap') else "N/A",
                    "_is_target": ct == ticker
                })
            except:
                pass

        if comp_data:
            df_comp = pd.DataFrame(comp_data).drop(columns=["_is_target"])
            st.dataframe(df_comp, use_container_width=True, hide_index=True)
        else:
            st.info("경쟁사 데이터를 불러오지 못했어요.")
    except Exception as e:
        st.info(f"경쟁사 비교 실패: {e}")

    st.markdown("---")

    # ══════════════════════════════════════════
    # 5. AI 종합 투자의견
    # ══════════════════════════════════════════
    card("🤖 AI 종합 투자의견", "재무·기술적·수급 데이터 기반 AI 분석 (참고용, 투자 책임은 본인에게 있습니다)")

    if st.button("🤖 AI 투자의견 생성", use_container_width=True, key="ai_opinion_btn"):
        with st.spinner("AI가 종목을 분석하는 중..."):
            try:
                # 데이터 수집
                t_info = yf.Ticker(ticker).info
                curr_per = t_info.get("trailingPE", "N/A")
                curr_pbr = t_info.get("priceToBook", "N/A")
                curr_roe = t_info.get("returnOnEquity", "N/A")
                target_price_analyst = t_info.get("targetMeanPrice", "N/A")

                prompt = f"""당신은 국내 최고 수준의 증권사 리서치센터 수석 애널리스트입니다.
아래 데이터를 바탕으로 {display_name}({raw_ticker})에 대한 전문 투자 리포트를 작성해주세요.

[기본 정보]
- 현재가: {curr_price:,.0f}원
- PER: {curr_per}
- PBR: {curr_pbr}
- ROE: {curr_roe}
- 애널리스트 평균 목표주가: {target_price_analyst}원

[기술적 분석]
- RSI(14): {rsi_val:.1f} ({rsi_label})
- 이동평균: {ma_status}
- 볼린저밴드 위치: {bb_pct:.0f}%
- 52주 위치: {pos_52:.1f}% (저점 대비)
- 52주 고가: {high_52:,.0f}원 / 저가: {low_52:,.0f}원

[작성 규칙]
1. 반드시 한국어로만 작성
2. 수치 근거를 반드시 포함
3. 단기(1개월)/중기(3개월)/장기(6개월) 관점 구분
4. 투자의견은 반드시 매수/중립/매도 중 하나로 명시
5. 목표주가는 현재가 기준 상승/하락 여력(%)도 함께 제시
6. 이 분석은 참고용이며 투자 책임은 본인에게 있음을 명시

아래 형식으로 작성:

【투자의견】 매수 / 중립 / 매도 (하나만 선택)
【목표주가】 X,XXX원 (현재가 대비 +X% / -X%)

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
                        "max_tokens": 1000
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

        # 투자의견 배지 색상
        if "매수" in opinion_text[:50]:
            badge_color = CANDLE_UP
            badge_text = "매수"
        elif "매도" in opinion_text[:50]:
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