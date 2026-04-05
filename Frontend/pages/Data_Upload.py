import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd
from pathlib import Path
from shared import COLORS, login_guard, render_shell, render_footer

st.set_page_config(
    page_title="Data Upload – STEMS",
    page_icon="📤",
    layout="wide",
    initial_sidebar_state="expanded",
)

login_guard()
C = COLORS

THIS_DIR = Path(__file__).resolve().parent
DATA_DIR = THIS_DIR.parent / "datasets"
DATA_DIR.mkdir(parents=True, exist_ok=True)

def smart_read(file) -> pd.DataFrame:
    file.seek(0)
    if file.name.endswith(".json"):
        import json
        data = json.load(file)
        if isinstance(data, list):
            return pd.DataFrame(data)
        elif isinstance(data, dict):
            try:
                return pd.json_normalize(data)
            except Exception:
                return pd.DataFrame(list(data.items()), columns=["key", "value"])
        else:
            return pd.DataFrame([{"value": data}])
    raw = (pd.read_csv(file, header=None) if file.name.endswith(".csv") else pd.read_excel(file, header=None))
    header_row = 0
    for i, row in raw.iterrows():
        values = [str(v).strip() for v in row if str(v).strip() not in ("", "nan", "None")]
        if len(values) >= max(2, int(len(row) * 0.3)):
            header_row = i
            break
    file.seek(0)
    df = (pd.read_csv(file, header=header_row) if file.name.endswith(".csv") else pd.read_excel(file, header=header_row))
    df = df.loc[:, ~df.columns.astype(str).str.match(r"^Unnamed")]
    df = df.dropna(how="all").reset_index(drop=True)
    return df


def compare_existing(df_new: pd.DataFrame, existing_path: Path) -> str:
    try:
        if existing_path.suffix == ".json":
            try:
                df_old = pd.read_json(existing_path)
            except Exception:
                return "same_cols"
        elif existing_path.suffix == ".csv":
            df_old = pd.read_csv(existing_path)
        else:
            df_old = pd.read_excel(existing_path)
        if list(df_new.columns) != list(df_old.columns):
            return "diff_cols"
        df_new_r = df_new.reset_index(drop=True)
        df_old_r = df_old.reset_index(drop=True)
        if df_new_r.shape == df_old_r.shape and (df_new_r.fillna("") == df_old_r.fillna("")).all(axis=None):
            return "identical"
        return "same_cols"
    except Exception:
        return "same_cols"


def versioned_path(original: Path) -> Path:
    stem, suffix = original.stem, original.suffix
    n = 1
    while True:
        candidate = original.parent / f"{stem}_{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def save_file(df: pd.DataFrame, dest: Path, raw_file=None) -> Path:
    if dest.suffix == ".json" and raw_file is not None:
        import json
        raw_file.seek(0)
        data = json.load(raw_file)
        with open(dest, "w") as f:
            json.dump(data, f, indent=2)
        return dest
    else:
        dest_csv = dest.with_suffix(".csv")
        df.to_csv(dest_csv, index=False)
        return dest_csv


def handle_upload(file) -> dict:
    df     = smart_read(file)
    suffix = Path(file.name).suffix.lower()
    if suffix not in (".json",):
        suffix = ".csv"
    stem   = Path(file.name).stem
    target = DATA_DIR / f"{stem}{suffix}"

    if target.exists():
        comparison = compare_existing(df, target)
        if comparison == "identical":
            action = "identical"
            dest   = target
        elif comparison == "same_cols":
            action = "overwrite"
            dest   = save_file(df, target, raw_file=file)
        else:
            action = "versioned"
            dest   = save_file(df, versioned_path(target), raw_file=file)
    else:
        action = "new"
        dest   = save_file(df, target, raw_file=file)

    return {"action": action, "dest": dest, "rows": len(df), "cols": len(df.columns), "df": df}

render_shell(
    active_label="Data Upload",
    page_title="📤 Data Upload",
    page_subtitle="Upload updated estate data files, saved locally and flagged for the backend team to deploy.",
)

st.markdown(f"""
<style>
[data-testid="stFileUploader"] label {{ display: none !important; }}

section[data-testid="stFileUploaderDropzone"] {{
    padding: 160px 40px !important;
    border: 2px dashed #A8CDB4 !important;
    border-radius: 20px !important;
    background: #EEF4F1 !important;
    box-sizing: border-box !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
}}
section[data-testid="stFileUploaderDropzone"] > div {{
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    width: 100% !important;
    gap: 16px !important;
}}
section[data-testid="stFileUploaderDropzone"] > div > div:first-child {{
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    text-align: center !important;
}}
section[data-testid="stFileUploaderDropzone"] button {{
    background: {C["tea_green"]} !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 10px 28px !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    cursor: pointer !important;
    align-self: center !important;
}}
section[data-testid="stFileUploaderDropzone"] button:hover {{
    background: {C["tea_dark"]} !important;
}}

.upload-result {{
    background: #fff;
    border: 1.5px solid #D9D4CC;
    border-radius: 14px;
    padding: 18px 22px;
    margin-bottom: 14px;
    font-family: 'Source Sans 3', sans-serif;
}}
.upload-result .file-name {{ font-size: 15px; font-weight: 700; color: {C["text_dark"]}; margin-bottom: 6px; }}
.upload-result .file-meta {{ font-size: 13px; color: {C["text_muted"]}; margin-bottom: 10px; }}
.upload-result .dest-path {{
    font-size: 11px; font-family: monospace; background: #F0EDE7;
    border-radius: 6px; padding: 4px 10px; color: {C["tea_dark"]}; display: inline-block;
}}
.badge-new      {{ background: #e8f5ee; color: #2E6B45; border: 1px solid #B6DAC2; }}
.badge-overwrite{{ background: #e8f0fe; color: #1a56a0; border: 1px solid #b3ccf5; }}
.badge-versioned{{ background: #fef3e2; color: #C8923A; border: 1px solid #f5d9a8; }}
.badge-identical{{ background: #f0f0f0; color: #6B7F6F; border: 1px solid #D0CCC6; }}
.action-badge {{
    display: inline-block; font-size: 11px; font-weight: 700;
    letter-spacing: .08em; text-transform: uppercase;
    border-radius: 20px; padding: 3px 12px; margin-bottom: 10px;
}}

/*Delete button*/
div[data-testid="stButton"] > button[kind="primary"] {{
    background: rgba(192,57,43,0.10) !important;
    border: 1.5px solid rgba(192,57,43,0.40) !important;
    color: #C0392B !important;
    box-shadow: none !important;
}}
div[data-testid="stButton"] > button[kind="primary"]:hover {{
    background: rgba(192,57,43,0.18) !important;
    border-color: #C0392B !important;
}}
</style>
""", unsafe_allow_html=True)

