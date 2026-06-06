import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import datetime as dt
import requests
from ui_components import (
    card, CANDLE_UP, CANDLE_DOWN, DIM, TEXT, SURFACE_1, SURFACE_2, LINE, BG, ACCENT
)

def render_report():
    st.markdown(
        "<div style='font-size:22px; font-weight:700; margin-bottom:4px;'>?뱥 Daily Quantfolio Report</div>"
        f"<div style='font-size:12px; color:{DIM}; margin-bottom:24px;'>{dt.datetime.now():%Y??%m??%d??%H:%M} 湲곗?</div>",
        unsafe_allow_html=True
    )

    # ?? ?쇨컙/二쇨컙 ?좉? ??
    report_type = st.radio("由ы룷???좏삎", ["?뱟 ?쇨컙 由ы룷??, "?뱠 二쇨컙 由ы룷??], horizontal=True)

    if report_type == "?뱟 ?쇨컙 由ы룷??:
        render_daily_report()
    else:
        render_weekly_report()


def render_daily_report():

    # ?? 1. ?쒖옣 ?꾪솴 ??
    card("?뙋 ?쒖옣 ?꾪솴", "二쇱슂 吏??쨌 ?섏쑉 쨌 ?먯옄???ㅼ떆媛?)

    @st.cache_data(ttl=300)
    def get_market_data():
        indices = {
            "肄붿뒪??: "^KS11",
            "肄붿뒪??: "^KQ11",
            "?섏뒪??: "^IXIC",
            "???щ윭": "USDKRW=X",
            "WTI??: "CL=F",
            "湲?: "GC=F",
            "誘멸뎅10?꾩콈": "^TNX"
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

    with st.spinner("?쒖옣 ?곗씠??遺덈윭?ㅻ뒗 以?.."):
        market_data = get_market_data()

    if market_data:
        cols = st.columns(4)
        for i, idx in enumerate(market_data):
            with cols[i % 4]:
                color = CANDLE_UP if idx["change"] >= 0 else CANDLE_DOWN
                arrow = "?? if idx["change"] >= 0 else "??
                st.markdown(f"""
                <div style='background:{SURFACE_2}; border:0.5px solid {LINE}; border-radius:12px; padding:12px 16px; margin-bottom:12px; box-shadow:0 4px 24px rgba(0,0,0,0.4);'>
                    <div style='font-size:11px; color:#9ca3af; margin-bottom:4px; font-weight:500;'>{idx["name"]}</div>
                    <div style='font-family:JetBrains Mono; font-size:17px; font-weight:600;'>{idx["price"]:,.2f}</div>
                    <div style='font-family:JetBrains Mono; font-size:12px; color:{color}; margin-top:2px;'>{arrow} {idx["change"]:+,.2f} ({idx["pct"]:+.2f}%)</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)

    # ?? 2. 愿?ъ쥌紐??좏샇 由ы룷????
    if st.session_state.get("watchlist"):
        card("?뵒 愿?ъ쥌紐??좏샇 由ы룷??, "RSI 湲곗? 留ㅼ닔/留ㅻ룄 ?좏샇 쨌 ?댁씪 蹂?숈꽦 ?뚰뙆 紐⑺몴媛")

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

                    _, _, sig, _, _, _, _, _, _ = run_strategy(df_w, "RSI ?꾨왂 (RSI)", 40, 20, 60, 20)
                    last_sig = sig.iloc[-1].values[0]
                    rsi_series = calculate_rsi(close)
                    rsi_val = float(rsi_series.iloc[-1])

                    # 蹂?숈꽦 ?뚰뙆 ?댁씪 紐⑺몴媛
                    today_open = float(hist["Open"].iloc[-1])
                    yesterday_high = float(high.iloc[-2])
                    yesterday_low = float(low.iloc[-2])
                    vb_target = today_open + (yesterday_high - yesterday_low) * 0.5

                    signal_str = "?윟 留ㅼ닔" if last_sig == 1 else "??愿留?
                    rsi_label = "怨쇰ℓ?? if rsi_val < 30 else ("怨쇰ℓ?? if rsi_val > 70 else "以묐┰")

                    rows.append({
                        "醫낅ぉ": item,
                        "?좏샇": signal_str,
                        "RSI": f"{rsi_val:.1f} ({rsi_label})",
                        "?댁씪 蹂?숈꽦 紐⑺몴媛": f"{int(vb_target):,}??,
                    })
                except:
                    pass
            return rows

        with st.spinner("?좏샇 遺꾩꽍 以?.."):
            signal_rows = get_signal_report(tuple(st.session_state.watchlist))

        if signal_rows:
            st.dataframe(pd.DataFrame(signal_rows), use_container_width=True, hide_index=True)

        st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)

    # ?? 3. ?ы듃?대━???꾪솴 ??
    try:
        from broker import get_access_token, get_balance
        token = get_access_token()
        balance_data = get_balance(token)
        if balance_data.get("rt_cd") == "0":
            card("?뮳 ?ы듃?대━???꾪솴", "KIS API ?ㅼ떆媛?湲곗?")
            output2 = balance_data.get("output2", [{}])[0]
            total_eval = int(output2.get("scts_evlu_amt", 0))
            total_profit = int(output2.get("evlu_pfls_smtl_amt", 0))
            cash = int(output2.get("dnca_tot_amt", 0))
            withdrawable = int(output2.get("nxdy_excc_amt", 0))

            profit_color = "#ef4444" if total_profit >= 0 else "#3b82f6"
            profit_arrow = "?? if total_profit >= 0 else "??

            p1, p2, p3, p4 = st.columns(4)
            for col, label, value, color in [
                (p1, "?뮳 珥??됯?湲덉븸", f"{total_eval:,}??, TEXT),
                (p2, "?뱢 ?됯??먯씡", f"{profit_arrow} {total_profit:+,}??, profit_color),
                (p3, "?뮥 ?덉닔湲?, f"{cash:,}??, TEXT),
                (p4, "?룲 異쒓툑媛??, f"{withdrawable:,}??, TEXT),
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
                    "醫낅ぉ": h.get("prdt_name", ""),
                    "?섎웾": int(h.get("hldg_qty", 0)),
                    "?꾩옱媛": f"{int(h.get('prpr', 0)):,}??,
                    "?됯퇏?④?": f"{float(h.get('pchs_avg_pric', 0)):,.0f}??,
                    "?됯??먯씡": f"{float(h.get('evlu_pfls_amt', 0)):+,.0f}??,
                    "?섏씡瑜?: f"{float(h.get('evlu_pfls_rt', 0)):+.2f}%"
                } for h in holdings if int(h.get("hldg_qty", 0)) > 0])
                if not hdf.empty:
                    st.dataframe(hdf, use_container_width=True, hide_index=True)
    except:
        card("?뮳 ?ы듃?대━???꾪솴", "KIS API ?곌껐 ?꾩슂")
        st.info("KIS API媛 ?곌껐?섏? ?딆븯?댁슂.")

    st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)

    # ?? 4. ?곴?愿怨?遺뺢눼 寃쎈낫 ??
    if st.session_state.get("watchlist") and len(st.session_state.watchlist) >= 2:
        card("?슚 ?곴?愿怨?遺뺢눼 寃쎈낫", "蹂댁쑀醫낅ぉ 媛?濡ㅻ쭅 ?곴?愿怨?쨌 1.0??媛源뚯슱?섎줉 遺꾩궛 臾대젰??)

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
            avg_corr = corr.where(~np.eye(len(corr), dtype=bool)).stack().mean()
            if avg_corr > 0.8:
                st.error(f"?좑툘 ?됯퇏 ?곴?愿怨?{avg_corr:.2f} ??遺꾩궛 ?④낵 嫄곗쓽 ?놁쓬! ?꾧툑 鍮꾩쨷 ?뺣? 沅뚭퀬")
            elif avg_corr > 0.6:
                st.warning(f"?윞 ?됯퇏 ?곴?愿怨?{avg_corr:.2f} ??遺꾩궛 ?④낵 ?쏀솕 以? 二쇱쓽 ?꾩슂")
            else:
                st.success(f"?윟 ?됯퇏 ?곴?愿怨?{avg_corr:.2f} ??遺꾩궛 ?④낵 ?묓샇")

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

    # ?? 5. ?ㅻ쭏??癒몃땲 ?몃뜳????
    card("?쭬 ?ㅻ쭏??癒몃땲 ?몃뜳??, "???쒖옉 30遺?vs 留덇컧 30遺??깅씫 ?ㅽ봽?덈뱶 쨌 湲곌?쨌?몄씤 ?섎룄 異붿쟻")
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
            res = requests.get(f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice",
                             headers=headers, params=params)
            data = res.json()
            if data.get("rt_cd") == "0":
                output = data.get("output2", [])
                if len(output) >= 2:
                    df_min = pd.DataFrame(output)
                    df_min["stck_bsop_date"] = pd.to_datetime(df_min["stck_cntg_hour"], format="%H%M%S")
                    return df_min
            return None

        smi_data = get_smi(token)
        if smi_data is not None:
            st.success("?ㅻ쭏??癒몃땲 ?몃뜳???곗씠???섏쭛 ?꾨즺")
        else:
            st.info("?뱤 ??以묒뿉留??ㅻ쭏??癒몃땲 ?몃뜳?ㅺ? ?쒖꽦?붾뤌?? (09:00 ~ 15:30)")
    except:
        st.info("?뱤 KIS API ?곌껐 ???ㅻ쭏??癒몃땲 ?몃뜳?ㅺ? ?쒖꽦?붾뤌??")

    st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)

    # ?? 6. ?쒖옣 ?댁뒋 & ?댁뒪 ??
    card("?벐 ?쒖옣 ?댁뒋 & ?댁뒪", "?ㅻ뒛??二쇱슂 ?쒖옣 ?댁뒪")
    try:
        naver_id = st.secrets.get("NAVER_CLIENT_ID", "")
        naver_secret = st.secrets.get("NAVER_CLIENT_SECRET", "")
        url = "https://openapi.naver.com/v1/search/news.json?query=二쇱떇+肄붿뒪??display=5&sort=date"
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
            st.info("?댁뒪瑜?遺덈윭?ㅼ? 紐삵뻽?댁슂.")
    except:
        st.info("?댁뒪瑜?遺덈윭?ㅼ? 紐삵뻽?댁슂.")

    # ?? PDF ?ㅼ슫濡쒕뱶 踰꾪듉 (異뷀썑 援ы쁽) ??
    st.markdown("<div style='margin-top:32px;'></div>", unsafe_allow_html=True)
    st.info("?뱞 PDF ?ㅼ슫濡쒕뱶 諛?移댁뭅?ㅽ넚 ?먮룞 諛쒖넚 湲곕뒫? 怨?異붽??쇱슂!")


def render_weekly_report():
    st.markdown(
        f"<div style='font-size:15px; color:{DIM}; margin-bottom:20px;'>二쇨컙 由ы룷????{dt.datetime.now():%Y??%m?? 湲곗?</div>",
        unsafe_allow_html=True
    )

    # ?? 二쇨컙 ?쒖옣 ?붿빟 ??
    card("?뱤 二쇨컙 ?쒖옣 ?붿빟", "肄붿뒪??肄붿뒪???섏뒪??二쇨컙 ?깅씫")

    @st.cache_data(ttl=3600)
    def get_weekly_market():
        indices = {"肄붿뒪??: "^KS11", "肄붿뒪??: "^KQ11", "?섏뒪??: "^IXIC", "S&P500": "^GSPC"}
        result = []
        for name, ticker in indices.items():
            try:
                hist = yf.Ticker(ticker).history(period="1mo").dropna(subset=["Close"])
                if len(hist) >= 6:
                    curr = hist["Close"].iloc[-1]
                    week_ago = hist["Close"].iloc[-6]
                    chg_pct = (curr - week_ago) / week_ago * 100
                    result.append({"吏??: name, "?꾩옱媛": f"{curr:,.2f}", "二쇨컙 ?깅씫": f"{chg_pct:+.2f}%", "_pct": chg_pct})
            except:
                pass
        return result

    weekly_data = get_weekly_market()
    if weekly_data:
        cols = st.columns(len(weekly_data))
        for i, d in enumerate(weekly_data):
            with cols[i]:
                color = CANDLE_UP if d["_pct"] >= 0 else CANDLE_DOWN
                arrow = "?? if d["_pct"] >= 0 else "??
                st.markdown(f"""
                <div style='background:{SURFACE_2}; border:0.5px solid {LINE}; border-radius:12px; padding:14px 16px; margin-bottom:12px; box-shadow:0 4px 24px rgba(0,0,0,0.4);'>
                    <div style='font-size:11px; color:#9ca3af; margin-bottom:4px;'>{d["吏??]}</div>
                    <div style='font-family:JetBrains Mono; font-size:17px; font-weight:600;'>{d["?꾩옱媛"]}</div>
                    <div style='font-family:JetBrains Mono; font-size:12px; color:{color}; margin-top:2px;'>{arrow} {d["二쇨컙 ?깅씫"]}</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)

    # ?? 二쇨컙 愿?ъ쥌紐??깃낵 ??
    if st.session_state.get("watchlist"):
        card("?뱢 愿?ъ쥌紐?二쇨컙 ?깃낵", "?대쾲 二??섏씡瑜??쒖쐞")

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
                        rows.append({"醫낅ぉ": item, "二쇨컙 ?섏씡瑜?: f"{chg_pct:+.2f}%", "_pct": chg_pct})
                except:
                    pass
            return sorted(rows, key=lambda x: x["_pct"], reverse=True)

        weekly_returns = get_weekly_returns(tuple(st.session_state.watchlist))
        if weekly_returns:
            df_weekly = pd.DataFrame([{k: v for k, v in r.items() if k != "_pct"} for r in weekly_returns])
            st.dataframe(df_weekly, use_container_width=True, hide_index=True)

    st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)

    # ?? ?ㅼ쓬 二?寃쎌젣 罹섎┛????
    card("?뱟 ?ㅼ쓬 二?寃쎌젣 罹섎┛??, "二쇱슂 寃쎌젣 吏??諛쒗몴 ?쇱젙")
    st.info("?뵩 寃쎌젣 罹섎┛?붾뒗 investing.com ?곕룞?쇰줈 怨?異붽??쇱슂!")

