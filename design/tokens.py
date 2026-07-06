"""
Quantfolio Design Tokens (Phase 1-1)
모든 화면/컴포넌트는 여기 정의된 토큰만 참조한다.
색상을 직접 하드코딩하지 않는다.
"""

BG = "#080a0f"
SURFACE_1 = "#0f1117"
SURFACE_2 = "#13161f"
SURFACE_3 = "#1a1f2e"
LINE = "#1e2330"
TEXT = "#e2e8f0"
DIM = "#9ca3af"

UP = "#ef4444"
DOWN = "#3b82f6"
ACCENT = "#3b82f6"
AI = "#6366f1"
SUCCESS = "#34d399"
WARNING = "#f59e0b"
RISK = "#dc2626"

RED = UP
GREEN = SUCCESS
CANDLE_UP = UP
CANDLE_DOWN = DOWN

STATUS_COLORS = {
    "strong_buy": UP,
    "buy": "#f87171",
    "neutral": DIM,
    "warning": WARNING,
    "risk": RISK,
}
STATUS_LABELS = {
    "strong_buy": "Strong Buy",
    "buy": "Buy",
    "neutral": "Neutral",
    "warning": "Warning",
    "risk": "Risk",
}

FONT_KR = "'Pretendard', sans-serif"
FONT_EN = "'Inter', sans-serif"
FONT_MONO = "'JetBrains Mono', monospace"

FONT_IMPORT_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Inter:wght@400;500;600&"
    "family=JetBrains+Mono:wght@400;600&display=swap"
)

RADIUS_SM = "8px"
RADIUS_MD = "12px"
RADIUS_LG = "16px"

SHADOW_CARD = "0 4px 24px rgba(0,0,0,0.4)"
SHADOW_HOVER = "0 6px 16px rgba(59,130,246,0.12)"

SPACE_XS = "8px"
SPACE_SM = "12px"
SPACE_MD = "16px"
SPACE_LG = "24px"
SPACE_XL = "32px"

DURATION_FAST = "0.15s"
DURATION_BASE = "0.2s"
DURATION_SLOW = "0.4s"
EASING = "cubic-bezier(0.4, 0, 0.2, 1)"

GLASS_BG = "rgba(19, 22, 31, 0.6)"
GLASS_BLUR = "blur(12px)"
GLASS_BORDER = "1px solid rgba(255,255,255,0.06)"