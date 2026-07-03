import streamlit as st
import yfinance as yf
import requests
import datetime as dt
from ui_components import (
    card, CANDLE_UP, CANDLE_DOWN, DIM, TEXT, SURFACE_1, SURFACE_2, LINE, BG, ACCENT
)


@st.cache_data(ttl=300)
def get_us_market_data():
    """미국 주요 지수 + 공포지수(VIX) + 달러인덱스"""
    indices = {
        "나스닥": "^IXIC",
        "S&P500": "^GSPC",
        "다우존스": "^DJI",
        "VIX(공포지수)": "^VIX",
        "달러인덱스": "DX-Y.NYB",
        "미국10년채": "^TNX",
        "WTI유": "CL=F",
        "금": "GC=F",
    }
    result = []
    for name, ticker in indices.items():
        try:
            hist = yf.Ticker(ticker).history(period="5d").dropna(subset=["Close"])
            if len(hist) >= 2:
                curr = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2])
                chg = curr - prev
                chg_pct = (chg / prev) * 100
                result.append({"name": name, "price": curr, "change": chg, "pct": chg_pct})
        except:
            pass
    return result


@st.cache_data(ttl=300)
def get_us_sector_data():
    """미국 섹터 ETF 등락률 (반도체/빅테크/AI 중심)"""
    sectors = {
        "반도체(SOX)": "SOXX",
        "빅테크(QQQ)": "QQQ",
        "AI(BOTZ)": "BOTZ",
        "필라델피아반도체": "^SOX",
        "에너지": "XLE",
        "금융": "XLF",
    }
    result = []
    for name, ticker in sectors.items():
        try:
            hist = yf.Ticker(ticker).history(period="5d").dropna(subset=["Close"])
            if len(hist) >= 2:
                curr = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2])
                chg_pct = (curr - prev) / prev * 100
                result.append({"섹터": name, "등락률": chg_pct})
        except:
            pass
    return sorted(result, key=lambda x: x["등락률"], reverse=True)


@st.cache_data(ttl=600)
def collect_morning_news():
    """미국장 중심 뉴스 수집 (RSS + 네이버 API fallback)"""
    import xml.etree.ElementTree as ET
    news = {"미국장": [], "국내전망": [], "섹터/종목": []}

    # 1. RSS 시도
    rss_sources = [
        ("미국장", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258"),
        ("미국장", "https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines"),
        ("국내전망", "https://www.hankyung.com/feed/stock-market"),
        ("국내전망", "https://www.mk.co.kr/rss/30000001/"),
    ]
    for category, url in rss_sources:
        try:
            res = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1)"})
            if res.status_code == 200:
                root = ET.fromstring(res.content)
                for item in root.iter("item"):
                    title = item.findtext("title", "").strip()
                    link = item.findtext("link", "").strip()
                    if title and len(news[category]) < 5:
                        news[category].append({"title": title, "link": link})
        except:
            pass

    # 2. 네이버 API fallback
    naver_id = st.secrets.get("NAVER_CLIENT_ID", "")
    naver_secret = st.secrets.get("NAVER_CLIENT_SECRET", "")
    headers = {"X-Naver-Client-Id": naver_id, "X-Naver-Client-Secret": naver_secret}

    queries = [
        ("미국장", "나스닥+미국증시+마감"),
        ("미국장", "S&P500+뉴욕증시+마감"),
        ("국내전망", "코스피+코스닥+전망+오늘"),
        ("섹터/종목", "반도체+AI+빅테크+주식"),
        ("섹터/종목", "외국인+기관+순매수+오늘"),
    ]
    for category, query in queries:
        if len(news[category]) >= 5:
            continue
        try:
            res = requests.get(
                f"https://openapi.naver.com/v1/search/news.json?query={query}&display=5&sort=date",
                headers=headers, timeout=5
            )
            for item in res.json().get("items", []):
                title = item["title"].replace("<b>", "").replace("</b>", "")
                if len(news[category]) < 5:
                    news[category].append({"title": title, "link": item["link"]})
        except:
            pass

    return news


