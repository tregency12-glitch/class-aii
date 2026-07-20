import streamlit as st


def inject_global_css() -> None:
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600;700&family=Outfit:wght@300;400;500;600;700&display=swap');
            
            /* Global reset and dark theme core */
            html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
                font-family: 'Kanit', 'Outfit', sans-serif !important;
                background-color: #0A0D1A !important;
                color: #E2E8F0 !important;
            }

            .block-container { 
                padding-top: 1.5rem; 
                max-width: 1200px; 
            }

            /* Premium Header Section */
            .hero-header {
                background: linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(139, 92, 246, 0.03) 100%);
                backdrop-filter: blur(16px);
                border: 1px solid rgba(99, 102, 241, 0.15);
                border-radius: 24px;
                padding: 28px 36px;
                margin-bottom: 2.2rem;
                box-shadow: 0 10px 40px rgba(99, 102, 241, 0.05);
            }
            .hero-title { 
                font-family: 'Kanit', sans-serif;
                font-size: 2.25rem; 
                font-weight: 700; 
                background: linear-gradient(90deg, #FFFFFF 30%, #C7D2FE 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin: 0; 
                letter-spacing: 0.5px; 
            }
            .hero-sub { 
                color: #94A3B8; 
                font-size: 1.05rem; 
                margin-top: 8px; 
                font-weight: 300; 
            }

            /* Metric Cards with subtle glow and hover transitions */
            .metric-card {
                background: rgba(30, 41, 59, 0.25);
                backdrop-filter: blur(12px);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 20px; 
                padding: 24px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            .metric-card:hover {
                transform: translateY(-5px);
                border-color: rgba(99, 102, 241, 0.25);
                background: rgba(30, 41, 59, 0.35);
                box-shadow: 0 12px 40px rgba(99, 102, 241, 0.08);
            }
            .metric-label {
                font-size: 11px; 
                color: #64748B; 
                text-transform: uppercase;
                letter-spacing: 1.5px; 
                margin-bottom: 10px; 
                font-weight: 600;
            }
            .metric-value { 
                font-size: 1.4rem; 
                font-weight: 600; 
                color: #F8FAFC; 
                overflow: hidden; 
                text-overflow: ellipsis; 
                white-space: nowrap; 
            }
            .metric-value--live { 
                color: #F87171; 
                font-weight: 700; 
                text-shadow: 0 0 12px rgba(248, 113, 113, 0.25); 
            }
            .metric-value--next { 
                color: #818CF8; 
                font-weight: 700; 
                text-shadow: 0 0 12px rgba(129, 140, 248, 0.25); 
            }
            .metric-value--free { 
                color: #34D399; 
                font-weight: 700; 
            }

            /* Glow Banners for Class Status */
            .status-banner {
                padding: 24px 30px; 
                border-radius: 20px; 
                color: white;
                margin-bottom: 24px; 
                border: 1px solid rgba(255, 255, 255, 0.05);
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
                backdrop-filter: blur(12px);
                transition: all 0.2s ease;
            }
            .status-banner:hover {
                transform: scale(1.003);
            }
            .status-now  { 
                background: linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(185, 28, 28, 0.03) 100%); 
                border-color: rgba(239, 68, 68, 0.35); 
            }
            .status-next { 
                background: linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(67, 56, 202, 0.03) 100%); 
                border-color: rgba(99, 102, 241, 0.35); 
            }
            .status-free { 
                background: linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(4, 120, 87, 0.03) 100%); 
                border-color: rgba(16, 185, 129, 0.35); 
            }

            /* Class Cards */
            .class-card {
                background: rgba(30, 41, 59, 0.2); 
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.04);
                border-radius: 18px; 
                padding: 20px 24px; 
                margin-bottom: 16px;
                border-left: 6px solid #6366F1; 
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            }
            .class-card:hover { 
                transform: translateX(6px); 
                background: rgba(30, 41, 59, 0.35);
                border-color: rgba(255,255,255,0.08);
                box-shadow: 0 8px 30px rgba(0,0,0,0.15);
            }
            .class-card--live { 
                border-left-color: #EF4444; 
                background: rgba(239, 68, 68, 0.03); 
                border-color: rgba(239, 68, 68, 0.12); 
            }
            .class-card--done { 
                border-left-color: #475569; 
                opacity: 0.45; 
            }
            .class-card__time { 
                color: #94A3B8; 
                font-size: 0.88rem; 
                font-weight: 500; 
                display: flex; 
                align-items: center; 
                gap: 6px; 
            }
            .class-card__subject { 
                font-size: 1.25rem; 
                font-weight: 600; 
                color: #F8FAFC; 
                margin: 8px 0; 
            }
            .class-card__room { 
                color: #CBD5E1; 
                font-size: 0.92rem; 
                display: flex; 
                align-items: center; 
                gap: 4px; 
            }

            /* Clean Badge Pills */
            .badge {
                display: inline-block; 
                padding: 4px 14px; 
                border-radius: 999px;
                font-size: 11px; 
                font-weight: 600; 
                margin-top: 12px;
                letter-spacing: 0.5px;
            }
            .badge--live { 
                background: rgba(239,68,68,0.1); 
                color: #FCA5A5; 
                border: 1px solid rgba(239,68,68,0.2); 
            }
            .badge--upcoming { 
                background: rgba(99,102,241,0.1); 
                color: #A5B4FC; 
                border: 1px solid rgba(99,102,241,0.2); 
            }
            .badge--done { 
                background: rgba(100,116,139,0.1); 
                color: #94A3B8; 
                border: 1px solid rgba(100,116,139,0.15); 
            }

            /* Live Countdown Card */
            .live-countdown-card {
                background: linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(139, 92, 246, 0.08) 100%);
                border: 1px solid rgba(99, 102, 241, 0.25);
                border-radius: 20px;
                padding: 28px;
                text-align: center;
                box-shadow: 0 10px 30px rgba(99, 102, 241, 0.08);
                margin-bottom: 28px;
                backdrop-filter: blur(12px);
                animation: pulseBorder 3s infinite alternate;
            }
            @keyframes pulseBorder {
                0% { border-color: rgba(99, 102, 241, 0.25); }
                100% { border-color: rgba(139, 92, 246, 0.45); }
            }
            .live-countdown-title {
                font-size: 0.85rem;
                color: #A5B4FC;
                text-transform: uppercase;
                letter-spacing: 2px;
                margin-bottom: 10px;
                font-weight: 600;
            }
            .live-countdown-subject {
                font-size: 1.5rem;
                font-weight: 700;
                color: #F8FAFC;
                margin-bottom: 14px;
            }
            .live-timer-value {
                font-size: 2.85rem;
                font-weight: 700;
                font-family: 'Outfit', monospace;
                color: #FCA5A5;
                text-shadow: 0 0 20px rgba(252, 165, 165, 0.35);
                letter-spacing: 1.5px;
            }

            /* Beautiful Empty State Cards */
            .empty-state {
                text-align: center; 
                padding: 60px 40px;
                background: rgba(30, 41, 59, 0.15); 
                border-radius: 20px;
                border: 1px dashed rgba(255,255,255,0.06);
                backdrop-filter: blur(10px);
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.05);
            }
            .empty-state h3 { 
                color: #F8FAFC; 
                margin-bottom: 12px; 
                font-weight: 600; 
                font-size: 1.35rem;
            }
            .empty-state p { 
                color: #64748B; 
                margin-bottom: 24px; 
                font-size: 0.95rem;
            }

            /* Sidebar custom layout */
            div[data-testid="stSidebar"] {
                background-color: #101424 !important;
                border-right: 1px solid rgba(255,255,255,0.05) !important;
            }
            div[data-testid="stSidebar"] .stMetric label { 
                color: #64748B !important; 
            }

            /* Form container enhancements */
            div[data-testid="stForm"] {
                background: rgba(30, 41, 59, 0.15) !important;
                backdrop-filter: blur(12px) !important;
                border: 1px solid rgba(255, 255, 255, 0.05) !important;
                border-radius: 20px !important;
                padding: 28px !important;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15) !important;
                margin-bottom: 20px !important;
            }

            /* Form input controls styling */
            .stTextInput input, .stNumberInput input, .stSelectbox select, .stTimeInput input {
                background-color: rgba(15, 23, 42, 0.5) !important;
                border: 1px solid rgba(255, 255, 255, 0.08) !important;
                border-radius: 12px !important;
                color: #F8FAFC !important;
                padding: 10px 16px !important;
                font-size: 0.95rem !important;
                transition: all 0.2s ease-in-out !important;
            }
            .stTextInput input:focus, .stNumberInput input:focus, .stSelectbox select:focus, .stTimeInput input:focus {
                border-color: rgba(99, 102, 241, 0.8) !important;
                box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.25) !important;
                background-color: rgba(15, 23, 42, 0.7) !important;
            }

            /* Tab bar customizations */
            button[data-baseweb="tab"] {
                font-size: 0.95rem !important;
                font-weight: 500 !important;
                color: #64748B !important;
                border-bottom: 2px solid transparent !important;
                padding: 14px 20px !important;
                transition: all 0.2s !important;
                background: transparent !important;
            }
            button[data-baseweb="tab"]:hover {
                color: #94A3B8 !important;
            }
            button[data-baseweb="tab"][aria-selected="true"] {
                color: #818CF8 !important;
                border-bottom-color: #818CF8 !important;
                font-weight: 600 !important;
            }
            div[data-baseweb="tab-highlight"] {
                background-color: #818CF8 !important;
            }

            /* Buttons: Primary (indigo gradient) & Secondary (glassy slate) */
            .stButton > button[kind="primary"] {
                background: linear-gradient(90deg, #6366F1, #8B5CF6) !important;
                border: none !important; 
                border-radius: 12px !important; 
                font-weight: 600 !important;
                color: #FFFFFF !important;
                padding: 10px 24px !important;
                box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3) !important;
                transition: all 0.2s ease-in-out !important;
            }
            .stButton > button[kind="primary"]:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 22px rgba(99, 102, 241, 0.45) !important;
            }
            .stButton > button {
                border-radius: 12px !important;
                border: 1px solid rgba(255,255,255,0.06) !important;
                background-color: rgba(30, 41, 59, 0.3) !important;
                color: #CBD5E1 !important;
                padding: 10px 24px !important;
                font-weight: 500 !important;
                transition: all 0.2s ease-in-out !important;
            }
            .stButton > button:hover {
                border-color: rgba(255,255,255,0.15) !important;
                background-color: rgba(30, 41, 59, 0.5) !important;
                color: #FFFFFF !important;
            }

            /* Custom UI Cards in list view */
            .stAlert {
                background-color: rgba(15, 23, 42, 0.4) !important;
                border: 1px solid rgba(255, 255, 255, 0.05) !important;
                border-radius: 16px !important;
                padding: 16px 20px !important;
            }

            /* Custom scrollbar */
            ::-webkit-scrollbar {
                width: 8px;
                height: 8px;
            }
            ::-webkit-scrollbar-track {
                background: #0A0D1A;
            }
            ::-webkit-scrollbar-thumb {
                background: #1E293B;
                border-radius: 4px;
            }
            ::-webkit-scrollbar-thumb:hover {
                background: #334155;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(label: str, value: str, css_class: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value {css_class}">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_banner(kind: str, title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="status-banner status-{kind}">
            <div style="font-size:0.8rem;opacity:0.85;text-transform:uppercase;letter-spacing:1px;font-weight:600;">{title}</div>
            <div style="font-size:1.25rem;font-weight:600;margin-top:4px;">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_class_card(c: dict, state: str) -> None:
    badge_map = {
        "live": ("กำลังเรียน", "badge--live"),
        "upcoming": ("ถัดไป", "badge--upcoming"),
        "done": ("เรียนจบแล้ว", "badge--done"),
    }
    badge_text, badge_cls = badge_map[state]
    st.markdown(
        f"""
        <div class="class-card class-card--{state}">
            <div class="class-card__time">⏰ {c['start_time']} – {c['end_time']}</div>
            <div class="class-card__subject">{c['subject']}</div>
            <div class="class-card__room">📍 {c.get('room') or 'ไม่ระบุห้อง'}</div>
            <span class="badge {badge_cls}">{badge_text}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )