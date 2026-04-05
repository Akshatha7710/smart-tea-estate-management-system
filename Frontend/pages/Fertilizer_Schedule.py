import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import json
from datetime import date, timedelta
import streamlit as st
import streamlit.components.v1
import pandas as pdS

from shared import COLORS, login_guard, render_shell, render_footer
from api_client import predict_fertilizer, get_fertilizer_schedule

st.set_page_config(
    page_title="Fertilizer Schedule – STEMS",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)
login_guard()
C = COLORS

# Nitrogen constants
VP_RATIO_THRESHOLD = 12
SD_RATIO_THRESHOLD = 10
TARGET_N_SD_KG_HA = 320
N_REPLACEMENT_RATIO = 100
MIN_APPLICATIONS_YEAR = 3
MAX_APPLICATIONS_YEAR = 4
UREA_N_FRACTION = 0.46
ANNUAL_FERT_MIN_KG_HA = 180
ANNUAL_FERT_MAX_KG_HA = 240

DIVISION_LABELS = {
    "AGO": "Agroya",
    "LDK": "Lower Dandukellewa",
    "LVO": "Lower Vellai Oya",
    "UDK": "Upper Dandukellewa",
    "UVO": "Upper Vellai Oya",
}

FIELD_CATALOGUE = {
    "AGO": ["3A", "3B", "4A", "9G", "9H", "9I"],
    "LDK": ["44", "45", "45A", "46", "47", "50", "51", "52", "52A", "53"],
    "LVO": ["1", "2", "3", "3B", "5", "5A", "6", "6A", "7", "7A", "8", "9A", "9B", "9C", "9D"],
    "UDK": ["23", "24", "24A", "25", "26", "26A", "27", "27A", "28", "29", "30", "30A", "32", "33", "49"],
    "UVO": ["11", "12", "13", "13A", "16NC", "17", "18", "18A", "19A", "19B", "19C",
            "20A", "20B", "20C", "21", "21A", "22", "48", "48A"],
}

SD_FIELDS = {"UDK": ["28"]}


def get_field_type(division, field_no):
    return "SD" if field_no in SD_FIELDS.get(division, []) else "VP"


def ratio_threshold(field_type):
    return VP_RATIO_THRESHOLD if str(field_type).upper() == "VP" else SD_RATIO_THRESHOLD


def urea_from_nitrogen(n_kg):
    return round(n_kg / UREA_N_FRACTION, 1)


def annual_n_target(yield_kgha, field_type):
    if str(field_type).upper() == "SD":
        return TARGET_N_SD_KG_HA
    n = yield_kgha / N_REPLACEMENT_RATIO
    n_min = ANNUAL_FERT_MIN_KG_HA * UREA_N_FRACTION
    n_max = ANNUAL_FERT_MAX_KG_HA * UREA_N_FRACTION
    return round(max(n_min, min(n_max, n)), 1)


def build_annual_n_schedule(yield_kgha, area_ha, field_type):
    n_annual_ha = annual_n_target(yield_kgha, field_type)
    if str(field_type).upper() == "SD":
        n_apps = MAX_APPLICATIONS_YEAR
    else:
        n_apps = MAX_APPLICATIONS_YEAR if n_annual_ha > (ANNUAL_FERT_MIN_KG_HA * UREA_N_FRACTION) else MIN_APPLICATIONS_YEAR
    n_per_app_ha = round(n_annual_ha / n_apps, 1)
    urea_per_app = urea_from_nitrogen(n_per_app_ha * area_ha)
    interval_days = 365 // n_apps
    return n_apps, n_per_app_ha, urea_per_app, interval_days


def pick(d, *keys, default=None):
    for k in keys:
        if d.get(k) is not None:
            return d[k]
    return default


@st.cache_data(show_spinner=False, ttl=3600)
def load_predicted_schedule():
    local_paths = [
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "predicted_schedule.json"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "datasets", "predicted_schedule.json"),
    ]
    for path in local_paths:
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f), None
    return None, "Predicted schedule file not found."