def render_morning():
    """🌅 아침 브리핑 — 장 시작 전 필수 확인"""

    kst_now = dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))
    st.markdown(
        f"<div style='font-size:12px; color:{DIM}; margin-bottom:16px;'>🕘 {kst_now:%Y년 %m월 %d일 %H:%M} KST 기준 · 장 시작 전 브리핑</div>",
        unsafe_allow_html=True
    )

    # ── 1. 미국 주요 지수 ──
    card("🌎 미국 시장 마감", "나스닥 · S&P500 · 다우 · VIX · 달러")
    with st.spinner("미국 시장 데이터 불러오는 중..."):
        us_data = get_us_market_data()

    if us_data:
        # 핵심 지수 4개 (나스닥, S&P500, VIX, 달러인덱스)
        core = [d for d in us_data if d["name"] in ["나스닥", "S&P500", "다우존스", "VIX(공포지수)"]]
        macro = [d for d in us_data if d["name"] in ["달러인덱스", "미국10년채", "WTI유", "금"]]

        # 핵심 지수 카드
        cols = st.columns(len(core))
        for col, idx in zip(cols, core):
            color = CANDLE_UP if idx["change"] >= 0 else CANDLE_DOWN
            arrow = "▲" if idx["change"] >= 0 else "▼"
            # VIX는 반대 (오르면 위험)
            if idx["name"] == "VIX(공포지수)":
                color = CANDLE_DOWN if idx["change"] >= 0 else CANDLE_UP
            with col:
                st.markdown(f"<div style='background:{SURFACE_1}; border:0.5px solid {LINE}; border-radius:12px; padding:12px 16px; margin-bottom:12px;'><div style='font-size:11px; color:{DIM}; margin-bottom:4px;'>{idx['name']}</div><div style='font-family:JetBrains Mono; font-size:17px; font-weight:600;'>{idx['price']:,.2f}</div><div style='font-size:12px; color:{color}; margin-top:2px;'>{arrow} {idx['pct']:+.2f}%</div></div>", unsafe_allow_html=True)

        # 매크로 지표 (작게)
        macro_cols = st.columns(len(macro))
        for col, idx in zip(macro_cols, macro):
            color = CANDLE_UP if idx["change"] >= 0 else CANDLE_DOWN
            arrow = "▲" if idx["change"] >= 0 else "▼"
            with col:
                st.markdown(f"<div style='background:{SURFACE_2}; border:0.5px solid {LINE}; border-radius:8px; padding:8px 12px; margin-bottom:12px;'><div style='font-size:10px; color:{DIM}; margin-bottom:2px;'>{idx['name']}</div><div style='font-family:JetBrains Mono; font-size:13px; font-weight:600;'>{idx['price']:,.2f}</div><div style='font-size:11px; color:{color};'>{arrow} {idx['pct']:+.2f}%</div></div>", unsafe_allow_html=True)

        # VIX 해석
        vix_item = next((d for d in us_data if d["name"] == "VIX(공포지수)"), None)
        if vix_item:
            vix_val = vix_item["price"]
            if vix_val >= 30:
                vix_msg = f"🔴 VIX {vix_val:.1f} — 공포 구간. 변동성 크니 단타 주의"
                vix_color = "#ef4444"
            elif vix_val >= 20:
                vix_msg = f"🟡 VIX {vix_val:.1f} — 불안 구간. 신중하게 접근"
                vix_color = "#f59e0b"
            else:
                vix_msg = f"🟢 VIX {vix_val:.1f} — 안정 구간. 시장 심리 양호"
                vix_color = "#22c55e"
            st.markdown(f"<div style='background:{SURFACE_1}; border-left:4px solid {vix_color}; padding:8px 16px; border-radius:0 8px 8px 0; margin-bottom:16px; font-size:12px; color:{TEXT};'>{vix_msg}</div>", unsafe_allow_html=True)
    else:
        st.info("미국 시장 데이터를 불러오지 못했어요.")

    # ── 2. 미국 섹터 등락률 ──
    card("🔬 미국 섹터 등락률", "반도체 · 빅테크 · AI — 국내 관련주 영향 파악")
    with st.spinner("섹터 데이터 불러오는 중..."):
        sector_data = get_us_sector_data()

    if sector_data:
        cols = st.columns(len(sector_data))
        for col, s in zip(cols, sector_data):
            color = CANDLE_UP if s["등락률"] >= 0 else CANDLE_DOWN
            arrow = "▲" if s["등락률"] >= 0 else "▼"
            with col:
                st.markdown(f"<div style='background:{SURFACE_1}; border:0.5px solid {LINE}; border-radius:8px; padding:10px 12px; text-align:center;'><div style='font-size:11px; color:{DIM}; margin-bottom:4px;'>{s['섹터']}</div><div style='font-size:14px; font-weight:700; color:{color}; font-family:JetBrains Mono;'>{arrow} {s['등락률']:+.2f}%</div></div>", unsafe_allow_html=True)

        # 반도체 섹터가 국내 영향 큰 거 강조
        sox = next((s for s in sector_data if "반도체" in s["섹터"] or "SOX" in s["섹터"]), None)
        if sox:
            impact = "삼성전자·SK하이닉스 강세 예상" if sox["등락률"] >= 0 else "삼성전자·SK하이닉스 약세 주의"
            impact_color = CANDLE_UP if sox["등락률"] >= 0 else CANDLE_DOWN
            st.markdown(f"<div style='font-size:12px; color:{impact_color}; margin-top:8px; margin-bottom:16px;'>💡 {impact}</div>", unsafe_allow_html=True)

    # ── 3. 오늘의 뉴스 ──
    card("📰 아침 뉴스", "미국장 · 국내 전망 · 섹터 이슈")
    with st.spinner("뉴스 수집 중..."):
        morning_news = collect_morning_news()

    news_items_for_ai = []
    for category, emoji, label in [("미국장", "🌎", "미국장"), ("국내전망", "🇰🇷", "국내 전망"), ("섹터/종목", "📊", "섹터/종목")]:
        news_list = morning_news.get(category, [])
        if news_list:
            st.markdown(f"<div style='font-size:13px; font-weight:600; color:{TEXT}; margin:12px 0 6px;'>{emoji} {label}</div>", unsafe_allow_html=True)
            for item in news_list[:3]:
                st.markdown(f"<div style='background:{SURFACE_1}; border:0.5px solid {LINE}; border-radius:10px; padding:10px 14px; margin-bottom:6px;'><a href='{item['link']}' target='_blank' style='color:{TEXT}; text-decoration:none; font-size:13px;'>{item['title']}</a></div>", unsafe_allow_html=True)
            news_items_for_ai.extend(news_list[:3])

    # ── 4. AI 아침 브리핑 ──
    card("🤖 AI 아침 브리핑", "미국장 마감 요약 → 오늘 국내 시장 전략")

    if st.button("📋 AI 브리핑 생성", use_container_width=True, key="morning_ai_btn"):
        with st.spinner("AI 브리핑 생성 중..."):
            try:
                # 시장 데이터 텍스트화
                us_text = ""
                for d in (us_data or []):
                    arrow = "상승" if d["change"] >= 0 else "하락"
                    us_text += f"- {d['name']}: {d['price']:,.2f} ({arrow} {d['pct']:+.2f}%)\n"

                # 섹터 텍스트화
                sector_text = "\n".join([f"- {s['섹터']}: {s['등락률']:+.2f}%" for s in (sector_data or [])])

                # 뉴스 텍스트화
                news_text = "\n".join([f"- {n['title']}" for n in news_items_for_ai])

                prompt = f"""당신은 국내 주식시장 전문 애널리스트입니다. 아래 미국 시장 마감 데이터와 뉴스를 보고, 오늘 한국 장 시작 전 투자자에게 꼭 필요한 브리핑을 작성해주세요.

[미국 시장 마감 지표]
{us_text}

[미국 섹터 등락률]
{sector_text}

[주요 뉴스]
{news_text}

[작성 규칙]
1. 반드시 한국어로만 작성
2. 위 실제 수치를 반드시 정확히 인용 (절대 임의 수치 생성 금지)
3. 나스닥이 올랐는데 하락이라고 쓰는 등 방향 오류 절대 금지
4. 반도체/AI 섹터 국내 영향 반드시 포함
5. 단타 투자자 관점으로 작성
6. 간결하게 각 섹션 2~3줄

아래 형식으로 작성:

🌎 미국장 마감 요약
(나스닥/S&P500 등락률 + 주요 원인)

📊 국내 시장 영향 전망
(오늘 코스피/코스닥 예상 방향 + 근거)

🔥 오늘 주목할 섹터/종목
(반도체/AI/수급 기반 오늘 주목 포인트)

⚠️ 오늘 리스크 요인
(조심해야 할 것)

💡 오늘의 단타 전략
(단 1줄 — 오늘 어떻게 대응할지)"""

                openai_key = st.secrets.get("OPENAI_API_KEY", "")
                res = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {openai_key}"},
                    json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}], "max_tokens": 600}
                )
                data = res.json()
                if "choices" not in data:
                    raise Exception(str(data))
                summary = data["choices"][0]["message"]["content"]
                st.session_state["morning_ai_summary"] = summary

            except Exception as e:
                st.error(f"AI 브리핑 생성 실패: {e}")

    if st.session_state.get("morning_ai_summary"):
        st.markdown(f"<div style='background:{SURFACE_2}; border:0.5px solid {LINE}; border-radius:12px; padding:20px; margin-top:12px;'><div style='font-size:13px; font-weight:700; color:{DIM}; margin-bottom:16px; letter-spacing:1px;'>🤖 AI 아침 브리핑</div><div style='font-size:13px; line-height:2.0; white-space:pre-line; color:{TEXT};'>{st.session_state['morning_ai_summary']}</div></div>", unsafe_allow_html=True)

    # ── 5. 오늘의 체크리스트 ──
    card("✅ 장 시작 전 체크리스트", "오늘 매매 전 반드시 확인")

    checklist = [
        ("미국 나스닥 방향 확인했나요?", "위 미국 시장 데이터 참고"),
        ("오늘 주목할 섹터를 정했나요?", "반도체/AI/방산/조선 중 강세 섹터"),
        ("진입 기준 3가지를 충족하는 종목이 있나요?", "거래량 + 수급 + 차트"),
        ("1회 투입 금액 상한선을 지킬 건가요?", "총 자산의 15% 이하"),
        ("손절가를 미리 정했나요?", "진입 전 반드시 설정"),
    ]

    for i, (check, hint) in enumerate(checklist):
        checked = st.session_state.get(f"morning_check_{i}", False)
        col1, col2 = st.columns([1, 10])
        with col1:
            if st.checkbox("", value=checked, key=f"morning_check_{i}"):
                pass
        with col2:
            color = "#22c55e" if st.session_state.get(f"morning_check_{i}") else TEXT
            st.markdown(f"<div style='padding-top:4px; font-size:13px; color:{color};'>{check}<div style='font-size:11px; color:{DIM};'>{hint}</div></div>", unsafe_allow_html=True)

    total_checked = sum(1 for i in range(len(checklist)) if st.session_state.get(f"morning_check_{i}"))
    if total_checked == len(checklist):
        st.success("✅ 모든 체크 완료! 오늘 매매 준비됐어요.")
    elif total_checked >= 3:
        st.warning(f"⚠️ {total_checked}/{len(checklist)} 완료 — 나머지도 확인해보세요.")
    else:
        st.error(f"🔴 {total_checked}/{len(checklist)} 완료 — 아직 준비가 덜 됐어요.")