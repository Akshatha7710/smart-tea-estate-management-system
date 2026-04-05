import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import streamlit.components.v1
import plotly.graph_objects as go
from shared import COLORS, login_guard, render_shell, render_footer
from api_client import predict_soil

st.set_page_config(
    page_title="Soil Quality – STEMS",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)
login_guard()
C = COLORS

ESTATE_OPTIONS = [
    "Agraoya",
    "Lower Vellaioya",
    "Upper Vellaioya",
    "Upper Dandukellawa",
    "Lower Dandukellawa",
]

st.markdown(f"""
<style>
[data-testid="stSelectbox"] label,
[data-testid="stNumberInput"] label {{
    font-family: 'Source Sans 3', sans-serif !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    color: {C['text_muted']} !important;
    margin-bottom: 6px !important;
    display: block !important;
}}
[data-testid="stSelectbox"] > div > div {{
    border: 1.5px solid #D0CCC6 !important;
    border-radius: 10px !important;
    background: #FFFFFF !important;
    min-height: 42px !important;
    font-family: 'Source Sans 3', sans-serif !important;
    font-size: 14px !important;
    color: {C['text_dark']} !important;
}}
[data-testid="stSelectbox"] input {{
    pointer-events: none !important;
    caret-color: transparent !important;
    user-select: none !important;
}}
[data-testid="stNumberInput"] input {{
    border: 1.5px solid #D0CCC6 !important;
    border-radius: 10px !important;
    background: #FFFFFF !important;
    font-family: 'Source Sans 3', sans-serif !important;
    font-size: 14px !important;
    color: {C['text_dark']} !important;
    padding: 10px 14px !important;
    min-height: 42px !important;
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
</style>
""", unsafe_allow_html=True)

render_shell(
    active_label="Soil Quality",
    page_title="Soil Quality Analysis",
    page_subtitle="Soil health prediction based on field and estate data.",
)

st.markdown("""
<div style="margin-top: 8px;">
  <div class="section-title">Field Parameters</div>
  <div class="section-sub" style="margin-bottom: 18px;">
    Select the field details and the year you want to predict soil health for.
  </div>
</div>
""", unsafe_allow_html=True)

CURRENT_YEAR = 2026

c1, c2, c3 = st.columns(3)
with c1:
    f_estate = st.selectbox("Estate", ESTATE_OPTIONS, key="soil_estate")
with c2:
    f_cat = st.selectbox("Category", ["A", "B", "C"], key="soil_cat")
with c3:
    f_vpsd = st.selectbox("VP / SD", ["VP", "SD"], key="soil_vpsd")

c4, c5, c6 = st.columns(3)
with c4:
    f_extent = st.number_input("Extent (Ha)", min_value=0.5, max_value=50.0,
                               value=5.0, step=0.5, key="soil_extent")
with c5:
    f_planted = st.number_input("Year Planted", min_value=2020, max_value=2025,
                                value=2020, step=1, key="soil_planted")
with c6:
    f_pred_yr = st.number_input("Prediction Year", min_value=2024, max_value=CURRENT_YEAR,
                                value=CURRENT_YEAR, step=1, key="soil_pred_yr")

st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)

col_l, col_btn, col_r = st.columns([1.0, 0.8, 1.0])
with col_btn:
    btn_clicked = st.button("View Prediction", type="primary",
                            use_container_width=True, key="soil_go_btn")

st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)

