"""
Quantfolio Intelligence Engine (Phase 5-4A)
score_engine / radar_engine / health_engine의 결과(dict)를 입력받아
최종 투자 판단(BUY/WATCH/AVOID/REDUCE/RISK_ALERT)으로 통합하는 Master Engine.

주의: 이 파일은 다른 엔진의 계산 로직을 전혀 건드리지 않는다.
각 엔진이 이미 계산해서 반환한 dict를 "읽기만" 해서 종합 판단을 내린다.
이번 단계는 화면에 연결하지 않는다.
"""


def _safe_get(info, key, default=None):
    if not isinstance(info, dict):
        return default
    value = info.get(key, default)
    return value if value is not None else default


def _neutral_result(reason=""):
    return {
        "decision": "WATCH",
        "confidence": 50,
        "priority": "MEDIUM",
        "status": "neutral",
        "summary": f"정보가 부족해 관망으로 판단했습니다. ({reason})" if reason else "정보가 부족해 관망으로 판단했습니다.",
        "actions": ["추가 정보 확인 후 판단 권장"],
        "reasons": [],
    }


def generate_intelligence_decision(score_info=None, radar_info=None, health_info=None, context=None):
    """
    score_info: score_engine.calculate_quantfolio_score()의 반환 dict (선택)
    radar_info: radar_engine.calculate_radar_signal()의 반환 dict (선택)
    health_info: health_engine.calculate_portfolio_health()의 반환 dict (선택)
    context: 예약 파라미터 (현재 버전 미사용, 추후 시장 상황 등 추가 컨텍스트용)

    셋 다 없으면 안전하게 WATCH/Neutral 반환.
    """
    try:
        if score_info is None and radar_info is None and health_info is None:
            return _neutral_result("입력값 없음")

        score_status = _safe_get(score_info, "status", "neutral")
        radar_status = _safe_get(radar_info, "status", "neutral")
        health_status = _safe_get(health_info, "status", None)

        reasons = []
        actions = []
        confidence = 50

        score_buy = score_status in ("strong_buy", "buy")
        score_bad = score_status in ("warning", "risk")
        radar_buy = radar_status in ("buy",)
        radar_risk = radar_status == "risk"
        radar_watch = radar_status in ("neutral", "warning")

        if score_info is not None:
            reasons.append(f"Q-Score {score_status.replace('_', ' ').title()}")
        if radar_info is not None:
            reasons.append(f"Radar {radar_status.replace('_', ' ').title()}")

        # ── 판단 기준 ──
        if radar_risk:
            decision = "RISK_ALERT"
            priority = "HIGH"
            status = "risk"
            confidence = 30
            actions = ["즉시 리스크 점검", "포지션 축소 고려", "손절 기준 재확인"]
        elif score_bad:
            decision = "AVOID" if not score_info or _safe_get(score_info, "status") == "risk" else "REDUCE"
            priority = "HIGH" if decision == "AVOID" else "MEDIUM"
            status = "risk" if decision == "AVOID" else "warning"
            confidence = 35
            actions = ["신규 진입 보류", "보유 중이면 비중 축소 검토", "리스크 요인 재점검"]
        elif score_buy and radar_buy:
            decision = "BUY"
            priority = "HIGH"
            status = "buy"
            confidence = 80
            actions = ["분할매수 관점 유지", "거래량 둔화 시 관망", "손절 기준을 사전에 설정"]
        elif score_buy and radar_watch:
            decision = "WATCH"
            priority = "MEDIUM"
            status = "neutral"
            confidence = 60
            actions = ["관심종목 등록 후 관찰", "추가 신호 확인 후 진입 고려"]
        else:
            decision = "WATCH"
            priority = "MEDIUM"
            status = "neutral"
            confidence = 50
            actions = ["뚜렷한 신호 없음, 관망 권장"]

        # ── Portfolio Health 반영 (confidence 조정) ──
        if health_status in ("warning", "risk"):
            confidence = max(10, confidence - 15)
            reasons.append("Portfolio Health 주의 필요")
            actions.append("포트폴리오 전체 리스크 재점검 권장")
        elif health_status in ("buy", "strong_buy"):
            reasons.append("Portfolio Health 양호")

        confidence = int(max(0, min(100, confidence)))

        if decision == "BUY":
            summary = "Q-Score와 Radar가 모두 우호적입니다."
        elif decision == "RISK_ALERT":
            summary = "Radar에서 위험 신호가 감지되었습니다."
        elif decision in ("AVOID", "REDUCE"):
            summary = "Q-Score 기준 리스크 요인이 확인되었습니다."
        else:
            summary = "뚜렷한 우호/위험 신호가 없어 관망이 적절합니다."

        return {
            "decision": decision,
            "confidence": confidence,
            "priority": priority,
            "status": status,
            "summary": summary,
            "actions": actions,
            "reasons": reasons,
        }
    except Exception:
        return _neutral_result("계산 실패 — 안전 모드")


if __name__ == "__main__":
    # 샘플 테스트 실행 — 기존 화면과 무관, 단독 실행 가능
    sample_score = {"score": 87, "grade": "A", "status": "buy", "label": "Buy"}
    sample_radar = {"radar_score": 78, "status": "buy", "label": "Radar Buy"}
    sample_health = {"score": 82, "grade": "A-", "status": "buy"}

    print("[BUY 케이스]")
    print(generate_intelligence_decision(sample_score, sample_radar, sample_health))

    print("\n[입력값 전부 없음]")
    print(generate_intelligence_decision())

    print("\n[Radar Risk 케이스]")
    print(generate_intelligence_decision(sample_score, {"status": "risk"}, sample_health))