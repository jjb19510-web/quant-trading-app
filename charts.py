import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ui_components import (
    ACCENT, RED, GREEN, CANDLE_UP, CANDLE_DOWN,
    DIM, TEXT, SURFACE_1, SURFACE_2, SURFACE_3, LINE, BG,
    style_fig
)


def make_candlestick_fig(close_p, open_p, high_p, low_p, volume=None,
                          has_rsi=False, rsi_data=None, rsi_threshold=40,
                          extra_traces=None, buy_idx=None, sell_idx=None, chart_col=None):

    rows = 1
    row_heights = [1.0]

    if volume is not None and has_rsi:
        rows = 3
        row_heights = [0.6, 0.2, 0.2]
    elif volume is not None:
        rows = 2
        row_heights = [0.7, 0.3]
    elif has_rsi:
        rows = 2
        row_heights = [0.7, 0.3]

    fig = make_subplots(
        rows=rows, cols=1,
        shared_xaxes=True,
        row_heights=row_heights,
        vertical_spacing=0.02
    )

    fig.add_trace(go.Candlestick(
        x=close_p.index,
        open=open_p, high=high_p, low=low_p, close=close_p,
        name="캔들",
        increasing=dict(line=dict(color=CANDLE_UP, width=1), fillcolor=CANDLE_UP),
        decreasing=dict(line=dict(color=CANDLE_DOWN, width=1), fillcolor=CANDLE_DOWN),
        whiskerwidth=0.3,
    ), row=1, col=1)

    if extra_traces:
        for trace in extra_traces:
            fig.add_trace(trace, row=1, col=1)

    if buy_idx is not None and len(buy_idx) > 0:
        close_df = close_p.to_frame() if isinstance(close_p, pd.Series) else close_p
        fig.add_trace(go.Scatter(
            x=buy_idx,
            y=close_df.loc[buy_idx].iloc[:, 0] * 0.98,
            mode="markers", name="매수▲",
            marker=dict(symbol="triangle-up", size=10, color="#00ffff"),
            hovertemplate="%{x}<br>매수<extra></extra>"
        ), row=1, col=1)

    if sell_idx is not None and len(sell_idx) > 0:
        close_df = close_p.to_frame() if isinstance(close_p, pd.Series) else close_p
        fig.add_trace(go.Scatter(
            x=sell_idx,
            y=close_df.loc[sell_idx].iloc[:, 0] * 1.02,
            mode="markers", name="매도▼",
            marker=dict(symbol="triangle-down", size=10, color="#ffff00"),
            hovertemplate="%{x}<br>매도<extra></extra>"
        ), row=1, col=1)

    if volume is not None:
        colors = [CANDLE_UP if c >= o else CANDLE_DOWN
                  for c, o in zip(close_p, open_p)]
        fig.add_trace(go.Bar(
            x=close_p.index, y=volume,
            name="거래량",
            marker=dict(color=colors, opacity=0.7),
            showlegend=False
        ), row=2, col=1)

    if has_rsi and rsi_data is not None:
        rsi_row = 3 if volume is not None else 2
        fig.add_trace(go.Scatter(
            x=rsi_data.index, y=rsi_data,
            name="RSI", line=dict(color=ACCENT, width=1.5)
        ), row=rsi_row, col=1)
        fig.add_hline(y=rsi_threshold, line_dash="dash", line_color=CANDLE_UP, opacity=0.5, row=rsi_row, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color=CANDLE_DOWN, opacity=0.5, row=rsi_row, col=1)

    fig.update_layout(
        height=400 + (rows * 100),
        margin=dict(l=0, r=60, t=8, b=28),
        paper_bgcolor=BG, plot_bgcolor=BG,
        font=dict(family="Inter, sans-serif", color=TEXT, size=11),
        showlegend=True,
        hovermode="x unified",
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)",
                    font=dict(size=10), orientation="h",
                    yanchor="bottom", y=1.02, xanchor="left", x=0),
        xaxis=dict(rangeslider=dict(visible=False)),
    )

    for i in range(1, rows + 1):
        fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.03)",
                         linecolor=LINE, zeroline=False,
                         tickfont=dict(color=DIM, size=10), row=i, col=1)
        fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.03)",
                         linecolor=LINE, zeroline=False,
                         tickfont=dict(color=DIM, size=10), side="right", row=i, col=1)

    return fig


