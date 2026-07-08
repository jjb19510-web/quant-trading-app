"""
Quantfolio Portfolio Health™ Engine (Phase 5-2A)
독립 모듈 — 기존 화면(portfolio.py 등)에는 아직 연결하지 않음.
기존 계산 로직(broker.py, data_utils.py, score_engine.py)과 완전히 분리된 신규 모듈.
데이터가 부족해도 에러 없이 Neutral(50점)로 안전 처리한다.

holdings 입력 구조 (list of dict), 각 항목은 아래 키를 사용:
{
    "name": "삼성전자",          # 선택
    "sector": "반도체",          # 선택
    "value": 5000000,           # 필수 — 평가금액(원)
    "returns": pandas Series,   # 선택 — 일별 수익률 (변동성 계산용)
    "mdd": -12.5,               # 선택 — 최대낙폭(%), 없으면 Neutral 처리
}
없는 필드는 전부 안전하게 Neutral 처리되며 에러를 던지지 않는다.
"""

import numpy as np

COMPONENT_NAMES_KR = {
    "diversification": "분산도",
    "concentration": "집중도",
    "cash_ratio": "현금비중",
    "volatility": "변동성",
    "drawdown": "손실위험",
}

# 컴포넌트 가중치 (초기 버전, 추후 데이터 검증 후 조정 가능)
WEIGHTS = {
    "diversification": 0.25,
    "concentration": 0.25,
    "cash_ratio": 0.15,
    "volatility": 0.20,
    "drawdown": 0.15,
}


def _safe(value, default=50.0):
    try:
        if value is None or (isinstance(value, float) and (np.isnan(value) or np.isinf(value))):
            return default
        return float(value)
    except Exception:
        return default


def _get_weights(holdings, total_value):
    weights = []
    for h in holdings:
        try:
            v = float(h.get("value", 0) or 0)
            weights.append(v / total_value if total_value > 0 else 0)
        except Exception:
            weights.append(0.0)
    return weights


def _diversification_score(holdings, weights):
    try:
        n = len(holdings)
        if n == 0:
            return 20.0
        base = {1: 20.0, 2: 35.0, 3: 45.0}.get(n, None)
        if base is None:
            base = 65.0 if n <= 6 else (85.0 if n <= 10 else 95.0)

        # 균등 분산 여부 보정 (HHI 기반)
        hhi = sum(w ** 2 for w in weights) if weights else 1.0
        ideal_hhi = 1.0 / n if n > 0 else 1.0
        evenness_penalty = max(0.0, (hhi - ideal_hhi) * 100)
        score = base - evenness_penalty
        return float(max(0, min(100, score)))
    except Exception:
        return 50.0


def _concentration_score(weights):
    try:
        if not weights:
            return 50.0
        top3 = sum(sorted(weights, reverse=True)[:3]) * 100
        if top3 <= 30:
            return 90.0
        elif top3 <= 50:
            return 70.0
        elif top3 <= 70:
            return 50.0
        elif top3 <= 85:
            return 30.0
        else:
            return 15.0
    except Exception:
        return 50.0


def _cash_ratio_score(cash, total_value):
    try:
        if total_value <= 0:
            return 50.0
        ratio = cash / total_value * 100
        if 5 <= ratio <= 20:
            return 90.0
        elif ratio < 5:
            return 60.0 if ratio >= 2 else 40.0
        elif ratio <= 40:
            return 65.0
        else:
            return 40.0
    except Exception:
        return 50.0


def _volatility_score(holdings, weights):
    try:
        vols = []
        w_used = []
        for h, w in zip(holdings, weights):
            returns = h.get("returns")
            if returns is None or len(returns) < 5:
                continue
            vol = float(returns.std()) * (252 ** 0.5) * 100  # 연환산 변동성(%)
            vols.append(vol)
            w_used.append(w)
        if not vols:
            return 50.0
        weighted_vol = sum(v * w for v, w in zip(vols, w_used)) / (sum(w_used) or 1)
        if weighted_vol <= 20:
            return 85.0
        elif weighted_vol <= 35:
            return 65.0
        elif weighted_vol <= 50:
            return 45.0
        else:
            return 25.0
    except Exception:
        return 50.0


def _drawdown_score(holdings, weights):
    try:
        mdds = []
        w_used = []
        for h, w in zip(holdings, weights):
            mdd = h.get("mdd")
            if mdd is None:
                continue
            mdds.append(float(mdd))
            w_used.append(w)
        if not mdds:
            return 50.0
        weighted_mdd = sum(m * w for m, w in zip(mdds, w_used)) / (sum(w_used) or 1)
        if weighted_mdd >= -10:
            return 90.0
        elif weighted_mdd >= -20:
            return 70.0
        elif weighted_mdd >= -35:
            return 50.0
        elif weighted_mdd >= -50:
            return 30.0
        else:
            return 15.0
    except Exception:
        return 50.0


