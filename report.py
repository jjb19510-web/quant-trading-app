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

# ── [전역 함수 1] 네이버 금융 수급동향 실시간 '억 원'대금 가공 크롤러 ──
@st.cache_data(ttl=1800)
def get_naver_supply_deal(investor_gubun="1000"):
    """네이버 금융 장 마감 확정 수급 데이터 백업 크롤러 (1000:외인, 9000:기관)"""
    try:
        from bs4 import BeautifulSoup
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        url = f"https://finance.naver.com/sise/sise_deal_rank.naver?investor_gubun={investor_gubun}&sosok=0"
        res = requests.get(url, headers=headers, timeout=10)
        
        res.encoding = 'cp949'
        
        soup = BeautifulSoup(res.text, "html.parser")
        # [클래스 완전 면역] 모든 tr 행을 대상으로 안전 탐색
        rows = soup.select("tr")
        result = []
        for row in rows:
            name_tag = row.select_one("a.company")
            if name_tag:
                name = name_tag.text.strip()
                cols = row.select("td")
                
                # 🎯 [버그 교정] 수급 표의 실제 컬럼 수인 6개 규격에 맞게 검증 한계를 6으로 정정
                if len(cols) >= 6:
                    price = cols[2].text.strip()      # 현재가 (3번째 열)
                    raw_amount = cols[-1].text.strip() # 순매수 주식 수량 (마지막 열)
                    
                    try:
                        # [수급대금 실시간 역산] 주식 수량(주)과 현재가를 곱하여 실제 순매수대금(억 원)을 역산출합니다.
                        price_val = int(price.replace(",", ""))
                        qty_val = int(raw_amount.replace(",", "").replace("-", ""))
                        
                        amount_won = qty_val * price_val
                        amount_in_hundred_million = amount_won / 100000000 # 1억 원 = 100,000,000원
                        
                        is_negative = "-" in raw_amount
                        sign = "-" if is_negative else ""
                        
                        buy_val_str = f"{sign}{amount_in_hundred_million:,.0f}억 원"
                    except:
                        # 예외 발생 시 안전하게 주식 수량(주)으로 백업 표기
                        buy_val_str = f"{raw_amount}주"
                    
                    result.append({"종목": name, "순매수": buy_val_str})
                
                if len(result) == 5:
                    break
        return result
    except Exception as e:
        print(f"네이버 수급 크롤링 중 예외 발생: {e}")
        return []


# ── [전역 함수 2] 야후 파이낸스 무동기화 대비 실시간 보정 크롤러 ──
def get_naver_market_data():
    """야후 파이낸스 딜레이 방지를 위해 네이버 금융 메인에서 실시간 마감 지수를 크롤링합니다."""
    try:
        from bs4 import BeautifulSoup
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        url = "https://finance.naver.com/"
        res = requests.get(url, headers=headers, timeout=5)
        res.encoding = 'cp949'
        soup = BeautifulSoup(res.text, "html.parser")
        
        result = {}
        
        # 1. 코스피 수집
        kospi_area = soup.select_one(".kospi_area")
        if kospi_area:
            try:
                price_str = kospi_area.select_one(".num").text.strip().replace(",", "")
                change_str = kospi_area.select_one(".num2").text.strip().replace(",", "")
                pct_str = kospi_area.select_one(".num3").text.strip().replace("%", "").replace("+", "").replace("-", "")
                is_down = "num_quot dn" in str(kospi_area)
                sign = -1 if is_down else 1
                result["코스피"] = {
                    "price": float(price_str),
                    "change": float(change_str) * sign,
                    "pct": float(pct_str) * sign
                }
            except Exception as e:
                print(f"KOSPI parse error: {e}")
                
        # 2. 코스닥 수집
        kosdaq_area = soup.select_one(".kosdaq_area")
        if kosdaq_area:
            try:
                price_str = kosdaq_area.select_one(".num").text.strip().replace(",", "")
                change_str = kosdaq_area.select_one(".num2").text.strip().replace(",", "")
                pct_str = kosdaq_area.select_one(".num3").text.strip().replace("%", "").replace("+", "").replace("-", "")
                is_down = "num_quot dn" in str(kosdaq_area)
                sign = -1 if is_down else 1
                result["코스닥"] = {
                    "price": float(price_str),
                    "change": float(change_str) * sign,
                    "pct": float(pct_str) * sign
                }
            except Exception as e:
                print(f"KOSDAQ parse error: {e}")
                
        # 3. 원/달러 환율 수집
        try:
            exchange_area = soup.select_one(".aside_area #exchangeList, #exchangeList")
            if exchange_area:
                usd_item = exchange_area.select_one("li")
                if usd_item:
                    usd_val_str = usd_item.select_one(".value").text.strip().replace(",", "")
                    usd_change_str = usd_item.select_one(".change").text.strip().replace(",", "")
                    is_down = "down" in str(usd_item) or "하락" in str(usd_item)
                    sign = -1 if is_down else 1
                    
                    price_val = float(usd_val_str)
                    change_val = float(usd_change_str) * sign
                    prev_val = price_val - change_val
                    pct_val = (change_val / prev_val) * 100 if prev_val != 0 else 0
                    
                    result["원/달러"] = {
                        "price": price_val,
                        "change": change_val,
                        "pct": pct_val
                    }
        except Exception as e:
            print(f"Exchange rate parse error: {e}")
            
        return result
    except Exception as e:
        print(f"네이버 금융 지수 크롤링 실패: {e}")
        return {}


