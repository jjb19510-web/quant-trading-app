import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import datetime as dt
import requests
import os
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
    signal_rows = []
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
        from broker import get_foreign_institution_trade, get_access_token
        token = st.session_state.get("kis_token")
        if not token:
            last_attempt = st.session_state.get("kis_token_last_attempt", 0)
            now = dt.datetime.now().timestamp()
            if now - last_attempt < 60:
                st.info("📊 수급 데이터는 장 중(09:00~15:30)에만 활성화돼요.")
                raise Exception("토큰 발급 대기 중")
            try:
                st.session_state["kis_token_last_attempt"] = now
                token = get_access_token()
                st.session_state["kis_token"] = token
            except Exception as e:
                st.info("📊 수급 데이터는 장 중(09:00~15:30)에만 활성화돼요.")
                raise Exception("토큰 발급 실패")

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
                    etf_keywords = ["KODEX", "TIGER", "KBSTAR", "ARIRANG", "HANARO", "KOSEF", "PLUS", "ACE", "SOL", "TIMEFOLIO", "ETF", "ETN", "인버스", "레버리지", "선물"]
                    if name and not any(k in name for k in etf_keywords):
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
    items = []
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

            # AI 뉴스 요약
            if st.button("🤖 AI 뉴스 요약", use_container_width=True):
                with st.spinner("AI가 뉴스를 분석하는 중..."):
                    try:
                        news_text = "\n".join([
                            item["title"].replace("<b>","").replace("</b>","")
                            for item in items
                        ])

                        anal_res = requests.get(
                            "https://openapi.naver.com/v1/search/news.json?query=애널리스트+투자의견+목표주가&display=3&sort=date",
                            headers={
                                "X-Naver-Client-Id": naver_id,
                                "X-Naver-Client-Secret": naver_secret
                            }, timeout=5
                        )
                        anal_items = anal_res.json().get("items", [])
                        anal_text = "\n".join([
                            item["title"].replace("<b>","").replace("</b>","")
                            for item in anal_items
                        ])

                        prompt = f"""다음 주식 뉴스와 애널리스트 의견을 투자자 관점에서 분석해줘.

[오늘의 주요 뉴스]
{news_text}

[애널리스트 의견]
{anal_text}

반드시 한국어로만 답해줘. 영어나 다른 언어 절대 사용 금지.
아래 형식으로 구체적이고 자세하게 답해줘:
📈 상승 요인: (구체적 수치나 종목명 포함해서 2~3줄)
📉 하락 요인: (구체적 리스크 요인 포함해서 2~3줄)
📌 핵심 이슈:
- (핵심 1: 배경과 영향 포함)
- (핵심 2: 배경과 영향 포함)
- (핵심 3: 배경과 영향 포함)
💼 애널리스트 주요 의견: (종목별 목표가, 투자의견 등 구체적으로 2~3줄)
🔮 오늘 시장 영향 전망: (코스피/코스닥 방향성 포함해서 2줄)"""

                        groq_key = st.secrets.get("GROQ_API_KEY", "")
                        ai_res = requests.post(
                            "https://api.groq.com/openai/v1/chat/completions",
                            headers={"Content-Type": "application/json", "Authorization": f"Bearer {groq_key}"},
                            json={
                                "model": "llama-3.3-70b-versatile",
                                "messages": [{"role": "user", "content": prompt}],
                                "max_tokens": 800
                            }
                        )
                        ai_data = ai_res.json()
                        if "choices" not in ai_data:
                            raise Exception(str(ai_data))
                        summary = ai_data["choices"][0]["message"]["content"]
                        st.session_state["ai_summary"] = summary
                        st.markdown(f"""
                        <div style='background:{SURFACE_2}; border:0.5px solid {LINE}; border-radius:12px; padding:20px; margin-top:12px;'>
                            <div style='font-size:13px; font-weight:700; color:#9ca3af; margin-bottom:16px; letter-spacing:1px;'>🤖 AI 시장 분석</div>
                            <div style='font-size:13px; line-height:2.0; white-space:pre-line; color:{TEXT};'>{summary}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"AI 요약 실패: {e}")

            # 이전 AI 요약 표시
            elif st.session_state.get("ai_summary"):
                st.markdown(f"""
                <div style='background:{SURFACE_2}; border:0.5px solid {LINE}; border-radius:12px; padding:20px; margin-top:12px;'>
                    <div style='font-size:13px; font-weight:700; color:#9ca3af; margin-bottom:16px; letter-spacing:1px;'>🤖 AI 시장 분석</div>
                    <div style='font-size:13px; line-height:2.0; white-space:pre-line; color:{TEXT};'>{st.session_state["ai_summary"]}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("뉴스를 불러오지 못했어요.")
    except:
        st.info("뉴스를 불러오지 못했어요.")

    st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)

    # ── [신규 추가] 9. 3대 증권사 주간 추천주 AI 교차 검증 및 컨센서스 선별 모듈 ──
    card("🏦 증권사 컨센서스(공통) 추천주", "하나, KB, 미래에셋증권의 주간 공식 추천 목록을 대조 분석하여, 교차 추천되었거나 가장 설득력 있는 핵심 5~8개 종목을 엄선합니다.")
    try:
        naver_id = st.secrets.get("NAVER_CLIENT_ID", "")
        naver_secret = st.secrets.get("NAVER_CLIENT_SECRET", "")
        
        # 🎯 네이버 연산자 에러 회피를 위해 '가장 단순하고 안전한' 단어로 15개 넉넉히 수집
        rec_url = "https://openapi.naver.com/v1/search/news.json"
        params = {
            "query": "주간추천종목",
            "display": 15,
            "sort": "date"
        }
        rec_res = requests.get(rec_url, headers={
            "X-Naver-Client-Id": naver_id,
            "X-Naver-Client-Secret": naver_secret
        }, params=params, timeout=5)
        rec_items = rec_res.json().get("items", [])
        
        if rec_items:
            rec_titles = [item["title"].replace("<b>", "").replace("</b>", "") for item in rec_items]
            
            if st.button("🤖 증권사 공통 추천종목 교차 분석 시작", use_container_width=True):
                with st.spinner("하나, KB, 미래에셋의 주간 추천 목록을 AI 교차 분석 중..."):
                    # 💎 아이티센글로벌의 공식 상장 사명을 수호하고 요약 퀄리티를 극대화하는 보정 프롬프트
                    rec_prompt = f"""너는 정교한 퀀트 금융 리서치 애널리스트야.
아래 리스트는 타겟 3대 증권사(하나증권, KB증권, 미래에셋증권)의 최신 추천종목 뉴스 제목들입니다.
이 정보들을 바탕으로 다음의 [엄격한 품질 필터]를 적용하여 5~8개의 핵심 추천 종목 요약 표를 생성해줘.

[엄격한 품질 필터 가이드라인]
1. **공식적인 국내 상장사명(KOSPI, KOSDAQ)만 사용**:
   - '아이센티' 같은 오타나 과거 사명인 '아이티센'이 등장할 경우, 반드시 최근 변경된 정확한 공식 상장사명인 **'아이티센글로벌'**로 정정하여 통일해 표기하십시오. (아이티센글로벌은 실제 상장된 공식 명칭이므로 그대로 사용해야 합니다.)
   - '텔레그램', '유튜브', '뉴스레터' 등 종목이 아닌 메신저나 채널 이름은 절대 표에 올리지 말고 무조건 배제하십시오.
2. **사유 중복 복사-붙여넣기 절대 금지 (나태함 방지)**:
   - 종목별로 완전히 독립적이고 차별화된 고유 사유를 작성해야 합니다. 한화비전(CCTV/보안 솔루션), 삼성SDI(배터리/에너지), GS건설(건설/인프라), 삼성물산(상사/패션) 등 각 종목의 실제 사업 영역에 완벽하게 부합하는 1줄의 핵심 사업 촉매제(Catalyst)를 명확히 작성하십시오.
3. **논리적 모순 차단**:
   - 수주 감소 우려 등 악재성 이슈를 매수 추천 사유로 둔갑시키지 마십시오. 철저히 수주 증가, 실적 턴어라운드, 신사업 확장 등 긍정적이고 객관적인 호재 위주로 요약해야 합니다.

결과는 다른 설명이나 인사말 없이 깔끔한 마크다운 테이블(Table) 형태로 즉시 출력해 주어야 해.
컬럼명 규격:
| 공통 추천 종목명 | 추천한 증권사들(쉼표로 구분) | 종합 추천 사유 및 특징 |

[증권사 추천 뉴스 헤드라인 리스트]
{"\n".join(rec_titles)}

반드시 한국어로만 명확하게 답해줘."""

                    groq_key = st.secrets.get("GROQ_API_KEY", "")
                    ai_res = requests.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Content-Type": "application/json", "Authorization": f"Bearer {groq_key}"},
                        json={
                            "model": "llama-3.3-70b-versatile",
                            "messages": [{"role": "user", "content": rec_prompt}],
                            "max_tokens": 700
                        }
                    )
                    ai_data = ai_res.json()
                    extracted_table = ai_data["choices"][0]["message"]["content"]
                    st.session_state["broker_consensus_table"] = extracted_table
                    st.markdown(extracted_table)
            
            elif st.session_state.get("broker_consensus_table"):
                st.markdown(st.session_state["broker_consensus_table"])
        else:
            st.info("증권사 추천 뉴스를 불러오지 못했습니다.")
    except Exception as e:
        st.info(f"컨센서스 종목 분석 실패: {e}")

    st.markdown("<div style='margin-top:32px;'></div>", unsafe_allow_html=True)

    # ── 카카오톡 발송 ──
    st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
    if st.button("📱 카카오톡으로 리포트 받기", use_container_width=True):
        try:
            from broker import send_kakao_message

            market_text = ""
            if market_data:
                for idx in market_data:
                    arrow = "▲" if idx["change"] >= 0 else "▼"
                    market_text += f"{idx['name']}: {idx['price']:,.2f} {arrow}{idx['pct']:+.2f}%\n"

            signal_text = ""
            if signal_rows:
                for row in signal_rows:
                    signal_text += f"{row['종목']}: {row['신호']} | RSI {row['RSI']}\n"

            ai_text = ""
            if st.session_state.get("ai_summary"):
                ai_text = f"{'─'*30}\n\n🤖 AI 시장 분석\n{st.session_state['ai_summary'][:300]}...\n"

            message = (
                f"📊 Quantfolio 일간 리포트\n"
                f"{dt.datetime.now():%Y년 %m월 %d일 %H:%M} 기준\n"
                f"{'─'*30}\n\n"
                f"🌐 시장 현황\n{market_text}\n"
                f"{'─'*30}\n\n"
                f"🔔 관심종목 신호\n{signal_text if signal_text else '관심종목 없음'}\n"
                f"{ai_text}"
                f"{'─'*30}\n\n"
                f"🔗 Quantfolio 앱 바로가기\n"
                f"https://quant-trading-app-gdvn3rpskejdaihwjjjqzf.streamlit.app"
            )

            result = send_kakao_message(message)
            if result.get("result_code") == 0:
                st.success("✅ 카카오톡 발송 완료!")
            else:
                st.error(f"발송 실패: {result}")
        except Exception as e:
            st.error(f"카카오톡 발송 오류: {e}")

    st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

    # ── PDF 다운로드 ──
    if st.button("📄 PDF 리포트 다운로드", use_container_width=True):
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            import urllib.request
            import io

            # 나눔고딕 폰트 보존 검증 및 자동 주입
            font_path = "/tmp/NanumGothic.ttf"
            if not os.path.exists(font_path):
                urllib.request.urlretrieve(
                    "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf",
                    font_path
                )
            pdfmetrics.registerFont(TTFont("NanumGothic", font_path))

            buffer = io.BytesIO()
            # 용지 마진을 타이트하게 잡아 내용 잘림 예방 (A4 표준)
            doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=40, bottomMargin=40)
            story = []

            # 💎 기관 리포트 규격 전용 스타일셋 정의 (글자 겹침 방지 leading 정밀 보정)
            title_style = ParagraphStyle('title', fontSize=22, fontName='NanumGothic', leading=28, spaceAfter=10, textColor=colors.HexColor("#0f172a"))
            meta_style = ParagraphStyle('meta', fontSize=10, fontName='NanumGothic', leading=14, spaceAfter=14, textColor=colors.HexColor("#64748b"))
            h2_style = ParagraphStyle('h2', fontSize=13, fontName='NanumGothic', spaceAfter=8, spaceBefore=18, textColor=colors.HexColor("#1e293b"))
            normal_style = ParagraphStyle('normal', fontSize=9, fontName='NanumGothic', spaceAfter=4, leading=15, textColor=colors.HexColor("#334155"))
            bullet_style = ParagraphStyle('bullet', fontSize=9, fontName='NanumGothic', spaceAfter=4, leading=15, leftIndent=12, textColor=colors.HexColor("#334155"))

            # 헤더 섹션 구성
            story.append(Paragraph("Quantfolio Daily Report", title_style))
            story.append(Paragraph(f"발행일시: {dt.datetime.now():%Y년 %m월 %d일 %H:%M} | 분석 파트너: Groq Llama-3.3", meta_style))
            
            # 장식용 탑 배너 라인
            banner = Table([[""]], colWidths=[523], rowHeights=[3])
            banner.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#0f172a"))]))
            story.append(banner)
            story.append(Spacer(1, 15))

            # 🌐 1. 글로벌 시장 현황
            story.append(Paragraph("🌐 글로벌 시장 종합 지표", h2_style))
            if market_data:
                table_data = [["지수/원자재명", "현재가", "전일 대비 등락률"]]
                for idx in market_data:
                    arrow = "▲" if idx["change"] >= 0 else "▼"
                    table_data.append([
                        idx["name"], 
                        f"{idx['price']:,.2f}" if "환율" not in idx["name"] else f"{idx['price']:,.1f}원", 
                        f"{arrow} {idx['change']:+,.2f} ({idx['pct']:+.2f}%)"
                    ])
                
                t = Table(table_data, colWidths=[180, 160, 183])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f172a")), # 딥 네이비 헤더
                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                    ('FONTNAME', (0,0), (-1,-1), 'NanumGothic'),
                    ('FONTSIZE', (0,0), (-1,-1), 9),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                    ('TOPPADDING', (0,0), (-1,-1), 6),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]), # 교차 행 배경색
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
                ]))
                story.append(t)
            story.append(Spacer(1, 14))

            # 🔔 2. 관심종목 신호 리포트
            if st.session_state.get("watchlist") and signal_rows:
                story.append(Paragraph("🔔 관심종목 퀀트 목표가 요약", h2_style))
                sig_data = [["종목코드", "전략 신호", "RSI 지표 상태", "내일 변동성 돌파 목표가"]]
                for row in signal_rows:
                    sig_data.append([row["종목"], row["신호"], row["RSI"], row["내일 변동성 목표가"]])
                
                t2 = Table(sig_data, colWidths=[110, 100, 140, 173])
                t2.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f172a")),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                    ('FONTNAME', (0,0), (-1,-1), 'NanumGothic'),
                    ('FONTSIZE', (0,0), (-1,-1), 9),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                    ('TOPPADDING', (0,0), (-1,-1), 6),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
                ]))
                story.append(t2)
                story.append(Spacer(1, 14))

            # 📊 3. 당일 거래대금 TOP 10 (주요 노이즈 ETF 필터링 반영)
            if volume_data:
                story.append(Paragraph("📊 당일 거래대금 상위 TOP 10 (ETF 제외)", h2_style))
                vol_data = [["종목명", "현재가", "당일 누적 거래량"]]
                for row in volume_data:
                    vol_data.append([row["종목"], f"{row['현재가']}원" if "원" not in row["현재가"] else row["현재가"], row["거래량"]])
                
                t3 = Table(vol_data, colWidths=[180, 160, 183])
                t3.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f172a")),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                    ('FONTNAME', (0,0), (-1,-1), 'NanumGothic'),
                    ('FONTSIZE', (0,0), (-1,-1), 9),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                    ('TOPPADDING', (0,0), (-1,-1), 6),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
                ]))
                story.append(t3)
                story.append(Spacer(1, 14))

            # 🏦 [신규 통합] 4. 증권사 컨센서스(공통) 추천주 (네이티브 마크다운 표 자동 파싱 인쇄)
            consensus_markdown = st.session_state.get("broker_consensus_table", "")
            if consensus_markdown:
                story.append(Paragraph("🏦 증권사 컨센서스(공통) 추천주", h2_style))
                
                # 마크다운 문자열 표 -> 리스크 없는 리스트 파싱 전처리
                lines = consensus_markdown.strip().split("\n")
                parsed_table_data = []
                for line in lines:
                    if not line.strip():
                        continue
                    if "---" in line or ":::" in line:
                        continue
                    parts = [cell.strip() for cell in line.split("|")]
                    if parts and parts[0] == "":
                        parts = parts[1:]
                    if parts and parts[-1] == "":
                        parts = parts[:-1]
                    if parts:
                        parsed_table_data.append(parts)
                
                if len(parsed_table_data) >= 2:
                    # 표의 텍스트가 경계선을 넘지 않도록 Paragraph 스타일 감싸기 (자동 줄바꿈 지원)
                    final_table_data = []
                    # 헤더 스타일
                    final_table_data.append([Paragraph(cell, ParagraphStyle('h_cell', fontName='NanumGothic', fontSize=9, textColor=colors.white, alignment=1)) for cell in parsed_table_data[0]])
                    
                    # 바디 스타일 (추천사유 컬럼만 좌측 정렬, 나머지는 중앙 정렬)
                    cell_style_center = ParagraphStyle('c_cell', fontName='NanumGothic', fontSize=8, leading=11, alignment=1)
                    cell_style_left = ParagraphStyle('l_cell', fontName='NanumGothic', fontSize=8, leading=11, alignment=0)
                    
                    for r_idx, row in enumerate(parsed_table_data[1:]):
                        row_cells = []
                        for c_idx, cell in enumerate(row):
                            style = cell_style_left if c_idx == 2 else cell_style_center
                            row_cells.append(Paragraph(cell, style))
                        final_table_data.append(row_cells)
                    
                    # 용지 가로 규격(523pt)에 맞춰 분배
                    t4 = Table(final_table_data, colWidths=[120, 110, 293])
                    t4.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f172a")),
                        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                        ('TOPPADDING', (0,0), (-1,-1), 6),
                        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
                    ]))
                    story.append(t4)
                    story.append(Spacer(1, 14))

            # 🧠 5. AI 시장 분석 및 종합 전망 (블록쿼트형 리포트 카드 적용)
            ai_summary = st.session_state.get("ai_summary", "")
            if ai_summary:
                story.append(Paragraph("🧠 AI 시장 종합 브리핑", h2_style))
                
                # 가독성과 줄바꿈 유지를 위한 패러그래프 팩
                ai_paragraphs = []
                for line in ai_summary.split("\n"):
                    if line.strip():
                        cleaned_line = line.strip().replace("**", "")
                        # 글머리 기호가 포함된 경우 들여쓰기 양식 기입
                        if cleaned_line.startswith("-") or cleaned_line.startswith("•"):
                            ai_paragraphs.append(Paragraph(cleaned_line, bullet_style))
                        else:
                            ai_paragraphs.append(Paragraph(cleaned_line, normal_style))
                
                # 1x1 투명 그리드 내부 보드 삽입으로 블록쿼트(blockquote)형 연출
                quote_table = Table([[ai_paragraphs]], colWidths=[523])
                quote_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")), # 아주 옅은 회색 배경
                    ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")), # 연한 경계선
                    ('LINELEFT', (0,0), (0,-1), 4, colors.HexColor("#0f172a")), # 왼쪽 굵은 시그니처 바
                    ('TOPPADDING', (0,0), (-1,-1), 12),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 12),
                    ('LEFTPADDING', (0,0), (-1,-1), 15),
                    ('RIGHTPADDING', (0,0), (-1,-1), 15),
                ]))
                story.append(quote_table)
                story.append(Spacer(1, 14))

            story.append(Spacer(1, 10))
            
            # 하단 저작권 푸터선
            footer_table = Table([[Paragraph("본 보고서는 Quantfolio에 의해 장 마감 후 자동 생성되었으며, 무단 전재를 금합니다.", meta_style)]], colWidths=[523])
            footer_table.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('LINEABOVE', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1"))
            ]))
            story.append(footer_table)

            doc.build(story)
            buffer.seek(0)

            st.download_button(
                label="⬇️ 고화질 PDF 보고서 다운로드",
                data=buffer,
                file_name=f"Quantfolio_Daily_Report_{dt.datetime.now():%Y%m%d}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"PDF 생성 오류: {e}")


def render_weekly_report():
    st.markdown(
        f"<div style='font-size:15px; color:{DIM}; margin-bottom:20px;'>주간 리포트 — {dt.datetime.now():%Y년 %m월} 기준</div>",
        unsafe_allow_html=True
    )

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

    card("📅 다음 주 경제 캘린더", "주요 경제 지표 발표 일정")
    st.info("🔧 경제 캘린더는 investing.com 연동으로 곧 추가돼요!")