def _grade_status(score):
    if score >= 90:
        return "S", "strong_buy"
    elif score >= 80:
        return "A", "buy"
    elif score >= 65:
        return "B", "buy"
    elif score >= 50:
        return "C", "neutral"
    elif score >= 35:
        return "D", "warning"
    else:
        return "F", "risk"


def _build_recommendations(components, cash_ratio_pct):
    tips = []
    if components["concentration"] <= 50:
        tips.append("상위 종목 비중이 높습니다. 분산을 고려해보세요.")
    if components["diversification"] <= 45:
        tips.append("보유 종목 수가 적어 분산 효과가 제한적입니다.")
    if cash_ratio_pct is not None and cash_ratio_pct < 5:
        tips.append("현금 비중이 낮습니다. 일부 현금 확보를 고려해보세요.")
    elif cash_ratio_pct is not None and cash_ratio_pct > 40:
        tips.append("현금 비중이 높아 기회비용이 발생할 수 있습니다.")
    if components["volatility"] <= 45:
        tips.append("포트폴리오 변동성이 높습니다. 리스크 관리가 필요합니다.")
    if components["drawdown"] <= 50:
        tips.append("최근 손실폭이 커서 리스크 관리가 필요합니다.")
    if not tips:
        tips.append("특별한 조정이 필요하지 않은 안정적인 포트폴리오입니다.")
    return tips


def _build_summary(components):
    strong = [k for k, v in components.items() if v >= 75]
    weak = [k for k, v in components.items() if v <= 40]
    parts = []
    if strong:
        parts.append(f"{'·'.join(COMPONENT_NAMES_KR[k] for k in strong)}은(는) 우수합니다")
    if weak:
        parts.append(f"{'·'.join(COMPONENT_NAMES_KR[k] for k in weak)}은(는) 개선이 필요합니다")
    return (", ".join(parts) + ".") if parts else "전반적으로 건강한 포트폴리오입니다."


def _neutral_result(reason=""):
    components = {k: 50.0 for k in COMPONENT_NAMES_KR}
    return {
        "score": 50.0,
        "grade": "C",
        "status": "neutral",
        "components": components,
        "recommendations": ["데이터가 부족해 정확한 진단이 어렵습니다."],
        "summary": f"데이터 부족으로 중립 처리되었습니다. ({reason})" if reason else "데이터 부족으로 중립 처리되었습니다.",
    }


def calculate_portfolio_health(holdings, cash=0, benchmark=None):
    """
    Portfolio Health™ 계산.
    holdings: list of dict (모듈 상단 docstring 참고), 비어있어도 에러 없이 Neutral 반환
    cash: 현금 평가액(원)
    benchmark: 예약 파라미터 (현재 버전 미사용, 추후 상대 비교용)
    """
    try:
        if not holdings:
            return _neutral_result("보유 종목 없음")

        holdings_value = 0.0
        for h in holdings:
            try:
                holdings_value += float(h.get("value", 0) or 0)
            except Exception:
                pass

        total_value = holdings_value + float(cash or 0)
        if total_value <= 0:
            return _neutral_result("평가금액 0 이하")

        weights = _get_weights(holdings, total_value)
        cash_ratio_pct = (float(cash or 0) / total_value * 100) if total_value > 0 else None

        components = {
            "diversification": round(_diversification_score(holdings, weights), 1),
            "concentration": round(_concentration_score(weights), 1),
            "cash_ratio": round(_cash_ratio_score(float(cash or 0), total_value), 1),
            "volatility": round(_volatility_score(holdings, weights), 1),
            "drawdown": round(_drawdown_score(holdings, weights), 1),
        }

        total = sum(components[k] * WEIGHTS[k] for k in WEIGHTS)
        total = round(max(0, min(100, total)), 1)
        grade, status = _grade_status(total)

        return {
            "score": total,
            "grade": grade,
            "status": status,
            "components": components,
            "recommendations": _build_recommendations(components, cash_ratio_pct),
            "summary": _build_summary(components),
        }
    except Exception:
        return _neutral_result("계산 실패 — 안전 모드")


if __name__ == "__main__":
    # 샘플 테스트 실행 — 기존 화면과 무관, 단독 실행 가능
    sample_holdings = [
        {"name": "삼성전자", "sector": "반도체", "value": 5000000, "mdd": -15.0},
        {"name": "SK하이닉스", "sector": "반도체", "value": 3000000, "mdd": -22.0},
        {"name": "NAVER", "sector": "IT", "value": 2000000, "mdd": -10.0},
    ]
    result = calculate_portfolio_health(sample_holdings, cash=1000000)
    print(result)