st.markdown(f"""
<style>
[data-testid="stSelectbox"] label {{
    font-family: 'Source Sans 3', sans-serif !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    color: {C['text_muted']} !important;
}}
[data-testid="stSelectbox"] > div > div {{
    border: 1.5px solid #D0CCC6 !important;
    border-radius: 10px !important;
    background: #FFFFFF !important;
    min-height: 40px !important;
    font-family: 'Source Sans 3', sans-serif !important;
    font-size: 14px !important;
    color: {C['text_dark']} !important;
}}
[data-testid="stSelectbox"] input {{
    pointer-events: none !important;
    caret-color: transparent !important;
    user-select: none !important;
}}
[data-testid="stButton"] > button[kind="primary"] {{
    background: #5BA870 !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Source Sans 3', sans-serif !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    height: 44px !important;
    box-shadow: 0 3px 10px rgba(91,168,112,0.25) !important;
    transition: opacity .18s, transform .15s !important;
}}
[data-testid="stButton"] > button[kind="primary"]:hover {{
    opacity: 0.91 !important;
    transform: translateY(-1px) !important;
}}

.interactive-box {{
    cursor: pointer;
    transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}}
.interactive-box:hover {{
    transform: translateY(-3px);
    box-shadow: 0 8px 28px rgba(30,77,51,0.14) !important;
    border-color: #5BA870 !important;
}}
.interactive-box:active {{
    transform: translateY(-1px);
}}

.n-budget-box {{
    background: #fff;
    border: 1.5px solid #D9D4CC;
    border-radius: 18px;
    padding: 28px 32px;
    margin: 32px 0 0 0;
    box-shadow: 0 2px 10px rgba(30,77,51,0.06);
    transition: box-shadow 0.2s ease, border-color 0.2s ease;
}}
.n-budget-box:hover {{
    box-shadow: 0 8px 28px rgba(30,77,51,0.12);
    border-color: #5BA870;
}}
.n-budget-title {{
    font-family: 'Playfair Display', serif;
    font-size: 17px;
    font-weight: 700;
    color: #1F3D2A;
    margin-bottom: 18px;
    display: flex;
    align-items: center;
    gap: 10px;
}}
.n-budget-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
}}
.n-rule-card {{
    background: #EEF4F1;
    border: 1px solid #C2DFC9;
    border-radius: 12px;
    padding: 16px 18px;
    transition: background 0.15s;
}}
.n-rule-card:hover {{
    background: #e0f0e6;
}}
.n-rule-label {{
    font-size: 10px;
    font-weight: 700;
    letter-spacing: .12em;
    text-transform: uppercase;
    color: #2E6B45;
    margin-bottom: 6px;
    font-family: 'Source Sans 3', sans-serif;
}}
.n-rule-value {{
    font-family: 'Playfair Display', serif;
    font-size: 22px;
    font-weight: 700;
    color: #1F3D2A;
    line-height: 1.1;
}}
.n-rule-sub {{
    font-size: 12px;
    color: #6B7F6F;
    margin-top: 4px;
    font-family: 'Source Sans 3', sans-serif;
    line-height: 1.4;
}}
.n-rule-row {{
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    margin-top: 14px;
}}
.n-inline-badge {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #F0F7F3;
    border: 1px solid #B6DAC2;
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 600;
    color: #2E6B45;
    font-family: 'Source Sans 3', sans-serif;
    transition: background 0.15s;
}}
.n-inline-badge:hover {{
    background: #D8EEE0;
}}

.chart-gap {{
    height: 40px;
}}
.chart-section-gap {{
    height: 52px;
}}
</style>
""", unsafe_allow_html=True)

render_shell(
    active_label="Fertilizer Schedule",
    page_title="🌱 Fertilizer Schedule",
    page_subtitle="Individual field predictions and the full estate fertilizer schedule.",
)

# Individual field prediction
st.markdown("""
<div style="margin-top: 8px;">
  <div class="section-title">Individual Field Prediction</div>
  <div class="section-sub" style="margin-bottom: 18px;">
    Select a division and field to view its predicted fertilizer schedule.
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<script>
(function() {
    function lock() {
        window.parent.document.querySelectorAll('[data-testid="stSelectbox"] input').forEach(function(el) {
            if (el._locked) return;
            el._locked = true;
            el.setAttribute('readonly','readonly');
            el.style.caretColor='transparent';
            ['keydown','keypress','keyup','input','paste'].forEach(function(ev) {
                el.addEventListener(ev, function(e){e.preventDefault();e.stopPropagation();}, true);
            });
        });
    }
    lock(); setTimeout(lock,300); setTimeout(lock,800);
    new MutationObserver(lock).observe(window.parent.document.body,{childList:true,subtree:true});
})();
</script>
""", unsafe_allow_html=True)

col_div, col_field = st.columns([1, 1])
with col_div:
    sel_div = st.selectbox(
        "Division",
        list(FIELD_CATALOGUE.keys()),
        format_func=lambda d: f"{d} - {DIVISION_LABELS[d]}",
        key="fert_div_sel"
    )
with col_field:
    sel_fld = st.selectbox(
        "Field Number",
        FIELD_CATALOGUE[sel_div],
        format_func=lambda f: f"Field {f}",
        key="fert_fld_sel"
    )

st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

col_l, col_btn, col_r = st.columns([1.0, 0.8, 1.0])
with col_btn:
    go = st.button("View Prediction ↓", type="primary", use_container_width=True, key="fert_go_btn")

st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)

