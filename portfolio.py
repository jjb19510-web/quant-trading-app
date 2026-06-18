import streamlit as st
import pandas as pd
from ui_components import card

def render_portfolio(KIS_AVAILABLE, get_kis_token, get_balance):
    if KIS_AVAILABLE:
        col_refresh, _ = st.columns([1, 5])
        with col_refresh:
            if st.button("🔄 새로고침", key="portfolio_refresh"):
                st.cache_data.clear()
                st.rerun()
        kis_token = get_kis_token()
        if kis_token:
            balance_data = get_balance(kis_token)
            if balance_data.get("rt_cd") == "0":
                output2 = balance_data.get("output2", [{}])[0]
                total_eval = int(output2.get("scts_evlu_amt", 0))
                total_profit = int(output2.get("evlu_pfls_smtl_amt", 0))
                cash = int(output2.get("dnca_tot_amt", 0))
                withdrawable = int(output2.get("nxdy_excc_amt", 0))

                profit_color = "#ef4444" if total_profit >= 0 else "#3b82f6"
                profit_arrow = "▲" if total_profit >= 0 else "▼"
                st.markdown(f"""
                <div style='display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:20px;'>
                  <div style='background:#0f1117; border:0.5px solid #1e2330; border-radius:12px; padding:16px 20px; box-shadow:0 4px 24px rgba(0,0,0,0.4);'>
                    <div style='font-size:11px; color:#9ca3af; margin-bottom:6px;'>💼 총 평가금액</div>
                    <div style='font-size:22px; font-weight:600; font-family:JetBrains Mono;'>{total_eval:,}원</div>
                  </div>
                  <div style='background:#0f1117; border:0.5px solid rgba(239,68,68,0.3); border-radius:12px; padding:16px 20px; box-shadow:0 4px 24px rgba(0,0,0,0.4);'>
                    <div style='font-size:11px; color:#9ca3af; margin-bottom:6px;'>📈 평가손익</div>
                    <div style='font-size:22px; font-weight:600; font-family:JetBrains Mono; color:{profit_color};'>{profit_arrow} {total_profit:+,}원</div>
                  </div>
                  <div style='background:#0f1117; border:0.5px solid #1e2330; border-radius:12px; padding:16px 20px; box-shadow:0 4px 24px rgba(0,0,0,0.4);'>
                    <div style='font-size:11px; color:#9ca3af; margin-bottom:6px;'>💰 예수금</div>
                    <div style='font-size:22px; font-weight:600; font-family:JetBrains Mono;'>{cash:,}원</div>
                  </div>
                  <div style='background:#0f1117; border:0.5px solid #1e2330; border-radius:12px; padding:16px 20px; box-shadow:0 4px 24px rgba(0,0,0,0.4);'>
                    <div style='font-size:11px; color:#9ca3af; margin-bottom:6px;'>🏧 출금가능금액</div>
                    <div style='font-size:22px; font-weight:600; font-family:JetBrains Mono;'>{withdrawable:,}원</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                card("📋 보유종목", "현재 포지션 기준")
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
                    else:
                        st.info("보유 종목이 없어요.")

                # ── 리밸런싱 시뮬레이션 ──
                card("⚖️ 리밸런싱 시뮬레이션", "목표 비중으로 조정 시 필요 금액 계산")
                if holdings_list:
                    st.markdown("**목표 비중 설정 (%)**")
                    tickers_held = [h.get("prdt_name", "") for h in holdings_list if int(h.get("hldg_qty", 0)) > 0]
                    target_weights = {}
                    cols_rbl = st.columns(len(tickers_held))
                    for i, t in enumerate(tickers_held):
                        with cols_rbl[i]:
                            target_weights[t] = st.number_input(t, min_value=0, max_value=100, value=round(100/len(tickers_held)), step=5, key=f"rbl_{t}")

                    total_weight = sum(target_weights.values())
                    if total_weight != 100:
                        st.warning(f"⚠️ 목표 비중 합계가 {total_weight}%예요. 100%가 되도록 조정해주세요!")
                    else:
                        rebal_data = []
                        for h in holdings_list:
                            if int(h.get("hldg_qty", 0)) > 0:
                                name = h.get("prdt_name", "")
                                curr_val = int(h.get("evlu_amt", 0))
                                target_val = total_eval * (target_weights.get(name, 0) / 100)
                                diff = target_val - curr_val
                                rebal_data.append({
                                    "종목": name,
                                    "현재금액": f"{curr_val:,}원",
                                    "목표금액": f"{int(target_val):,}원",
                                    "조정금액": f"{diff:+,.0f}원",
                                    "액션": "매수 🟢" if diff > 0 else "매도 🔴"
                                })
                        st.dataframe(pd.DataFrame(rebal_data), use_container_width=True, hide_index=True)
        else:
            st.info("KIS API 연결 필요")
    else:
        st.info("KIS API가 연결되지 않았어요.")

    # ══════════════════════════════════════════
    # 📊 단타 거래 관리
    # ══════════════════════════════════════════
    st.markdown("<div style='margin-top:32px;'></div>", unsafe_allow_html=True)
    card("⚡ 단타 거래 관리", "매수 내역 저장 · 실시간 손익 모니터링 · 목표가/손절가 도달 알림")

    # 저장된 단타 거래 불러오기
    if "daytrading" not in st.session_state:
        st.session_state["daytrading"] = []

    # 새 거래 추가
    with st.expander("➕ 새 단타 거래 추가", expanded=len(st.session_state["daytrading"]) == 0):
        dt1, dt2, dt3 = st.columns(3)
        with dt1:
            dt_name = st.text_input("종목명", placeholder="예: 후성", key="dt_name")
            dt_code = st.text_input("종목코드", placeholder="예: 093370", key="dt_code")
        with dt2:
            dt_buy = st.number_input("매수가 (원)", value=0, step=100, key="dt_buy")
            dt_qty = st.number_input("수량 (주)", value=0, step=1, key="dt_qty")
        with dt3:
            dt_target = st.number_input("목표가 (원)", value=0, step=100, key="dt_target")
            dt_stop = st.number_input("손절가 (원)", value=0, step=100, key="dt_stop")

        dt_memo = st.text_input("메모 (진입 이유)", placeholder="예: 변동성 돌파 K=0.5 진입, 원전 테마 모멘텀", key="dt_memo")

        if st.button("💾 거래 저장", use_container_width=True, key="dt_save"):
            if dt_name and dt_buy > 0 and dt_qty > 0:
                import datetime as dt_module
                new_trade = {
                    "id": len(st.session_state["daytrading"]),
                    "name": dt_name,
                    "code": dt_code.zfill(6) if dt_code else "",
                    "buy_price": dt_buy,
                    "qty": dt_qty,
                    "target": dt_target,
                    "stop": dt_stop,
                    "memo": dt_memo,
                    "buy_date": dt_module.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "status": "보유중",
                    "sell_price": None,
                    "sell_date": None,
                }
                st.session_state["daytrading"].append(new_trade)
                st.success(f"✅ {dt_name} 거래가 저장됐어요!")
                st.rerun()
            else:
                st.warning("종목명, 매수가, 수량은 필수예요.")

    # 저장된 거래 목록
    if st.session_state["daytrading"]:
        holding = [t for t in st.session_state["daytrading"] if t["status"] == "보유중"]
        closed = [t for t in st.session_state["daytrading"] if t["status"] != "보유중"]

        if holding:
            st.markdown(f"<div style='font-size:14px; font-weight:700; margin:16px 0 8px;'>📌 보유 중 ({len(holding)}건)</div>", unsafe_allow_html=True)

            for trade in holding:
                # 현재가 조회
                curr = None
                ticker_ks = trade["code"] + ".KS" if trade["code"] else None
                if ticker_ks:
                    try:
                        import yfinance as yf
                        hist = yf.Ticker(ticker_ks).history(period="1d")
                        if not hist.empty:
                            curr = float(hist["Close"].iloc[-1])
                    except:
                        pass

                buy = trade["buy_price"]
                qty = trade["qty"]
                target = trade["target"]
                stop = trade["stop"]
                total_cost = buy * qty

                if curr:
                    pnl = (curr - buy) * qty
                    pnl_pct = (curr - buy) / buy * 100
                    to_target = (target - curr) / curr * 100 if target else 0
                    to_stop = (curr - stop) / curr * 100 if stop else 0
                    pnl_color = "#22c55e" if pnl >= 0 else "#ef4444"
                    pnl_arrow = "▲" if pnl >= 0 else "▼"

                    # 목표가/손절가 도달 여부
                    if curr >= target and target > 0:
                        status_msg = "🎯 목표가 도달! 매도 고려"
                        status_color = "#22c55e"
                        status_bg = "#22c55e15"
                    elif curr <= stop and stop > 0:
                        status_msg = "🛑 손절가 도달! 즉시 매도 권고"
                        status_color = "#ef4444"
                        status_bg = "#ef444415"
                    elif to_target <= 2:
                        status_msg = f"⚡ 목표가까지 {to_target:.1f}% 남음"
                        status_color = "#f59e0b"
                        status_bg = "#f59e0b15"
                    else:
                        status_msg = f"📊 목표 +{to_target:.1f}% / 손절 -{to_stop:.1f}% 여유"
                        status_color = "#6b7280"
                        status_bg = "#13161f"
                else:
                    pnl = 0
                    pnl_pct = 0
                    pnl_color = "#6b7280"
                    pnl_arrow = "-"
                    status_msg = "현재가 조회 실패"
                    status_color = "#6b7280"
                    status_bg = "#13161f"
                    to_target = (target - buy) / buy * 100 if target else 0
                    to_stop = (buy - stop) / buy * 100 if stop else 0

                from ui_components import SURFACE_2, LINE, DIM, TEXT, CANDLE_UP, CANDLE_DOWN, ACCENT
                st.markdown(f"""
                <div style='background:#13161f; border:0.5px solid #1e2330; border-radius:14px; padding:16px; margin-bottom:12px;'>
                    <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;'>
                        <div>
                            <span style='font-size:16px; font-weight:700; color:#e2e8f0;'>{trade["name"]}</span>
                            <span style='font-size:11px; color:#6b7280; margin-left:8px;'>{trade["code"]} · {trade["buy_date"]}</span>
                        </div>
                        <div style='background:{status_bg}; border:0.5px solid {status_color}40; border-radius:20px; padding:4px 12px; font-size:11px; color:{status_color}; font-weight:600;'>{status_msg}</div>
                    </div>

                    <div style='display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin-bottom:12px;'>
                        <div style='background:#0f1117; border-radius:8px; padding:10px; text-align:center;'>
                            <div style='font-size:10px; color:#6b7280; margin-bottom:2px;'>매수가</div>
                            <div style='font-size:13px; font-weight:600; font-family:JetBrains Mono;'>{buy:,}원</div>
                        </div>
                        <div style='background:#0f1117; border-radius:8px; padding:10px; text-align:center;'>
                            <div style='font-size:10px; color:#6b7280; margin-bottom:2px;'>현재가</div>
                            <div style='font-size:13px; font-weight:600; font-family:JetBrains Mono; color:{pnl_color};'>{f"{int(curr):,}원" if curr else "조회중"}</div>
                        </div>
                        <div style='background:#0f1117; border-radius:8px; padding:10px; text-align:center;'>
                            <div style='font-size:10px; color:#6b7280; margin-bottom:2px;'>목표가</div>
                            <div style='font-size:13px; font-weight:600; font-family:JetBrains Mono; color:#22c55e;'>{target:,}원</div>
                        </div>
                        <div style='background:#0f1117; border-radius:8px; padding:10px; text-align:center;'>
                            <div style='font-size:10px; color:#6b7280; margin-bottom:2px;'>손절가</div>
                            <div style='font-size:13px; font-weight:600; font-family:JetBrains Mono; color:#ef4444;'>{stop:,}원</div>
                        </div>
                    </div>

                    <div style='display:flex; justify-content:space-between; align-items:center; padding:10px 14px; background:#0f1117; border-radius:8px; margin-bottom:10px;'>
                        <span style='font-size:12px; color:#6b7280;'>{qty}주 · 투입 {total_cost/10000:,.0f}만원</span>
                        <span style='font-size:15px; font-weight:700; color:{pnl_color}; font-family:JetBrains Mono;'>{pnl_arrow} {abs(pnl):,.0f}원 ({pnl_pct:+.2f}%)</span>
                    </div>

                    {f'<div style="font-size:11px; color:#6b7280; margin-bottom:8px;">📝 {trade["memo"]}</div>' if trade["memo"] else ""}
                </div>
                """, unsafe_allow_html=True)

                # 매도 처리
                sc1, sc2, sc3 = st.columns([2, 1, 1])
                with sc1:
                    sell_price = st.number_input(
                        "매도가 입력",
                        value=int(curr) if curr else buy,
                        step=100,
                        key=f"sell_{trade['id']}"
                    )
                with sc2:
                    st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
                    if st.button("💰 매도 완료", key=f"sell_btn_{trade['id']}", use_container_width=True):
                        import datetime as dt_module
                        for t in st.session_state["daytrading"]:
                            if t["id"] == trade["id"]:
                                t["status"] = "매도완료"
                                t["sell_price"] = sell_price
                                t["sell_date"] = dt_module.datetime.now().strftime("%Y-%m-%d %H:%M")
                                final_pnl = (sell_price - buy) * qty
                                t["final_pnl"] = final_pnl
                                break
                        st.rerun()
                with sc3:
                    st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
                    if st.button("🗑 삭제", key=f"del_{trade['id']}", use_container_width=True):
                        st.session_state["daytrading"] = [t for t in st.session_state["daytrading"] if t["id"] != trade["id"]]
                        st.rerun()

        # 종료된 거래 기록
        if closed:
            with st.expander(f"📋 종료된 거래 ({len(closed)}건)", expanded=False):
                total_pnl = sum(t.get("final_pnl", 0) for t in closed)
                wins = [t for t in closed if t.get("final_pnl", 0) > 0]
                pnl_color = "#22c55e" if total_pnl >= 0 else "#ef4444"
                st.markdown(f"""
                <div style='display:flex; gap:16px; margin-bottom:12px;'>
                    <div style='background:#13161f; border-radius:8px; padding:10px 16px;'>
                        <div style='font-size:10px; color:#6b7280;'>총 손익</div>
                        <div style='font-size:16px; font-weight:700; color:{pnl_color};'>{total_pnl:+,.0f}원</div>
                    </div>
                    <div style='background:#13161f; border-radius:8px; padding:10px 16px;'>
                        <div style='font-size:10px; color:#6b7280;'>승률</div>
                        <div style='font-size:16px; font-weight:700;'>{len(wins)}/{len(closed)} ({len(wins)/len(closed)*100:.0f}%)</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                for t in closed:
                    pnl = t.get("final_pnl", 0)
                    pnl_color = "#22c55e" if pnl >= 0 else "#ef4444"
                    pnl_pct = (t["sell_price"] - t["buy_price"]) / t["buy_price"] * 100 if t.get("sell_price") else 0
                    st.markdown(f"""
                    <div style='background:#13161f; border:0.5px solid #1e2330; border-radius:10px; padding:12px 16px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;'>
                        <div>
                            <span style='font-size:14px; font-weight:600;'>{t["name"]}</span>
                            <span style='font-size:11px; color:#6b7280; margin-left:8px;'>{t["buy_date"]} → {t.get("sell_date","")}</span>
                            <div style='font-size:11px; color:#6b7280; margin-top:2px;'>매수 {t["buy_price"]:,}원 → 매도 {t.get("sell_price",0):,}원 ({t["qty"]}주)</div>
                        </div>
                        <div style='text-align:right;'>
                            <div style='font-size:15px; font-weight:700; color:{pnl_color};'>{pnl:+,.0f}원</div>
                            <div style='font-size:12px; color:{pnl_color};'>{pnl_pct:+.2f}%</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
    else:
        st.info("저장된 단타 거래가 없어요. 위에서 거래를 추가해보세요!")

    def render_portfolio():
        pass
