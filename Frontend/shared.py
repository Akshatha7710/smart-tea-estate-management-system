import streamlit as st
import pandas as pd
import hashlib
from pathlib import Path
from datetime import datetime

COLORS = {
    "tea_green": "#2E6B45",
    "tea_green_light": "#C2DFC9",
    "tea_dark": "#1E4D33",
    "earth_brown": "#5C4A2A",
    "earth_warm": "#C8923A",
    "sun_gold": "#E8B832",
    "mist": "#E8EDED",
    "rain_blue": "#5C99B8",
    "bg": "#F5F3EF",
    "card_bg": "#F0EDE7",
    "text_dark": "#1F3D2A",
    "text_muted": "#6B7F6F",
    "destructive": "#C0392B",
    "white": "#FFFFFF",
}


def _load_users() -> dict:
    csv_path = Path(__file__).resolve().parent / "users.csv"
    if not csv_path.exists():
        return {
            "admin": hashlib.sha256("admin123".encode()).hexdigest(),
            "manager": hashlib.sha256("tea2026".encode()).hexdigest(),
        }
    df = pd.read_csv(csv_path)
    return dict(zip(df["username"], df["password_sha256"]))


def _save_user(username: str, hashed_password: str):
    csv_path = Path(__file__).resolve().parent / "users.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
    else:
        df = pd.DataFrame(columns=["username", "password_sha256"])
    new_row = pd.DataFrame([{"username": username, "password_sha256": hashed_password}])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(csv_path, index=False)


SOIL_DATA = pd.DataFrame({
    "Nutrient": ["Nitrogen (N)", "Phosphorus (P)", "Potassium (K)", "pH Level", "Organic Matter", "Calcium (Ca)"],
    "Current": [42.5, 18.3, 35.8, 5.8, 3.2, 120],
    "Predicted (Next Month)": [44.1, 17.8, 37.2, 5.9, 3.4, 118],
    "Unit": ["mg/kg", "mg/kg", "mg/kg", "pH", "%", "mg/kg"],
    "Status": ["Optimal", "Low", "Optimal", "Optimal", "Good", "Optimal"],
    "Trend": ["↑", "↓", "↑", "→", "↑", "↓"],
})

FERTILIZER_DATA = pd.DataFrame({
    "Field": ["Field A – Upper Hill", "Field B – Valley", "Field C – Riverside", "Field D – Plateau", "Field E – Slope"],
    "Area (ha)": [12, 8, 15, 10, 6],
    "Nitrogen (kg)": [45, 32, 58, 40, 24],
    "Phosphorus (kg)": [18, 14, 22, 16, 10],
    "Potassium (kg)": [30, 22, 38, 28, 18],
    "Total (kg)": [93, 68, 118, 84, 52],
})

FERTILIZER_SCHEDULE = pd.DataFrame({
    "Division": ["UVO","LVO","UVO","AGO","LDK","LVO","UDK","AGO","UVO","LDK","LVO","UDK"],
    "Field": [
        "Field A – Upper Hill","Field B – Valley","Field C – Riverside",
        "Field D – Plateau","Field E – Slope","Field F – Terrace",
        "Field G – East Block","Field H – Lowland","Field I – Ridge",
        "Field J – Creek Side","Field K – Midhill","Field L – Summit",
    ],
    "Last_Application": [
        "2026-01-10","2026-01-28","2025-12-20",
        "2026-02-05","2026-01-15","2026-02-01",
        "2025-12-01","2026-01-22","2026-02-10",
        "2026-01-05","2026-02-08","2025-11-30",
    ],
    "Predicted_Cycle_Days": [45,40,60,42,50,38,55,44,48,52,46,58],
    "Days_Since_Application": [68,50,89,42,63,47,108,56,37,73,39,109],
    "Days_Until_Next": [-23,-10,-29,0,-13,-9,-53,-12,11,-21,7,-51],
    "Next_Application_Date": [
        "2026-01-25","2026-03-09","2026-02-18",
        "2026-03-19","2026-03-06","2026-03-10",
        "2026-01-25","2026-03-07","2026-03-30",
        "2026-02-26","2026-03-26","2026-01-27",
    ],
    "Predicted_Amount_kg": [93.0,68.0,118.0,84.0,52.0,76.0,105.0,71.0,89.0,97.0,62.0,111.0],
    "Status": [
        "OVERDUE","OVERDUE","OVERDUE",
        "DUE SOON","OVERDUE","DUE SOON",
        "OVERDUE","OVERDUE","UPCOMING",
        "OVERDUE","UPCOMING","OVERDUE",
    ],
})

