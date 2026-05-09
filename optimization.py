import pandas as pd
import numpy as np
from strategies import run_strategy, calculate_sharpe, calculate_mdd


def optimize_parameters(df, strategy, metric="수익률"):
    """파라미터 최적화 - 최적값 탐색"""
    results = []

    if strategy == "RSI 전략 (RSI)":
        for val in range(10, 71, 5):
            ret, wr, _, _, _, _, _, _, _ = run_strategy(df, strategy, val, 20, 60, 20)
            sharpe = calculate_sharpe(wr.dropna())
            mdd = calculate_mdd((1 + wr).cumprod())
            results.append({"RSI 기준값": val, "수익률 (%)": round(ret, 2),
                          "샤프지수": round(sharpe, 2), "MDD (%)": round(mdd, 2)})

    elif strategy == "이동평균선 전략 (Moving Average)":
        for short in range(5, 31, 5):
            for long in range(30, 121, 10):
                if short >= long:
                    continue
                ret, wr, _, _, _, _, _, _, _ = run_strategy(df, strategy, 40, short, long, 20)
                sharpe = calculate_sharpe(wr.dropna())
                mdd = calculate_mdd((1 + wr).cumprod())
                results.append({"단기 MA": short, "장기 MA": long, "수익률 (%)": round(ret, 2),
                              "샤프지수": round(sharpe, 2), "MDD (%)": round(mdd, 2)})

    elif strategy == "볼린저 밴드 전략 (Bollinger Bands)":
        for val in range(5, 61, 5):
            ret, wr, _, _, _, _, _, _, _ = run_strategy(df, strategy, 40, 20, 60, val)
            sharpe = calculate_sharpe(wr.dropna())
            mdd = calculate_mdd((1 + wr).cumprod())
            results.append({"BB 기간": val, "수익률 (%)": round(ret, 2),
                          "샤프지수": round(sharpe, 2), "MDD (%)": round(mdd, 2)})

    else:  # Combined
        for rsi_val in range(10, 71, 10):
            for short in range(5, 31, 5):
                for long in range(30, 121, 10):
                    if short >= long:
                        continue
                    ret, wr, _, _, _, _, _, _, _ = run_strategy(df, strategy, rsi_val, short, long, 20)
                    sharpe = calculate_sharpe(wr.dropna())
                    mdd = calculate_mdd((1 + wr).cumprod())
                    results.append({"RSI": rsi_val, "단기 MA": short, "장기 MA": long,
                                  "수익률 (%)": round(ret, 2), "샤프지수": round(sharpe, 2),
                                  "MDD (%)": round(mdd, 2)})

    return pd.DataFrame(results)


def walk_forward_test(df, strategy, train_months=24, test_months=6):
    """워크포워드 테스트"""
    results = []
    dates = df.index

    train_days = train_months * 21
    test_days = test_months * 21

    i = train_days
    while i + test_days <= len(dates):
        # 학습 구간
        train_df = df.iloc[i - train_days:i]
        # 검증 구간
        test_df = df.iloc[i:i + test_days]

        if len(train_df) < 60 or len(test_df) < 10:
            i += test_days
            continue

        # 학습 구간에서 최적 파라미터 찾기
        opt_df = optimize_parameters(train_df, strategy)
        if opt_df.empty:
            i += test_days
            continue

        best = opt_df.loc[opt_df["수익률 (%)"].idxmax()]

        # 최적 파라미터로 검증 구간 테스트
        if strategy == "RSI 전략 (RSI)":
            ret, _, _, _, _, _, _, _, _ = run_strategy(
                test_df, strategy, int(best["RSI 기준값"]), 20, 60, 20)
            params = f"RSI={int(best['RSI 기준값'])}"
        elif strategy == "이동평균선 전략 (Moving Average)":
            ret, _, _, _, _, _, _, _, _ = run_strategy(
                test_df, strategy, 40, int(best["단기 MA"]), int(best["장기 MA"]), 20)
            params = f"MA{int(best['단기 MA'])}/{int(best['장기 MA'])}"
        elif strategy == "볼린저 밴드 전략 (Bollinger Bands)":
            ret, _, _, _, _, _, _, _, _ = run_strategy(
                test_df, strategy, 40, 20, 60, int(best["BB 기간"]))
            params = f"BB={int(best['BB 기간'])}"
        else:
            ret, _, _, _, _, _, _, _, _ = run_strategy(
                test_df, strategy, int(best["RSI"]), int(best["단기 MA"]), int(best["장기 MA"]), 20)
            params = f"RSI={int(best['RSI'])}, MA{int(best['단기 MA'])}/{int(best['장기 MA'])}"

        results.append({
            "학습 구간": f"{dates[i-train_days].strftime('%Y-%m')} ~ {dates[i-1].strftime('%Y-%m')}",
            "검증 구간": f"{dates[i].strftime('%Y-%m')} ~ {dates[i+test_days-1].strftime('%Y-%m')}",
            "최적 파라미터": params,
            "검증 수익률 (%)": round(ret, 2)
        })

        i += test_days

    return pd.DataFrame(results)