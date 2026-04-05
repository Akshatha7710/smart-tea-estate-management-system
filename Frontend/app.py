import re
import hashlib
import streamlit as st
from shared import COLORS, _load_users, _save_user, render_shell, render_footer

st.set_page_config(
    page_title="STEMS – Smart Tea Estate Management",
    page_icon="🍃",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("user", None)
st.session_state.setdefault("show_signup", False)

FEATURES = [
    (
        "Fertilizer Scheduling",
        "Predicts fertilizer quantity and application date using climate, yield, plucking, and fertilizer history.",
        "🌱",
        "pages/Fertilizer_Schedule.py",
    ),
    (
        "Soil Quality",
        "Predicts pH, nitrogen, carbon, and nutrient balance. Suggests soil improvements for optimal growth.",
        "🧪",
        "pages/Soil_Quality.py",
    ),
    (
        "Production Analytics",
        "Predicts yield using labour and climate data, and presents estate production analytics and trends.",
        "📈",
        "pages/Production_Analytics.py",
    ),
    (
        "Harvest Readiness",
        "Predicts optimal plucking time to ensure maximum quality leaf yield from the estate.",
        "🌿",
        "pages/Harvest_Readiness.py",
    ),
]


def _auth_css(C):
    bg = f"linear-gradient(135deg,{C['tea_dark']} 0%,{C['tea_green']} 100%)"
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Source+Sans+3:wght@400;600&display=swap');
#MainMenu,header,footer{{display:none!important;}}
[data-testid="stSidebar"],[data-testid="stSidebarContent"],
[data-testid="stSidebarNav"],[data-testid="stSidebarCollapseButton"]{{display:none!important;width:0!important;min-width:0!important;}}
.stApp{{background:{bg}!important;}}
html,body,.stApp{{height:100%!important;margin:0!important;padding:0!important;}}
.main .block-container{{padding:0!important;margin:0!important;max-width:100%!important;width:100%!important;}}
section[data-testid="stMain"] .stVerticalBlock{{gap:0!important;}}
[data-testid="stHorizontalBlock"]{{
    position:fixed!important;top:0!important;left:0!important;
    width:100%!important;height:100%!important;
    display:flex!important;align-items:center!important;justify-content:center!important;
    padding:0!important;margin:0!important;gap:0!important;
    pointer-events:none!important;overflow-y:auto!important;
}}
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]{{display:none!important;pointer-events:none!important;}}
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2){{
    display:flex!important;pointer-events:all!important;flex:0 0 auto!important;
    width:460px!important;max-width:94vw!important;margin:40px 0!important;
}}
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) > div:first-child{{
    background:white!important;border-radius:22px!important;
    padding:36px 32px 30px!important;box-shadow:0 20px 60px rgba(0,0,0,0.18)!important;width:100%!important;
}}
.stTextInput > div > div > input{{background-color:#fafafa!important;border-radius:8px!important;}}
div[data-testid="stButton"]:has(button[kind="primary"]){{margin-top:18px!important;display:block!important;}}
button[kind="primary"],.stButton > button[kind="primary"]{{
    background-color:{C['tea_green']}!important;border-color:{C['tea_green']}!important;
    color:white!important;border-radius:10px!important;
    font-family:'Source Sans 3',sans-serif!important;font-weight:600!important;
}}
button[kind="primary"]:hover,.stButton > button[kind="primary"]:hover{{
    background-color:{C['tea_dark']}!important;border-color:{C['tea_dark']}!important;
}}
</style>"""


def _auth_logo(C):
    logo = f"linear-gradient(135deg,{C['tea_green']},{C['tea_dark']})"
    return f"""
<div style="display:flex;align-items:center;gap:14px;margin-bottom:22px;">
  <div style="background:{logo};border-radius:14px;width:64px;height:64px;
              display:flex;align-items:center;justify-content:center;flex-shrink:0;">
    <span style="font-size:30px;">🍃</span>
  </div>
  <div>
    <div style="font-family:'Playfair Display',serif;font-size:30px;font-weight:700;
                color:{C['text_dark']};line-height:1.1;">STEMS</div>
    <div style="font-size:10px;letter-spacing:2.5px;text-transform:uppercase;
                color:{C['text_muted']};margin-top:3px;font-family:'Source Sans 3',sans-serif;">
      Smart Tea Estate Management System
    </div>
  </div>
</div>"""


def page_login():
    C = COLORS
    st.markdown(_auth_css(C), unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        st.markdown(
            _auth_logo(C)
            + f'<div style="font-family:\'Source Sans 3\',sans-serif;font-size:19px;font-weight:600;'
              f'color:{C["text_dark"]};margin-bottom:18px;text-align:center;">Welcome</div>',
            unsafe_allow_html=True,
        )
        username = st.text_input("Username", key="login_user", placeholder="Enter your username")
        password = st.text_input("Password", type="password", key="login_pass", placeholder="Enter your password")

        if st.button("Log In", use_container_width=True, type="primary", key="login_btn"):
            hashed = hashlib.sha256(password.encode()).hexdigest()
            users = _load_users()
            if username in users and users[username] == hashed:
                st.session_state.logged_in = True
                st.session_state.user = {"username": username, "fullName": username.title()}
                st.rerun()
            else:
                st.error("Invalid username or password")

        st.markdown(
            '<div style="text-align:center;margin-top:16px;font-size:14px;'
            'color:#6B7F6F;font-family:\'Source Sans 3\',sans-serif;">Don\'t have an account?</div>',
            unsafe_allow_html=True,
        )
        if st.button("Sign up", key="goto_signup"):
            st.session_state.show_signup = True
            st.rerun()


def page_signup():
    C = COLORS
    st.markdown(_auth_css(C), unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown(
            _auth_logo(C)
            + f'<div style="font-family:\'Source Sans 3\',sans-serif;font-size:19px;font-weight:600;'
              f'color:{C["text_dark"]};margin-bottom:18px;text-align:center;">Create your account</div>',
            unsafe_allow_html=True,
        )
        full_name   = st.text_input("Full Name",       key="su_name",    placeholder="e.g. Amal Perera")
        designation = st.text_input("Designation",     key="su_desig",   placeholder="e.g. Field Supervisor, Estate Manager")
        email       = st.text_input("Email Address",   key="su_email",   placeholder="e.g. amal@estate.lk")
        phone       = st.text_input("Phone Number",    key="su_phone",   placeholder="e.g. +94771234567")
        username    = st.text_input("Username",        key="su_user",    placeholder="Choose a username")
        password    = st.text_input("Password",        key="su_pass",    type="password", placeholder="Minimum 8 characters")
        confirm_pass = st.text_input("Confirm Password", key="su_confirm", type="password", placeholder="Re-enter your password")

        if st.button("Create Account", use_container_width=True, type="primary", key="signup_btn"):
            errors = []
            if not full_name.strip():
                errors.append("Full Name is required.")
            if not designation.strip():
                errors.append("Designation is required.")
            if not email.strip():
                errors.append("Email Address is required.")
            if not phone.strip():
                errors.append("Phone Number is required.")
            if not username.strip():
                errors.append("Username is required.")
            if not password:
                errors.append("Password is required.")
            if not confirm_pass:
                errors.append("Please confirm your password.")
            if email.strip() and not re.match(r"^[\w\.-]+@[\w\.-]+\.\w{2,}$", email.strip()):
                errors.append("Email address is not valid.")
            if phone.strip() and not re.match(r"^\+?[\d\s\-]{7,15}$", phone.strip()):
                errors.append("Phone number is not valid.")
            if password and len(password) < 8:
                errors.append("Password must be at least 8 characters.")
            if password and confirm_pass and password != confirm_pass:
                errors.append("Passwords do not match.")

            from shared import _load_users
            current_users = _load_users()
            if username.strip() and username.strip() in current_users:
                errors.append("That username is already taken.")

            if errors:
                for e in errors:
                    st.error(e)
            else:
                hashed = hashlib.sha256(password.encode()).hexdigest()
                _save_user(username.strip(), hashed)
                st.session_state.logged_in = True
                st.session_state.user = {"username": username.strip(), "fullName": full_name.strip()}
                st.session_state.show_signup = False
                st.rerun()

        st.markdown(
            '<div style="text-align:center;margin-top:16px;font-size:14px;'
            'color:#6B7F6F;font-family:\'Source Sans 3\',sans-serif;">Already have an account?</div>',
            unsafe_allow_html=True,
        )
        if st.button("Log in", key="goto_login_from_signup"):
            st.session_state.show_signup = False
            st.rerun()


def page_dashboard():
    C = COLORS

    st.markdown(f"""
<style>
[data-testid="stHorizontalBlock"] {{
    gap: 24px !important;
    padding: 0 !important;
    margin: 0 !important;
    align-items: stretch !important;
}}
[data-testid="stColumn"] {{
    display: flex !important;
    flex-direction: column !important;
}}
[data-testid="stColumn"] > div,
[data-testid="stColumn"] .stVerticalBlock,
[data-testid="stColumn"] > div > div > div {{
    display: flex !important;
    flex-direction: column !important;
    gap: 0 !important;
}}
[data-testid="stColumn"] [data-testid="stButton"] {{ margin: 0 !important; padding: 0 !important; }}
[data-testid="stColumn"] [data-testid="stButton"] > button {{
    background: #C2DFC9 !important;
    border: 1px solid #E0DBD4 !important;
    border-top: none !important;
    border-radius: 0 0 16px 16px !important;
    color: {C["tea_green"]} !important;
    font-family: 'Source Sans 3', sans-serif !important;
    font-size: 13px !important;
    font-weight: 700 !important;
    padding: 10px 20px !important;
    width: 100% !important;
    transition: background 0.18s, color 0.18s !important;
    box-shadow: none !important;
    margin: 0 !important;
}}
[data-testid="stColumn"] [data-testid="stButton"] > button:hover {{
    background: {C["tea_green"]} !important;
    color: #fff !important;
    border-color: {C["tea_green"]} !important;
}}
</style>
""", unsafe_allow_html=True)

    render_shell(
        active_label="Dashboard",
        page_title="Dashboard",
        page_subtitle="Smart insights to optimize tea estate management.",
    )

    def render_card(col, title, desc, icon, page_file, btn_key):
        with col:
            st.markdown(f"""
<div style="background:#fff;border:1px solid #E0DBD4;border-radius:16px 16px 0 0;
            border-bottom:none;padding:24px 24px 20px;height:160px;
            box-sizing:border-box;box-shadow:0 1px 4px rgba(0,0,0,0.06);">
  <div style="display:flex;align-items:center;gap:14px;margin-bottom:14px;">
    <div style="width:50px;height:50px;border-radius:12px;background:#EEF2EF;
                display:flex;align-items:center;justify-content:center;font-size:23px;flex-shrink:0;">{icon}</div>
    <div style="font-family:'Playfair Display',serif;font-size:18px;font-weight:700;
                color:{C["text_dark"]};">{title}</div>
  </div>
  <div style="font-size:13px;line-height:1.65;color:{C["text_muted"]};
              display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;">{desc}</div>
</div>
""", unsafe_allow_html=True)
            if st.button("View Details", key=btn_key, use_container_width=True):
                st.switch_page(page_file)

    col1, col2 = st.columns(2, gap="large")
    render_card(col1, *FEATURES[0], "btn_f0")
    render_card(col2, *FEATURES[1], "btn_f1")

    st.markdown('<div style="height:2rem;"></div>', unsafe_allow_html=True)

    col3, col4 = st.columns(2, gap="large")
    render_card(col3, *FEATURES[2], "btn_f2")
    render_card(col4, *FEATURES[3], "btn_f3")

    render_footer()


def main():
    if st.session_state.logged_in:
        page_dashboard()
    elif st.session_state.show_signup:
        page_signup()
    else:
        page_login()


main()