HARVEST_DATA = [
    {"name": "Field B – Valley",    "last": "Jan 28, 2026", "days": 2,  "cycle": 40, "status": "Urgent"},
    {"name": "Field F – Terrace",   "last": "Feb 1, 2026",  "days": 5,  "cycle": 38, "status": "Soon"},
    {"name": "Field A – Upper Hill","last": "Feb 10, 2026", "days": 8,  "cycle": 45, "status": "Soon"},
    {"name": "Field D – Plateau",   "last": "Feb 5, 2026",  "days": 14, "cycle": 42, "status": "On Track"},
    {"name": "Field E – Slope",     "last": "Feb 15, 2026", "days": 18, "cycle": 48, "status": "On Track"},
    {"name": "Field C – Riverside", "last": "Feb 18, 2026", "days": 22, "cycle": 50, "status": "On Track"},
]


def get_productivity_data():
    months = ["Sep", "Oct", "Nov", "Dec", "Jan", "Feb"]
    return pd.DataFrame({
        "Month": months,
        "Yield (kg/ha)": [320, 345, 310, 290, 340, 365],
        "Revenue (LKR)": [480000, 517500, 465000, 435000, 510000, 547500],
        "Quality Score": [82, 85, 78, 80, 88, 91],
    })


def get_greeting():
    h = datetime.now().hour
    if h < 12:
        return "Good morning"
    if h < 17:
        return "Good afternoon"
    return "Good evening"


def login_guard():
    if not st.session_state.get("logged_in"):
        st.switch_page("app.py")


def inject_css():
    pass


NAV_ITEMS = [
    ("⊞  Dashboard", "app.py"),
    ("📤 Data Upload", "pages/Data_Upload.py"),
    ("🌱 Fertilizer Scheduling", "pages/Fertilizer_Schedule.py"),
    ("🌿 Harvest Readiness", "pages/Harvest_Readiness.py"),
    ("📈 Production Analytics", "pages/Production_Analytics.py"),
    ("🧪 Soil Quality", "pages/Soil_Quality.py"),
    ("ⓘ  About STEMS", "pages/About.py"),
]

MARGIN = "32px"
TOPBAR_H = 54


def render_shell(active_label: str, page_title: str, page_subtitle: str, content_html: str = ""):
    C = COLORS
    user = st.session_state.get("user") or {}
    greeting = get_greeting()
    username = user.get("fullName", "")
    greeting_str = f"{greeting}, <strong>{username}</strong>" if username else greeting

    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Source+Sans+3:wght@300;400;500;600;700&display=swap');

#MainMenu, header, footer {{ display: none !important; }}
[data-testid="stSidebarNav"] {{ display: none !important; }}

html, body, .stApp {{
    background: {C["bg"]} !important;
    margin: 0 !important;
    padding: 0 !important;
}}

section[data-testid="stMain"] {{
    padding: {TOPBAR_H + 16}px {MARGIN} 0 {MARGIN} !important;
    margin: 0 !important;
    box-sizing: border-box !important;
    overflow-x: hidden !important;
    width: 100% !important;
}}
section[data-testid="stMain"] > div {{
    padding: 0 !important;
    margin: 0 !important;
    width: 100% !important;
    box-sizing: border-box !important;
}}
.main .block-container {{
    padding: 0 !important;
    margin: 0 !important;
    max-width: 100% !important;
    width: 100% !important;
    box-sizing: border-box !important;
}}
section[data-testid="stMain"] .stVerticalBlock {{ gap: 0 !important; }}

[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {C["tea_dark"]} 0%, #153927 100%) !important;
    width: 256px !important;
    min-width: 256px !important;
    max-width: 256px !important;
    padding: 0 !important;
    overflow: hidden !important;
}}
[data-testid="stSidebarContent"],
[data-testid="stSidebarUserContent"],
[data-testid="stSidebar"] > div,
[data-testid="stSidebar"] > div > div,
[data-testid="stSidebar"] > div > div > div,
[data-testid="stSidebar"] > div > div > div > div,
[data-testid="stSidebar"] section,
[data-testid="stSidebar"] section > div,
[data-testid="stSidebar"] .block-container {{
    padding: 0 !important;
    margin: 0 !important;
    gap: 0 !important;
}}
[data-testid="stSidebar"] .stVerticalBlock {{
    gap: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
}}
[data-testid="stSidebar"] .stMarkdown {{ padding: 0 !important; margin: 0 !important; }}