uploaded = st.file_uploader(
    "Upload",
    type=["csv", "xlsx", "json"],
    accept_multiple_files=True,
    label_visibility="collapsed",
)

#Process uploads
if uploaded:
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    for file in uploaded:
        try:
            res    = handle_upload(file)
            action = res["action"]
            dest   = res["dest"]
            rows   = res["rows"]
            cols   = res["cols"]
            df     = res["df"]

            badge_class = {"new":"badge-new","overwrite":"badge-overwrite","versioned":"badge-versioned","identical":"badge-identical"}.get(action,"badge-new")
            badge_label = {"new":" New file saved","overwrite":"File updated (same structure, new data)","versioned":"Saved as new version (structure differs)","identical":"✔ No changes detected, file unchanged"}.get(action, action)
            action_note = {"new":"Saved to datasets folder.","overwrite":"Updated in place, columns matched.","versioned":"Saved as new version; structure differs.","identical":"Already up to date; nothing changed."}.get(action,"")
            pending_note = ''

            st.markdown(
                f'<div class="upload-result">'
                f'<div class="file-name">📄 {file.name}</div>'
                f'<span class="action-badge {badge_class}">{badge_label}</span>'
                f'<div class="file-meta">{rows:,} rows &nbsp;·&nbsp; {cols} columns &nbsp;·&nbsp; {action_note}</div>'
                f'<div class="dest-path">datasets/{dest.name}</div>'
                f'{pending_note}'
                f'</div>',
                unsafe_allow_html=True
            )

            with st.expander(f"Preview : {dest.name} (first 15 rows)"):
                st.dataframe(df.head(15), use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"Could not process **{file.name}**: {e}")

#Current datasets folder
st.markdown("<div style='height:60px'></div>", unsafe_allow_html=True)
st.markdown("<div style='font-family:Playfair Display,serif;font-size:20px;font-weight:700;color:#1F3D2A;margin-bottom:12px;'>Current Data Folder</div>", unsafe_allow_html=True)
st.markdown("<div style='font-size:13px;color:#6B7F6F;font-family:Source Sans 3,sans-serif;margin-bottom:20px;'>Data files currently available for use by the prediction models.</div>", unsafe_allow_html=True)

data_files = sorted(DATA_DIR.glob("*.*"))

PLACEHOLDER = "  select a file to delete  "

if data_files:
    rows_html = ""
    for i, f in enumerate(data_files):
        size_kb  = f.stat().st_size / 1024
        size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.2f} MB"
        icon     = "🗂️" if f.suffix == ".json" else "📄"
        border   = "border-bottom:1px solid #E8E4DE;" if i < len(data_files) - 1 else ""
        rows_html += (
            f'<div style="display:flex;align-items:center;padding:14px 20px;{border}">'
            f'<span style="font-size:18px;margin-right:16px;flex-shrink:0;">{icon}</span>'
            f'<span style="flex:1;font-size:13px;font-weight:600;color:#1F3D2A;font-family:\'Source Sans 3\',sans-serif;">{f.name}</span>'
            f'<span style="font-size:12px;color:#6B7F6F;font-family:\'Source Sans 3\',sans-serif;">{size_str}</span>'
            f'</div>'
        )

    st.markdown(
        f'<div style="background:#fff;border:1.5px solid #E0DBD4;border-radius:16px;overflow:hidden;margin-top:4px;">'
        f'{rows_html}</div>',
        unsafe_allow_html=True
    )

    st.markdown("<div style='height:44px;'></div>", unsafe_allow_html=True)

    file_names = [f.name for f in data_files]
    col_sel, col_btn = st.columns([0.7, 0.3])
    with col_sel:
        to_delete = st.selectbox(
            "Select file to delete",
            options=[PLACEHOLDER] + file_names,
            label_visibility="collapsed",
            key="del_select",
        )
    with col_btn:
        if st.button("🗑 Delete selected", type="primary", use_container_width=True, key="del_confirm"):
            if to_delete and to_delete != PLACEHOLDER:
                target = DATA_DIR / to_delete
                if target.exists():
                    try:
                        target.unlink()
                        st.success(f"**{to_delete}** deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not delete: {e}")
                else:
                    st.error("File not found.")
            else:
                st.warning("Please select a file to delete.")

else:
    st.markdown(
        '<div style="background:#fff;border:1.5px solid #E0DBD4;border-radius:16px;padding:24px;'
        'margin-top:8px;text-align:center;font-size:13px;color:#6B7F6F;'
        'font-family:Source Sans 3,sans-serif;">No data files yet, upload your first file above.</div>',
        unsafe_allow_html=True,
    )

render_footer()