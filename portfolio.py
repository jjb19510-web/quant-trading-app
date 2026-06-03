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