#stems-sidebar-logo {{
    margin-top: -3rem;
    padding: 2px 16px 16px 16px;
    border-bottom: 1px solid rgba(255,255,255,0.10);
    display: flex;
    align-items: center;
    gap: 12px;
    box-sizing: border-box;
}}
#stems-sidebar-logo .s-ico {{
    background: rgba(255,255,255,0.13);
    border-radius: 10px;
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 19px;
    flex-shrink: 0;
}}
#stems-sidebar-logo .s-name {{
    font-family: 'Playfair Display', serif;
    font-size: 18px;
    font-weight: 700;
    color: rgba(255,255,255,0.95);
    line-height: 1.1;
}}
#stems-sidebar-logo .s-sub {{
    font-size: 7.5px;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: rgba(255,255,255,0.40);
    font-family: 'Source Sans 3', sans-serif;
    margin-top: 3px;
}}
#stems-nav-label {{
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: rgba(255,255,255,0.32);
    padding: 28px 18px 16px;
    font-family: 'Source Sans 3', sans-serif;
    pointer-events: none;
}}
[data-testid="stSidebar"] [data-testid="stPageLink"] {{
    display: block !important;
    background: transparent !important;
    border-radius: 8px !important;
    margin: 8px 10px !important;
    padding: 0 !important;
    transition: background 0.15s !important;
}}
[data-testid="stSidebar"] [data-testid="stPageLink"]:hover {{
    background: rgba(255,255,255,0.09) !important;
}}
[data-testid="stSidebar"] [data-testid="stPageLink"][aria-current="page"] {{
    background: rgba(46,107,69,0.45) !important;
}}
[data-testid="stSidebar"] [data-testid="stPageLink"] p {{
    font-family: 'Source Sans 3', sans-serif !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    color: rgba(255,255,255,0.78) !important;
    padding: 11px 12px !important;
    margin: 0 !important;
    line-height: 1.3 !important;
}}
[data-testid="stSidebar"] [data-testid="stPageLink"]:hover p {{
    color: rgba(255,255,255,0.97) !important;
}}
[data-testid="stSidebar"] [data-testid="stPageLink"][aria-current="page"] p {{
    color: #C2DFC9 !important;
}}
[data-testid="stSidebar"] [data-testid="stButton"] {{
    position: fixed !important;
    bottom: 0 !important;
    left: 0 !important;
    width: 256px !important;
    padding: 12px 16px 18px !important;
    background: linear-gradient(0deg, #153927 75%, transparent) !important;
    z-index: 200 !important;
}}
[data-testid="stSidebar"] [data-testid="stButton"] > button {{
    background: transparent !important;
    border: 1px solid rgba(255,255,255,0.22) !important;
    border-radius: 9px !important;
    color: rgba(255,255,255,0.95) !important;
    font-family: 'Source Sans 3', sans-serif !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    width: 100% !important;
    padding: 10px !important;
    transition: background 0.15s, color 0.15s !important;
    box-shadow: none !important;
}}
[data-testid="stSidebar"] [data-testid="stButton"] > button:hover {{
    background: rgba(255,255,255,0.09) !important;
    color: rgba(255,255,255,0.97) !important;
    border-color: rgba(255,255,255,0.38) !important;
}}

#stems-topbar {{
    position: fixed;
    top: 0;
    left: 256px;
    right: 0;
    z-index: 999;
    height: {TOPBAR_H}px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 {MARGIN};
    background: {C["tea_dark"]};
    font-family: 'Source Sans 3', sans-serif;
}}
#stems-topbar .greeting {{ font-size: 13px; color: rgba(255,255,255,0.82); }}
#stems-topbar .greeting strong {{ color: #fff; font-weight: 600; }}
#stems-topbar .hdr-right {{ font-size: 13px; color: rgba(255,255,255,0.48); }}

#stems-content {{
    padding: 0;
    background: {C["bg"]};
}}

.pg-title {{
    font-family: 'Playfair Display', serif;
    font-size: 30px;
    font-weight: 700;
    color: {C["text_dark"]};
    margin: 0 0 6px 0;
}}
.pg-sub {{
    font-size: 14px;
    color: {C["text_muted"]};
    margin: 0 0 24px 0;
    font-family: 'Source Sans 3', sans-serif;
}}
.section-title {{
    font-family: 'Playfair Display', serif;
    font-size: 20px;
    font-weight: 700;
    color: {C["text_dark"]};
    margin: 24px 0 4px 0;
}}
.section-sub {{
    font-size: 13px;
    color: {C["text_muted"]};
    margin: 0 0 14px 0;
    font-family: 'Source Sans 3', sans-serif;
}}
.metric-box {{ background: #fff; border: 1px solid #E2DDD7; border-radius: 14px; padding: 18px 20px; }}
.metric-value {{ font-family: 'Playfair Display', serif; font-size: 32px; font-weight: 700; line-height: 1.1; }}
.metric-label {{ font-size: 13px; color: #6B7F6F; margin-top: 4px; font-family: 'Source Sans 3', sans-serif; }}
.badge {{ display: inline-block; font-size: 12px; font-weight: 700; padding: 3px 10px; border-radius: 20px; font-family: 'Source Sans 3', sans-serif; }}
.badge-urgent {{ background: #fde8e8; color: #C0392B; }}
.badge-soon {{ background: #fef3e2; color: #C8923A; }}
.badge-ok {{ background: #e8f5ee; color: #2E6B45; }}
.progress-outer {{ background: #E8E4DE; border-radius: 99px; height: 8px; overflow: hidden; }}
.progress-inner {{ background: linear-gradient(90deg, #2E6B45, #C2DFC9); height: 100%; border-radius: 99px; }}
.trend-up {{ color: #2E6B45; }}
.trend-down {{ color: #C0392B; }}
.trend-stable {{ color: #6B7F6F; }}
.dot {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 5px; vertical-align: middle; }}
.stems-footer {{
    position: fixed !important;
    bottom: 0 !important;
    left: 256px !important;
    right: 0 !important;
    border-top: 1px solid #E0DBD3;
    padding: 10px {MARGIN};
    text-align: center;
    font-size: 11px;
    color: {C["text_muted"]};
    background: {C["bg"]};
    font-family: 'Source Sans 3', sans-serif;
    letter-spacing: .04em;
    z-index: 100 !important;
}}
section[data-testid="stMain"] {{
    padding-bottom: 72px !important;
}}
hr.divider {{ border: none; border-top: 1px solid #E0DBD3; margin: 20px 0; }}
</style>
""", unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("""
<script>
(function() {
    function fix() {
        var el = window.parent.document.querySelector('[data-testid="stSidebarUserContent"]');
        if (el) el.style.setProperty('padding-top', '0px', 'important');
        var el2 = window.parent.document.querySelector('[data-testid="stSidebarContent"]');
        if (el2) el2.style.setProperty('padding-top', '0px', 'important');
    }
    fix(); setTimeout(fix, 100); setTimeout(fix, 500);
})();
</script>
<div id="stems-sidebar-logo">
  <div class="s-ico">🍃</div>
  <div>
    <div class="s-name">STEMS</div>
    <div class="s-sub">Smart Tea Estate Management System</div>
  </div>
</div>
<div id="stems-nav-label">Navigation</div>
""", unsafe_allow_html=True)

        for label, page_file in NAV_ITEMS:
            if page_file:
                st.page_link(page_file, label=label)
            else:
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:10px;'
                    f'padding:11px 12px;margin:8px 10px;border-radius:8px;'
                    f'font-size:14px;font-weight:600;color:rgba(255,255,255,.28);'
                    f'cursor:not-allowed;">{label}</div>',
                    unsafe_allow_html=True
                )

        if st.button("Logout", key="logout_btn", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.switch_page("app.py")

    st.markdown(f"""
<div id="stems-topbar">
  <div class="greeting">{greeting_str}</div>
  <div class="hdr-right">Vellai Oya Estate, Sri Lanka</div>
</div>
""", unsafe_allow_html=True)

    st.markdown(f"""
<div id="stems-content">
  <div class="pg-title">{page_title}</div>
  <div class="pg-sub">{page_subtitle}</div>
  {content_html}
</div>
""", unsafe_allow_html=True)


def render_footer():
    C = COLORS
    st.markdown(
        f'<div class="stems-footer">'
        f'\u00a9 2026 STEMS \u00b7 Smart Tea Estate Management System \u00b7 Vellai Oya Estate, Sri Lanka'
        f'</div>',
        unsafe_allow_html=True
    )