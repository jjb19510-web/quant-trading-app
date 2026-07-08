"""
Quantfolio Radar™ Engine (Phase 5-3A)
독립 모듈 — 기존 화면에는 아직 연결하지 않음.
급변 종목(갑자기 좋아지거나 나빠지는 종목)을 탐지하는 계산 엔진.
score_engine.py와 병행 사용 가능하나, health_engine.py 및 기존 UI는 전혀 수정하지 않는다.
데이터가 부족해도 에러 없이 Neutral로 안전 처리한다.
"""

import numpy as np
import pandas as pd


def _safe(value, default=0.0):
    try:
        if value is None or (isinstance(value, float) and (np.isnan(value) or np.isinf(value))):
            return default
        return float(value)
    except Exception:
        return default


def _calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _neutral_result(reason=""):
    return {
        "radar_score": 50.0,
        "status": "neutral",
        "label": "Radar Neutral",
        "reason": [],
        "summary": f"데이터 부족으로 중립 처리되었습니다. ({reason})" if reason else "데이터 부족으로 중립 처리되었습니다.",
    }


def calculate_radar_signal(close, high=None, low=None, volume=None, q_score=None):
    """
    Quantfolio Radar™ 계산.
    close: pandas Series (필수)
    high/low/volume: 선택 — 없으면 해당 신호만 생략
    q_score: score_engine.calculate_quantfolio_score()의 반환값 중 'score'(0~100), 선택
    데이터가 부족해도 에러 없이 Neutral 결과를 반환한다.
    """
    try:
        close = pd.Series(close).dropna()
        if len(close) < 21:
            return _neutral_result("종가 데이터 부족(21일 미만)")

        reasons = []

        # 1) 최근 5일 수익률 (단기 방향성)
        ret5 = _safe((close.iloc[-1] / close.iloc[-6] - 1) * 100) if len(close) > 6 else 0.0

        # 2) 최근 20일 추세 (중기 방향성)
        trend20 = _safe((close.iloc[-1] / close.iloc[-21] - 1) * 100)

        direction = 1 if (ret5 + trend20) >= 0 else -1

        # 3) RSI 변화 (모멘텀 급변)
        rsi_component = 0.0
        rsi_series = _calc_rsi(close)
        if len(rsi_series.dropna()) > 6:
            rsi_now = _safe(rsi_series.iloc[-1], 50.0)
            rsi_prev = _safe(rsi_series.iloc[-6], 50.0)
            rsi_delta = rsi_now - rsi_prev
            rsi_component = min(100, abs(rsi_delta) * 4)
            if abs(rsi_delta) >= 15:
                reasons.append("모멘텀 급변(RSI)")

        # 4) 거래량 급증
        volume_component = 0.0
        if volume is not None:
            volume = pd.Series(volume).dropna()
            if len(volume) >= 20:
                avg20 = volume.rolling(20).mean().iloc[-1]
                if avg20 and not np.isnan(avg20) and avg20 > 0:
                    vol_ratio = volume.iloc[-1] / avg20
                    volume_component = min(100, max(0, (vol_ratio - 1) * 60))
                    if vol_ratio >= 2:
                        reasons.append("거래량 급증")

        # 5) 변동성 증가
        volatility_component = 0.0
        if high is not None and low is not None:
            high = pd.Series(high).dropna()
            low = pd.Series(low).dropna()
            if len(high) >= 20 and len(low) >= 20 and len(close) >= 20:
                rng = (high - low) / close
                recent_vol = rng.rolling(5).mean().iloc[-1]
                base_vol = rng.rolling(20).mean().iloc[-1]
                if base_vol and not np.isnan(base_vol) and base_vol > 0:
                    vol_increase = recent_vol / base_vol
                    volatility_component = min(100, max(0, (vol_increase - 1) * 80))
                    if vol_increase >= 1.5:
                        reasons.append("변동성 확대")

        # 6) 추세 전환/강화 판정
        trend_component = min(100, abs(trend20) * 4)
        if (ret5 >= 3 and trend20 <= -3) or (ret5 <= -3 and trend20 >= 3):
            reasons.append("추세 전환")
        elif abs(trend20) >= 10:
            reasons.append("추세 강화")

        # 7) Quantfolio Score 반영 (선택)
        score_component = 0.0
        if q_score is not None:
            q_score = _safe(q_score, 50.0)
            if q_score >= 75:
                score_component = min(100, (q_score - 50))
                reasons.append("Q-Score 상승")
            elif q_score <= 30:
                score_component = min(100, (50 - q_score))
                reasons.append("Q-Score 하락")

        components = [volume_component, rsi_component, trend_component, volatility_component, score_component]
        weights = [0.25, 0.20, 0.20, 0.15, 0.20]
        radar_score = round(sum(c * w for c, w in zip(components, weights)), 1)
        radar_score = max(0.0, min(100.0, radar_score))

        if radar_score >= 75:
            status, label = ("buy", "Radar Strong Buy") if direction > 0 else ("risk", "Radar Risk")
        elif radar_score >= 50:
            status, label = ("buy", "Radar Buy") if direction > 0 else ("warning", "Radar Watch")
        else:
            status, label = "neutral", "Radar Neutral"

        if not reasons:
            reasons = ["뚜렷한 급변 신호 없음"]

        if radar_score >= 50:
            summary = "관심이 필요한 종목입니다." if direction > 0 else "주의가 필요한 종목입니다."
        else:
            summary = "특별한 변화가 감지되지 않았습니다."

        return {
            "radar_score": radar_score,
            "status": status,
            "label": label,
            "reason": reasons,
            "summary": summary,
        }
    except Exception:
        return _neutral_result("계산 실패 — 안전 모드")


if __name__ == "__main__":
    # 샘플 테스트 실행 — 기존 화면과 무관, 단독 실행 가능
    np.random.seed(1)
    sample_close = pd.Series(np.cumsum(np.random.randn(60)) + 100)
    sample_high = sample_close + np.random.rand(60) * 2
    sample_low = sample_close - np.random.rand(60) * 2
    sample_volume = pd.Series(np.random.randint(100000, 300000, 60)).astype(float)
    # 마지막 구간에 거래량/변동성 급증 시뮬레이션
    sample_volume.iloc[-1] = sample_volume.iloc[-20:-1].mean() * 3
    sample_high.iloc[-1] += 5
    sample_low.iloc[-1] -= 5

    result = calculate_radar_signal(sample_close, sample_high, sample_low, sample_volume, q_score=82)
    print(result)