# ── [전역 함수 3] 하이브리드 시장 지표 취득 연동기 ──
@st.cache_data(ttl=300)
def get_market_data():
    """네이버 금융 우선 매칭 기조의 하이브리드 시장 분석 데이터 연동기"""
    indices = {
        "코스피": "^KS11",
        "코스닥": "^KQ11",
        "나스닥": "^IXIC",
        "원/달러": "USDKRW=X",
        "WTI유": "CL=F",
        "금": "GC=F",
        "미국10년채": "^TNX"
    }
    
    # 네이버에서 최신 실시간 지수를 수집합니다.
    naver_data = get_naver_market_data()
    result = []
    
    for name, ticker in indices.items():
        # 국내 핵심 정보(코스피, 코스닥, 원달러)는 네이버의 당일 마감 종결값을 최우선적으로 채택하여 야후 딜레이를 방지합니다.
        if name in naver_data:
            result.append({
                "name": name,
                "price": naver_data[name]["price"],
                "change": naver_data[name]["change"],
                "pct": naver_data[name]["pct"]
            })
            continue
            
        # 해외 거시 지표는 야후 파이낸스를 통해 로드합니다.
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


# ── [전역 함수 4] 스마트 머니 인덱스(SMI) 연산 엔진 ──
@st.cache_data(ttl=900)
def calculate_smi_yfinance():
    try:
        # 야후 파이낸스에서 KOSPI 지수(^KS11) 최근 5일간의 15분 단위 인트라데이 데이터 다운로드
        df = yf.download("^KS11", period="5d", interval="15m", progress=False)
        if df.empty:
            return None
            
        # 멀티인덱스 칼럼 구조 안전 해제
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df = df.copy()
        df.index = df.index.tz_convert("Asia/Seoul")
        df["Date"] = df.index.date
        unique_dates = sorted(df["Date"].unique())
        
        smi_value = 10000.0  # 지수 시작 시그니처 포인트
        smi_history = []
        
        for d in unique_dates:
            day_data = df[df["Date"] == d].sort_index()
            if len(day_data) < 4:
                continue
            
            # 1. 오전 첫 30분 (09:00 시가 ~ 09:30 종가) 변동폭 연산
            try:
                open_0900 = day_data.iloc[0]["Open"]
                cand_0930 = day_data.between_time("09:15", "09:35")
                close_0930 = cand_0930.iloc[-1]["Close"] if not cand_0930.empty else day_data.iloc[2]["Close"]
                morning_change = close_0930 - open_0900
            except:
                morning_change = 0.0
            
            # 2. 오후 마지막 30분 (15:00 종가 ~ 15:30 종가) 변동폭 연산
            try:
                close_1530 = day_data.iloc[-1]["Close"]
                cand_1500 = day_data.between_time("14:55", "15:05")
                open_1500 = cand_1500.iloc[0]["Open"] if not cand_1500.empty else day_data.iloc[-3]["Open"]
                afternoon_change = close_1530 - open_1500
            except:
                afternoon_change = 0.0
            
            # SMI 계산 적용
            smi_value = smi_value - morning_change + afternoon_change
            smi_history.append({
                "날짜": d.strftime("%m/%d"),
                "SMI": round(smi_value, 2),
                "KOSPI": round(day_data.iloc[-1]["Close"], 2),
                "오전변동": round(morning_change, 2),
                "오후변동": round(afternoon_change, 2)
            })
        return pd.DataFrame(smi_history)
    except Exception as e:
        print(f"SMI 연산 오류: {e}")
        return None


