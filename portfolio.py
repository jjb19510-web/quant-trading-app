import streamlit as st
import pandas as pd
import yfinance as yf
import datetime as dt_module
import json
import requests as req
from ui_components import card, SURFACE_1, SURFACE_2, LINE, DIM, TEXT, CANDLE_UP, CANDLE_DOWN, ACCENT

GIST_FILENAME = "quantfolio_trades.json"


def get_gist_id(token, debug=False):
    try:
        headers = {"Authorization": f"token {token}"}
        res = req.get("https://api.github.com/gists", headers=headers, timeout=5)
        if res.status_code != 200:
            if debug:
                st.error(f"🔧 Gist 목록 조회 실패: {res.status_code} - {res.text[:300]}")
            return None
        for gist in res.json():
            if GIST_FILENAME in gist.get("files", {}):
                return gist["id"]
        # 없으면 새로 생성
        create_res = req.post(
            "https://api.github.com/gists",
            headers=headers,
            json={
                "description": "Quantfolio 단타 거래 기록",
                "public": False,
                "files": {GIST_FILENAME: {"content": "[]"}}
            },
            timeout=5
        )
        if create_res.status_code != 201:
            if debug:
                st.error(f"🔧 Gist 생성 실패: {create_res.status_code} - {create_res.text[:300]}")
            return None
        return create_res.json().get("id")
    except Exception as e:
        if debug:
            st.error(f"🔧 Gist 연결 오류: {e}")
        return None


def save_trades(trades, token):
    if not token:
        st.error("🔧 GITHUB_TOKEN이 비어있어요. Streamlit Secrets를 확인해주세요.")
        return False
    try:
        gist_id = get_gist_id(token, debug=True)
        if gist_id:
            headers = {"Authorization": f"token {token}"}
            res = req.patch(
                f"https://api.github.com/gists/{gist_id}",
                headers=headers,
                json={"files": {GIST_FILENAME: {"content": json.dumps(trades, ensure_ascii=False, indent=2)}}},
                timeout=5
            )
            if res.status_code != 200:
                st.error(f"🔧 Gist 저장 실패: {res.status_code} - {res.text[:300]}")
                return False
            return True
        else:
            st.error("🔧 Gist ID를 가져오지 못했어요.")
            return False
    except Exception as e:
        st.error(f"🔧 저장 중 오류: {e}")
        return False


def load_trades(token):
    if not token:
        return []
    try:
        gist_id = get_gist_id(token, debug=False)
        if gist_id:
            headers = {"Authorization": f"token {token}"}
            res = req.get(f"https://api.github.com/gists/{gist_id}", headers=headers, timeout=5)
            content = res.json()["files"][GIST_FILENAME]["content"]
            return json.loads(content)
    except:
        pass
    return []


