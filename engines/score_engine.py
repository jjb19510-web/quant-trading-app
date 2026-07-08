"""
Quantfolio Score™ Engine (Phase 5-1A)
독립 모듈 — 기존 화면에는 아직 연결하지 않음.
기존 전략/API/AI 로직과 완전히 분리된 신규 계산 모듈.
데이터가 부족해도 에러 없이 Neutral(50점)로 안전 처리한다.
"""

import numpy as np
import pandas as pd

COMPONENT_NAMES_KR = {
    "trend": "추세", "momentum": "모멘텀", "volume": "거래량",
    "volatility": "변동성", "relative_strength": "상대강도",
    "fundamental": "밸류에이션", "risk": "리스크 관리",
}


def _safe(value, default=50.0):
    try:
        if value is None or (isinstance(value, float) and (np.isnan(value) or np.isinf(value))):
            return default
        return float(value)
    except Exception:
        return default


def _trend_score(close):
    try:
        if len(close) < 120:
            return 50.0
        price = close.iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        ma60 = close.rolling(60).mean().iloc[-1]
        ma120 = close.rolling(120).mean().iloc[-1]
        passed = sum([price > ma20, ma20 > ma60, ma60 > ma120])
        return {3: 95.0, 2: 78.0, 1: 55.0, 0: 25.0}[passed]
    except Exception:
        return 50.0


def _momentum_score(close):
    try:
        if len(close) < 21:
            return 50.0
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi_val = _safe((100 - (100 / (1 + rs))).iloc[-1])
        ret5 = _safe((close.iloc[-1] / close.iloc[-6] - 1) * 100) if len(close) > 6 else 0.0
        ret20 = _safe((close.iloc[-1] / close.iloc[-21] - 1) * 100) if len(close) > 21 else 0.0

        score = 50.0
        if 50 <= rsi_val <= 65:
            score += 20
        elif rsi_val > 70:
            score -= 15
        elif rsi_val < 30:
            score += 5

        score += max(min(ret5, 10), -10)
        score += max(min(ret20 * 0.5, 10), -10)
        return float(max(0, min(100, score)))
    except Exception:
        return 50.0


def _volume_score(volume):
    try:
        if volume is None or len(volume) < 20:
            return 50.0
        avg20 = volume.rolling(20).mean().iloc[-1]
        today = volume.iloc[-1]
        if not avg20 or np.isnan(avg20):
            return 50.0
        ratio = today / avg20
        if ratio >= 2:
            return 95.0
        elif ratio >= 1.3:
            return 80.0
        elif ratio >= 0.8:
            return 55.0
        else:
            return 35.0
    except Exception:
        return 50.0


def _volatility_score(close, high, low):
    try:
        if high is None or low is None or len(close) < 20:
            return 50.0
        daily_range_pct = ((high - low) / close).rolling(20).mean().iloc[-1] * 100
        if 1.5 <= daily_range_pct <= 4.0:
            return 85.0
        elif daily_range_pct < 1.5:
            return 45.0
        elif daily_range_pct <= 6.0:
            return 60.0
        else:
            return 30.0
    except Exception:
        return 50.0


def _relative_strength_score(close, market_close):
    try:
        if market_close is None or len(close) < 21 or len(market_close) < 21:
            return 50.0
        stock_ret = (close.iloc[-1] / close.iloc[-21] - 1) * 100
        market_ret = (market_close.iloc[-1] / market_close.iloc[-21] - 1) * 100
        score = 50 + (stock_ret - market_ret) * 2
        return float(max(0, min(100, score)))
    except Exception:
        return 50.0


def _fundamental_score(fundamentals):
    if not fundamentals:
        return 50.0
    try:
        score = 50.0
        per = fundamentals.get("per")
        pbr = fundamentals.get("pbr")
        roe = fundamentals.get("roe")
        if per is not None and 0 < per <= 15:
            score += 10
        elif per is not None and per > 30:
            score -= 10
        if pbr is not None and 0 < pbr <= 1.5:
            score += 10
        elif pbr is not None and pbr > 3:
            score -= 10
        if roe is not None and roe >= 10:
            score += 15
        elif roe is not None and roe < 0:
            score -= 15
        return float(max(0, min(100, score)))
    except Exception:
        return 50.0


