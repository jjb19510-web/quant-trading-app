import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from ui_components import card, CANDLE_UP, CANDLE_DOWN, DIM, TEXT, SURFACE_1, LINE, BG, SURFACE_2

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

def render_dashboard():
    # ── 시장 현황 ──
    @st.cache_data(ttl=300)
    def get_market_indices():
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
                hist = yf.Ticker(ticker).history(period="1mo")
                hist = hist.dropna(subset=["Close"])
                if len(hist) >= 2:
                    curr = hist["Close"].iloc[-1]
                    prev = hist["Close"].iloc[-2]
                    chg = curr - prev
                    chg_pct = (chg / prev) * 100
                    result.append({"name": name, "price": curr, "change": chg, "pct": chg_pct})
            except:
                pass
        return result

    def render_index_card(col, idx, margin_top=False):
        color = CANDLE_UP if idx["change"] >= 0 else CANDLE_DOWN
        arrow = "▲" if idx["change"] >= 0 else "▼"
        mt = "margin-top:16px;" if margin_top else ""
        with col:
            st.markdown(f"""
            <div style='background:{SURFACE_1}; border:0.5px solid {LINE}; border-radius:12px; padding:12px 16px; margin-bottom:16px; {mt}'>
                <div style='font-size:11px; color:#9ca3af; margin-bottom:4px; font-weight:500;'>{idx["name"]}</div>
                <div style='font-family:JetBrains Mono; font-size:18px; font-weight:600;'>{idx["price"]:,.2f}</div>
                <div style='font-family:JetBrains Mono; font-size:12px; color:{color}; margin-top:2px;'>{arrow} {idx["change"]:+,.2f} ({idx["pct"]:+.2f}%)</div>
            </div>
            """, unsafe_allow_html=True)

    indices = get_market_indices()
    if indices:
        row1 = indices[:3]
        row2 = indices[3:]
        cols1 = st.columns(len(row1))
        for col, idx in zip(cols1, row1):
            render_index_card(col, idx, margin_top=True)
        if row2:
            cols2 = st.columns(len(row2))
            for col, idx in zip(cols2, row2):
                render_index_card(col, idx, margin_top=False)

    # ── 관심종목 수익률 순위 ──
    if st.session_state.watchlist:
        @st.cache_data(ttl=300)
        def get_watchlist_returns(watchlist):
            name_map = get_krx_name_map()
            result = []
            for item in watchlist:
                ticker = item + ".KS" if not item.endswith(".KS") else item
                try:
                    hist = yf.Ticker(ticker).history(period="1y")
                    if len(hist) >= 2:
                        curr = hist["Close"].iloc[-1]
                        start = hist["Close"].iloc[0]
                        ret = (curr - start) / start * 100
                        chg = hist["Close"].iloc[-1] - hist["Close"].iloc[-2]
                        chg_pct = (chg / hist["Close"].iloc[-2]) * 100
                        display = name_map.get(item, item)
                        result.append({
                            "종목": f"{display} ({item})",
                            "현재가": f"{int(curr):,}원",
                            "1년 수익률": f"{ret:+.1f}%",
                            "전일비": f"{chg_pct:+.2f}%",
                            "_ret": ret
                        })
                except:
                    pass
            return sorted(result, key=lambda x: x["_ret"], reverse=True)

        with st.spinner("관심종목 수익률 조회 중..."):
            wl_data = get_watchlist_returns(tuple(st.session_state.watchlist))
        if wl_data:
            card("📊 관심종목 수익률 순위", "1년 수익률 기준")
            display_df = pd.DataFrame([{k: v for k, v in d.items() if k != "_ret"} for d in wl_data])
            st.dataframe(display_df, use_container_width=True, hide_index=True)

    # ── 거래량 급증 감지 ──
    if st.session_state.watchlist:
        @st.cache_data(ttl=300)
        def get_volume_spike(watchlist):
            name_map = get_krx_name_map()
            result = []
            for item in watchlist:
                ticker = item + ".KS" if not item.endswith(".KS") else item
                try:
                    hist = yf.Ticker(ticker).history(period="2mo").dropna(subset=["Close"])
                    if len(hist) < 22:
                        continue
                    vol_today = float(hist["Volume"].iloc[-1])
                    vol_ma20 = float(hist["Volume"].iloc[-21:-1].mean())
                    if vol_ma20 == 0:
                        continue
                    ratio = vol_today / vol_ma20
                    curr = float(hist["Close"].iloc[-1])
                    prev = float(hist["Close"].iloc[-2])
                    chg_pct = (curr - prev) / prev * 100
                    display = name_map.get(item, item)

                    if ratio >= 2.0:
                        result.append({
                            "종목": display,
                            "현재가": f"{int(curr):,}원",
                            "등락률": chg_pct,
                            "거래량 배수": ratio,
                            "_ratio": ratio
                        })
                except:
                    pass
            return sorted(result, key=lambda x: x["_ratio"], reverse=True)

        with st.spinner("거래량 급증 감지 중..."):
            spike_data = get_volume_spike(tuple(st.session_state.watchlist))

        if spike_data:
            card("🚨 거래량 급증 감지", "관심종목 중 20일 평균 대비 2배 이상 거래량 종목")
            for item in spike_data:
                ratio = item["_ratio"]
                badge = "🚨 폭발" if ratio >= 3 else "🔥 급증"
                color = CANDLE_UP if item["등락률"] >= 0 else CANDLE_DOWN
                arrow = "▲" if item["등락률"] >= 0 else "▼"
                st.markdown(f"<div style='background:{SURFACE_2}; border:0.5px solid {LINE}; border-radius:10px; padding:12px 16px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;'><div><span style='font-size:14px; font-weight:700; color:#e2e8f0;'>{item['종목']}</span> <span style='font-size:12px; background:#ef444420; color:#ef4444; border-radius:6px; padding:2px 8px; margin-left:8px;'>{badge} {ratio:.1f}배</span></div><div style='text-align:right;'><div style='font-size:14px; font-family:JetBrains Mono;'>{item['현재가']}</div><div style='font-size:12px; color:{color}; font-family:JetBrains Mono;'>{arrow} {item['등락률']:+.2f}%</div></div></div>", unsafe_allow_html=True)
        else:
            if st.session_state.watchlist:
                st.caption("관심종목 중 거래량 급증 종목이 없어요. (20일 평균 대비 2배 미만)")

    # ── 섹터별 수익률 비교 ──
    if st.session_state.sectors:
        @st.cache_data(ttl=300)
        def get_sector_returns(sectors_str):
            sectors = st.session_state.sectors
            result = []
            for sector_name, tickers_list in sectors.items():
                sector_rets = []
                for code in tickers_list:
                    ticker = code + ".KS" if not code.endswith(".KS") else code
                    try:
                        hist = yf.Ticker(ticker).history(period="1y")["Close"]
                        if len(hist) >= 2:
                            ret = (hist.iloc[-1] - hist.iloc[0]) / hist.iloc[0] * 100
                            sector_rets.append(ret)
                    except:
                        pass
                if sector_rets:
                    avg_ret = sum(sector_rets) / len(sector_rets)
                    result.append({"섹터": sector_name, "평균 수익률": round(avg_ret, 2), "_ret": avg_ret})
            return sorted(result, key=lambda x: x["_ret"], reverse=True)

        sector_data = get_sector_returns(str(st.session_state.sectors))
        if sector_data:
            card("📂 섹터별 수익률 비교", "1년 수익률 기준")
            fig_sector = go.Figure(go.Bar(
                x=[d["섹터"] for d in sector_data],
                y=[d["평균 수익률"] for d in sector_data],
                marker=dict(color=[CANDLE_UP if d["_ret"] >= 0 else CANDLE_DOWN for d in sector_data], opacity=0.85),
                text=[f"{d['평균 수익률']:+.1f}%" for d in sector_data],
                textposition="outside",
                textfont=dict(family="JetBrains Mono", size=11, color=TEXT),
            ))
            fig_sector.add_hline(y=0, line=dict(color=DIM, width=1, dash="dot"))
            fig_sector.update_layout(
                height=300, margin=dict(l=0, r=20, t=8, b=28),
                paper_bgcolor=BG, plot_bgcolor=BG,
                font=dict(family="Inter, sans-serif", color=TEXT, size=11),
                showlegend=False,
                yaxis=dict(ticksuffix="%", side="right", gridcolor="rgba(255,255,255,0.03)"),
                xaxis=dict(showgrid=False),
            )
            st.plotly_chart(fig_sector, use_container_width=True, config={"displayModeBar": False})

    # ── 상관관계 히트맵 ──
    if st.session_state.watchlist and len(st.session_state.watchlist) >= 2:
        @st.cache_data(ttl=300)
        def get_correlation(watchlist):
            price_data = {}
            for item in watchlist:
                ticker = item + ".KS" if not item.endswith(".KS") else item
                try:
                    hist = yf.Ticker(ticker).history(period="1y")["Close"]
                    if len(hist) > 0:
                        price_data[item] = hist
                except:
                    pass
            if len(price_data) >= 2:
                df_prices = pd.DataFrame(price_data).dropna()
                return df_prices.pct_change().corr()
            return None

        corr = get_correlation(tuple(st.session_state.watchlist))
        if corr is not None:
            name_map = get_krx_name_map()
            corr.index = [name_map.get(i, i) for i in corr.index]
            corr.columns = [name_map.get(c, c) for c in corr.columns]
            card("🔗 관심종목 상관관계", "1에 가까울수록 같이 움직임 · 0에 가까울수록 독립적")
            fig_corr = go.Figure(go.Heatmap(
                z=corr.values,
                x=corr.columns.tolist(),
                y=corr.index.tolist(),
                colorscale=[[0, "#3b82f6"], [0.5, "#1a1f2e"], [1, "#ef4444"]],
                zmin=-1, zmax=1, zmid=0,
                text=[[f"{v*100:.0f}%" for v in row] for row in corr.values],
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