def render_portfolio(KIS_AVAILABLE, get_kis_token, get_balance):

    GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")

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
                  <div style='background:#0f1117; border:0.5px solid #1e2330; border-radius:12px; padding:16px 20px;'>
                    <div style='font-size:11px; color:#9ca3af; margin-bottom:6px;'>💼 총 평가금액</div>
                    <div style='font-size:22px; font-weight:600; font-family:JetBrains Mono;'>{total_eval:,}원</div>
                  </div>
                  <div style='background:#0f1117; border:0.5px solid rgba(239,68,68,0.3); border-radius:12px; padding:16px 20px;'>
                    <div style='font-size:11px; color:#9ca3af; margin-bottom:6px;'>📈 평가손익</div>
                    <div style='font-size:22px; font-weight:600; font-family:JetBrains Mono; color:{profit_color};'>{profit_arrow} {total_profit:+,}원</div>
                  </div>
                  <div style='background:#0f1117; border:0.5px solid #1e2330; border-radius:12px; padding:16px 20px;'>
                    <div style='font-size:11px; color:#9ca3af; margin-bottom:6px;'>💰 예수금 (결제대기 포함)</div>
                    <div style='font-size:22px; font-weight:600; font-family:JetBrains Mono;'>{cash:,}원</div>
                  </div>
                  <div style='background:#0f1117; border:0.5px solid #1e2330; border-radius:12px; padding:16px 20px;'>
                    <div style='font-size:11px; color:#9ca3af; margin-bottom:6px;'>🏧 실제 출금가능 (D+2 결제 후)</div>
                    <div style='font-size:22px; font-weight:600; font-family:JetBrains Mono;'>{withdrawable:,}원</div>
                  </div>
                </div>
                <div style='font-size:11px; color:#6b7280; margin-bottom:20px;'>
                    💡 매수 체결 후 실제 대금 결제까지 2영업일(D+2)이 걸려요. 예수금은 결제 전 금액을 포함하므로, 실제 사용 가능한 금액은 '출금가능금액'을 참고하세요.
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
    # ⚡ 단타 거래 관리
    # ══════════════════════════════════════════
    st.markdown("<div style='margin-top:32px;'></div>", unsafe_allow_html=True)
    card("⚡ 단타 거래 관리", "매수 내역 저장 · 실시간 손익 모니터링 · AI 매도 전략")

    # 토큰 상태 표시 (디버그)
    if GITHUB_TOKEN:
        st.caption(f"🔑 GitHub Token 연결됨 ({GITHUB_TOKEN[:8]}...)")
    else:
        st.error("🔑 GITHUB_TOKEN이 설정되지 않았어요. Streamlit Secrets를 확인해주세요.")

    if "daytrading" not in st.session_state:
        with st.spinner("거래 기록 불러오는 중..."):
            st.session_state["daytrading"] = load_trades(GITHUB_TOKEN)

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
                import time
                new_trade = {
                    "id": int(time.time() * 1000),
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
                with st.spinner("저장 중..."):
                    success = save_trades(st.session_state["daytrading"], GITHUB_TOKEN)
                if success:
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
                curr = None
                if trade["code"]:
                    try:
                        from broker import get_access_token, get_current_price as kis_get_price
                        _token = get_access_token()
                        _price_data = kis_get_price(trade["code"], _token)
                        if _price_data:
                            curr = float(_price_data["current"])
                    except:
                        pass
                if curr is None and trade["code"]:
                    try:
                        hist = yf.Ticker(trade["code"] + ".KS").history(period="2d")
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

                now_time = dt_module.datetime.now().time()
                time_stop = dt_module.time(14, 30)
                stage1_price = int(buy * 1.03)
                stage2_price = int(buy * 1.05)
                stage3_price = int(target) if target else int(buy * 1.08)
                auto_stop = int(buy * 0.97)

                if curr:
                    if curr >= stage3_price:
                        rec_action = "🎯 3단계 전량 매도 추천"
                        rec_price = stage3_price
                        rec_color = "#22c55e"
                        rec_reason = f"목표가({stage3_price:,}원) 도달 — 전량 익절 타이밍"
                    elif curr >= stage2_price:
                        rec_action = "📈 2단계 부분 매도 추천"
                        rec_price = stage2_price
                        rec_color = "#22c55e"
                        rec_reason = f"+5% 달성 — 보유량 50% 매도 후 나머지 홀딩"
                    elif curr >= stage1_price:
                        rec_action = "💰 1단계 부분 매도 추천"
                        rec_price = stage1_price
                        rec_color = "#f59e0b"
                        rec_reason = f"+3% 달성 — 보유량 30% 매도로 수익 일부 확보"
                    elif curr <= auto_stop:
                        rec_action = "🛑 즉시 손절 권고"
                        rec_price = int(curr)
                        rec_color = "#ef4444"
                        rec_reason = "-3% 이탈 — 추가 손실 방지를 위해 즉시 매도"
                    elif now_time >= time_stop:
                        rec_action = "⏰ 시간 손절 권고"
                        rec_price = int(curr)
                        rec_color = "#ef4444"
                        rec_reason = "14:30 경과 — 목표가 미달성 시 당일 청산 원칙"
                    else:
                        to_s1 = (stage1_price - curr) / curr * 100
                        rec_action = f"⏳ 홀딩 — 1단계까지 +{to_s1:.1f}% 남음"
                        rec_price = stage1_price
                        rec_color = "#6b7280"
                        rec_reason = f"1단계({stage1_price:,}원) → 2단계({stage2_price:,}원) → 목표({stage3_price:,}원) 순서로 분할 매도"
                else:
                    rec_action = "현재가 조회 필요"
                    rec_price = buy
                    rec_color = "#6b7280"
                    rec_reason = "현재가를 확인할 수 없어요"

                st.markdown(f"""
<div style='background:#0f1117; border:1px solid {rec_color}40; border-radius:10px; padding:14px 16px; margin-bottom:10px;'>
    <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;'>
        <span style='font-size:13px; font-weight:700; color:{rec_color};'>{rec_action}</span>
        <span style='font-size:14px; font-weight:700; font-family:JetBrains Mono; color:{rec_color};'>{rec_price:,}원</span>
    </div>
    <div style='font-size:11px; color:#6b7280; margin-bottom:10px;'>{rec_reason}</div>
    <div style='display:flex; gap:8px; font-size:11px; color:#6b7280; flex-wrap:wrap;'>
        <span>1단계 +3%: <b style='color:#22c55e;'>{stage1_price:,}원</b></span>
        <span>|</span>
        <span>2단계 +5%: <b style='color:#22c55e;'>{stage2_price:,}원</b></span>
        <span>|</span>
        <span>자동손절 -3%: <b style='color:#ef4444;'>{auto_stop:,}원</b></span>
        <span>|</span>
        <span>시간손절: <b style='color:#ef4444;'>14:30</b></span>
    </div>
</div>
                """, unsafe_allow_html=True)

                sc1, sc2, sc3 = st.columns([2, 1, 1])
                with sc1:
                    sell_price = st.number_input(
                        "매도가 입력 (AI 추천가 자동 입력)",
                        value=rec_price,
                        step=100,
                        key=f"sell_{trade['id']}"
                    )
                with sc2:
                    st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
                    if st.button("💰 매도 완료", key=f"sell_btn_{trade['id']}", use_container_width=True):
                        for t in st.session_state["daytrading"]:
                            if t["id"] == trade["id"]:
                                t["status"] = "매도완료"
                                t["sell_price"] = sell_price
                                t["sell_date"] = dt_module.datetime.now().strftime("%Y-%m-%d %H:%M")
                                t["final_pnl"] = (sell_price - buy) * qty
                                break
                        save_trades(st.session_state["daytrading"], GITHUB_TOKEN)
                        st.rerun()
                with sc3:
                    st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
                    if st.button("🗑 삭제", key=f"del_{trade['id']}", use_container_width=True):
                        st.session_state["daytrading"] = [t for t in st.session_state["daytrading"] if t["id"] != trade["id"]]
                        save_trades(st.session_state["daytrading"], GITHUB_TOKEN)
                        st.rerun()

        if closed:
            with st.expander(f"📋 종료된 거래 ({len(closed)}건)", expanded=False):
                total_pnl = sum(t.get("final_pnl", 0) for t in closed)
                wins = [t for t in closed if t.get("final_pnl", 0) > 0]
                pnl_color = "#22c55e" if total_pnl >= 0 else "#ef4444"
                avg_pnl_pct = sum(
                    (t["sell_price"] - t["buy_price"]) / t["buy_price"] * 100
                    for t in closed if t.get("sell_price")
                ) / len(closed)

                st.markdown(f"""
<div style='display:flex; gap:16px; margin-bottom:16px;'>
    <div style='background:#13161f; border-radius:8px; padding:10px 16px;'>
        <div style='font-size:10px; color:#6b7280;'>총 손익</div>
        <div style='font-size:16px; font-weight:700; color:{pnl_color};'>{total_pnl:+,.0f}원</div>
    </div>
    <div style='background:#13161f; border-radius:8px; padding:10px 16px;'>
        <div style='font-size:10px; color:#6b7280;'>승률</div>
        <div style='font-size:16px; font-weight:700;'>{len(wins)}/{len(closed)} ({len(wins)/len(closed)*100:.0f}%)</div>
    </div>
    <div style='background:#13161f; border-radius:8px; padding:10px 16px;'>
        <div style='font-size:10px; color:#6b7280;'>평균 수익률</div>
        <div style='font-size:16px; font-weight:700; color:{"#22c55e" if avg_pnl_pct >= 0 else "#ef4444"};'>{avg_pnl_pct:+.2f}%</div>
    </div>
</div>
                """, unsafe_allow_html=True)

                closed_rows = []
                for t in sorted(closed, key=lambda x: x.get("sell_date", ""), reverse=True):
                    pnl = t.get("final_pnl", 0)
                    pp = (t["sell_price"] - t["buy_price"]) / t["buy_price"] * 100 if t.get("sell_price") else 0
                    closed_rows.append({
                        "종목": t["name"],
                        "매수일": t["buy_date"][:10],
                        "매도일": t.get("sell_date", "")[:10],
                        "매수가": f"{t['buy_price']:,}원",
                        "매도가": f"{t.get('sell_price',0):,}원",
                        "수량": f"{t['qty']}주",
                        "손익": f"{pnl:+,.0f}원",
                        "수익률": f"{pp:+.2f}%",
                        "결과": "✅ 승" if pnl >= 0 else "❌ 패"
                    })

                df_closed = pd.DataFrame(closed_rows)
                st.dataframe(df_closed, use_container_width=True, hide_index=True)

                st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
                for t in sorted(closed, key=lambda x: x.get("sell_date", ""), reverse=True):
                    dcol1, dcol2 = st.columns([5, 1])
                    with dcol1:
                        pnl = t.get("final_pnl", 0)
                        c = "#22c55e" if pnl >= 0 else "#ef4444"
                        st.markdown(f"<div style='font-size:12px; color:#9ca3af; padding-top:6px;'>{t['name']} ({t['buy_date'][:10]} → {t.get('sell_date','')[:10]}) · <span style='color:{c};'>{pnl:+,.0f}원</span></div>", unsafe_allow_html=True)
                    with dcol2:
                        if st.button("🗑 삭제", key=f"del_closed_{t['id']}", use_container_width=True):
                            st.session_state["daytrading"] = [x for x in st.session_state["daytrading"] if x["id"] != t["id"]]
                            save_trades(st.session_state["daytrading"], GITHUB_TOKEN)
                            st.rerun()

                st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
                if st.button("🗑 종료된 거래 전체 삭제", key="clear_closed"):
                    st.session_state["daytrading"] = [t for t in st.session_state["daytrading"] if t["status"] == "보유중"]
                    save_trades(st.session_state["daytrading"], GITHUB_TOKEN)
                    st.rerun()

    # ── 단타 복기 통계 ──
    st.markdown("<div style='margin-top:32px;'></div>", unsafe_allow_html=True)
    card("📊 단타 복기 통계", "누적 매매 성과 분석")

    all_closed = [t for t in st.session_state.get("daytrading", []) if t.get("status") == "매도완료"]

    if all_closed:
        total = len(all_closed)
        wins = [t for t in all_closed if t.get("final_pnl", 0) > 0]
        losses = [t for t in all_closed if t.get("final_pnl", 0) <= 0]
        win_rate = len(wins) / total * 100
        total_pnl = sum(t.get("final_pnl", 0) for t in all_closed)
        avg_win = sum(t.get("final_pnl", 0) for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t.get("final_pnl", 0) for t in losses) / len(losses) if losses else 0
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0

        # 최대 연속 손실 계산
        max_streak = 0
        curr_streak = 0
        for t in sorted(all_closed, key=lambda x: x.get("sell_date", "")):
            if t.get("final_pnl", 0) <= 0:
                curr_streak += 1
                max_streak = max(max_streak, curr_streak)
            else:
                curr_streak = 0

        # 핵심 지표 카드
        c1, c2, c3, c4, c5 = st.columns(5)
        metrics = [
            (c1, "총 매매", f"{total}건", None),
            (c2, "승률", f"{win_rate:.0f}%", win_rate >= 50),
            (c3, "손익비", f"{profit_factor:.2f}", profit_factor >= 1),
            (c4, "총 손익", f"{total_pnl:+,.0f}원", total_pnl >= 0),
            (c5, "최대연속손실", f"{max_streak}연패", max_streak <= 2),
        ]
        for col, label, value, is_good in metrics:
            color = "#22c55e" if is_good else "#ef4444" if is_good is not None else TEXT
            with col:
                st.markdown(f"<div style='background:{SURFACE_2}; border-radius:10px; padding:12px 16px; text-align:center; margin-bottom:12px;'><div style='font-size:11px; color:{DIM}; margin-bottom:4px;'>{label}</div><div style='font-size:18px; font-weight:700; color:{color};'>{value}</div></div>", unsafe_allow_html=True)

        # 복기 인사이트
        insights = []
        if win_rate < 40:
            insights.append(("🔴", "승률이 40% 미만이에요. 진입 기준을 더 엄격하게 적용해보세요."))
        if profit_factor < 1:
            insights.append(("🔴", "손익비가 1 미만이에요. 수익은 작고 손실이 크다는 의미예요. 익절을 더 길게, 손절을 더 빠르게 하세요."))
        if max_streak >= 3:
            insights.append(("⚠️", f"최대 {max_streak}연패를 기록했어요. 연속 손실 시 하루 매매를 중단하는 규칙을 만들어보세요."))
        if win_rate >= 60 and profit_factor >= 1.5:
            insights.append(("✅", "훌륭한 매매 패턴이에요! 지금 전략을 유지하세요."))
        if not insights:
            insights.append(("💡", "아직 데이터가 부족해요. 매매를 계속 기록하면 더 정확한 분석이 가능해요."))

        for emoji, msg in insights:
            border_c = "#ef4444" if emoji == "🔴" else "#f59e0b" if emoji == "⚠️" else "#22c55e"
            st.markdown(f"<div style='background:{SURFACE_1}; border-left:4px solid {border_c}; padding:10px 16px; border-radius:0 8px 8px 0; margin-bottom:8px; font-size:13px; color:{TEXT};'>{emoji} {msg}</div>", unsafe_allow_html=True)

        # 상세 매매 분석
        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"""
            <div style='background:{SURFACE_2}; border-radius:12px; padding:16px; margin-bottom:12px;'>
                <div style='font-size:12px; color:{DIM}; margin-bottom:10px; font-weight:600;'>📈 수익 거래 분석</div>
                <div style='display:flex; justify-content:space-between; margin-bottom:6px;'>
                    <span style='font-size:12px; color:{DIM};'>총 승리</span>
                    <span style='font-size:12px; font-weight:600; color:#22c55e;'>{len(wins)}건</span>
                </div>
                <div style='display:flex; justify-content:space-between; margin-bottom:6px;'>
                    <span style='font-size:12px; color:{DIM};'>평균 수익</span>
                    <span style='font-size:12px; font-weight:600; color:#22c55e;'>+{avg_win:,.0f}원</span>
                </div>
                <div style='display:flex; justify-content:space-between;'>
                    <span style='font-size:12px; color:{DIM};'>최대 단일 수익</span>
                    <span style='font-size:12px; font-weight:600; color:#22c55e;'>+{max((t.get("final_pnl",0) for t in wins), default=0):,.0f}원</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col_b:
            st.markdown(f"""
            <div style='background:{SURFACE_2}; border-radius:12px; padding:16px; margin-bottom:12px;'>
                <div style='font-size:12px; color:{DIM}; margin-bottom:10px; font-weight:600;'>📉 손실 거래 분석</div>
                <div style='display:flex; justify-content:space-between; margin-bottom:6px;'>
                    <span style='font-size:12px; color:{DIM};'>총 패배</span>
                    <span style='font-size:12px; font-weight:600; color:#ef4444;'>{len(losses)}건</span>
                </div>
                <div style='display:flex; justify-content:space-between; margin-bottom:6px;'>
                    <span style='font-size:12px; color:{DIM};'>평균 손실</span>
                    <span style='font-size:12px; font-weight:600; color:#ef4444;'>{avg_loss:,.0f}원</span>
                </div>
                <div style='display:flex; justify-content:space-between;'>
                    <span style='font-size:12px; color:{DIM};'>최대 단일 손실</span>
                    <span style='font-size:12px; font-weight:600; color:#ef4444;'>{min((t.get("final_pnl",0) for t in losses), default=0):,.0f}원</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # 월별 손익 차트 (X축 문자열로 고정)
        if len(all_closed) >= 2:
            import plotly.graph_objects as go
            monthly = {}
            for t in all_closed:
                raw_date = t.get("sell_date", "")
                if raw_date and len(raw_date) >= 7:
                    month = raw_date[:7]  # "2026-06" 형식
                    monthly[month] = monthly.get(month, 0) + t.get("final_pnl", 0)
            if monthly:
                months = sorted(monthly.keys())
                values = [monthly[m] for m in months]
                colors = ["#22c55e" if v >= 0 else "#ef4444" for v in values]
                text_labels = [f"+{v/10000:.1f}만" if v >= 0 else f"{v/10000:.1f}만" for v in values]

                fig = go.Figure(go.Bar(
                    x=months,
                    y=values,
                    marker_color=colors,
                    text=text_labels,
                    textposition="outside",
                    textfont=dict(color="#e2e8f0", size=11)
                ))
                fig.update_layout(
                    title=dict(text="📅 월별 손익", font=dict(size=13, color="#e2e8f0")),
                    plot_bgcolor="#0f1117",
                    paper_bgcolor="#0f1117",
                    font=dict(color="#e2e8f0"),
                    height=280,
                    margin=dict(l=20, r=20, t=50, b=40),
                    yaxis=dict(gridcolor="#1e2330", tickformat=",d", title="손익 (원)"),
                    xaxis=dict(
                        gridcolor="#1e2330",
                        type="category",  # 문자열로 강제 처리
                        tickangle=0
                    ),
                )
                st.plotly_chart(fig, use_container_width=True)

        # 누적 손익 추이
        if len(all_closed) >= 2:
            sorted_trades = sorted(all_closed, key=lambda x: x.get("sell_date", ""))
            cumulative = []
            running = 0
            labels = []
            for t in sorted_trades:
                running += t.get("final_pnl", 0)
                cumulative.append(running)
                labels.append(f"{t['name']} ({t.get('sell_date','')[:10]})")

            line_color = "#22c55e" if running >= 0 else "#ef4444"
            fig2 = go.Figure(go.Scatter(
                x=list(range(1, len(cumulative)+1)),
                y=cumulative,
                mode="lines+markers",
                line=dict(color=line_color, width=2),
                marker=dict(size=6, color=line_color),
                hovertext=labels,
                hoverinfo="text+y",
                fill="tozeroy",
                fillcolor=f"{line_color}20"
            ))
            fig2.add_hline(y=0, line_dash="dash", line_color="#6b7280", line_width=1)
            fig2.update_layout(
                title=dict(text="📈 누적 손익 추이", font=dict(size=13, color="#e2e8f0")),
                plot_bgcolor="#0f1117",
                paper_bgcolor="#0f1117",
                font=dict(color="#e2e8f0"),
                height=280,
                margin=dict(l=20, r=20, t=50, b=40),
                yaxis=dict(gridcolor="#1e2330", tickformat=",d", title="누적 손익 (원)"),
                xaxis=dict(gridcolor="#1e2330", title="매매 횟수"),
            )
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("아직 완료된 단타 거래가 없어요. 매매를 기록하고 복기해보세요!")