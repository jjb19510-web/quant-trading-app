import pandas as pd
import numpy as np
import yfinance as yf


def calculate_rsi(data, period=14):
    delta = data.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calculate_bb(data, period=20):
    ma = data.rolling(period).mean()
    std = data.rolling(period).std()
    return ma + (std * 2), ma - (std * 2), ma


def calculate_mdd(portfolio):
    peak = portfolio.cummax()
    return ((portfolio - peak) / peak).min() * 100


def calculate_sharpe(returns):
    return (returns.mean() / returns.std()) * (252 ** 0.5)


def calculate_cagr(portfolio, days):
    return ((portfolio.iloc[-1] / portfolio.iloc[0]) ** (365 / days) - 1) * 100


def run_strategy(df, strategy, rsi_threshold, ma_short, ma_long, bb_period, fee_pct=0.0):
    # ── [예외 처리] 비어 있는 데이터가 인자로 들어왔을 때 크래시 방어 ──
    if df.empty:
        import pandas as pd
        return 0, pd.Series(dtype=float), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    rsi = df.apply(calculate_rsi)
    ma_s = df.rolling(ma_short).mean()
    ma_l = df.rolling(ma_long).mean()
    bb_upper, bb_lower, bb_mid = calculate_bb(df, bb_period)

    if strategy == "RSI 전략 (RSI)":
        signal = (rsi < rsi_threshold).astype(int)
    elif strategy == "이동평균선 전략 (Moving Average)":
        signal = (ma_s > ma_l).astype(int)
    elif strategy == "볼린저 밴드 전략 (Bollinger Bands)":
        signal = (df < bb_lower).astype(int)
    else:
        signal = ((rsi < rsi_threshold) & (ma_s > ma_l)).astype(int)

    signal_count = signal.sum(axis=1).replace(0, 1)
    returns = df.pct_change()
    weighted_return = (returns * signal.shift(1)).sum(axis=1) / signal_count.shift(1)
    # 첫날 주가 변동률 공백(NaN)이 복리 연산 전체를 nan으로 오염시키는 현상 원천 방지
    portfolio = (1 + weighted_return.fillna(0)).cumprod()
    total_return = (portfolio.iloc[-1] - 1) * 100
    return total_return, weighted_return, signal, rsi, ma_s, ma_l, bb_upper, bb_lower, bb_mid