"""
Quantfolio Design System — Theme Builder (Phase 1-2)
tokens.py의 값을 참조해서 CSS 문자열을 조립하는 모듈.

주의: 이 파일은 CSS 문자열을 생성만 한다.
st.markdown()으로 실제 화면에 주입하는 연결 작업은 다음 단계에서 진행.
아직 ui_components.py, quant_app.py 어디에서도 import하지 않는다.
"""

from design import tokens as t

FONT_IMPORTS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600&display=swap');
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css');
"""

FONT_STACK_KR = "'Pretendard', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
FONT_STACK_MONO = "'JetBrains Mono', 'Pretendard', monospace"


def build_root_variables() -> str:
    return f"""
    :root {{
      --qf-bg: {t.BG};
      --qf-surface-1: {t.SURFACE_1};
      --qf-surface-2: {t.SURFACE_2};
      --qf-surface-3: {t.SURFACE_3};
      --qf-line: {t.LINE};
      --qf-text: {t.TEXT};
      --qf-dim: {t.DIM};

      --qf-up: {t.UP};
      --qf-down: {t.DOWN};
      --qf-accent: {t.ACCENT};
      --qf-ai: {t.AI};
      --qf-success: {t.SUCCESS};
      --qf-warning: {t.WARNING};
      --qf-risk: {t.RISK};

      --qf-radius-sm: {t.RADIUS_SM};
      --qf-radius-md: {t.RADIUS_MD};
      --qf-radius-lg: {t.RADIUS_LG};

      --qf-shadow-card: {t.SHADOW_CARD};
      --qf-shadow-hover: {t.SHADOW_HOVER};

      --qf-space-xs: {t.SPACE_XS};
      --qf-space-sm: {t.SPACE_SM};
      --qf-space-md: {t.SPACE_MD};
      --qf-space-lg: {t.SPACE_LG};
      --qf-space-xl: {t.SPACE_XL};

      --qf-duration-fast: {t.DURATION_FAST};
      --qf-duration-base: {t.DURATION_BASE};
      --qf-duration-slow: {t.DURATION_SLOW};
      --qf-easing: {t.EASING};

      --qf-glass-bg: {t.GLASS_BG};
      --qf-glass-blur: {t.GLASS_BLUR};
      --qf-glass-border: {t.GLASS_BORDER};

      --qf-font-kr: {FONT_STACK_KR};
      --qf-font-mono: {FONT_STACK_MONO};
    }}
    """


def build_base_styles() -> str:
    return """
    .stApp { background: var(--qf-bg); color: var(--qf-text); font-family: var(--qf-font-kr); }
    h1, h2, h3, h4 { letter-spacing: -0.02em; font-family: var(--qf-font-kr); }
    .qf-mono { font-family: var(--qf-font-mono); }
    """


def build_animation_keyframes() -> str:
    return """
    @keyframes qf-fade-in {
      from { opacity: 0; transform: translateY(4px); }
      to { opacity: 1; transform: translateY(0); }
    }
    @keyframes qf-pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }
    @keyframes qf-skeleton {
      0% { background-position: -200px 0; }
      100% { background-position: calc(200px + 100%) 0; }
    }
    .qf-fade-in { animation: qf-fade-in var(--qf-duration-base) var(--qf-easing); }
    .qf-pulse { animation: qf-pulse 1.6s ease-in-out infinite; }
    .qf-skeleton {
      background: linear-gradient(90deg, var(--qf-surface-1) 25%, var(--qf-surface-2) 50%, var(--qf-surface-1) 75%);
      background-size: 200px 100%;
      animation: qf-skeleton 1.4s ease-in-out infinite;
    }
    """


def build_theme_css() -> str:
    return (
        f"<style>{FONT_IMPORTS}"
        f"{build_root_variables()}"
        f"{build_base_styles()}"
        f"{build_animation_keyframes()}"
        f"</style>"
    )


def get_global_css() -> str:
    return build_theme_css()