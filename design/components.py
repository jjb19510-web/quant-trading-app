"""
Quantfolio Design System — Components (Phase 1-3)
순수 HTML 생성 함수만 정의한다. st.markdown() 호출이나
기존 화면(quant_app.py, dashboard.py, portfolio.py, report.py 등) 연결은 하지 않는다.

제공 함수:
- status_badge(status)
- kpi_card(title, value, delta=None, status=None, icon=None)
- hero_card(title, value, subtitle=None, status=None)
- ai_insight_card(title, content, confidence=None, status=None)
- get_component_css()
"""

from design import tokens as t

# ══════════════════════════════════
# SVG Icon System (Phase 4-1)
# 이모지를 대체하는 인라인 SVG 아이콘 모음.
# 새 아이콘이 필요하면 여기 딕셔너리에만 추가하면 전체 화면에 반영됨.
# ══════════════════════════════════
QF_ICONS = {
    "trend-up": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline></svg>',
    "trend-down": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"></polyline><polyline points="17 18 23 18 23 12"></polyline></svg>',
    "chart": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>',
    "briefcase": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path></svg>',
    "brain": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2Z"></path><path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2Z"></path></svg>',
    "alert-triangle": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>',
    "search": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>',
    "settings": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z"></path></svg>',
    "microscope": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 18h8"></path><path d="M3 22h18"></path><path d="M14 22a7 7 0 1 0 0-14h-1"></path><path d="M9 14h2"></path><path d="M9 12a2 2 0 0 1-2-2V6h6v4a2 2 0 0 1-2 2Z"></path><path d="M12 6V3a1 1 0 0 0-1-1H9a1 1 0 0 0-1 1v3"></path></svg>',
    "clipboard": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path></svg>',
    "newspaper": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"></path><path d="M18 14h-8"></path><path d="M15 18h-5"></path><path d="M10 6h8v4h-8V6Z"></path></svg>',
}

# ── Icon Token: 기능명이 아닌 의미(Semantic) 중심 이름으로 아이콘 매핑 ──
ICON_TOKENS = {
    "market": "chart",
    "portfolio": "briefcase",
    "report": "clipboard",
    "ai": "brain",
    "strategy": "settings",
    "analysis": "microscope",
    "trade": "trend-up",
    "profit": "trend-up",
    "loss": "trend-down",
    "news": "newspaper",
    "warning": "alert-triangle",
    "search": "search",
    "settings": "settings",
}

# ── Size / Color Token ──
ICON_SIZE_TOKENS = {"sm": 14, "md": 16, "lg": 20}
ICON_COLOR_TOKENS = {
    "primary": t.ACCENT,
    "secondary": t.DIM,
    "success": t.SUCCESS,
    "warning": t.WARNING,
    "danger": t.RISK,
}


def qf_icon(key, size="md", color=None):
    """
    key: ICON_TOKENS의 의미(semantic) 이름(예: "ai", "market") 또는 QF_ICONS의 원본 키(예: "brain") 둘 다 허용.
    매핑에 전혀 없으면 key(이모지 등)를 그대로 감싸서 반환 — 점진적 전환 호환.
    size: "sm"/"md"/"lg" 토큰 또는 정수(px) 직접 지정 가능.
    color: "primary"/"secondary"/"success"/"warning"/"danger" 토큰, hex 코드, 또는 None(기본 currentColor 유지).
    """
    icon_key = ICON_TOKENS.get(key, key)
    svg = QF_ICONS.get(icon_key)
    if not svg:
        return f"<span class='qf-icon'>{key}</span>"
    px = ICON_SIZE_TOKENS.get(size, size if isinstance(size, int) else 16)
    sized = svg.replace('width="16" height="16"', f'width="{px}" height="{px}"')
    if color:
        hex_color = ICON_COLOR_TOKENS.get(color, color)
        sized = sized.replace('stroke="currentColor"', f'stroke="{hex_color}"')
    return f"<span class='qf-icon' style='display:inline-flex; vertical-align:middle;'>{sized}</span>"


def status_badge(status: str) -> str:
    label = t.STATUS_LABELS.get(status, t.STATUS_LABELS["neutral"])
    css_class = status.replace("_", "-")
    return f"<span class='qf-status-badge {css_class}'>{label}</span>"


def kpi_card(title: str, value: str, delta: str = None, status: str = None, icon: str = None) -> str:
    icon_html = f"<span class='qf-kpi-card-icon'>{icon}</span>" if icon else ""
    delta_html = f"<div class='qf-kpi-card-delta'>{delta}</div>" if delta else ""
    badge_html = status_badge(status) if status else ""
    return (
        f"<div class='qf-kpi-card qf-fade-in'>"
        f"<div class='qf-kpi-card-head'>{icon_html}<span class='qf-kpi-card-title'>{title}</span>{badge_html}</div>"
        f"<div class='qf-kpi-card-value'>{value}</div>"
        f"{delta_html}"
        f"</div>"
    )


