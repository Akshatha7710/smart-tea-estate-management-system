import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import streamlit.components.v1
from datetime import date, datetime, timedelta
from collections import defaultdict
from shared import COLORS, login_guard, render_shell, render_footer
from api_client import predict_stems

st.set_page_config(page_title="Harvest Readiness – STEMS", page_icon="🌿",
                   layout="wide", initial_sidebar_state="expanded")
login_guard()
C = COLORS

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

# ── Styles ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
#stems-content .pg-sub {{ margin-bottom: 19px !important; }}
[data-testid="stSelectbox"] label,
[data-testid="stDateInput"] label {{
    font-family:'Source Sans 3',sans-serif !important;
    font-size:11px !important; font-weight:700 !important;
    letter-spacing:0.12em !important; text-transform:uppercase !important;
    color:{C['text_muted']} !important;
}}
[data-testid="stSelectbox"] > div > div {{
    border:1.5px solid #D0CCC6 !important; border-radius:10px !important;
    background:#FFFFFF !important; min-height:40px !important;
    font-family:'Source Sans 3',sans-serif !important;
    font-size:14px !important; color:{C['text_dark']} !important;
}}
[data-testid="stSelectbox"] input {{
    pointer-events:none !important; caret-color:transparent !important;
    user-select:none !important;
}}
[data-testid="stDateInput"] input {{
    border:1.5px solid #D0CCC6 !important; border-radius:10px !important;
    background:#FFFFFF !important; font-family:'Source Sans 3',sans-serif !important;
    font-size:14px !important; color:{C['text_dark']} !important;
    padding: 8px 12px !important;
}}
[data-testid="stButton"] > button[kind="primary"] {{
    background:#5BA870 !important; color:#fff !important;
    border:none !important; border-radius:10px !important;
    font-family:'Source Sans 3',sans-serif !important; font-size:14px !important;
    font-weight:600 !important; height:44px !important;
    box-shadow:0 3px 10px rgba(91,168,112,0.25) !important;
    transition:opacity .18s, transform .15s !important;
}}
[data-testid="stButton"] > button[kind="primary"]:hover {{
    opacity:0.91 !important; transform:translateY(-1px) !important;
}}
</style>
""", unsafe_allow_html=True)

render_shell(
    active_label="Harvest Readiness",
    page_title="🌿 Harvest Readiness",
    page_subtitle="Select a field and last harvest date to see all upcoming plucking rounds (~3 months ahead).",
)

# Lock selectbox typing
st.markdown("""
<script>
(function() {
    function lock() {
        window.parent.document.querySelectorAll('[data-testid="stSelectbox"] input').forEach(function(el) {
            if (el._locked) return; el._locked = true;
            el.setAttribute('readonly','readonly'); el.style.caretColor='transparent';
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

# ── Inputs ────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Field Selection</div>', unsafe_allow_html=True)
st.markdown("<div style='height:22px;'></div>", unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    sel_div = st.selectbox("Division", list(FIELD_CATALOGUE.keys()),
                           format_func=lambda d: f"{d} — {DIVISION_LABELS[d]}",
                           key="harv_div_sel")
with c2:
    sel_fld = st.selectbox("Field Number", FIELD_CATALOGUE[sel_div],
                           format_func=lambda f: f"Field {f}",
                           key="harv_fld_sel")

st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)
st.markdown('<div class="section-title">Harvest Details</div>', unsafe_allow_html=True)
st.markdown("<div style='height:22px;'></div>", unsafe_allow_html=True)

c3, _ = st.columns(2)
with c3:
    last_harvest = st.date_input("Last Harvest Date", value=date.today())

st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)

col_l, col_btn, col_r = st.columns([1, 0.8, 1])
with col_btn:
    go = st.button("View Prediction ↓", type="primary", use_container_width=True, key="harv_go_btn")

st.markdown("<div style='height:32px;'></div>", unsafe_allow_html=True)

# ── Prediction ────────────────────────────────────────────────────────────────
if go:
    days_since_harvest = (date.today() - last_harvest).days
    if days_since_harvest > 75:
        st.warning(
            f"⚠️ The last harvest date you entered was **{days_since_harvest} days ago**. "
            f"The backend's 6-round window (~75 days) may not reach far enough to return results. "
            f"Try entering a more recent last harvest date."
        )

    with st.spinner("Contacting backend…"):
        result, error = predict_stems(
            field_no=sel_fld,
            last_harvest_date=str(last_harvest),
            target_month=None,
        )

    if error:
        st.error(f"⚠️ {error}")
    elif not isinstance(result, dict):
        st.error(f"Unexpected response format: {result}")
    else:
        interval_days = result.get("interval_days", "—")
        mae_days      = result.get("mae_days", "—")
        last_harv_str = result.get("last_harvest", str(last_harvest))
        season        = result.get("season", "—")
        harvests      = result.get("harvests", [])
        pruning_warn  = result.get("pruning_warning", False)
        warn_msg      = result.get("warning_message", None)

        # NEW — monthly adjustment fields
        base_interval  = result.get("base_interval_days")
        monthly_adj    = result.get("monthly_adjustment")
        adj_month      = result.get("adjustment_month", "")

        # Next harvest date from interval
        try:
            base_date       = datetime.strptime(last_harv_str, "%Y-%m-%d").date()
            next_date       = base_date + timedelta(days=float(interval_days))
            next_date_str   = next_date.strftime("%d %b %Y").lstrip("0")
            days_from_today = (next_date - date.today()).days
        except Exception:
            next_date_str   = "—"
            days_from_today = None

        # Status tile colours
        if days_from_today is not None:
            if days_from_today <= 0:
                status_label  = "Harvest Now"
                status_bg     = "#fde8e8"; status_col = "#C0392B"; status_border = "#f1b8b4"
            elif days_from_today <= 5:
                status_label  = f"Urgent — {days_from_today}d away"
                status_bg     = "#fde8e8"; status_col = "#C0392B"; status_border = "#f1b8b4"
            elif days_from_today <= 14:
                status_label  = f"Due Soon — {days_from_today}d away"
                status_bg     = "#fef3e2"; status_col = "#C8923A"; status_border = "#f5d9a8"
            else:
                status_label  = f"On Track — {days_from_today}d away"
                status_bg     = "#e8f5ee"; status_col = "#2E6B45"; status_border = "#B6DAC2"
        else:
            status_label  = "—"
            status_bg     = C["card_bg"]; status_col = C["text_muted"]; status_border = "#D9D4CC"

        try:
            interval_display = f"{float(interval_days):.1f}"
            mae_display      = f"\u00b1{float(mae_days):.1f}"
        except Exception:
            interval_display = str(interval_days)
            mae_display      = str(mae_days)

        # Build model breakdown block
        if base_interval is not None and monthly_adj is not None:
            adj_sign   = "+" if float(monthly_adj) >= 0 else ""
            adj_colour = "#2E6B45" if float(monthly_adj) <= 0 else "#C8923A"
            adj_label  = "shorter interval (fast growth month)" if float(monthly_adj) < 0 else "longer interval (slow growth month)"
            model_breakdown = f"""
            <div style="margin-top:20px;background:#F5F3EF;border:1px solid #E0DBD4;
                        border-radius:12px;padding:16px 20px;">
              <div style="font-size:10px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;
                          color:#6B7F6F;margin-bottom:12px;font-family:'Source Sans 3',sans-serif;">
                How This Interval Was Calculated
              </div>
              <div style="display:grid;grid-template-columns:1fr auto 1fr auto 1fr;
                          align-items:center;gap:8px;text-align:center;">
                <div style="background:#fff;border:1px solid #E0DBD4;border-radius:10px;padding:12px;">
                  <div style="font-size:10px;color:#6B7F6F;font-family:'Source Sans 3',sans-serif;margin-bottom:4px;">SVR Base</div>
                  <div style="font-size:22px;font-weight:700;color:#1F3D2A;font-family:'Playfair Display',serif;">{float(base_interval):.1f}<span style="font-size:12px;font-weight:400;color:#6B7F6F;"> days</span></div>
                </div>
                <div style="font-size:20px;color:#6B7F6F;">+</div>
                <div style="background:#fff;border:1px solid #E0DBD4;border-radius:10px;padding:12px;">
                  <div style="font-size:10px;color:#6B7F6F;font-family:'Source Sans 3',sans-serif;margin-bottom:4px;">{adj_month} Adjustment</div>
                  <div style="font-size:22px;font-weight:700;color:{adj_colour};font-family:'Playfair Display',serif;">{adj_sign}{float(monthly_adj):.1f}<span style="font-size:12px;font-weight:400;color:#6B7F6F;"> days</span></div>
                  <div style="font-size:10px;color:{adj_colour};margin-top:3px;font-family:'Source Sans 3',sans-serif;">{adj_label}</div>
                </div>
                <div style="font-size:20px;color:#6B7F6F;">=</div>
                <div style="background:#e8f5ee;border:1px solid #B6DAC2;border-radius:10px;padding:12px;">
                  <div style="font-size:10px;color:#2E6B45;font-family:'Source Sans 3',sans-serif;margin-bottom:4px;">Final Interval</div>
                  <div style="font-size:22px;font-weight:700;color:#2E6B45;font-family:'Playfair Display',serif;">{interval_display}<span style="font-size:12px;font-weight:400;color:#6B7F6F;"> days</span></div>
                  <div style="font-size:10px;color:#6B7F6F;margin-top:3px;font-family:'Source Sans 3',sans-serif;">uncertainty {mae_display}</div>
                </div>
              </div>
            </div>"""
        else:
            model_breakdown = ""

        # ── Group harvests by month ───────────────────────────────────────────
        months_map = defaultdict(list)
        month_order = []

        for h in harvests:
            if not isinstance(h, dict):
                continue
            raw_date = h.get("date_display") or h.get("earliest") or ""
            try:
                parsed = datetime.strptime(raw_date, "%d %b %Y").date()
                month_key = parsed.strftime("%B %Y")
            except Exception:
                month_key = "Other"
            if month_key not in months_map:
                month_order.append(month_key)
            months_map[month_key].append(h)

        if harvests:
            month_sections = ""
            for month_key in month_order:
                rounds = months_map[month_key]
                rows_html = ""
                for h in rounds:
                    rnd        = h.get("round", "—")
                    date_disp  = h.get("date_display", "—")
                    earliest   = h.get("earliest", "—")
                    latest     = h.get("latest", "—")

                    row_urgent = ""
                    try:
                        rd = datetime.strptime(date_disp, "%d %b %Y").date()
                        diff = (rd - date.today()).days
                        if diff <= 0:
                            row_urgent = "background:#fff0f0;"
                        elif diff <= 7:
                            row_urgent = "background:#fffaf0;"
                    except Exception:
                        pass

                    rows_html += f"""
                    <tr style="{row_urgent}">
                      <td style="padding:10px 14px;font-weight:700;color:#1E4D33;
                                 font-family:'Source Sans 3',sans-serif;font-size:13px;
                                 border-bottom:1px solid #EAE6E0;white-space:nowrap;">
                        Round {rnd}
                      </td>
                      <td style="padding:10px 14px;color:#1F3D2A;
                                 font-family:'Playfair Display',serif;font-size:15px;font-weight:700;
                                 border-bottom:1px solid #EAE6E0;white-space:nowrap;">
                        {date_disp}
                      </td>
                      <td style="padding:10px 14px;color:#6B7F6F;
                                 font-family:'Source Sans 3',sans-serif;font-size:13px;
                                 border-bottom:1px solid #EAE6E0;white-space:nowrap;">
                        {earliest} — {latest}
                      </td>
                    </tr>"""

                month_sections += f"""
                <div style="margin-bottom:18px;">
                  <div style="font-size:12px;font-weight:700;letter-spacing:.10em;text-transform:uppercase;
                              color:#2E6B45;margin-bottom:8px;font-family:'Source Sans 3',sans-serif;
                              padding-left:2px;">
                    {month_key}
                  </div>
                  <table style="width:100%;border-collapse:collapse;
                                background:#FAFAF8;border:1px solid #E0DBD4;border-radius:10px;
                                overflow:hidden;">
                    <thead>
                      <tr style="background:#F0EDE7;">
                        <th style="padding:8px 14px;text-align:left;font-size:10px;font-weight:700;
                                   letter-spacing:.10em;text-transform:uppercase;color:#6B7F6F;
                                   font-family:'Source Sans 3',sans-serif;border-bottom:1px solid #E0DBD4;">
                          Round
                        </th>
                        <th style="padding:8px 14px;text-align:left;font-size:10px;font-weight:700;
                                   letter-spacing:.10em;text-transform:uppercase;color:#6B7F6F;
                                   font-family:'Source Sans 3',sans-serif;border-bottom:1px solid #E0DBD4;">
                          Date
                        </th>
                        <th style="padding:8px 14px;text-align:left;font-size:10px;font-weight:700;
                                   letter-spacing:.10em;text-transform:uppercase;color:#6B7F6F;
                                   font-family:'Source Sans 3',sans-serif;border-bottom:1px solid #E0DBD4;">
                          Window
                        </th>
                      </tr>
                    </thead>
                    <tbody>{rows_html}</tbody>
                  </table>
                </div>"""

            harvests_block = f"""
            <div style="margin-top:24px;border-top:1px solid #E8E4DE;padding-top:20px;">
              <div style="font-size:11px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;
                          color:#6B7F6F;margin-bottom:16px;font-family:'Source Sans 3',sans-serif;">
                Predicted Harvest Schedule — All Rounds
              </div>
              {month_sections}
            </div>"""

            n_months   = len(month_order)
            n_rounds   = len(harvests)
            table_h    = n_rounds * 45 + n_months * 70 + 80
        else:
            harvests_block = """
            <div style="margin-top:24px;border-top:1px solid #E8E4DE;padding-top:20px;
                        text-align:center;padding-bottom:12px;">
              <div style="font-size:13px;color:#6B7F6F;font-family:'Source Sans 3',sans-serif;">
                No harvest rounds returned for this field and date.<br>
                Try setting a more recent <strong>Last Harvest Date</strong>.
              </div>
            </div>"""
            table_h = 80

        warning_block = ""
        if pruning_warn and warn_msg:
            warning_block = f"""
            <div style="margin-top:16px;background:#fef3e2;border:1px solid #f5d9a8;
                 border-radius:10px;padding:12px 16px;display:flex;align-items:flex-start;gap:10px;">
              <span style="font-size:16px;flex-shrink:0;">&#9888;&#65039;</span>
              <span style="font-size:13px;color:#7a5200;font-family:'Source Sans 3',sans-serif;
                   line-height:1.6;">{warn_msg}</span>
            </div>"""

        breakdown_h = 120 if base_interval is not None else 0
        card_height = 260 + breakdown_h + table_h + (60 if pruning_warn and warn_msg else 0)

        st.components.v1.html(f"""
<!DOCTYPE html>
<html>
<head>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Source+Sans+3:wght@400;600;700&display=swap" rel="stylesheet">
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Source Sans 3', sans-serif; background: transparent; }}
.card {{ background: #fff; border: 1.5px solid #D9D4CC; border-radius: 18px;
         padding: 28px 32px; box-shadow: 0 4px 20px rgba(30,77,51,0.06); }}
.meta {{ font-size: 11px; font-weight: 700; letter-spacing: .14em; text-transform: uppercase;
         color: #6B7F6F; margin-bottom: 6px; }}
.field-name {{ font-family: 'Playfair Display', serif; font-size: 28px; font-weight: 700;
               color: #1F3D2A; margin-bottom: 22px; line-height: 1.1; }}
.tiles {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }}
.tile {{ border: 1px solid #E0DBD4; border-radius: 12px; padding: 18px 20px; background: #F0EDE7; }}
.tile-label {{ font-size: 11px; font-weight: 700; letter-spacing: .10em; text-transform: uppercase;
               color: #6B7F6F; margin-bottom: 10px; }}
.tile-value {{ font-family: 'Playfair Display', serif; font-weight: 700; color: #1F3D2A; line-height: 1.2; }}
.tile-sub {{ margin-top: 6px; font-size: 12px; color: #6B7F6F; }}
</style>
</head>
<body>
<div class="card">
  <div class="meta">{sel_div} &nbsp;&middot;&nbsp; {DIVISION_LABELS[sel_div]} Division</div>
  <div class="field-name">Field {sel_fld}</div>

  <div class="tiles">

    <div class="tile">
      <div class="tile-label">Next Harvest</div>
      <div class="tile-value" style="font-size:20px;">{next_date_str}</div>
      <div class="tile-sub">from {last_harv_str}</div>
    </div>

    <div class="tile">
      <div class="tile-label">Interval</div>
      <div class="tile-value" style="font-size:32px;color:#2E6B45;">
        {interval_display}
        <span style="font-size:14px;color:#6B7F6F;font-weight:400;margin-left:2px;">days</span>
      </div>
      <div class="tile-sub">Uncertainty {mae_display} days</div>
    </div>

    <div class="tile" style="background:{status_bg};border-color:{status_border};">
      <div class="tile-label" style="color:{status_col};">Status</div>
      <div class="tile-value" style="font-size:15px;color:{status_col};
           font-family:'Source Sans 3',sans-serif;">{status_label}</div>
      <div class="tile-sub">Season: {season}</div>
    </div>

  </div>

  {model_breakdown}
  {harvests_block}
  {warning_block}
</div>
</body>
</html>
""", height=card_height, scrolling=False)

render_footer()
