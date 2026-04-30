import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

# 종목 리스트
tickers = ["005930.KS", "000660.KS", "373220.KS"]

# 데이터 가져오기
df = yf.download(tickers, start="2023-01-01", end="2025-01-01")["Close"]

# RSI 계산 함수
def calculate_rsi(data, period=14):
    delta = data.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# 각 종목 RSI 계산
rsi = df.apply(calculate_rsi)

# RSI 40 이하인 종목만 매수 신호
signal = (rsi < 40).astype(int)

# 매수 종목 수 (0이면 현금)
signal_count = signal.sum(axis=1)
signal_count = signal_count.replace(0, 1)  # 0으로 나누기 방지

# 수익률 계산
returns = df.pct_change()

# 전략 수익률 (신호 있는 종목만 균등 배분)
weighted_return = (returns * signal.shift(1)).sum(axis=1) / signal_count.shift(1)

# 균등 포트폴리오 수익률
equal_return = returns.mean(axis=1)

# 누적 수익률
portfolio_rsi = (1 + weighted_return).cumprod()
portfolio_equal = (1 + equal_return).cumprod()

# 그래프
plt.figure(figsize=(12, 6))
plt.plot(portfolio_equal, label="Equal Portfolio", alpha=0.7)
plt.plot(portfolio_rsi, label="RSI Portfolio")
plt.title("Portfolio - RSI Strategy")
plt.xlabel("Date")
plt.ylabel("Cumulative Return")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()

print(f"균등 포트폴리오 수익률: {(portfolio_equal.iloc[-1] - 1) * 100:.2f}%")
print(f"RSI 포트폴리오 수익률: {(portfolio_rsi.iloc[-1] - 1) * 100:.2f}%")