def hero_card(title: str, value: str, subtitle: str = None, status: str = None) -> str:
    subtitle_html = f"<div class='qf-hero-card-subtitle'>{subtitle}</div>" if subtitle else ""
    badge_html = status_badge(status) if status else ""
    return (
        f"<div class='qf-hero-card qf-fade-in'>"
        f"<div class='qf-hero-card-head'><span class='qf-hero-card-title'>{title}</span>{badge_html}</div>"
        f"<div class='qf-hero-card-value'>{value}</div>"
        f"{subtitle_html}"
        f"</div>"
    )


def ai_insight_card(title: str, content: str, confidence: str = None, status: str = None) -> str:
    confidence_html = f"<span class='qf-ai-card-confidence'>AI Confidence {confidence}</span>" if confidence else ""
    badge_html = status_badge(status) if status else ""
    return (
        f"<div class='qf-ai-card qf-fade-in'>"
        f"<div class='qf-ai-card-head'><span class='qf-ai-card-title'>{qf_icon('brain', size=14)} {title}</span>{badge_html}</div>"
        f"<div class='qf-ai-card-content'>{content}</div>"
        f"{confidence_html}"
        f"</div>"
    )


def get_component_css() -> str:
    return f"""
    <style>
      .qf-status-badge {{
        display: inline-block;
        font-size: 11px;
        font-family: var(--qf-font-mono);
        padding: 2px 10px;
        border-radius: 20px;
        margin-left: 8px;
      }}
      .qf-status-badge.strong-buy {{
        color: var(--qf-up);
        background: rgba(239, 68, 68, 0.16);
        border: 1px solid rgba(239, 68, 68, 0.42);
        font-weight: 700;
      }}
      .qf-status-badge.buy {{
        color: #f87171;
        background: rgba(248, 113, 113, 0.10);
        border: 1px solid rgba(248, 113, 113, 0.28);
        font-weight: 600;
      }}
      .qf-status-badge.neutral {{
        color: var(--qf-dim);
        background: rgba(156, 163, 175, 0.10);
        border: 1px solid rgba(156, 163, 175, 0.28);
        font-weight: 600;
      }}
      .qf-status-badge.warning {{
        color: var(--qf-warning);
        background: rgba(245, 158, 11, 0.12);
        border: 1px solid rgba(245, 158, 11, 0.32);
        font-weight: 600;
      }}
      .qf-status-badge.risk {{
        color: var(--qf-risk);
        background: rgba(220, 38, 38, 0.16);
        border: 1px solid rgba(220, 38, 38, 0.42);
        font-weight: 700;
      }}

      .qf-kpi-card {{
        background: var(--qf-surface-1);
        border: 0.5px solid var(--qf-line);
        border-radius: var(--qf-radius-md);
        padding: var(--qf-space-md) var(--qf-space-lg);
        box-shadow: var(--qf-shadow-card);
        transition: all var(--qf-duration-base) var(--qf-easing);
      }}
      .qf-kpi-card:hover {{
        transform: translateY(-2px);
        box-shadow: var(--qf-shadow-hover);
        border-color: var(--qf-accent);
      }}
      .qf-kpi-card-head {{
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 11px;
        color: var(--qf-dim);
        text-transform: uppercase;
        letter-spacing: 0.07em;
        margin-bottom: 6px;
      }}
      .qf-kpi-card-value {{
        font-family: var(--qf-font-mono);
        font-size: 22px;
        font-weight: 600;
        color: var(--qf-text);
      }}
      .qf-kpi-card-delta {{
        font-family: var(--qf-font-mono);
        font-size: 11px;
        color: var(--qf-dim);
        margin-top: 4px;
      }}

      .qf-hero-card {{
        background: var(--qf-glass-bg);
        backdrop-filter: var(--qf-glass-blur);
        -webkit-backdrop-filter: var(--qf-glass-blur);
        border: var(--qf-glass-border);
        border-radius: var(--qf-radius-lg);
        padding: var(--qf-space-lg) var(--qf-space-xl);
        box-shadow: var(--qf-shadow-card);
      }}
      .qf-hero-card-head {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 8px;
      }}
      .qf-hero-card-title {{
        font-size: 13px;
        color: var(--qf-dim);
        text-transform: uppercase;
        letter-spacing: 0.07em;
      }}
      .qf-hero-card-value {{
        font-family: var(--qf-font-mono);
        font-size: 32px;
        font-weight: 600;
        color: var(--qf-text);
      }}
      .qf-hero-card-subtitle {{
        font-size: 12px;
        color: var(--qf-dim);
        margin-top: 4px;
      }}

      .qf-ai-card {{
        background: var(--qf-glass-bg);
        backdrop-filter: var(--qf-glass-blur);
        -webkit-backdrop-filter: var(--qf-glass-blur);
        border: 1px solid {t.AI}40;
        border-radius: var(--qf-radius-md);
        padding: var(--qf-space-md) var(--qf-space-lg);
      }}
      .qf-ai-card-head {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 10px;
      }}
      .qf-ai-card-title {{
        font-size: 13px;
        font-weight: 600;
        color: {t.AI};
      }}
      .qf-ai-card-content {{
        font-size: 13px;
        line-height: 1.8;
        color: var(--qf-text);
      }}
      .qf-ai-card-confidence {{
        display: inline-block;
        margin-top: 8px;
        font-family: var(--qf-font-mono);
        font-size: 10.5px;
        color: {t.AI};
      }}
    </style>
    """