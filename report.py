import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import datetime as dt
import requests
from ui_components import (
    card, CANDLE_UP, CANDLE_DOWN, DIM, TEXT, SURFACE_1, SURFACE_2, LINE, BG, ACCENT
)

def render_report():
    st.markdown(
        "<div style='font-size:22px; font-weight:700; margin-bottom:4px;'>📋 Daily Quantfolio Report</div>"
        f"<div style='font-size:12px; color:{DIM}; margin-bottom:24px;'>{dt.datetime.now():%Y년 %m월 %d일 %H:%M} 기준</div>",
        unsafe_allow_html=True
    )

    report_type = st.radio("리포트 유형", ["📅 일간 리포트", "📆 주간 리포트"], horizontal=True)

    if report_type == "📅 일간 리포트":
        render_daily_report()
    else:
        render_weekly_report()


def render_daily_report():

    # ── 1. 시장 현황 ──
    card("🌐 시장 현황", "주요 지수 · 환율 · 원자재 실시간")

    @st.cache_data(ttl=300)
    def get_market_data():
        indices = {
            "코스피": "^KS11",
            "코스닥": "^KQ11",
            "나스닥": "^IXIC",
            "원/달러": "USDKRW=X",
            "WTI유": "CL=F",
            "금": "GC=F",
            "미국10년채": "^TNX"
        }
        result = []
        for name, ticker in indices.items():
            try:
                hist = yf.Ticker(ticker).history(period="5d").dropna(subset=["Close"])
                if len(hist) >= 2:
                    curr = hist["Close"].iloc[-1]
                    prev = hist["Close"].iloc[-2]
                    chg = curr - prev
                    chg_pct = (chg / prev) * 100
                    result.append({"name": name, "price": curr, "change": chg, "pct": chg_pct})
            except:
                pass
        return result

    with st.spinner("시장 데이터 불러오는 중..."):
        market_data = get_market_data()

    if market_data:
        cols = st.columns(4)
        for i, idx in enumerate(market_data):
            with cols[i % 4]:
                color = CANDLE_UP if idx["change"] >= 0 else CANDLE_DOWN
                arrow = "▲" if idx["change"] >= 0 else "▼"
                st.markdown(f"""
                <div style='background:{SURFACE_2}; border:0.5px solid {LINE}; border-radius:12px; padding:12px 16px; margin-bottom:12px; box-shadow:0 4px 24px rgba(0,0,0,0.4);'>
                    <div style='font-size:11px; color:#9ca3af; margin-bottom:4px; font-weight:500;'>{idx["name"]}</div>
                    <div style='font-family:JetBrains Mono; font-size:17px; font-weight:600;'>{idx["price"]:,.2f}</div>
                    <div style='font-family:JetBrains Mono; font-size:12px; color:{color}; margin-top:2px;'>{arrow} {idx["change"]:+,.2f} ({idx["pct"]:+.2f}%)</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)

    # ── 2. 관심종목 신호 리포트 ──
    if st.session_state.get("watchlist"):
        card("🔔 관심종목 신호 리포트", "RSI 기준 매수/매도 신호 · 내일 변동성 돌파 목표가")

        @st.cache_data(ttl=300)
        def get_signal_report(watchlist):
            from strategies import run_strategy, calculate_rsi
            rows = []
            for item in watchlist:
                ticker = item if item.endswith(".KS") or item.endswith(".KQ") else item + ".KS"
                try:
                    hist = yf.download(ticker, period="6mo", progress=False)
                    close = hist["Close"].squeeze()
                    high = hist["High"].squeeze()
                    low = hist["Low"].squeeze()

                    df_w = close.to_frame()
                    df_w.columns = [ticker]

                    _, _, sig, _, _, _, _, _, _ = run_strategy(df_w, "RSI 전략 (RSI)", 40, 20, 60, 20)
                    last_sig = sig.iloc[-1].values[0]
                    rsi_series = calculate_rsi(close)
                    rsi_val = float(rsi_series.iloc[-1])

                    today_open = float(hist["Open"].iloc[-1])
                    yesterday_high = float(high.iloc[-2])
                    yesterday_low = float(low.iloc[-2])
                    vb_target = today_open + (yesterday_high - yesterday_low) * 0.5

                    signal_str = "🟢 매수" if last_sig == 1 else "⚪ 관망"
                    rsi_label = "과매도" if rsi_val < 30 else ("과매수" if rsi_val > 70 else "중립")

                    rows.append({
                        "종목": item,
                        "신호": signal_str,
                        "RSI": f"{rsi_val:.1f} ({rsi_label})",
                        "내일 변동성 목표가": f"{int(vb_target):,}원",
                    })
                except:
                    pass
            return rows

        with st.spinner("신호 분석 중..."):
            signal_rows = get_signal_report(tuple(st.session_state.watchlist))

        if signal_rows:
            st.dataframe(pd.DataFrame(signal_rows), use_container_width=True, hide_index=True)

        st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)

    # ── 3. 포트폴리오 현황 ──
    try:
        from broker import get_access_token, get_balance
        token = get_access_token()
        balance_data = get_balance(token)
        if balance_data.get("rt_cd") == "0":
            card("💼 포트폴리오 현황", "KIS API 실시간 기준")
            output2 = balance_data.get("output2", [{}])[0]
            total_eval = int(output2.get("scts_evlu_amt", 0))
            total_profit = int(output2.get("evlu_pfls_smtl_amt", 0))
            cash = int(output2.get("dnca_tot_amt", 0))
            withdrawable = int(output2.get("nxdy_excc_amt", 0))

            profit_color = "#ef4444" if total_profit >= 0 else "#3b82f6"
            profit_arrow = "▲" if total_profit >= 0 else "▼"

            p1, p2, p3, p4 = st.columns(4)
            for col, label, value, color in [
                (p1, "💼 총 평가금액", f"{total_eval:,}원", TEXT),
                (p2, "📈 평가손익", f"{profit_arrow} {total_profit:+,}원", profit_color),
                (p3, "💰 예수금", f"{cash:,}원", TEXT),
                (p4, "🏧 출금가능", f"{withdrawable:,}원", TEXT),
            ]:
                with col:
                    st.markdown(f"""
                    <div style='background:{SURFACE_2}; border:0.5px solid {LINE}; border-radius:12px; padding:14px 16px; margin-bottom:12px; box-shadow:0 4px 24px rgba(0,0,0,0.4);'>
                        <div style='font-size:11px; color:#9ca3af; margin-bottom:6px;'>{label}</div>
                        <div style='font-size:17px; font-weight:600; font-family:JetBrains Mono; color:{color};'>{value}</div>
                    </div>
                    """, unsafe_allow_html=True)

            holdings = balance_data.get("output1", [])
            if holdings:
                hdf = pd.DataFrame([{
                    "종목": h.get("prdt_name", ""),
                    "수량": int(h.get("hldg_qty", 0)),
                    "현재가": f"{int(h.get('prpr', 0)):,}원",
                    "평균단가": f"{float(h.get('pchs_avg_pric', 0)):,.0f}원",
                    "평가손익": f"{float(h.get('evlu_pfls_amt', 0)):+,.0f}원",
                    "수익률": f"{float(h.get('evlu_pfls_rt', 0)):+.2f}%"
                } for h in holdings if int(h.get("hldg_qty", 0)) > 0])
                if not hdf.empty:
                    st.dataframe(hdf, use_container_width=True, hide_index=True)
    except:
        card("💼 포트폴리오 현황", "KIS API 연결 필요")
        st.info("KIS API가 연결되지 않았어요.")

    st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)

    # ── 4. 상관관계 붕괴 경보 ──
    if st.session_state.get("watchlist") and len(st.session_state.watchlist) >= 2:
        card("🚨 상관관계 붕괴 경보", "보유종목 간 롤링 상관관계 · 1.0에 가까울수록 분산 무력화")

        @st.cache_data(ttl=300)
        def get_rolling_corr(watchlist):
            price_data = {}
            for item in watchlist:
                ticker = item if item.endswith(".KS") or item.endswith(".KQ") else item + ".KS"
                try:
                    hist = yf.Ticker(ticker).history(period="3mo")["Close"]
                    if len(hist) > 0:
                        price_data[item] = hist
                except:
                    pass
            if len(price_data) >= 2:
                df_p = pd.DataFrame(price_data).dropna()
                return df_p.pct_change().corr()
            return None

        corr = get_rolling_corr(tuple(st.session_state.watchlist))
        if corr is not None:
            mask = ~np.eye(len(corr), dtype=bool)
            avg_corr = corr.where(mask).stack().mean()
            if avg_corr > 0.8:
                st.error(f"⚠️ 평균 상관관계 {avg_corr:.2f} — 분산 효과 거의 없음! 현금 비중 확대 권고")
            elif avg_corr > 0.6:
                st.warning(f"🟡 평균 상관관계 {avg_corr:.2f} — 분산 효과 약화 중, 주의 필요")
            else:
                st.success(f"🟢 평균 상관관계 {avg_corr:.2f} — 분산 효과 양호")

            fig_corr = go.Figure(go.Heatmap(
                z=corr.values,
                x=corr.columns.tolist(),
                y=corr.index.tolist(),
                colorscale=[[0, "#3b82f6"], [0.5, "#1a1f2e"], [1, "#ef4444"]],
                zmin=-1, zmax=1, zmid=0,
                text=[[f"{v:.2f}" for v in row] for row in corr.values],
                texttemplate="%{text}",
                textfont=dict(size=12, color=TEXT),
                colorbar=dict(thickness=8, tickfont=dict(color=DIM, size=9))
            ))
            fig_corr.update_layout(
                height=350, margin=dict(l=60, r=60, t=8, b=8),
                paper_bgcolor=BG, plot_bgcolor=BG,
                font=dict(family="Inter, sans-serif", color=TEXT, size=11),
                xaxis=dict(type="category"),
                yaxis=dict(type="category")
            )
            st.plotly_chart(fig_corr, use_container_width=True, config={"displayModeBar": False})

    st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)

    # ── 5. 스마트 머니 인덱스 ──
    card("🧠 스마트 머니 인덱스", "장 시작 30분 vs 마감 30분 등락 스프레드 · 기관·외인 의도 추적")
    try:
        from broker import get_access_token
        token = get_access_token()

        @st.cache_data(ttl=300)
        def get_smi(token):
            BASE_URL = "https://openapi.koreainvestment.com:9443"
            try:
                from broker import APP_KEY, APP_SECRET
            except:
                return None

            headers = {
                "content-type": "application/json",
                "authorization": f"Bearer {token}",
                "appkey": APP_KEY,
                "appsecret": APP_SECRET,
                "tr_id": "FHKST03010200"
            }
            today = dt.datetime.now().strftime("%Y%m%d")
            params = {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": "0001",
                "FID_INPUT_DATE_1": today,
                "FID_INPUT_DATE_2": today,
                "FID_PW_DATA_INCU_YN": "N"
            }
            res = requests.get(
                f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice",
                headers=headers, params=params
            )
            data = res.json()
            if data.get("rt_cd") == "0":
                output = data.get("output2", [])
                if len(output) >= 2:
                    return pd.DataFrame(output)
            return None

        smi_data = get_smi(token)
        if smi_data is not None:
            st.success("스마트 머니 인덱스 데이터 수집 완료")
        else:
            st.info("📊 장 중에만 스마트 머니 인덱스가 활성화돼요. (09:00 ~ 15:30)")
    except:
        st.info("📊 KIS API 연결 시 스마트 머니 인덱스가 활성화돼요.")

    st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)

    # ── 6. 수급 동향 ──
    card("💰 수급 동향", "외국인 · 기관 · 개인 순매수 상위 종목 (KIS API)")

    try:
        from broker import get_access_token, get_foreign_institution_trade
        token = st.session_state.get("kis_token")
        if not token:
            token = get_access_token()
            st.session_state["kis_token"] = token

        def parse_supply(data):
            rows = []
            for item in data.get("output", [])[:5]:
                name = item.get("hts_kor_isnm", "")
                buy = item.get("frgn_ntby_qty", "0")
                if name:
                    rows.append({"종목": name, "순매수(주)": buy})
            return rows

        with st.spinner("수급 데이터 불러오는 중..."):
            foreign_raw = get_foreign_institution_trade(token, div_cls="0")
            institution_raw = get_foreign_institution_trade(token, div_cls="1")
            individual_raw = get_foreign_institution_trade(token, div_cls="2")

        foreign_rows = parse_supply(foreign_raw)
        institution_rows = parse_supply(institution_raw)
        individual_rows = parse_supply(individual_raw)

        col_f, col_i, col_p = st.columns(3)
        with col_f:
            st.markdown("<div style='font-size:13px; font-weight:600; color:#9ca3af; margin-bottom:8px;'>🌍 외국인 순매수 TOP 5</div>", unsafe_allow_html=True)
            if foreign_rows:
                st.dataframe(pd.DataFrame(foreign_rows), use_container_width=True, hide_index=True)
            else:
                st.info("데이터 없음")
        with col_i:
            st.markdown("<div style='font-size:13px; font-weight:600; color:#9ca3af; margin-bottom:8px;'>🏦 기관 순매수 TOP 5</div>", unsafe_allow_html=True)
            if institution_rows:
                st.dataframe(pd.DataFrame(institution_rows), use_container_width=True, hide_index=True)
            else:
                st.info("데이터 없음")
        with col_p:
            st.markdown("<div style='font-size:13px; font-weight:600; color:#9ca3af; margin-bottom:8px;'>👤 개인 순매수 TOP 5</div>", unsafe_allow_html=True)
            if individual_rows:
                st.dataframe(pd.DataFrame(individual_rows), use_container_width=True, hide_index=True)
            else:
                st.info("데이터 없음")
    except Exception as e:
        st.info(f"수급 데이터를 불러오지 못했어요. ({e})")

    st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)

    # ── 7. 거래대금 상위 ──
    card("📊 거래대금 상위 TOP 10", "오늘 가장 많이 거래된 종목")

    @st.cache_data(ttl=300)
    def get_top_volume():
        try:
            from bs4 import BeautifulSoup
            headers = {"User-Agent": "Mozilla/5.0"}
            url = "https://finance.naver.com/sise/sise_quant.naver?sosok=0"
            res = requests.get(url, headers=headers, timeout=5)
            soup = BeautifulSoup(res.text, "html.parser")
            rows = soup.select("table.type_2 tr")
            result = []
            for row in rows[2:12]:
                cols = row.select("td")
                if len(cols) >= 3:
                    name = cols[1].text.strip()
                    price = cols[2].text.strip()
                    volume = cols[5].text.strip() if len(cols) > 5 else "-"
                    if name:
                        result.append({"종목": name, "현재가": price, "거래량": volume})
            return result
        except:
            return []

    with st.spinner("거래대금 데이터 불러오는 중..."):
        volume_data = get_top_volume()

    if volume_data:
        st.dataframe(pd.DataFrame(volume_data), use_container_width=True, hide_index=True)
    else:
        st.info("거래대금 데이터를 불러오지 못했어요.")

    st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)

    # ── 8. 시장 이슈 & 뉴스 ──
    card("📰 시장 이슈 & 뉴스", "오늘의 주요 시장 뉴스")
    try:
        naver_id = st.secrets.get("NAVER_CLIENT_ID", "")
        naver_secret = st.secrets.get("NAVER_CLIENT_SECRET", "")
        url = "https://openapi.naver.com/v1/search/news.json?query=주식+코스피&display=5&sort=date"
        res = requests.get(url, headers={
            "X-Naver-Client-Id": naver_id,
            "X-Naver-Client-Secret": naver_secret
        }, timeout=5)
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

    st.markdown("<div style='margin-top:32px;'></div>", unsafe_allow_html=True)
    st.info("📄 PDF 다운로드 및 카카오톡 자동 발송 기능은 곧 추가돼요!")


def render_weekly_report():
    st.markdown(
        f"<div style='font-size:15px; color:{DIM}; margin-bottom:20px;'>주간 리포트 — {dt.datetime.now():%Y년 %m월} 기준</div>",
        unsafe_allow_html=True
    )

    # ── 주간 시장 요약 ──
    card("📊 주간 시장 요약", "코스피/코스닥/나스닥 주간 등락")

    @st.cache_data(ttl=3600)
    def get_weekly_market():
        indices = {"코스피": "^KS11", "코스닥": "^KQ11", "나스닥": "^IXIC", "S&P500": "^GSPC"}
        result = []
        for name, ticker in indices.items():
            try:
                hist = yf.Ticker(ticker).history(period="1mo").dropna(subset=["Close"])
                if len(hist) >= 6:
                    curr = hist["Close"].iloc[-1]
                    week_ago = hist["Close"].iloc[-6]
                    chg_pct = (curr - week_ago) / week_ago * 100
                    result.append({"지수": name, "현재가": f"{curr:,.2f}", "주간 등락": f"{chg_pct:+.2f}%", "_pct": chg_pct})
            except:
                pass
        return result

    weekly_data = get_weekly_market()
    if weekly_data:
        cols = st.columns(len(weekly_data))
        for i, d in enumerate(weekly_data):
            with cols[i]:
                color = CANDLE_UP if d["_pct"] >= 0 else CANDLE_DOWN
                arrow = "▲" if d["_pct"] >= 0 else "▼"
                st.markdown(f"""
                <div style='background:{SURFACE_2}; border:0.5px solid {LINE}; border-radius:12px; padding:14px 16px; margin-bottom:12px; box-shadow:0 4px 24px rgba(0,0,0,0.4);'>
                    <div style='font-size:11px; color:#9ca3af; margin-bottom:4px;'>{d["지수"]}</div>
                    <div style='font-family:JetBrains Mono; font-size:17px; font-weight:600;'>{d["현재가"]}</div>
                    <div style='font-family:JetBrains Mono; font-size:12px; color:{color}; margin-top:2px;'>{arrow} {d["주간 등락"]}</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)

    # ── 주간 관심종목 성과 ──
    if st.session_state.get("watchlist"):
        card("📈 관심종목 주간 성과", "이번 주 수익률 순위")

        @st.cache_data(ttl=3600)
        def get_weekly_returns(watchlist):
            rows = []
            for item in watchlist:
                ticker = item if item.endswith(".KS") or item.endswith(".KQ") else item + ".KS"
                try:
                    hist = yf.Ticker(ticker).history(period="1mo").dropna(subset=["Close"])
                    if len(hist) >= 6:
                        curr = hist["Close"].iloc[-1]
                        week_ago = hist["Close"].iloc[-6]
                        chg_pct = (curr - week_ago) / week_ago * 100
                        rows.append({"종목": item, "주간 수익률": f"{chg_pct:+.2f}%", "_pct": chg_pct})
                except:
                    pass
            return sorted(rows, key=lambda x: x["_pct"], reverse=True)

        weekly_returns = get_weekly_returns(tuple(st.session_state.watchlist))
        if weekly_returns:
            df_weekly = pd.DataFrame([{k: v for k, v in r.items() if k != "_pct"} for r in weekly_returns])
            st.dataframe(df_weekly, use_container_width=True, hide_index=True)

    st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)

    # ── 다음 주 경제 캘린더 ──
    card("📅 다음 주 경제 캘린더", "주요 경제 지표 발표 일정")
    st.info("🔧 경제 캘린더는 investing.com 연동으로 곧 추가돼요!")