if go:
    local_pred_rows, _ = load_predicted_schedule()
    local_data = None
    if local_pred_rows:
        for row in local_pred_rows:
            if str(row.get("Division", "")).strip() == sel_div and str(row.get("Field", "")).strip() == sel_fld:
                local_data = row
                break

    if local_data:
        data = {
            "predicted_amount_kg": local_data.get("Pred_Amount_kg"),
            "days_until_next": local_data.get("Days_Until_Next"),
            "status_message": local_data.get("Schedule_Status"),
            "yield_kgha": local_data.get("Annual_Yield_kgha"),
            "extent_ha": local_data.get("Extent_Ha"),
            "pred_dose_kgha": local_data.get("Pred_Dose_kgha"),
            "n_ratio_seas": local_data.get("N_Ratio_Seas"),
            "apps_per_year": None,
            "n_per_app_kgha": None,
            "urea_per_app_kg": None,
            "interval_days": local_data.get("Pred_Cycle_Days"),
        }
        error = None
    else:
        with st.spinner("Fetching prediction…"):
            result, error = predict_fertilizer(division=sel_div, field_no=sel_fld)
        if not error:
            try:
                data = json.loads(result) if isinstance(result, str) else result
            except Exception:
                data = {}
        else:
            data = {}

    if error and not local_data:
        st.error(f"⚠️ {error}")
    else:
        amt_raw = pick(data, "predicted_amount_kg", "total_amount_kg", "amount_kg")
        days_until = pick(data, "days_until_next", "days_until", "days_remaining")
        status_msg = str(pick(data, "status_message", "status", default="—"))
        yield_kgha = pick(data, "yield_kgha", "yield_per_ha", default=None)
        area_ha = pick(data, "extent_ha", "area_ha", "area", default=1.0)
        pred_dose = pick(data, "pred_dose_kgha", "dose_kgha", default=None)
        n_ratio_seas = pick(data, "n_ratio_seas", default=None)
        apps_py = pick(data, "apps_per_year", default=None)
        n_per_app = pick(data, "n_per_app_kgha", default=None)
        urea_app = pick(data, "urea_per_app_kg", default=None)
        interval_d = pick(data, "interval_days", default=None)

        amt_display = f"{float(amt_raw):.1f}" if amt_raw is not None else "-"
        is_overdue  = days_until is not None and int(float(days_until)) < 0

        days_val = None
        days_display = "—"
        if days_until is not None:
            days_val = int(float(days_until))
            days_display = f"{abs(days_val)} days overdue" if is_overdue else f"{days_val} days"

        field_type      = get_field_type(sel_div, sel_fld)
        n_ratio         = None
        n_ratio_display = "—"
        n_ratio_status  = ""
        if n_ratio_seas is not None:
            try:
                n_ratio = float(n_ratio_seas)
                threshold = ratio_threshold(field_type)
                n_ratio_display = f"{n_ratio:.2f}"
                n_ratio_status = "⚠ Apply N" if n_ratio < threshold else "✓ Adequate"
            except Exception:
                pass

        n_apps_val = None
        n_per_app_val = None
        urea_per_app_val = None
        interval_val = None

        if apps_py is not None and n_per_app is not None and urea_app is not None and interval_d is not None:
            n_apps_val = int(apps_py)
            n_per_app_val = float(n_per_app)
            urea_per_app_val = float(urea_app)
            interval_val = int(interval_d)
        elif yield_kgha is not None and area_ha is not None:
            try:
                n_apps_val, n_per_app_val, urea_per_app_val, interval_val = build_annual_n_schedule(
                    float(yield_kgha), float(area_ha), field_type
                )
            except Exception:
                pass
        elif interval_d is not None:
            interval_val = int(float(interval_d))

        next_app_date = None
        if days_until is not None:
            try:
                next_app_date = date.today() + timedelta(days=int(float(days_until)))
            except Exception:
                pass

        if is_overdue:
            status_color = C["destructive"]
            status_bg = "#fde8e8"
        elif days_until is not None and int(float(days_until)) <= 90:
            status_color = C["earth_warm"]
            status_bg = "#fef3e2"
        else:
            status_color = C["tea_green"]
            status_bg = "#e8f5ee"

        if is_overdue:
            days_card_html = f"""
              <div class="metric interactive-box" style="background:#fde8e8;border-color:#f1b8b4;">
                <div class="metric-label">Overdue By</div>
                <div class="metric-value date-val" style="color:#C0392B;">{abs(days_val)}</div>
                <div style="font-size:12px;color:#C0392B;margin-top:4px;font-weight:600;">days</div>
                {f'<div style="font-size:10px;color:#C0392B;margin-top:4px;">Was due: {next_app_date.strftime("%d %b %Y")}</div>' if next_app_date else ''}
              </div>"""
        else:
            days_color = "#C8923A" if days_val is not None and days_val <= 90 else "#2E6B45"
            days_card_html = f"""
              <div class="metric interactive-box">
                <div class="metric-label">Days Until Next</div>
                <div class="metric-value date-val" style="color:{days_color};">{days_display if days_val is None else days_val}</div>
                <div style="font-size:12px;color:{days_color};margin-top:4px;font-weight:600;">days</div>
                {f'<div style="font-size:10px;color:#6B7F6F;margin-top:4px;">{next_app_date.strftime("%d %b %Y")}</div>' if next_app_date else ''}
              </div>"""

        n_color = "#C0392B" if (n_ratio is not None and n_ratio < ratio_threshold(field_type)) else "#2E6B45"
        n_panel_html = f"""
          <div class="metric interactive-box" style="background:#F0F7F3;border-color:#B6DAC2;">
            <div class="metric-label">N Ratio ({field_type})</div>
            <div class="metric-value" style="font-size:26px;color:{n_color};">{n_ratio_display}</div>
            <div style="font-size:11px;color:{n_color};margin-top:5px;font-weight:700;">{n_ratio_status}</div>
          </div>"""

        dose_panel_html = ""
        if pred_dose is not None:
            dose_val = float(pred_dose)
            dose_display = f"{dose_val:.2f}"
            dose_panel_html = f"""
              <div class="metric interactive-box" style="background:#F0F7F3;border-color:#B6DAC2;">
                <div class="metric-label">Predicted Dose Rate</div>
                <div class="metric-value" style="font-size:24px;color:#2E6B45;">{dose_display}</div>
                <div style="font-size:11px;color:#6B7F6F;margin-top:4px;">kg N / ha</div>
              </div>"""

        cycle_card_html = ""
        if interval_val is not None:
            cycle_card_html = f"""
              <div class="metric interactive-box" style="background:#F9F7F4;border-color:#E8E4DE;">
                <div class="metric-label">Cycle Days</div>
                <div class="metric-value" style="font-size:24px;color:#5C4A2A;">{interval_val}</div>
                <div style="font-size:11px;color:#6B7F6F;margin-top:4px;">predicted interval</div>
              </div>"""

        card_height = 340

        st.components.v1.html(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Source+Sans+3:wght@400;600&display=swap');
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: 'Source Sans 3', sans-serif; }}
        .card-wrap {{ background: #FFFFFF; border: 1.5px solid #D9D4CC; border-radius: 18px;
                      padding: 26px 28px; box-shadow: 0 4px 20px rgba(30,77,51,0.06); }}
        .card-division {{ font-size: 11px; font-weight: 700; letter-spacing: .14em;
                          text-transform: uppercase; color: #6B7F6F; margin-bottom: 5px; }}
        .card-field {{ font-family: 'Playfair Display', serif; font-size: 28px; font-weight: 700;
                       color: #1F3D2A; margin-bottom: 22px; line-height: 1.1; }}
        .cards {{ display: flex; gap: 12px; flex-wrap: wrap; }}
        .metric {{ flex: 1; min-width: 120px; background: #F9F7F4; border: 1px solid #E8E4DE;
                   border-radius: 12px; padding: 20px 16px; text-align: center;
                   cursor: pointer; transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease; }}
        .metric:hover {{ transform: translateY(-3px); box-shadow: 0 8px 22px rgba(30,77,51,0.13);
                         border-color: #5BA870; }}
        .metric:active {{ transform: translateY(-1px); }}
        .metric-label {{ font-size: 10px; font-weight: 700; letter-spacing: .10em;
                         text-transform: uppercase; color: #6B7F6F; margin-bottom: 10px; line-height: 1.4; }}
        .metric-value {{ font-family: 'Playfair Display', serif; font-size: 28px;
                         font-weight: 700; color: #1F3D2A; line-height: 1; }}
        .metric-value.status-val {{ font-size: 14px; color: {status_color}; line-height: 1.6; }}
        .unit {{ font-size: 13px; font-weight: 400; color: #6B7F6F; }}
        </style>
        <div class="card-wrap">
          <div class="card-division">{sel_div} &nbsp;·&nbsp; {DIVISION_LABELS[sel_div]} Division &nbsp;·&nbsp; {field_type} field</div>
          <div class="card-field">
            Field {sel_fld}
            <span style="font-size:13px;font-weight:400;color:#6B7F6F;margin-left:12px;font-family:'Source Sans 3',sans-serif;">
              N Ratio: <strong style="color:{n_color};">{n_ratio_display}</strong>
              <span style="margin-left:6px;font-size:11px;color:{n_color};">{n_ratio_status}</span>
            </span>
          </div>
          <div class="cards">
            <div class="metric">
              <div class="metric-label">Predicted Amount</div>
              <div class="metric-value">{amt_display}<span class="unit"> kg</span></div>
            </div>
            {dose_panel_html}
            {days_card_html}
            <div class="metric" style="background:{status_bg};border-color:{status_color}44;">
              <div class="metric-label">Status</div>
              <div class="metric-value status-val">{status_msg}</div>
            </div>
            {n_panel_html}
            {cycle_card_html}
          </div>
        </div>
        """, height=card_height, scrolling=False)

        # Per-field N applications chart
        st.markdown("<div class='chart-gap'></div>", unsafe_allow_html=True)

        if n_apps_val is not None and n_per_app_val is not None and interval_val is not None:
            try:
                import plotly.graph_objects as go_fig

                today_date = date.today()
                next_day = int(float(days_until)) if days_until is not None else interval_val
                start_offset = max(0, next_day)

                app_labels = []
                n_values = []
                urea_values = []

                for i in range(n_apps_val):
                    d_off = start_offset + i * interval_val
                    app_d = today_date + timedelta(days=d_off)
                    app_labels.append(app_d.strftime("%d %b %Y"))
                    n_values.append(n_per_app_val)
                    urea_total = urea_per_app_val if urea_per_app_val is not None else urea_from_nitrogen(n_per_app_val * float(area_ha))
                    urea_values.append(urea_total)

                n_annual_ha = n_per_app_val * n_apps_val
                bar_colors = ["#5BA870"] * n_apps_val
                if is_overdue or (days_val is not None and days_val <= 14):
                    bar_colors[0] = "#C0392B"

                fig = go_fig.Figure()
                fig.add_trace(go_fig.Bar(
                    x=app_labels,
                    y=n_values,
                    name="N Applied (kg/ha)",
                    marker_color=bar_colors,
                    marker_line_color="white",
                    marker_line_width=1.5,
                    customdata=list(zip(urea_values, [f"App #{i+1}" for i in range(n_apps_val)], [n_ratio_display]*n_apps_val)),
                    hovertemplate=(
                        "<b>%{customdata[1]}</b><br>"
                        "Date: %{x}<br>"
                        "N Rate: %{y:.1f} kg N/ha<br>"
                        "Urea Total: %{customdata[0]:.0f} kg<br>"
                        f"N Ratio (current): {n_ratio_display}<br>"
                        "<extra></extra>"
                    ),
                    text=[f"N: {v:.1f} kg/ha<br>Urea: {u:.0f} kg" for v, u in zip(n_values, urea_values)],
                    textposition="outside",
                    textfont=dict(size=11, family="Source Sans 3, sans-serif"),
                ))
                fig.add_hline(
                    y=n_per_app_val,
                    line_dash="dot",
                    line_color="#C0392B",
                    line_width=1.8,
                    annotation_text=f"Target N/app = {n_per_app_val:.1f} kg/ha",
                    annotation_position="bottom left",
                    annotation_font=dict(size=11, color="#C0392B"),
                )

                if n_ratio is not None:
                    threshold_val = ratio_threshold(field_type)
                    summary_text = (
                        f"<b>Annual Total:</b> {n_annual_ha:.0f} kg N/ha &nbsp;&nbsp;|&nbsp;&nbsp; "
                        f"<b>{n_apps_val}</b> applications &nbsp;&nbsp;|&nbsp;&nbsp; Every ~{interval_val} days &nbsp;&nbsp;|&nbsp;&nbsp; "
                        f"<b>N Ratio:</b> {n_ratio_display} (threshold: {threshold_val})"
                    )
                else:
                    summary_text = (
                        f"<b>Annual Total:</b> {n_annual_ha:.0f} kg N/ha &nbsp;&nbsp;|&nbsp;&nbsp; "
                        f"<b>{n_apps_val}</b> applications &nbsp;&nbsp;|&nbsp;&nbsp; Every ~{interval_val} days"
                    )

                fig.add_shape(
                    type="rect",
                    xref="paper", yref="paper",
                    x0=0, x1=1, y0=1.04, y1=1.13,
                    fillcolor="rgba(232,245,238,0.9)",
                    line=dict(color="#B6DAC2", width=1),
                )
                fig.add_annotation(
                    x=0.5, y=1.085, xref="paper", yref="paper",
                    text=summary_text,
                    showarrow=False, align="center",
                    font=dict(size=12, family="Source Sans 3, sans-serif", color="#2E6B45"),
                    bgcolor="rgba(0,0,0,0)",
                    xanchor="center", yanchor="middle",
                )

                fig.update_layout(
                    title=dict(
                        text=f"Field {sel_fld} ({sel_div} · {field_type}) — Predicted Nitrogen Applications Per Year",
                        font=dict(family="Playfair Display, serif", size=17, color="#1F3D2A"),
                        x=0.01,
                    ),
                    xaxis=dict(title="Application Date", tickfont=dict(family="Source Sans 3, sans-serif", size=12), showgrid=False),
                    yaxis=dict(title="Nitrogen (kg / ha)", tickfont=dict(family="Source Sans 3, sans-serif", size=12),
                               gridcolor="#EEE", range=[0, n_per_app_val * 1.55]),
                    plot_bgcolor="#FAFAF8",
                    paper_bgcolor="#FFFFFF",
                    font=dict(family="Source Sans 3, sans-serif", size=13),
                    showlegend=False,
                    height=420,
                    margin=dict(t=130, b=40, l=75, r=30),
                    bargap=0.35,
                )
                st.plotly_chart(fig, use_container_width=True)

            except ImportError:
                try:
                    rows_tbl = []
                    for i in range(n_apps_val):
                        d_off = max(0, int(float(days_until)) if days_until is not None else interval_val) + i * interval_val
                        app_date = date.today() + timedelta(days=d_off)
                        rows_tbl.append({
                            "Application": f"#{i+1}",
                            "Date": app_date.strftime("%d %b %Y"),
                            "N (kg/ha)": n_per_app_val,
                            "N Ratio": n_ratio_display,
                            "Urea — Field Total (kg)": urea_per_app_val,
                        })
                    st.markdown("**Predicted N Applications This Year**")
                    st.dataframe(pd.DataFrame(rows_tbl), hide_index=True, use_container_width=True)
                except Exception:
                    pass
            except Exception:
                pass

st.markdown("<hr class='divider'>", unsafe_allow_html=True)

# Estate-wide schedule
st.markdown("""
<div style="margin-top: 4px;">
  <div class="section-title">Estate Fertilizer Schedule</div>
  <div class="section-sub" style="margin-bottom: 18px;">
    Full predicted schedule for all fields, ordered by urgency.
    Only overdue fields within the last 7 days are shown.
    Fields with adequate nitrogen ratio are excluded.
  </div>
</div>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner=False, ttl=60 * 60 * 3)
def fetch_schedule():
    local_data, _ = load_predicted_schedule()
    if local_data:
        return local_data, None
    return get_fertilizer_schedule()


with st.spinner("Loading schedule…"):
    raw_schedule, sched_error = fetch_schedule()

if sched_error:
    st.error(f"⚠️ Could not load schedule: {sched_error}")
else:
    if isinstance(raw_schedule, list):
        rows = raw_schedule
    elif isinstance(raw_schedule, dict):
        rows = (
            raw_schedule.get("schedule")
            or raw_schedule.get("data")
            or raw_schedule.get("fields")
            or (list(raw_schedule.values())[0] if raw_schedule else [])
        )
    else:
        rows = []

    if not rows:
        st.warning("No schedule data returned.")
    else:
        records = []
        for r in rows:
            if not isinstance(r, dict):
                continue

            days_until_raw = pick(r, "Days_Until_Next", "days_until_next", "days_until", "days_remaining")
            status_raw = str(pick(r, "Schedule_Status", "status", "Status", default=""))
            div_raw = str(pick(r, "Division", "division", default=""))
            fld_raw = str(pick(r, "Field", "field_no", "field", default=""))
            yield_raw = pick(r, "Annual_Yield_kgha", "yield_kgha", "yield_per_ha", default=None)
            n_ratio_raw = pick(r, "N_Ratio_Seas", "n_ratio_seas", default=None)
            extent_raw = pick(r, "Extent_Ha", "extent_ha", "area_ha", default=None)
            amt_raw_r = pick(r, "Pred_Amount_kg", "predicted_amount_kg", "Predicted_Amount_kg",
                                  "total_amount_kg", "amount_kg", default="")
            pred_dose_raw  = pick(r, "Pred_Dose_kgha", "pred_dose_kgha", "dose_kgha", default=None)
            apps_py_raw= pick(r, "apps_per_year", default=None)
            n_per_app_raw  = pick(r, "n_per_app_kgha", default=None)
            cycle_days_raw = pick(r, "Pred_Cycle_Days", "pred_cycle_days", default=None)

            status_raw = status_raw.upper()
            if status_raw == "DUE TODAY":
                status_raw = "DUE SOON"

            try:
                dun = int(float(days_until_raw)) if days_until_raw is not None else None
                if status_raw == "OVERDUE" and dun is not None and dun < -7:
                    continue
            except Exception:
                pass

            ftype = get_field_type(div_raw, fld_raw)
            n_ratio_val = None
            n_ratio_display = "—"
            needs_n = True

            if n_ratio_raw is not None:
                try:
                    n_ratio_val = float(n_ratio_raw)
                    n_ratio_display = f"{n_ratio_val:.2f}"
                    needs_n = n_ratio_val < ratio_threshold(ftype)
                except Exception:
                    pass

            try:
                days_fmt = int(float(days_until_raw)) if days_until_raw is not None else None
            except Exception:
                days_fmt = None

            annual_n = None
            try:
                if apps_py_raw is not None and n_per_app_raw is not None:
                    annual_n = round(int(apps_py_raw) * float(n_per_app_raw), 1)
                elif yield_raw is not None:
                    annual_n = annual_n_target(float(yield_raw), ftype)
            except Exception:
                pass

            apps_per_yr = None
            try:
                if apps_py_raw is not None:
                    apps_per_yr = int(apps_py_raw)
                elif yield_raw is not None:
                    na = annual_n_target(float(yield_raw), ftype)
                    apps_per_yr = MAX_APPLICATIONS_YEAR if ftype == "SD" or na > (ANNUAL_FERT_MIN_KG_HA * UREA_N_FRACTION) else MIN_APPLICATIONS_YEAR
            except Exception:
                pass

            n_needs_flag = "⚠ Apply N" if needs_n else "✓ Adequate"

            records.append({
                "Division": div_raw,
                "Field": fld_raw,
                "Type": ftype,
                "Days Until Next": days_fmt,
                "Predicted Amount (kg)": amt_raw_r,
                "Pred Dose (kg/ha)": pred_dose_raw,
                "N Ratio": n_ratio_display,
                "N Status": n_needs_flag,
                "Status": status_raw,
                "_annual_n_kgha": annual_n,
                "_apps_per_yr": apps_per_yr,
                "_pred_dose": pred_dose_raw,
                "_extent_ha": extent_raw,
                "_needs_n": needs_n,
                "_n_ratio_val": n_ratio_val,
                "_pred_amount_kg": amt_raw_r,
            })

        if not records:
            st.warning("No fields to display.")
        else:
            schedule_df = pd.DataFrame(records)
            schedule_df["Days Until Next"]       = pd.to_numeric(schedule_df["Days Until Next"], errors="coerce")
            schedule_df["Predicted Amount (kg)"] = pd.to_numeric(schedule_df["Predicted Amount (kg)"], errors="coerce")
            schedule_df["_annual_n_kgha"]        = pd.to_numeric(schedule_df["_annual_n_kgha"], errors="coerce")
            schedule_df["_apps_per_yr"]          = pd.to_numeric(schedule_df["_apps_per_yr"], errors="coerce")
            schedule_df["_n_ratio_val"]          = pd.to_numeric(schedule_df["_n_ratio_val"], errors="coerce")
            schedule_df["_pred_amount_kg"]       = pd.to_numeric(schedule_df["_pred_amount_kg"], errors="coerce")

            try:
                schedule_df["Next Date"] = schedule_df["Days Until Next"].apply(
                    lambda d: (date.today() + timedelta(days=int(d))).strftime("%d %b %Y") if pd.notna(d) else "—"
                )
            except Exception:
                schedule_df["Next Date"] = "—"

            n_overdue  = (schedule_df["Status"] == "OVERDUE").sum()
            n_due_soon = (schedule_df["Status"] == "DUE SOON").sum()
            n_upcoming = (schedule_df["Status"] == "UPCOMING").sum()
            n_need_n   = schedule_df["_needs_n"].sum()

            st.markdown(f"""
<div style="display:flex;gap:12px;margin:14px 0 18px 0;flex-wrap:wrap;justify-content:center;align-items:center;">
  <div class="interactive-box" style="background:#fde8e8;border:1px solid #f1b8b4;border-radius:10px;padding:10px 20px;text-align:center;cursor:default;">
    <div style="font-size:22px;font-weight:700;color:#C0392B;font-family:'Playfair Display',serif;">{n_overdue}</div>
    <div style="font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#C0392B;font-family:'Source Sans 3',sans-serif;margin-top:3px;">Overdue</div>
  </div>
  <div class="interactive-box" style="background:#fef3e2;border:1px solid #f5d9a8;border-radius:10px;padding:10px 20px;text-align:center;cursor:default;">
    <div style="font-size:22px;font-weight:700;color:#C8923A;font-family:'Playfair Display',serif;">{n_due_soon}</div>
    <div style="font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#C8923A;font-family:'Source Sans 3',sans-serif;margin-top:3px;">Due Soon</div>
  </div>
  <div class="interactive-box" style="background:#e8f5ee;border:1px solid #B6DAC2;border-radius:10px;padding:10px 20px;text-align:center;cursor:default;">
    <div style="font-size:22px;font-weight:700;color:#2E6B45;font-family:'Playfair Display',serif;">{n_upcoming}</div>
    <div style="font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#2E6B45;font-family:'Source Sans 3',sans-serif;margin-top:3px;">Upcoming</div>
  </div>
  <div class="interactive-box" style="background:#F0EDE7;border:1px solid #D9D4CC;border-radius:10px;padding:10px 20px;text-align:center;cursor:default;">
    <div style="font-size:22px;font-weight:700;color:#1F3D2A;font-family:'Playfair Display',serif;">{len(schedule_df)}</div>
    <div style="font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#6B7F6F;font-family:'Source Sans 3',sans-serif;margin-top:3px;">Total Fields</div>
  </div>
  <div class="interactive-box" style="background:#fff3e0;border:1px solid #ffc870;border-radius:10px;padding:10px 20px;text-align:center;cursor:default;">
    <div style="font-size:22px;font-weight:700;color:#C8923A;font-family:'Playfair Display',serif;">{n_need_n}</div>
    <div style="font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#C8923A;font-family:'Source Sans 3',sans-serif;margin-top:3px;">Need N</div>
  </div>
</div>
""", unsafe_allow_html=True)

            #state chart: predicted nitrogen amount + applications per year
            st.markdown("<div class='chart-section-gap'></div>", unsafe_allow_html=True)

            st.markdown("""
<div style="margin-bottom:12px;">
  <div class="section-title" style="font-size:18px;">Predicted Nitrogen Amount and Applications per Field</div>
  <div class="section-sub">
    Bar chart shows annual predicted nitrogen requirement (kg N/ha) for each field.
    The red dotted line shows the expected number of fertilizer applications per year.
  </div>
</div>
""", unsafe_allow_html=True)

            try:
                import plotly.graph_objects as go_chart

                chart_src = schedule_df.dropna(subset=["_annual_n_kgha"]).copy()
                chart_src = chart_src.sort_values(["Division", "_annual_n_kgha"], ascending=[True, False]).reset_index(drop=True)
                chart_src["Field_Label"] = chart_src["Division"] + " · " + chart_src["Field"]

                div_palette = {
                    "AGO": "#2E6B45",
                    "LDK": "#5BA870",
                    "LVO": "#87C99A",
                    "UDK": "#C8923A",
                    "UVO": "#5C99B8",
                }
                bar_colors = [div_palette.get(d, "#5BA870") for d in chart_src["Division"]]

                fig_estate = go_chart.Figure()

                fig_estate.add_trace(go_chart.Bar(
                    x=chart_src["Field_Label"],
                    y=chart_src["_annual_n_kgha"],
                    name="Predicted N (kg/ha/year)",
                    marker_color=bar_colors,
                    marker_line_color="white",
                    marker_line_width=1,
                    customdata=list(zip(
                        chart_src["N Ratio"].tolist(),
                        chart_src["N Status"].tolist(),
                        chart_src["Status"].tolist(),
                        chart_src["Predicted Amount (kg)"].fillna(0).tolist(),
                    )),
                    hovertemplate=(
                        "<b>%{x}</b><br>"
                        "Annual Nitrogen: <b>%{y:.1f} kg N/ha</b><br>"
                        "N Ratio: <b>%{customdata[0]}</b><br>"
                        "N Status: <b>%{customdata[1]}</b><br>"
                        "Schedule Status: <b>%{customdata[2]}</b><br>"
                        "Predicted Amount: <b>%{customdata[3]:.0f} kg</b><br>"
                        "<extra></extra>"
                    ),
                ))

                if chart_src["_apps_per_yr"].notna().any():
                    fig_estate.add_trace(go_chart.Scatter(
                        x=chart_src["Field_Label"],
                        y=chart_src["_apps_per_yr"],
                        name="Applications / Year",
                        mode="lines+markers",
                        line=dict(color="#C0392B", width=2, dash="dot"),
                        marker=dict(size=7, color="#C0392B", symbol="circle"),
                        yaxis="y2",
                        hovertemplate=(
                            "<b>%{x}</b><br>"
                            "Applications / year: <b>%{y}</b><br>"
                            "<extra></extra>"
                        ),
                    ))

                for div, col in div_palette.items():
                    if div in chart_src["Division"].values:
                        fig_estate.add_trace(go_chart.Bar(
                            x=[None], y=[None],
                            name=f"{div} — {DIVISION_LABELS.get(div, div)}",
                            marker_color=col,
                            showlegend=True,
                            yaxis="y1",
                        ))

                fig_estate.update_layout(
                    title=dict(
                        text="Predicted Nitrogen Amount & Applications per Year — Estate Overview",
                        font=dict(family="Playfair Display, serif", size=16, color="#1F3D2A"),
                        x=0.01,
                    ),
                    xaxis=dict(
                        title="Field",
                        tickfont=dict(family="Source Sans 3, sans-serif", size=10),
                        tickangle=-50,
                        showgrid=False,
                    ),
                    yaxis=dict(
                        title="Annual Nitrogen (kg N/ha)",
                        tickfont=dict(family="Source Sans 3, sans-serif", size=12),
                        gridcolor="#EEE",
                        side="left",
                    ),
                    yaxis2=dict(
                        title="Applications / Year",
                        tickfont=dict(family="Source Sans 3, sans-serif", size=12),
                        overlaying="y",
                        side="right",
                        showgrid=False,
                        range=[0, 6],
                        dtick=1,
                    ),
                    plot_bgcolor="#FAFAF8",
                    paper_bgcolor="#FFFFFF",
                    font=dict(family="Source Sans 3, sans-serif", size=12),
                    legend=dict(
                        orientation="h",
                        yanchor="bottom", y=1.02,
                        xanchor="left", x=0,
                        font=dict(size=11),
                        itemsizing="constant",
                        itemwidth=40,
                        tracegroupgap=8,
                    ),
                    barmode="overlay",
                    bargap=0.28,
                    height=500,
                    margin=dict(t=100, b=130, l=75, r=75),
                )

                st.plotly_chart(fig_estate, use_container_width=True)

            except ImportError:
                pass
            except Exception:
                pass

            st.markdown("<div class='chart-section-gap'></div>", unsafe_allow_html=True)

            status_filter = st.selectbox(
                "Filter by status",
                ["All", "OVERDUE", "DUE SOON", "UPCOMING"],
                key="sched_filter",
            )
            display_df = (
                schedule_df[schedule_df["Status"] == status_filter].reset_index(drop=True)
                if status_filter != "All" else schedule_df.copy()
            )

            table_df = display_df.drop(
                columns=["_annual_n_kgha", "_apps_per_yr", "_pred_dose", "_extent_ha",
                         "_needs_n", "_n_ratio_val", "_pred_amount_kg"],
                errors="ignore"
            ).copy()

            def style_status(val):
                if val == "OVERDUE":
                    return "background-color:#fde8e8;color:#C0392B;font-weight:700;"
                elif val == "DUE SOON":
                    return "background-color:#fef3e2;color:#C8923A;font-weight:700;"
                elif val == "UPCOMING":
                    return "background-color:#e8f5ee;color:#2E6B45;font-weight:700;"
                return ""

            def style_days(val):
                try:
                    v = int(float(val))
                    if v < 0:
                        return "color:#C0392B;font-weight:700;"
                    if v <= 14:
                        return "color:#C8923A;font-weight:700;"
                    if v <= 90:
                        return "color:#2E6B45;"
                except Exception:
                    pass
                return ""

            def style_ratio(val):
                try:
                    v = float(val)
                    if v < SD_RATIO_THRESHOLD:
                        return "color:#C0392B;font-weight:700;"
                    if v < VP_RATIO_THRESHOLD:
                        return "color:#C8923A;font-weight:700;"
                    return "color:#2E6B45;"
                except Exception:
                    return ""

            def style_n_status(val):
                if "Apply" in str(val):
                    return "color:#C0392B;font-weight:700;"
                return "color:#2E6B45;font-weight:600;"

            table_df["Division"] = table_df["Division"].map(lambda d: f"{d} — {DIVISION_LABELS.get(d, d)}")

            styled_cols = {
                "Predicted Amount (kg)": lambda v: f"{v:.0f}" if pd.notna(v) else "—",
                "Days Until Next": lambda v: f"{int(v):+d}" if pd.notna(v) else "—",
            }
            if "Pred Dose (kg/ha)" in table_df.columns:
                styled_cols["Pred Dose (kg/ha)"] = lambda v: f"{v:.2f}" if pd.notna(v) and v else "—"

            style_obj = (
                table_df.style
                .applymap(style_status, subset=["Status"])
                .applymap(style_days, subset=["Days Until Next"])
                .applymap(style_ratio, subset=["N Ratio"])
                .applymap(style_n_status, subset=["N Status"])
                .format(styled_cols)
                .set_properties(**{
                    "font-family": "Source Sans 3, sans-serif",
                    "font-size": "13px",
                })
            )

            st.dataframe(style_obj, use_container_width=True, hide_index=True, height=460)
            st.markdown("<div style='height: 48px;'></div>", unsafe_allow_html=True)

            n_annual_vp_min = ANNUAL_FERT_MIN_KG_HA * UREA_N_FRACTION
            n_annual_vp_max = ANNUAL_FERT_MAX_KG_HA * UREA_N_FRACTION
            n_budget_html = f"""
<div class="n-budget-box interactive-box">
  <div class="n-budget-title">
    Estate Nitrogen Budget Summary
  </div>

  <div class="n-budget-grid">
    <div class="n-rule-card">
      <div class="n-rule-label">VP Field Rule</div>
      <div class="n-rule-value">N Ratio &lt; {VP_RATIO_THRESHOLD}</div>
      <div class="n-rule-sub">Apply when seasonal N ratio falls below {VP_RATIO_THRESHOLD} for Vegetatively Propagated fields</div>
    </div>
    <div class="n-rule-card">
      <div class="n-rule-label">SD Field Rule</div>
      <div class="n-rule-value">N Ratio &lt; {SD_RATIO_THRESHOLD}</div>
      <div class="n-rule-sub">Apply when seasonal N ratio falls below {SD_RATIO_THRESHOLD} for Seedling fields</div>
    </div>
    <div class="n-rule-card">
      <div class="n-rule-label">VP Annual N Target</div>
      <div class="n-rule-value">{n_annual_vp_min:.0f}–{n_annual_vp_max:.0f} kg/ha</div>
      <div class="n-rule-sub">Yield ÷ 100 clamped to range. Urea = N ÷ 0.46 (46% nitrogen)</div>
    </div>
    <div class="n-rule-card">
      <div class="n-rule-label">SD Annual N Target</div>
      <div class="n-rule-value">{TARGET_N_SD_KG_HA} kg N/ha</div>
      <div class="n-rule-sub">Fixed rate for all Seedling fields, applied across {MAX_APPLICATIONS_YEAR} rounds</div>
    </div>
  </div>

  <div class="n-rule-row">
    <div class="n-inline-badge">VP: {MIN_APPLICATIONS_YEAR}–{MAX_APPLICATIONS_YEAR} applications/year</div>
    <div class="n-inline-badge">SD: Always {MAX_APPLICATIONS_YEAR} applications/year</div>
    <div class="n-inline-badge">Urea range: {ANNUAL_FERT_MIN_KG_HA}–{ANNUAL_FERT_MAX_KG_HA} kg/ha/year</div>
    <div class="n-inline-badge">Urea = N ÷ 0.46</div>
    <div class="n-inline-badge">N replacement: 1 kg N per 100 kg tea</div>
  </div>
</div>
"""
            st.markdown(n_budget_html, unsafe_allow_html=True)

st.markdown("<div style='height: 80px;'></div>", unsafe_allow_html=True)
render_footer()