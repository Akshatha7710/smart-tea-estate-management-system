import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import date
from pathlib import Path
from shared import COLORS, login_guard, render_shell, render_footer
from api_client import predict_productivity

st.set_page_config(
    page_title="Production Analytics – STEMS",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
login_guard()
C = COLORS

#Month helpers
MONTH_NAMES = [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
]
MONTH_SHORT = [
    "Jan","Feb","Mar","Apr","May","Jun",
    "Jul","Aug","Sep","Oct","Nov","Dec"
]

#Derive current and next month from today
_today      = date.today()
CUR_YEAR    = _today.year
CUR_MONTH_N = _today.month
CUR_MONTH   = MONTH_NAMES[CUR_MONTH_N - 1]

_next_m    = CUR_MONTH_N % 12 + 1
_next_y    = CUR_YEAR + (1 if CUR_MONTH_N == 12 else 0)
NEXT_MONTH = MONTH_NAMES[_next_m - 1]
NEXT_YEAR  = _next_y

#Load actual yield history from the dataset CSV
_HERE = Path(__file__).resolve().parent

def _find_csv():
    candidates = [
        _HERE.parent / "datasets" / "ProductionForecastingDataset.csv"
    ]
    for p in candidates:
        if p.exists():
            return p
    return None

@st.cache_data(show_spinner=False, ttl=300)
def load_yield_history() -> dict:

    #Returns dict  {  'YYYY-MM' : yield_kg  }
    #Only rows where yield is not NaN are included.

    csv_path = _find_csv()
    if csv_path is None:
        return {}
    try:
        df = pd.read_csv(csv_path)
        result = {}
        for _, row in df.iterrows():
            if pd.notna(row.get("yield")):
                m_name = str(row["month"]).strip()
                if m_name in MONTH_NAMES:
                    m_num = MONTH_NAMES.index(m_name) + 1
                    key   = f"{int(row['year'])}-{m_num:02d}"
                    result[key] = float(row["yield"])
        return result
    except Exception:
        return {}

_YIELDS = load_yield_history()


# RMSE from notebook — used as confidence interval half-width
RMSE_INTERVAL = 6143.22


#Helpers
def ym_key(year: int, month_name: str) -> str:
    return f"{year}-{MONTH_NAMES.index(month_name) + 1:02d}"


def build_trailing_24(sel_year: int, sel_month: str):
    """
    Returns (x_labels, y_values) for the 24 months ENDING at (and including)
    the month BEFORE sel_year/sel_month — i.e. the historical window the user
    sees before clicking Predict.
    Only months with actual yield data are plotted (None values are skipped).
    """
    sel_m = MONTH_NAMES.index(sel_month) + 1
    pairs = []
    y, m  = sel_year, sel_m
    for _ in range(24):
        m -= 1
        if m == 0:
            m, y = 12, y - 1
        pairs.append((y, m))
    pairs.reverse()

    x  = [f"{MONTH_SHORT[m-1]} '{str(yr)[2:]}" for yr, m in pairs]
    ys = [_YIELDS.get(f"{yr}-{m:02d}") for yr, m in pairs]
    return x, ys


def prior_year_yield(sel_year: int, sel_month: str):
    return _YIELDS.get(ym_key(sel_year - 1, sel_month))


def same_month_all_years(sel_year: int, sel_month: str):
    #Return {year: yield_kg} for sel_month across all years in the dataset.
    m_num = MONTH_NAMES.index(sel_month) + 1
    result = {}
    for key, val in _YIELDS.items():
        yr_str, m_str = key.split("-")
        if int(m_str) == m_num:
            result[int(yr_str)] = val
    return result



# PAGE-LEVEL CSS
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Source+Sans+3:wght@400;600;700&display=swap');

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
    background: {C['tea_green']} !important;
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
[data-testid="stButton"] > button:not([kind="primary"]) {{
    border-radius: 10px !important;
    font-family: 'Source Sans 3', sans-serif !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    min-height: 52px !important;
    transition: all .15s !important;
}}
.section-title {{
    font-family: 'Playfair Display', serif;
    font-size: 18px;
    font-weight: 700;
    color: {C['text_dark']};
    margin-bottom: 6px;
}}
.section-sub {{
    font-family: 'Source Sans 3', sans-serif;
    font-size: 13px;
    color: {C['text_muted']};
    line-height: 1.6;
}}
hr.divider {{
    border: none;
    border-top: 1px solid #E8E4DE;
    margin: 28px 0;
}}
</style>
""", unsafe_allow_html=True)

render_shell(
    active_label="Production Analytics",
    page_title="📊 Production Analytics",
    page_subtitle="Choose a prediction period and enter workforce figures to forecast estate yield.",
    content_html="",
)


# SECTION 1 — Period toggle
st.markdown("""
<div style="margin-top: 8px;">
  <div class="section-title">Prediction Period</div>
  <div class="section-sub" style="margin-bottom: 18px;">
    Choose whether to forecast yield for the current month or next month.
  </div>
</div>
""", unsafe_allow_html=True)

if "pa_period" not in st.session_state:
    st.session_state["pa_period"] = "current"

col_cur, col_nxt, col_pad = st.columns([1, 1, 2])

with col_cur:
    cur_active = st.session_state["pa_period"] == "current"
    if st.button(
        f"This Month\n{CUR_MONTH} {CUR_YEAR}",
        key="pa_btn_current",
        type="primary" if cur_active else "secondary",
        use_container_width=True,
    ):
        st.session_state["pa_period"] = "current"
        st.session_state["pa_prediction_done"] = False
        st.rerun()

with col_nxt:
    nxt_active = st.session_state["pa_period"] == "next"
    if st.button(
        f"Next Month\n{NEXT_MONTH} {NEXT_YEAR}",
        key="pa_btn_next",
        type="primary" if nxt_active else "secondary",
        use_container_width=True,
    ):
        st.session_state["pa_period"] = "next"
        st.session_state["pa_prediction_done"] = False
        st.rerun()

# Resolve selected year / month
if st.session_state["pa_period"] == "next":
    sel_year  = NEXT_YEAR
    sel_month = NEXT_MONTH
else:
    sel_year  = CUR_YEAR
    sel_month = CUR_MONTH


# SECTION 2 — Workforce inputs
st.markdown("""
<div style="margin-top: 28px;">
  <div class="section-title">Workforce Input</div>
  <div class="section-sub" style="margin-bottom: 18px;">
    Enter the expected headcount for the selected month.
  </div>
</div>
""", unsafe_allow_html=True)

col_f, col_m, col_pad2 = st.columns([1, 1, 2])
with col_f:
    female_count = st.number_input(
        "Female Labour Count", min_value=0, step=1, value=250, key="pa_female"
    )
with col_m:
    male_count = st.number_input(
        "Male Labour Count", min_value=0, step=1, value=200, key="pa_male"
    )


# SECTION 3 — Predict button  (NOW above the chart)
st.markdown("<hr class='divider'>", unsafe_allow_html=True)

col_l, col_btn, col_r = st.columns([1.2, 0.8, 1.2])
with col_btn:
    predict_clicked = st.button(
        "Predict Yield ↓", type="primary",
        use_container_width=True, key="pa_go_btn"
    )

#Call backend on click
if predict_clicked:
    with st.spinner("Fetching features and running model…"):
        result, error = predict_productivity(
            year=int(sel_year),
            month=sel_month,
            female_workforce=float(female_count),
            male_workforce=float(male_count),
        )

    if error:
        st.error(f"⚠️ {error}")
    else:
        try:
            if isinstance(result, dict):
                raw = (
                    result.get("predicted_yield_kg")
                    or result.get("predicted_yield")
                    or result.get("yield")
                    or result.get("prediction")
                )
                if raw is None:
                    st.error(f"Unexpected backend response — no yield key found: {result}")
                    st.stop()
                predicted_yield = max(0, int(float(raw)))
            else:
                predicted_yield = max(0, int(float(result)))
        except (TypeError, ValueError):
            st.error(f"Could not parse backend response: {result}")
            st.stop()

        st.session_state.update({
            "pa_predicted_yield": predicted_yield,
            "pa_lower_bound":     max(0, predicted_yield - int(RMSE_INTERVAL)),
            "pa_upper_bound":     predicted_yield + int(RMSE_INTERVAL),
            "pa_prediction_done": True,
            "pa_sel_year":        int(sel_year),
            "pa_sel_month":       sel_month,
        })
        st.rerun()

#Resolve prediction state
prediction_done = (
    st.session_state.get("pa_prediction_done", False)
    and st.session_state.get("pa_sel_month") == sel_month
    and st.session_state.get("pa_sel_year")  == sel_year
)

if prediction_done:
    PY      = st.session_state["pa_predicted_yield"]
    LB      = st.session_state["pa_lower_bound"]
    UB      = st.session_state["pa_upper_bound"]
    P_YEAR  = st.session_state["pa_sel_year"]
    P_MON   = st.session_state["pa_sel_month"]
    P_LABEL = f"{P_MON} {P_YEAR}"
    P_SHORT = f"{MONTH_SHORT[MONTH_NAMES.index(P_MON)]} '{str(P_YEAR)[2:]}"
    PRIOR   = prior_year_yield(P_YEAR, P_MON)
    PRIOR_LABEL = f"{P_MON} {P_YEAR - 1}"


# SECTION 4 — Stat labels  (between Predict button and chart, only after predict)
if prediction_done:
    prior_card = ""
    yoy_card   = ""

    if PRIOR and PRIOR > 0:
        YOY   = round(((PY - PRIOR) / PRIOR) * 100, 1)
        up    = YOY >= 0
        arrow = "↑" if up else "↓"
        yc    = C["tea_green"] if up else C["destructive"]
        yoy_bg = "#EBF5EF" if up else "#FDECEA"
        yoy_bd = f"1px solid {'#B6DAC2' if up else '#F1B8B4'}"

        prior_card = f"""
  <div style="flex:1;min-width:180px;background:#fff;border:1px solid #E2DDD7;
       border-radius:14px;padding:22px 24px;">
    <div style="font-size:11px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;
         color:{C['text_muted']};font-family:'Source Sans 3',sans-serif;margin-bottom:10px;">
      {PRIOR_LABEL} — Same Month Last Year
    </div>
    <div style="font-family:'Playfair Display',serif;font-size:30px;font-weight:700;
         color:{C['text_dark']};line-height:1.15;">
      {PRIOR:,.0f}<span style="font-size:14px;color:{C['text_muted']};margin-left:5px;">kg</span>
    </div>
    <div style="margin-top:10px;font-size:13px;color:{C['text_muted']};
         font-family:'Source Sans 3',sans-serif;line-height:1.5;">
      Actual yield, prior year
    </div>
  </div>"""

        yoy_card = f"""
  <div style="flex:1;min-width:160px;background:{yoy_bg};border:{yoy_bd};
       border-radius:14px;padding:22px 24px;">
    <div style="font-size:11px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;
         color:{C['text_muted']};font-family:'Source Sans 3',sans-serif;margin-bottom:10px;">
      Year-on-Year Change
    </div>
    <div style="font-family:'Playfair Display',serif;font-size:34px;font-weight:700;
         color:{yc};line-height:1.15;">
      {arrow}&nbsp;{abs(YOY)}%
    </div>
    <div style="margin-top:10px;font-size:13px;color:{C['text_muted']};
         font-family:'Source Sans 3',sans-serif;line-height:1.5;">
      vs {PRIOR_LABEL}
    </div>
  </div>"""

    st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
    st.markdown(f"""
<div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:4px;">
  <div style="flex:2;min-width:220px;background:#fff;border:1px solid #E2DDD7;
       border-radius:14px;padding:22px 24px;">
    <div style="font-size:11px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;
         color:{C['text_muted']};font-family:'Source Sans 3',sans-serif;margin-bottom:10px;">
      Predicted Yield — {P_LABEL}
    </div>
    <div style="font-family:'Playfair Display',serif;font-size:38px;font-weight:700;
         color:{C['tea_green']};line-height:1.15;">
      {PY:,}<span style="font-size:16px;color:{C['text_muted']};margin-left:6px;">kg</span>
    </div>
    <div style="margin-top:12px;background:{C['card_bg']};border-radius:9px;
         padding:9px 14px;font-size:13px;color:{C['text_muted']};
         font-family:'Source Sans 3',sans-serif;line-height:1.5;">
      Confidence range &nbsp;
      <strong style="color:{C['text_dark']};">{LB:,} – {UB:,} kg</strong>
    </div>
  </div>
  {prior_card}
  {yoy_card}
</div>
""", unsafe_allow_html=True)


# SECTION 5 — Historical yield trend chart
#Before predict: shows historical data only
#After predict : forecast point APPENDED to the SAME chart (single chart)
st.markdown("<hr class='divider'>", unsafe_allow_html=True)

x_hist, y_hist = build_trailing_24(sel_year, sel_month)
x_clean = [x for x, y in zip(x_hist, y_hist) if y is not None]
y_clean = [y for y in y_hist if y is not None]

if prediction_done:
    chart_title    = "Historical Yield Trend — Last 24 Months + Forecast"
    chart_subtitle = (
        f"Displays available yield records from the 24 months leading up to "
        f"<strong>{P_LABEL}</strong>, with the model's forecast appended for comparison."
    )
else:
    chart_title    = "Historical Yield Trend — Last 24 Months"
    chart_subtitle = (
        f"Displays available yield records from the 24 months leading up to "
        f"<strong>{sel_month} {sel_year}</strong>. "
        f"Click <em>Predict</em> to append the model's forecast to this trend."
    )

st.markdown(f"""
<div style="margin-top: 4px;">
  <div class="section-title">{chart_title}</div>
  <div class="section-sub" style="margin-bottom: 16px;">{chart_subtitle}</div>
</div>
""", unsafe_allow_html=True)

# Build the unified chart (historical + optional forecast)
fig_yield = go.Figure()

if x_clean:
    fig_yield.add_trace(go.Scatter(
        x=x_clean, y=y_clean,
        mode="lines+markers",
        fill="tozeroy",
        fillcolor="rgba(46,107,69,0.07)",
        line=dict(color=C["tea_green"], width=2.5),
        marker=dict(size=5, color=C["tea_green"]),
        name="Actual Yield",
        hovertemplate="%{x}<br><b>%{y:,} kg</b><extra></extra>",
    ))
else:
    fig_yield.add_annotation(
        text="No historical yield data found in dataset.",
        xref="paper", yref="paper", x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=14, color=C["text_muted"]),
    )

# Append forecast traces to the SAME chart if prediction is done
if prediction_done and x_clean:
    # Confidence interval band
    fig_yield.add_trace(go.Scatter(
        x=[x_clean[-1], P_SHORT, P_SHORT, x_clean[-1]],
        y=[LB, LB, UB, UB],
        fill="toself",
        fillcolor="rgba(200,146,58,0.12)",
        line=dict(width=0),
        showlegend=True,
        name="Confidence Range",
        hoverinfo="skip",
    ))

    # Dashed connector from last historical point to forecast
    fig_yield.add_trace(go.Scatter(
        x=[x_clean[-1], P_SHORT],
        y=[y_clean[-1], PY],
        mode="lines",
        line=dict(color=C["earth_warm"], width=1.8, dash="dash"),
        showlegend=False, hoverinfo="skip",
    ))

    # Predicted point
    fig_yield.add_trace(go.Scatter(
        x=[P_SHORT], y=[PY],
        mode="markers+text",
        marker=dict(
            size=14, color=C["earth_warm"], symbol="diamond",
            line=dict(color="#fff", width=2)
        ),
        text=[f"  {PY:,} kg"],
        textposition="middle right",
        textfont=dict(size=12, color=C["earth_warm"], family="Source Sans 3"),
        name=f"Predicted",
        hovertemplate=f"{P_LABEL}<br><b>{PY:,} kg</b> (predicted)<extra></extra>",
    ))

fig_yield.update_layout(
    plot_bgcolor=C["white"], paper_bgcolor=C["bg"],
    font=dict(family="Source Sans 3", color=C["text_dark"]),
    margin=dict(l=20, r=20, t=20, b=60), height=370,
    xaxis=dict(gridcolor="#E8E4DE", tickangle=-40, tickfont=dict(size=11)),
    yaxis=dict(gridcolor="#E8E4DE", title="Yield (kg)", tickformat=","),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    hovermode="x unified",
)
st.plotly_chart(fig_yield, use_container_width=True, key="chart_yield_unified")


# SECTION 6 — Year-on-Year bar chart  (only after prediction)
#Historical bars + prediction bar appended
if prediction_done:
    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    P_SHORT_MON = MONTH_SHORT[MONTH_NAMES.index(P_MON)]
    yoy_data    = same_month_all_years(P_YEAR, P_MON)

    # Historical years only (exclude the prediction year if it has actual data)
    hist_yrs  = sorted(yr for yr in yoy_data if yr < P_YEAR)
    hist_vals = [yoy_data[yr] for yr in hist_yrs]

    # Append the prediction as an extra bar
    all_yrs   = [str(y) for y in hist_yrs] + [f"{P_YEAR} (Pred.)"]
    all_vals  = hist_vals + [PY]
    bar_colors = [C["tea_green"]] * len(hist_yrs) + [C["earth_warm"]]
    y_max      = max(all_vals) * 1.22 if all_vals else 100000

    # Append prediction ONLY when available
    if PY is not None:
        all_yrs.append(f"{P_YEAR} (Pred.)")
        all_vals.append(PY)
        bar_colors.append(C["earth_warm"])

    yoy_legend_text = ""
    if PRIOR and PRIOR > 0:
        YOY_bar   = round(((PY - PRIOR) / PRIOR) * 100, 1)
        up_bar    = YOY_bar >= 0
        arrow_bar = "↑" if up_bar else "↓"
        yc_bar    = C["tea_green"] if up_bar else C["destructive"]
        yoy_legend_text = (
            f"&nbsp;&nbsp;{arrow_bar}&nbsp;"
            f"<strong style='color:{yc_bar};'>{abs(YOY_bar)}%</strong>"
            f"&nbsp;vs {PRIOR_LABEL}"
            f"&nbsp;&middot;&nbsp; {PRIOR:,.0f} kg &rarr; {PY:,} kg"
        )

    st.markdown(f"""
<div style="margin-top: 4px;">
  <div class="section-title">{P_SHORT_MON} Yield — Year-on-Year Comparison</div>
  <div class="section-sub" style="margin-bottom: 16px;">
    Predicted <strong>{P_LABEL}</strong> compared against the same month in all prior
    years available in the dataset.
  </div>
</div>
""", unsafe_allow_html=True)

    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        x=all_yrs, y=all_vals,
        marker_color=bar_colors,
        marker_line=dict(width=0),
        text=[f"{int(v):,}" for v in all_vals],
        textposition="outside",
        textfont=dict(size=11, family="Source Sans 3", color=C["text_dark"]),
        hovertemplate="%{x}<br><b>%{y:,} kg</b><extra></extra>",
        cliponaxis=False,
    ))
    # Draw the dotted line across the chart
    fig_bar.add_hline(
        y=PY,
        line_dash="dash",
        line_color=C["earth_warm"],
        line_width=3
    )

    fig_bar.update_layout(
        plot_bgcolor=C["white"], paper_bgcolor=C["bg"],
        font=dict(family="Source Sans 3", color=C["text_dark"]),
        margin=dict(l=20, r=20, t=30, b=40), height=360,
        xaxis=dict(gridcolor="#E8E4DE", title="Year"),
        yaxis=dict(
            gridcolor="#E8E4DE", title="Yield (kg)",
            tickformat=",", range=[0, y_max]
        ),
        showlegend=False,
    )
    st.plotly_chart(fig_bar, use_container_width=True, key="chart_yoy")

    # Legend / annotation strip
    st.markdown(f"""
<div style="background:{C['card_bg']};border:1px solid #D9D4CC;border-radius:12px;
     padding:13px 20px;margin-top:6px;display:flex;gap:24px;align-items:center;flex-wrap:wrap;">
  <span style="display:inline-flex;align-items:center;gap:8px;font-size:13px;
       color:{C['text_muted']};font-family:'Source Sans 3',sans-serif;line-height:1.5;">
    <span style="width:12px;height:12px;border-radius:3px;flex-shrink:0;
         background:{C['tea_green']};display:inline-block;"></span>
    Historical yield
  </span>
  <span style="display:inline-flex;align-items:center;gap:8px;font-size:13px;
       color:{C['text_muted']};font-family:'Source Sans 3',sans-serif;line-height:1.5;">
    <span style="width:16px;height:0px;border-top:2px dashed {C['earth_warm']};flex-shrink:0;
         display:inline-block;margin-right:4px;"></span>
    Predicted Yield ({PY:,} kg)
  </span>
  <span style="font-size:13px;color:{C['text_muted']};
       font-family:'Source Sans 3',sans-serif;line-height:1.5;">
    {yoy_legend_text}
  </span>
</div>
""", unsafe_allow_html=True)

render_footer()