def _risk_score(close):
    """리스크는 낮을수록 좋음 → 반환값이 높을수록 안전(=risk_adjusted 점수 높음)"""
    try:
        if len(close) < 60:
            return 50.0
        cummax = close.cummax()
        mdd = ((close / cummax - 1) * 100).min()
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi_val = _safe((100 - (100 / (1 + rs))).iloc[-1])

        score = 70.0
        if mdd < -30:
            score -= 25
        elif mdd < -15:
            score -= 10
        if rsi_val > 75:
            score -= 15
        return float(max(0, min(100, score)))
    except Exception:
        return 50.0


def _grade_status(score):
    if score >= 90:
        return "S", "strong_buy", "Strong Buy"
    elif score >= 80:
        return "A", "buy", "Buy"
    elif score >= 65:
        return "B", "buy", "Neutral+"
    elif score >= 50:
        return "C", "neutral", "Neutral"
    elif score >= 35:
        return "D", "warning", "Warning"
    else:
        return "F", "risk", "Risk"


def _build_summary(components):
    strong = [k for k, v in components.items() if v >= 75]
    weak = [k for k, v in components.items() if v <= 35]
    parts = []
    if strong:
        parts.append(f"{'·'.join(COMPONENT_NAMES_KR[k] for k in strong)}은(는) 강합니다")
    if weak:
        parts.append(f"{'·'.join(COMPONENT_NAMES_KR[k] for k in weak)}은(는) 약합니다")
    return (", ".join(parts) + ".") if parts else "전반적으로 중립적인 지표입니다."


def _neutral_result(reason=""):
    return {
        "score": 50.0,
        "grade": "C",
        "status": "neutral",
        "label": "Neutral",
        "components": {k: 50.0 for k in COMPONENT_NAMES_KR},
        "summary": f"데이터 부족으로 중립 처리되었습니다. ({reason})" if reason else "데이터 부족으로 중립 처리되었습니다.",
    }


def calculate_quantfolio_score(close, high=None, low=None, volume=None, market_close=None, fundamentals=None):
    """
    Quantfolio Score™ 계산.
    close: pandas Series (필수)
    high/low/volume/market_close/fundamentals: 선택 — 없으면 해당 항목만 Neutral(50) 처리
    데이터가 부족해도 에러 없이 Neutral 결과를 반환한다.
    """
    try:
        close = pd.Series(close).dropna()
        if len(close) == 0:
            return _neutral_result("종가 데이터 없음")

        components = {
            "trend": round(_trend_score(close), 1),
            "momentum": round(_momentum_score(close), 1),
            "volume": round(_volume_score(volume), 1),
            "volatility": round(_volatility_score(close, high, low), 1),
            "relative_strength": round(_relative_strength_score(close, market_close), 1),
            "fundamental": round(_fundamental_score(fundamentals), 1),
            "risk": round(_risk_score(close), 1),
        }

        total = (
            components["trend"] * 0.20
            + components["momentum"] * 0.20
            + components["volume"] * 0.15
            + components["volatility"] * 0.10
            + components["relative_strength"] * 0.15
            + components["fundamental"] * 0.10
            + components["risk"] * 0.10
        )
        total = round(max(0, min(100, total)), 1)
        grade, status, label = _grade_status(total)

        return {
            "score": total,
            "grade": grade,
            "status": status,
            "label": label,
            "components": components,
            "summary": _build_summary(components),
        }
    except Exception:
        return _neutral_result("계산 실패 — 안전 모드")


if __name__ == "__main__":
    # 샘플 테스트 실행 — 기존 화면과 무관, 단독 실행 가능
    sample_close = pd.Series(np.cumsum(np.random.randn(150)) + 100)
    sample_high = sample_close + 1
    sample_low = sample_close - 1
    sample_volume = pd.Series(np.random.randint(100000, 500000, 150))

    result = calculate_quantfolio_score(sample_close, sample_high, sample_low, sample_volume)
    print(result)