def make_return_chart(portfolio_equal, portfolio_strategy, strategy_name):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=portfolio_equal.index, y=((portfolio_equal - 1) * 100),
        name="균등 포트폴리오",
        line=dict(color=CANDLE_DOWN, width=1.5),
        hovertemplate="%{x}<br>수익률: %{y:.2f}%<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=portfolio_strategy.index, y=((portfolio_strategy - 1) * 100),
        name="전략 포트폴리오",
        line=dict(color=CANDLE_UP, width=2),
        hovertemplate="%{x}<br>수익률: %{y:.2f}%<extra></extra>"
    ))
    fig.add_hline(y=0, line=dict(color=DIM, width=1, dash="dot"), opacity=0.4)
    return style_fig(fig, 350)


def make_drawdown_chart(portfolio_strategy):
    peak = portfolio_strategy.cummax()
    drawdown = (portfolio_strategy - peak) / peak * 100
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=drawdown.index, y=drawdown.values,
        fill="tozeroy", line=dict(color=CANDLE_DOWN, width=1.5),
        fillcolor="rgba(59,130,246,0.15)", name="Drawdown",
        hovertemplate="%{x}<br>낙폭: %{y:.2f}%<extra></extra>"
    ))
    fig.update_layout(
        height=280, margin=dict(l=0, r=60, t=8, b=28),
        paper_bgcolor=BG, plot_bgcolor=BG,
        font=dict(family="Inter, sans-serif", color=TEXT, size=11),
        showlegend=False, hovermode="x unified"
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.03)",
                     linecolor=LINE, zeroline=False, tickfont=dict(color=DIM, size=10))
    fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.03)",
                     linecolor=LINE, zeroline=False, tickfont=dict(color=DIM, size=10), side="right")
    return fig


def make_heatmap_chart(weighted_return):
    monthly = weighted_return.resample("ME").apply(lambda x: (1 + x).prod() - 1) * 100
    monthly_df = monthly.to_frame("return")
    monthly_df["year"] = monthly_df.index.year
    monthly_df["month"] = monthly_df.index.month
    pivot = monthly_df.pivot(index="year", columns="month", values="return")

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],
        y=pivot.index.astype(str),
        colorscale=[[0, CANDLE_DOWN], [0.5, "#111318"], [1, CANDLE_UP]],
        zmid=0,
        text=[[f"{v:+.1f}" if not pd.isna(v) else "" for v in row] for row in pivot.values],
        texttemplate="%{text}",
        textfont=dict(family="JetBrains Mono", size=11, color="white"),
        colorbar=dict(thickness=6, len=0.8, tickfont=dict(color=DIM, size=9))
    ))
    fig.update_layout(
        height=280, margin=dict(l=0, r=60, t=8, b=28),
        paper_bgcolor=BG, plot_bgcolor=BG,
        font=dict(family="Inter, sans-serif", color=TEXT, size=11),
    )
    fig.update_xaxes(tickfont=dict(color=DIM, size=10))
    fig.update_yaxes(tickfont=dict(color=DIM, size=10), side="right")
    return fig


def make_pie_chart(active, tickers, DIM=DIM):
    cash_count = len(tickers) - len(active)

    if len(active) > 0:
        labels = active + (["현금"] if cash_count > 0 else [])
        values = [100 / len(tickers)] * len(active) + ([cash_count * 100 / len(tickers)] if cash_count > 0 else [])
        colors = [CANDLE_UP] * len(active) + ([DIM] if cash_count > 0 else [])
    else:
        labels = ["현금 (전량)"]
        values = [100]
        colors = [DIM]

    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        marker=dict(colors=colors, line=dict(color=BG, width=2)),
        textinfo="label+percent",
        textfont=dict(size=12, color=TEXT),
        hole=0.4
    ))
    fig.update_layout(
        height=320, margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor=SURFACE_1,
        font=dict(family="Inter, sans-serif", color=TEXT),
        showlegend=True,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10))
    )
    return fig