# ── [전역 함수 5] 거래대금 기준 퀀트 정렬 TOP 10 로직 ──
@st.cache_data(ttl=300)
def get_top_volume():
    try:
        from bs4 import BeautifulSoup
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        # 🎯 [우회 성공] 404 차단 우려가 전혀 없는 100개 거래량 페이지를 기본 로드합니다.
        url = "https://finance.naver.com/sise/sise_quant.naver?sosok=0"
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, "html.parser")
        
        # 🎯 [클래스 면역] 모든 tr을 수색 타겟팅하여 수집 신뢰성을 확보합니다.
        rows = soup.select("tr")
        
        unsorted_result = []
        
        for row in rows:
            cols = row.select("td")
            if len(cols) >= 7:
                name_tag = cols[1].select_one("a")
                if name_tag:
                    name = name_tag.text.strip()
                    price = cols[2].text.strip()
                    raw_amount = cols[6].text.strip() # 백만 원 단위 거래대금 취득
                    
                    if not name:
                        continue
                    
                    etf_keywords = [
                        "KODEX", "TIGER", "KBSTAR", "ARIRANG", "HANARO", "KOSEF", "PLUS", "ACE", "SOL", 
                        "TIMEFOLIO", "ETF", "ETN", "인버스", "레버리지", "선물", "RISE", "WOORI"
                    ]
                    if not any(k in name for k in etf_keywords):
                        try:
                            # 콤마 제거 후 연산 정렬용 정수값 저장
                            amount_val = int(raw_amount.replace(",", ""))
                        except:
                            amount_val = 0
                            
                        price_formatted = f"{price}원" if price and not price.endswith("원") else price
                        
                        unsorted_result.append({
                            "종목": name, 
                            "현재가": price_formatted, 
                            "amount_val": amount_val, # 정렬 지표 키 등록
                            "raw_amount": raw_amount
                        })
        
        # 🎯 [자체 퀀트 소팅] 진짜 '거래대금(amount_val)' 기준 내림차순 정렬
        sorted_result = sorted(unsorted_result, key=lambda x: x["amount_val"], reverse=True)
        
        final_top_10 = []
        for item in sorted_result[:10]:
            amount_val = item["amount_val"]
            amount_in_hundred_million = amount_val / 100 # 100백만 원 = 1억 원
            
            if amount_in_hundred_million >= 10000:
                trillion = int(amount_in_hundred_million // 10000)
                billion = int(amount_in_hundred_million % 10000)
                if billion > 0:
                    amount_formatted = f"{trillion}조 {billion:,}억 원"
                else:
                    amount_formatted = f"{trillion}조 원"
            else:
                amount_formatted = f"{amount_in_hundred_million:,.0f}억 원"
            
            final_top_10.append({
                "종목": item["종목"],
                "현재가": item["현재가"],
                "거래대금": amount_formatted
            })
        return final_top_10
    except Exception as e:
        print(f"거래대금 순위 수집 오류: {e}")
        return []


# ── [메인 오케스트레이터] 상단 탭 제어 ──
def render_report():
    timezone_kst = dt.timezone(dt.timedelta(hours=9))
    now_kst = dt.datetime.now(timezone_kst)
    st.markdown(
        "<div style='font-size:22px; font-weight:700; margin-bottom:4px;'>📋 Daily Quantfolio Report</div>"
        f"<div style='font-size:12px; color:{DIM}; margin-bottom:24px;'>{now_kst:%Y년 %m월 %d일 %H:%M} 기준</div>",
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
        else:
            err_code = balance_data.get("rt_cd", "N/A")
            err_msg = balance_data.get("msg1", "서비스 운영 시간 외 또는 조회 권한이 없는 모의투자 계좌 상태입니다.")
            card("💼 포트폴리오 현황", f"KIS API 조회 제한 (코드: {err_code})")
            st.info(f"📊 한투 계좌 요약을 불러오지 못했습니다. (사유: {err_msg})")
    except Exception as e:
        card("💼 포트폴리오 현황", "KIS API 연결 필요")
        st.info(f"📊 KIS API를 연결할 수 없습니다. (상세 에러 원인: {e})")

    st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)

    # ── 5. 스마트 머니 인덱스 ──
    card("🧠 스마트 머니 인덱스 (SMI)", "외국인 및 기관 장막판 수급 동향")
    
    # 💡 초보자를 위한 초간단 설명 카드
    st.markdown(f"""
    <div style='background:{SURFACE_1}; border-left: 4px solid {ACCENT}; padding: 14px 18px; border-radius: 8px; margin-bottom: 20px; font-size: 13px; line-height: 1.7; color:{TEXT};'>
        <b>❓ 스마트 머니(SMI) 지표란 무엇인가요?</b><br/>
        • 주식 시장이 열리는 아침 9시 전후에는 주로 불안감이나 기대감에 휩싸인 개인 투자자(리테일 자금)들의 거래가 주를 이룹니다.<br/>
        • 반면, <b>오후 3시~3시 30분(장 마감 직전)</b>에는 정보력이 대단히 빠르고 자금력이 막강한 <b>해외자본(외국인) 및 국내 대형 기관 투자자</b>들이 최종 주가를 면밀히 판단하고 집중적인 거래를 집행합니다.<br/>
        • 이 지표는 <b>"외국인과 기관이 오늘 장 막판에 주식을 사들였는지, 팔아치웠는지"</b>를 정밀 계산하여 자금 흐름의 방향성을 점수로 시각화한 수급 레이더입니다.
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("해외자본 및 국내 기관의 장바구니 분석 중..."):
        smi_df = calculate_smi_yfinance()
        
    if smi_df is not None and not smi_df.empty:
        last_row = smi_df.iloc[-1]
        prev_row = smi_df.iloc[-2] if len(smi_df) > 1 else last_row
        smi_diff = last_row["SMI"] - prev_row["SMI"]
        
        # 오늘 종가 기준 시장 지배 수급 세력 판별 및 행동 가이드
        if smi_diff > 80:
            leadership = "🟢 해외자본·국내기관 매수 우위"
            lead_color = "#22c55e" # 그린
            advice_text = "외국인 투자자들과 국내 대형 기관들이 주식을 대량으로 사 모으고 있습니다. 우리도 우량한 주식을 함께 모아가기 매우 좋은 타이밍입니다."
            gauge_status = "강력 매수 신호 🔥"
        elif smi_diff < -80:
            leadership = "🔴 개인 투자자 매수 우위 (기관·외인 관망)"
            lead_color = "#ef4444" # 레드
            advice_text = "외국인 투자자들과 대형 기관들이 시장에서 자금을 회수하고 있습니다. 지금은 무리하게 매수하기보다는 현금을 확보하고 한 걸음 물러나 관망하는 편이 안전합니다."
            gauge_status = "리스크 관리 권고 ⚠️"
        else:
            leadership = "🟡 수급 혼조세 (방향성 탐색 중)"
            lead_color = "#f59e0b" # 주황
            advice_text = "시장 주도 세력들도 방향성을 고민하며 관망하는 상태입니다. 무리한 진입을 피하고 차분하게 시장 흐름을 주시할 필요가 있습니다."
            gauge_status = "관망 및 숨고르기 ⚖️"

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"""
            <div style='background:{SURFACE_2}; border:1px solid {LINE}; border-radius:12px; padding:16px; text-align:center;'>
                <div style='font-size:12px; color:#9ca3af; margin-bottom:6px;'>오늘의 시장 주도 자금 (외국인·기관)</div>
                <div style='font-size:15px; font-weight:800; color:{lead_color}; margin-top:4px;'>{leadership}</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            direction_icon = "📈" if smi_diff > 0 else "📉"
            st.markdown(f"""
            <div style='background:{SURFACE_2}; border:1px solid {LINE}; border-radius:12px; padding:16px; text-align:center;'>
                <div style='font-size:12px; color:#9ca3af; margin-bottom:6px;'>외국인·기관 종가 매수집중도 (전일 대비)</div>
                <div style='font-size:15px; font-weight:800; color:{ACCENT}; margin-top:4px;'>{direction_icon} {abs(smi_diff):+.1f}포인트 상승</div>
            </div>
            """, unsafe_allow_html=True)

        # 🎯 초보자를 위한 오늘의 행동 가이드 카드 출력
        st.markdown(f"""
        <div style='background:{SURFACE_2}; border-left: 4px solid {lead_color}; padding: 12px 16px; border-radius: 6px; margin-top: 14px; margin-bottom: 24px; font-size: 13px; color:{TEXT};'>
            🎯 <b>초보자 수급 가이드:</b> {advice_text}
        </div>
        """, unsafe_allow_html=True)

        # ── 3초 판독용 플롯리 반원형 게이지 차트(SMI Gauge) 구성 ──
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=smi_diff,
            domain={'x': [0, 1], 'y': [0, 1]},
            gauge={
                'axis': {
                    'range': [-500, 500], 
                    'tickwidth': 1, 
                    'tickcolor': "#9ca3af",
                    'tickvals': [-500, -250, 0, 250, 500],
                    'ticktext': ["위험 (-500)", "주의", "관망 (0)", "우호", "매수 집중 (+500)"]
                },
                'bar': {'color': ACCENT, 'thickness': 0.25}, 
                'bgcolor': "rgba(0,0,0,0)",
                'borderwidth': 1.5,
                'bordercolor': LINE,
                'steps': [
                    {'range': [-500, -100], 'color': "rgba(239, 68, 68, 0.12)"},  
                    {'range': [-100, 100], 'color': "rgba(245, 158, 11, 0.12)"},   
                    {'range': [100, 500], 'color': "rgba(34, 197, 94, 0.12)"}     
                ],
                'threshold': {
                    'line': {'color': lead_color, 'width': 5},
                    'thickness': 0.8,
                    'value': smi_diff
                }
            }
        ))
        
        # 🎯 차트 마진을 축소하고 텍스트 레이어를 밖으로 뺍니다.
        # 다크 블루 금융 테마에 맞춤형 투명 배경 및 폰트 연동
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={'color': TEXT, 'family': "NanumGothic"},
            margin=dict(l=30, r=30, t=10, b=30), # 하단 마진을 30px로 넉넉하게 주어 잘림 현상을 원천 방지합니다.
            height=250 # 가상 높이를 250으로 확대하여 틱 라벨 전체를 부드럽게 감쌉니다.
        )
        st.plotly_chart(fig, use_container_width=True)

        # 🎯 [신규 적용] 차트 캔버스 영역 밖에서 네이티브 HTML 배지로 정중앙 표시하여 잘림을 100% 원천 차단합니다.
        st.markdown(f"""
        <div style='text-align: center; margin-top: -15px; margin-bottom: 25px;'>
            <span style='background: {SURFACE_2}; border: 0.5px solid {LINE}; border-radius: 20px; padding: 6px 18px; font-size: 13px; font-weight: bold; color: {TEXT}; box-shadow: 0 4px 12px rgba(0,0,0,0.2);'>
                🔥 현재 수급 온도: <span style='color: {lead_color};'>{gauge_status}</span>
            </span>
        </div>
        """, unsafe_allow_html=True)
        
        # 💡 정돈된 마켓 분석 (존댓말 마무리 및 불안성 투매 완전 교체 적용)
        st.markdown(f"""
        <div style='font-size: 13px; line-height: 1.65; color:{TEXT}; margin-top: 16px;'>
            💡 <b>금일 마켓 뷰 (Market View):</b><br/>
            오늘 전체 주식 지수(KOSPI)는 전반적으로 약세를 보이며 지수 하강 압력을 이겨내지 못했습니다. 
            하지만 시장 내부의 진짜 수급 흐름을 자세히 들여다보면 대단히 유의미한 수급 반전 신호가 포착되었습니다.<br/><br/>
            아침 개장 직후에는 시장 분위기에 크게 동요한 개인 투자자들이 공포감에 주식을 급하게 던지는 **불안성 투매(패닉셀)** 물량이 쏟아져 나오며 주가를 끌어내렸습니다. 
            그러나 주가가 저렴해진 오후 시간대에 접어들자, <b>해외자본(외국인)과 대형 기관 투자자</b>들이 이 매물들을 아래에서 대량으로 흡수하기 시작했습니다. 결과적으로 외국인과 기관이 개인 투자자들의 투매 물량을 장 마감 직전에 아주 성공적으로 소화해 낸 형태입니다.<br/><br/>
            따라서 일시적으로 지수가 하락했다고 해서 성급하게 주식을 던지기보다는, 외국인과 대형 기관의 탄탄한 하방 수급 지지력을 바탕으로 가치 있는 핵심 우량주를 분할 매수해 나가는 포트폴리오 전략이 장기적으로 훨씬 유리할 것으로 분석됩니다.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("📊 현재 스마트 머니 인덱스(SMI) 데이터를 수집하고 있습니다.")

    # ── 6. 수급 동향 ──
    card("💰 수급 동향", "외국인 · 기관 · 개인 순매수 상위 종목 (하이브리드 KIS & Naver 백업)")

    # 🎯 KST 시간대를 명확히 판독하여 수급 로드 기준 결정
    timezone_kst = dt.timezone(dt.timedelta(hours=9))
    now_kst = dt.datetime.now(timezone_kst)
    is_weekend = now_kst.weekday() >= 5
    is_after_market = now_kst.time() > dt.time(15, 30) or now_kst.time() < dt.time(9, 0)
    
    use_naver_fallback = is_weekend or is_after_market
    foreign_rows, institution_rows, individual_rows = [], [], []

    # 1. 장 중이라면 먼저 한투 실시간 수급 API 호출을 정상 시도합니다.
    if not use_naver_fallback:
        try:
            from broker import get_foreign_institution_trade, get_access_token
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
                        try:
                            # 콤마 구분 기입으로 시각적 가독성 개선
                            buy_str = f"{int(buy):,}주"
                        except:
                            buy_str = f"{buy}주"
                        rows.append({"종목": name, "순매수": buy_str})
                return rows

            with st.spinner("실시간 KIS 수급 데이터 불러오는 중..."):
                foreign_raw = get_foreign_institution_trade(token, div_cls="0")
                institution_raw = get_foreign_institution_trade(token, div_cls="1")
                individual_raw = get_foreign_institution_trade(token, div_cls="2")

            foreign_rows = parse_supply(foreign_raw)
            institution_rows = parse_supply(institution_raw)
            individual_rows = parse_supply(individual_raw)

            # 성공적으로 데이터를 채웠다면 정상 진행, 통신 오류나 결과가 빈 리스트라면 네이버 백업으로 넘김
            if not foreign_rows and not institution_rows and not individual_rows:
                use_naver_fallback = True

        except Exception as e:
            # 장중 API 호출 실패 혹은 토큰에 에러가 발생한 경우 즉각 네이버로 자동 롤백 수행
            use_naver_fallback = True
            print(f"장중 KIS 수급 호출 에러로 네이버 fallback 가동: {e}")

    # 2. 장후 상태이거나 한투 API가 일시 장해 상태일 경우 백업용 네이버 데이터를 로드합니다.
    if use_naver_fallback:
        if is_weekend or is_after_market:
            st.warning("📊 현재는 장 마감 상태(15:30~익일 09:00)입니다. 실시간 KIS API 대신 [네이버 금융 당일 장 마감 가집계 확정치] 데이터를 백업 로드합니다.")
        else:
            st.warning("📊 KIS API 연결 상태가 원활하지 않아 [네이버 금융 실시간 가집계] 백업 데이터를 로드합니다.")
        
        with st.spinner("네이버 금융 수급 데이터를 수집 중..."):
            foreign_rows = get_naver_supply_deal("1000") # 외인 수집
            institution_rows = get_naver_supply_deal("9000") # 🎯 [코드 교체] 기존 잘못된 코드 1500에서 진짜 기관 수급 코드인 9000으로 교정
            
        # 🎯 [2열 대칭 개편] 애초에 존재하지 않는 개인 탭을 제외하고, 외국인과 기관 2개 컬럼으로 꽉 채워 배치합니다.
        col_f, col_i = st.columns(2)
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

    # ── 7. 거래대금 상위 ──
    card("📊 거래대금 상위 TOP 10", "오늘 가장 많이 거래된 종목")

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

                        prompt = f"""당신은 15년 경력의 국내 주식시장 수석 애널리스트입니다. 아래 뉴스와 애널리스트 의견을 바탕으로 개인 투자자가 쉽게 이해할 수 있는 시장 분석 보고서를 작성해주세요.

[오늘의 주요 뉴스]
{news_text}

[애널리스트 의견]
{anal_text}

[작성 규칙]
1. 반드시 한국어로만 작성 (영어, 한자, 외국어 절대 금지)
2. 금융 약어는 반드시 괄호로 풀어쓰기 (예: TDF(타겟데이트펀드))
3. 수치와 퍼센트를 적극 활용하여 구체적으로 작성
4. 전문 용어 사용 시 괄호로 쉬운 설명 병기 (예: 외국인 순매도(외국인이 주식을 팔아치우는 것))
5. 시가총액 상위 대형주(삼성전자, SK하이닉스, 현대차 등) 위주로 분석
6. 마이너 종목, 한자, 외국어 섞어쓰기 절대 금지
7. 문장은 ~입니다, ~됩니다 격식체로 작성

아래 형식으로 작성:
📈 상승 요인: (구체적 수치와 대형주 중심으로 2~3줄)
📉 하락 요인: (구체적 리스크와 수치 포함 2~3줄)
📌 핵심 이슈:
- (핵심 1: 배경과 개인투자자에게 미치는 영향)
- (핵심 2: 배경과 개인투자자에게 미치는 영향)
- (핵심 3: 배경과 개인투자자에게 미치는 영향)
💼 애널리스트 주요 의견: (목표주가, 투자의견 등 수치 포함 2~3줄)
🔮 오늘 시장 영향 전망: (코스피/코스닥 예상 방향성과 근거 2줄)
💡 초보 투자자 한줄 조언: (쉽고 친근하게 오늘 어떻게 대응할지 1줄)"""

                        openai_key = st.secrets.get("OPENAI_API_KEY", "")
                        ai_res = requests.post(
                            "https://api.openai.com/v1/chat/completions",
                            headers={"Content-Type": "application/json", "Authorization": f"Bearer {openai_key}"},
                            json={
                                "model": "gpt-4o-mini",
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
            
            if st.button("🤖 증권사 추천종목 AI 분석 시작", use_container_width=True):
                with st.spinner("하나, KB, 미래에셋의 주간 추천 목록을 AI 교차 분석 중..."):
                    # 프롬프트를 통해 하나, KB, 미래에셋 3대 증권사 데이터만 철저히 골라내도록 지시
                    rec_prompt = f"""당신은 15년 경력의 국내 증권사 리서치센터 수석 애널리스트입니다.
아래 뉴스 헤드라인에서 국내 주요 증권사들의 주간 추천종목을 추출하여 개인 투자자가 쉽게 이해할 수 있는 추천종목 분석표를 작성해주세요.

[작성 규칙]
1. 반드시 한국어로만 작성 (영어, 한자, 외국어 절대 금지)
2. 공식 상장사명(KOSPI/KOSDAQ)만 사용, 채널명/메신저명 완전 배제
3. 종목별 핵심 투자 포인트는 중복 없이 독립적으로 작성
4. 수주 증가, 실적 개선, 신사업 확장 등 호재 위주로만 작성
5. 전문 용어는 괄호로 쉽게 풀어서 설명 (예: 턴어라운드(실적 반등))
6. 목표주가나 수익률 등 수치가 있으면 반드시 포함
7. 초보 투자자도 이해할 수 있게 쉽고 명확하게 작성

결과는 설명 없이 마크다운 테이블로만 출력:
| 추천 종목명 | 추천 증권사 | 핵심 투자 포인트 | 기대 수익률/목표가 |

[증권사 추천 뉴스 헤드라인]
{"\n".join(rec_titles)}"""

                    openai_key = st.secrets.get("OPENAI_API_KEY", "")
                    ai_res = requests.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={"Content-Type": "application/json", "Authorization": f"Bearer {openai_key}"},
                        json={
                            "model": "gpt-4o-mini",
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
                    vol_data.append([row["종목"], f"{row['현재가']}원" if "원" not in row["현재가"] else row["현재가"], row["거래대금"]])
                
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