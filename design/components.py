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
        f"<div class='qf-ai-card-head'><span class='qf-ai-card-title'>🤖 {title}</span>{badge_html}</div>"
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