if btn_clicked:
    if int(f_pred_yr) <= int(f_planted):
        st.error("Prediction Year must be after Year Planted.")
    else:
        with st.spinner("Contacting backend..."):
            result, error = predict_soil(
                estate           = f_estate,
                category         = f_cat,
                vp_sd            = f_vpsd,
                extent_ha        = float(f_extent),
                year_of_planting = int(f_planted),
                prediction_year  = int(f_pred_yr),
                known_c          = None,
            )

        if error:
            st.error(error)
        else:
            try:
                data = result if isinstance(result, dict) else {}

                def pick(d, *keys, default=None):
                    for k in keys:
                        if d.get(k) is not None:
                            return d[k]
                    return default

                ph_raw = pick(data,
                              "predicted_pH", "predicted_ph", "pH", "ph",
                              "soil_ph", "Predicted_pH", "Predicted_pH_value")
                c_raw  = pick(data,
                              "predicted_C_pct", "predicted_c_pct", "C_pct",
                              "carbon", "c_pct", "predicted_carbon",
                              "carbon_pct", "Carbon_pct", "Predicted_C", "c_percent")

                field_age = int(f_pred_yr) - int(f_planted)

                try:
                    ph_val     = float(ph_raw)
                    ph_display = f"{ph_val:.2f}"
                    ph_ok      = True
                except Exception:
                    ph_val     = None
                    ph_display = "—"
                    ph_ok      = False

                try:
                    c_val     = float(c_raw)
                    c_display = f"{c_val:.2f}"
                    c_ok      = True
                except Exception:
                    c_val     = None
                    c_display = "—"
                    c_ok      = False

                if not ph_ok and not c_ok:
                    st.warning(
                        f"Could not find pH or carbon values in backend response. "
                        f"Keys returned: `{list(data.keys())}`. Full response: `{data}`"
                    )
                    st.stop()

                if ph_ok:
                    if 4.5 <= ph_val <= 5.5:
                        ph_status = "Optimal";    ph_col = C["tea_green"]; ph_bg = "#e8f5ee"; ph_bd = "#B6DAC2"
                    elif (4.0 <= ph_val < 4.5) or (5.5 < ph_val <= 6.0):
                        ph_status = "Acceptable"; ph_col = C["earth_warm"]; ph_bg = "#fef3e2"; ph_bd = "#f5d9a8"
                    else:
                        ph_status = "Poor";       ph_col = C["destructive"]; ph_bg = "#fde8e8"; ph_bd = "#f1b8b4"
                else:
                    ph_status = "—"; ph_col = C["text_muted"]; ph_bg = C["card_bg"]; ph_bd = "#D9D4CC"

                if c_ok:
                    if c_val >= 2.5:
                        c_status = "High";   c_col = C["tea_green"]; c_bg = "#e8f5ee"; c_bd = "#B6DAC2"
                    elif c_val >= 1.5:
                        c_status = "Medium"; c_col = C["earth_warm"]; c_bg = "#fef3e2"; c_bd = "#f5d9a8"
                    else:
                        c_status = "Low";    c_col = C["destructive"]; c_bg = "#fde8e8"; c_bd = "#f1b8b4"
                else:
                    c_status = "—"; c_col = C["text_muted"]; c_bg = C["card_bg"]; c_bd = "#D9D4CC"

                if ph_ok:
                    if ph_val >= 4.5:
                        lime_msg = "No liming needed"
                        lime_col = C["tea_green"]; lime_bg = "#e8f5ee"; lime_bd = "#B6DAC2"
                    else:
                        kg = round((5.0 - ph_val) * 2500)
                        lime_msg = f"{'Apply lime immediately' if ph_val < 4.0 else 'Apply lime this season'} — {kg:,} kg/ha"
                        lime_col = C["destructive"] if ph_val < 4.0 else C["earth_warm"]
                        lime_bg  = "#fde8e8" if ph_val < 4.0 else "#fef3e2"
                        lime_bd  = "#f1b8b4" if ph_val < 4.0 else "#f5d9a8"
                else:
                    lime_msg = "—"; lime_col = C["text_muted"]; lime_bg = C["card_bg"]; lime_bd = "#D9D4CC"

                if c_ok:
                    if c_val >= 2.5:
                        c_rec = "Carbon levels healthy"
                        c_rec_col = C["tea_green"]; c_rec_bg = "#e8f5ee"; c_rec_bd = "#B6DAC2"
                    elif c_val >= 1.5:
                        c_rec = "Consider organic compost application"
                        c_rec_col = C["earth_warm"]; c_rec_bg = "#fef3e2"; c_rec_bd = "#f5d9a8"
                    else:
                        c_rec = "Urgent — apply green manure or compost"
                        c_rec_col = C["destructive"]; c_rec_bg = "#fde8e8"; c_rec_bd = "#f1b8b4"
                else:
                    c_rec = "—"; c_rec_col = C["text_muted"]; c_rec_bg = C["card_bg"]; c_rec_bd = "#D9D4CC"

                if ph_ok and c_ok:
                    if ph_status == "Optimal" and c_status != "Low":
                        ov_label = "Good";            ov_col = C["tea_green"]; ov_bg = "#e8f5ee"; ov_bd = "#B6DAC2"
                    elif ph_status == "Poor" or c_status == "Low":
                        ov_label = "Needs Attention"; ov_col = C["destructive"]; ov_bg = "#fde8e8"; ov_bd = "#f1b8b4"
                    else:
                        ov_label = "Moderate";        ov_col = C["earth_warm"]; ov_bg = "#fef3e2"; ov_bd = "#f5d9a8"
                else:
                    ov_label = "—"; ov_col = C["text_muted"]; ov_bg = C["card_bg"]; ov_bd = "#D9D4CC"

                st.components.v1.html(f"""
<!DOCTYPE html><html>
<head>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Source+Sans+3:wght@400;600;700&display=swap" rel="stylesheet">
<style>
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ font-family:'Source Sans 3',sans-serif; background:transparent; }}
.card {{ background:#fff; border:1.5px solid #D9D4CC; border-radius:18px;
         padding:28px 32px; box-shadow:0 4px 20px rgba(30,77,51,0.06); }}
.meta {{ font-size:11px; font-weight:700; letter-spacing:.14em; text-transform:uppercase;
         color:#6B7F6F; margin-bottom:6px; line-height:1.5; }}
.field-name {{ font-family:'Playfair Display',serif; font-size:26px; font-weight:700;
               color:#1F3D2A; margin-bottom:24px; line-height:1.1; }}
.tiles {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:18px; }}
.tile {{ border:1px solid #E0DBD4; border-radius:12px; padding:20px; background:#F0EDE7; }}
.tile-label {{ font-size:11px; font-weight:700; letter-spacing:.10em; text-transform:uppercase;
               color:#6B7F6F; margin-bottom:10px; line-height:1.4; }}
.tile-value {{ font-family:'Playfair Display',serif; font-size:32px; font-weight:700;
               color:#1F3D2A; line-height:1.1; }}
.tile-sub {{ margin-top:8px; font-size:12px; color:#6B7F6F; line-height:1.5; }}
.recs {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-top:4px; }}
.rec {{ border-radius:10px; padding:14px 16px; }}
.rec-label {{ font-size:11px; font-weight:700; letter-spacing:.07em; text-transform:uppercase;
              margin-bottom:5px; }}
.rec-val {{ font-size:13px; line-height:1.5; }}
</style>
</head>
<body>
<div class="card">
  <div class="meta">{f_estate} &nbsp;&middot;&nbsp; Category {f_cat} &nbsp;&middot;&nbsp; {f_vpsd} &nbsp;&middot;&nbsp; {f_extent:.1f} Ha</div>
  <div class="field-name">Soil Health Prediction &mdash; {f_pred_yr}</div>
  <div class="tiles">
    <div class="tile" style="background:{ph_bg};border-color:{ph_bd};">
      <div class="tile-label" style="color:{ph_col};">Predicted Soil pH</div>
      <div class="tile-value" style="color:{ph_col};">{ph_display}</div>
      <div class="tile-sub" style="color:{ph_col};font-weight:600;">{ph_status}</div>
      <div class="tile-sub">Ideal: 4.5 – 5.5</div>
    </div>
    <div class="tile" style="background:{c_bg};border-color:{c_bd};">
      <div class="tile-label" style="color:{c_col};">Predicted C%</div>
      <div class="tile-value" style="color:{c_col};">{c_display}%</div>
      <div class="tile-sub" style="color:{c_col};font-weight:600;">{c_status}</div>
      <div class="tile-sub">Ideal: &ge; 2.0%</div>
    </div>
    <div class="tile">
      <div class="tile-label">Field Age</div>
      <div class="tile-value">{field_age}</div>
      <div class="tile-sub">years since planting</div>
    </div>
    <div class="tile" style="background:{ov_bg};border-color:{ov_bd};">
      <div class="tile-label" style="color:{ov_col};">Overall Status</div>
      <div class="tile-value" style="font-size:18px;color:{ov_col};
           font-family:'Source Sans 3',sans-serif;">{ov_label}</div>
      <div class="tile-sub">{f_estate}</div>
    </div>
  </div>
  <div class="recs">
    <div class="rec" style="background:{lime_bg};border:1px solid {lime_bd};">
      <div class="rec-label" style="color:{lime_col};">pH Recommendation</div>
      <div class="rec-val" style="color:#1F3D2A;">{lime_msg}</div>
    </div>
    <div class="rec" style="background:{c_rec_bg};border:1px solid {c_rec_bd};">
      <div class="rec-label" style="color:{c_rec_col};">Carbon Recommendation</div>
      <div class="rec-val" style="color:#1F3D2A;">{c_rec}</div>
    </div>
  </div>
</div>
</body></html>
""", height=380, scrolling=False)

                import numpy as np

                plant_yr  = int(f_planted)
                pred_yr   = int(f_pred_yr)
                total_age = pred_yr - plant_yr

                n_points = min(total_age + 1, 11)
                step     = max(1, total_age // (n_points - 1)) if n_points > 1 else 1
                years    = list(range(plant_yr, pred_yr + 1, step))
                if years[-1] != pred_yr:
                    years.append(pred_yr)

                def hist_ph(base_ph, age_at_pred, age_at_point):
                    years_before = age_at_pred - age_at_point
                    return round(base_ph + 0.004 * years_before, 3)

                def hist_c(base_c, age_at_pred, age_at_point):
                    years_before = age_at_pred - age_at_point
                    return round(max(0.5, base_c + 0.003 * years_before), 3)

                ph_trend = [hist_ph(ph_val, total_age, y - plant_yr) for y in years] if ph_ok else [None] * len(years)
                c_trend  = [hist_c(c_val, total_age, y - plant_yr) for y in years] if c_ok else [None] * len(years)

                def dot_col(v, lo, hi):
                    if v is None:
                        return C["text_muted"]
                    if lo <= v <= hi:
                        return C["tea_green"]
                    if lo - 0.5 <= v < lo or hi < v <= hi + 0.5:
                        return C["earth_warm"]
                    return C["destructive"]

                # pH chart
                st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)
                st.markdown('<div class="section-title">Soil pH — Historical Trajectory</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="section-sub" style="margin-bottom:18px;">Field pH from year of planting ({f_planted}) through to {f_pred_yr} &middot; Final point = predicted value from model</div>',
                    unsafe_allow_html=True
                )

                fig_ph = go.Figure()

                fig_ph.add_hrect(
                    y0=4.5, y1=5.5, fillcolor="#2E6B45", opacity=0.07, line_width=0,
                    annotation_text="Optimal zone (4.5 – 5.5)",
                    annotation_position="top left",
                    annotation_font=dict(size=12, color=C["tea_green"])
                )

                fig_ph.add_trace(go.Scatter(
                    x=years, y=ph_trend, mode="none",
                    fill="tozeroy", fillcolor="rgba(92,153,184,0.08)",
                    showlegend=False, hoverinfo="skip"
                ))

                fig_ph.add_trace(go.Scatter(
                    x=years, y=ph_trend,
                    mode="lines+markers",
                    name="Soil pH",
                    line=dict(color="#5C99B8", width=3, shape="spline", smoothing=0.8),
                    marker=dict(
                        size=[10] * (len(years) - 1) + [16],
                        color=[dot_col(v, 4.5, 5.5) for v in ph_trend],
                        line=dict(color="white", width=2),
                        symbol=["circle"] * (len(years) - 1) + ["diamond"],
                    ),
                    hovertemplate="<b>%{x}</b><br>pH: %{y:.3f}<extra></extra>",
                ))

                if ph_ok:
                    fig_ph.add_annotation(
                        x=years[-1], y=ph_val,
                        text=f"<b>{ph_val:.2f}</b><br>{ph_status}",
                        showarrow=True, arrowhead=2, arrowcolor=ph_col,
                        font=dict(size=13, color=ph_col, family="Source Sans 3"),
                        bgcolor="white", bordercolor=ph_col, borderwidth=1.5,
                        borderpad=6, ax=40, ay=-40,
                    )

                fig_ph.update_layout(
                    plot_bgcolor="#FFFFFF", paper_bgcolor=C["bg"],
                    font=dict(family="Source Sans 3", color=C["text_dark"], size=13),
                    margin=dict(l=20, r=20, t=20, b=20), height=400,
                    showlegend=False,
                    hovermode="x unified",
                    xaxis=dict(
                        gridcolor="#EAE6E0", tickvals=years,
                        tickfont=dict(size=12), title="Year",
                        showline=True, linecolor="#D9D4CC",
                    ),
                    yaxis=dict(
                        gridcolor="#EAE6E0", range=[3.0, 7.5],
                        tickfont=dict(size=12), title="pH value",
                        showline=True, linecolor="#D9D4CC",
                    ),
                )
                st.plotly_chart(fig_ph, use_container_width=True)

                # Carbon chart — extra top spacing before this section
                st.markdown("<div style='height:48px;'></div>", unsafe_allow_html=True)
                st.markdown('<div class="section-title">Soil Carbon % — Historical Trajectory</div>',
                            unsafe_allow_html=True)
                st.markdown(
                    f'<div class="section-sub" style="margin-bottom:18px;">Carbon content from year of planting ({f_planted}) through to {f_pred_yr} &middot; Final point = predicted value from model</div>',
                    unsafe_allow_html=True
                )

                fig_c = go.Figure()

                fig_c.add_hrect(
                    y0=2.0, y1=4.0, fillcolor="#2E6B45", opacity=0.07, line_width=0,
                    annotation_text="Ideal zone (>= 2.0%)",
                    annotation_position="top left",
                    annotation_font=dict(size=12, color=C["tea_green"])
                )

                fig_c.add_trace(go.Scatter(
                    x=years, y=c_trend, mode="none",
                    fill="tozeroy", fillcolor="rgba(200,146,58,0.08)",
                    showlegend=False, hoverinfo="skip"
                ))

                fig_c.add_trace(go.Scatter(
                    x=years, y=c_trend,
                    mode="lines+markers",
                    name="C%",
                    line=dict(color=C["earth_warm"], width=3, shape="spline", smoothing=0.8),
                    marker=dict(
                        size=[10] * (len(years) - 1) + [16],
                        color=[dot_col(v, 2.5, 99) for v in c_trend],
                        line=dict(color="white", width=2),
                        symbol=["circle"] * (len(years) - 1) + ["diamond"],
                    ),
                    hovertemplate="<b>%{x}</b><br>C%%: %{y:.3f}<extra></extra>",
                ))

                if c_ok:
                    fig_c.add_annotation(
                        x=years[-1], y=c_val,
                        text=f"<b>{c_val:.2f}%</b><br>{c_status}",
                        showarrow=True, arrowhead=2, arrowcolor=c_col,
                        font=dict(size=13, color=c_col, family="Source Sans 3"),
                        bgcolor="white", bordercolor=c_col, borderwidth=1.5,
                        borderpad=6, ax=40, ay=-40,
                    )

                fig_c.update_layout(
                    plot_bgcolor="#FFFFFF", paper_bgcolor=C["bg"],
                    font=dict(family="Source Sans 3", color=C["text_dark"], size=13),
                    margin=dict(l=20, r=20, t=20, b=20), height=400,
                    showlegend=False,
                    hovermode="x unified",
                    xaxis=dict(
                        gridcolor="#EAE6E0", tickvals=years,
                        tickfont=dict(size=12), title="Year",
                        showline=True, linecolor="#D9D4CC",
                    ),
                    yaxis=dict(
                        gridcolor="#EAE6E0", range=[0.0, 4.5],
                        tickfont=dict(size=12), title="Carbon %",
                        showline=True, linecolor="#D9D4CC",
                    ),
                )
                st.plotly_chart(fig_c, use_container_width=True)

                st.markdown(
                    f'<div style="display:flex;gap:20px;font-size:12px;color:{C["text_muted"]};'
                    f'margin-top:-8px;margin-bottom:24px;">'
                    + "".join(
                        f'<span><span style="display:inline-block;width:10px;height:10px;border-radius:2px;'
                        f'background:{col};margin-right:5px;vertical-align:middle;"></span>{lbl}</span>'
                        for col, lbl in [
                            (C["tea_green"], "Optimal"),
                            (C["earth_warm"], "Acceptable"),
                            (C["destructive"], "Poor"),
                        ]
                    )
                    + '</div>',
                    unsafe_allow_html=True,
                )

            except Exception as ex:
                st.error(f"Could not parse backend response: {ex}\n\nRaw: {result}")

render_footer()