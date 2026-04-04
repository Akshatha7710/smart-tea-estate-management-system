from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import date, timedelta, datetime
from pathlib import Path
import joblib, numpy as np, pandas as pd, json, math

app = FastAPI(title="STEMS Harvest Prediction API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE = Path(__file__).parent

# ════════════════════════════════════════════════════════════════════
# LOAD ALL MODELS AT STARTUP
# ════════════════════════════════════════════════════════════════════

# STEMS
STEMS_BUNDLE   = joblib.load(BASE / "models" / "stems_svr_bundle.pkl")
STEMS_MODEL    = STEMS_BUNDLE["model"]
STEMS_T_SCALER = STEMS_BUNDLE["t_scaler"]
STEMS_CLIP_LO  = STEMS_BUNDLE["clip_lo"]
STEMS_CLIP_HI  = STEMS_BUNDLE["clip_hi"]
STEMS_FEATURES = STEMS_BUNDLE["feature_cols"]
STEMS_MAE      = 2.5263
STEMS_FIELDS   = pd.read_csv(BASE / "models" / "stems_field_data.csv")
STEMS_FIELDS["Field_No"] = STEMS_FIELDS["Field_No"].astype(str).str.strip()

# MONTHLY PLUCKING AVERAGE LOOKUP
with open(BASE / "models" / "plucking_monthly_lookup.json") as _f:
    MONTHLY_LOOKUP = json.load(_f)

# FERTILIZER — new pkl files from teammate
FERT_FIELD_LOOKUP  = joblib.load(BASE / "models" / "field_lookup.pkl")
FERT_SCHEDULE_DATA = joblib.load(BASE / "models" / "schedule_data.pkl")
FERT_MODEL_AMT     = joblib.load(BASE / "models" / "fertilizer_model_amount.pkl")
FERT_MODEL_DAYS    = joblib.load(BASE / "models" / "fertilizer_model_days.pkl")
FERT_SCALER_AMT    = joblib.load(BASE / "models" / "scaler_amount.pkl")
FERT_SCALER_DAYS   = joblib.load(BASE / "models" / "scaler_days.pkl")
FERT_LE_DIV        = joblib.load(BASE / "models" / "label_encoder_division.pkl")
FERT_LE_VPSD       = joblib.load(BASE / "models" / "label_encoder_vpsd.pkl")
FERT_FEAT_AMT      = joblib.load(BASE / "models" / "feature_names_amount.pkl")
FERT_FEAT_DAYS     = joblib.load(BASE / "models" / "feature_names_days.pkl")
UREA_N             = 0.46

# SOIL
SOIL_PH_MODEL  = joblib.load(BASE / "models" / "soil-model-1.pkl")
SOIL_WET_MODEL = joblib.load(BASE / "models" / "soil-model-2.pkl")
SOIL_C_MODEL   = joblib.load(BASE / "models" / "soil-model-3.pkl")
with open(BASE / "models" / "soil_encoding_meta.json") as f:
    SOIL_META = json.load(f)
ESTATE_PH_MAP   = SOIL_META["estate_pH_map"]
CATEGORY_PH_MAP = SOIL_META["category_pH_map"]
ESTATE_C_MAP    = SOIL_META["estate_C_map"]
CATEGORY_C_MAP  = SOIL_META["category_C_map"]
GLOBAL_PH_MEAN  = SOIL_META["global_pH_mean"]
GLOBAL_C_MEAN   = SOIL_META["global_C_mean"]
CAT_COLS_PH = ["Category", "VP/SD", "Estate"]
NUM_COLS_PH = ["Extent (Ha)", "FieldAge", "C%", "C_Age", "C_sq",
               "log_Age", "log_C", "Ha_C", "Estate_enc_pH", "Cat_enc_pH"]
CAT_COLS_C  = ["Category", "VP/SD", "Estate"]
NUM_COLS_C  = ["Extent (Ha)", "FieldAge", "pH", "pH_Age", "pH_sq",
               "log_Age", "Estate_enc_C", "Cat_enc_C"]

# PRODUCTIVITY
PROD_MODEL   = joblib.load(BASE / "models" / "xgb_model.pkl")
PROD_SCALER  = joblib.load(BASE / "models" / "scaler.pkl")
PROD_DATA    = pd.read_csv(BASE / "models" / "productivity_data.csv")
with open(BASE / "models" / "medians.json") as _mf:
    PROD_MEDIANS = json.load(_mf)
PROD_RMSE    = 6143.22
PROD_SCALER_FEATURES = [
    "rainfall", "wet_days", "female_workforceRatio",
    "yield_lag_1", "yield_lag_2", "yield_lag_3", "yield_lag_12",
    "rainfall_lag_1", "irradiance_SW_DWN",
    "sin_month", "cos_month", "NDVI", "EVI", "yield_momentum"
]


# ════════════════════════════════════════════════════════════════════
# HEALTH CHECK
# ════════════════════════════════════════════════════════════════════

@app.get("/")
def root():
    return {
        "status": "running",
        "endpoints": [
            "POST /predict/stems",
            "POST /predict/fertilizer",
            "POST /predict/soil",
            "POST /predict/soil_wetdays",
            "POST /predict/productivity",
            "GET  /fields",
            "GET  /productivity/months"
        ],
        "docs": "/docs"
    }


# ════════════════════════════════════════════════════════════════════
# 1. STEMS — HARVEST INTERVAL + SCHEDULE
# ════════════════════════════════════════════════════════════════════

def stems_engineer(df):
    df = df.copy()
    df["Soil_Index"]      = df["Soil_Carbon"]       / (df["Soil_pH"].replace(0, np.nan) + 1e-9)
    df["Yield_Eff"]       = df["Yield_Prev_Year"]   / (df["Extent_Hect"].replace(0, np.nan) + 1e-9)
    df["Prune_Age_Ratio"] = df["Prune_Cycle_Stage"] / (df["Age_Months"] / 12 + 1e-9)
    df["Rain_Trend"]      = df["Rainfall_Lag1"]     - df["Rainfall_Lag3"]
    df["Growth_per_Prod"] = df["Growth_Response"]   / (df["Field_Productivity"] + 1e-9)
    return df

class StemsInput(BaseModel):
    field_no:          str
    last_harvest_date: str
    target_month:      Optional[str] = None

@app.post("/predict/stems")
def predict_stems(data: StemsInput):
    field_rows = STEMS_FIELDS[STEMS_FIELDS["Field_No"] == str(data.field_no).strip()]
    if len(field_rows) == 0:
        raise HTTPException(status_code=404,
            detail=f"Field {data.field_no} not found.")

    row        = field_rows.sort_values("Year", ascending=False).iloc[0]
    is_pruning = bool(row.get("Near_Pruning_Flag", 0) == 1)
    df_row     = stems_engineer(pd.DataFrame([row]))

    for c in STEMS_FEATURES:
        if c not in df_row.columns:
            df_row[c] = 0.0

    X              = df_row[STEMS_FEATURES].clip(lower=STEMS_CLIP_LO, upper=STEMS_CLIP_HI, axis=1)
    pred_n         = np.clip(STEMS_MODEL.predict(X), 0, 1)
    base_interval  = round(float(STEMS_T_SCALER.inverse_transform(pred_n.reshape(-1,1)).ravel()[0]), 2)

    # Parse last_harvest date FIRST before using it in monthly adjustment
    try:
        last_harvest = datetime.strptime(data.last_harvest_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="last_harvest_date must be YYYY-MM-DD.")

    # Monthly adjustment using division-level plucking averages
    division_str   = str(row["Division"]).strip()
    next_date_est  = last_harvest + timedelta(days=base_interval)
    harvest_month  = next_date_est.strftime("%B")
    annual_mean    = MONTHLY_LOOKUP.get("annual_mean", 22.42)
    div_monthly    = MONTHLY_LOOKUP.get("division_monthly_avg", {}).get(division_str, {})
    monthly_avg    = div_monthly.get(harvest_month, annual_mean)
    adjustment     = round(monthly_avg - annual_mean, 2)
    interval_days  = round(max(7.0, base_interval + adjustment), 2)

    upcoming = []
    for i in range(1, 7):
        harvest_date = last_harvest + timedelta(days=interval_days * i)
        if harvest_date.year > last_harvest.year + 1:
            break
        early = harvest_date - timedelta(days=STEMS_MAE)
        late  = harvest_date + timedelta(days=STEMS_MAE)
        upcoming.append({
            "round":         i,
            "date":          harvest_date.strftime("%Y-%m-%d"),
            "date_display":  harvest_date.strftime("%d %b %Y"),
            "earliest":      early.strftime("%d %b"),
            "latest":        late.strftime("%d %b"),
            "error_window":  f"+-{STEMS_MAE} days",
            "month":         harvest_date.strftime("%Y-%m"),
            "month_display": harvest_date.strftime("%B %Y"),
        })

    filtered = [h for h in upcoming if h["month"] == data.target_month] if data.target_month else upcoming

    return {
        "field_no":            data.field_no,
        "division":            str(row["Division"]),
        "season":              str(row.get("Season", "N/A")),
        "interval_days":       interval_days,
        "base_interval_days":  base_interval,
        "monthly_adjustment":  adjustment,
        "adjustment_month":    harvest_month,
        "mae_days":            STEMS_MAE,
        "last_harvest":        data.last_harvest_date,
        "target_month":        data.target_month or "all",
        "harvests":            filtered,
        "note":                f"Base interval {base_interval} days, adjusted {adjustment:+.1f} days for {harvest_month}. Final: {interval_days} days +-{STEMS_MAE} days.",
        "pruning_warning":     is_pruning,
        "warning_message":     "Near_Pruning_Flag=1: post-pruning recovery. Accuracy may be lower." if is_pruning else None,
        "status":              "success"
    }



# ════════════════════════════════════════════════════════════════════
# 2b. FERTILIZER SCHEDULE — Full schedule for all fields
# ════════════════════════════════════════════════════════════════════


@app.get("/schedule")
def get_fertilizer_schedule(division: str = None, status: str = None):
    df = FERT_SCHEDULE_DATA.copy()
    if division:
        df = df[df["Division"].str.upper() == division.upper()]
    if status:
        df = df[df["Schedule_Status"].str.upper() == status.upper()]

    order = {"OVERDUE": 0, "DUE TODAY": 1, "DUE SOON": 2, "UPCOMING": 3}
    df["_sort"] = df["Schedule_Status"].map(order).fillna(4)
    df = df.sort_values(["_sort", "Days_Until_Next"]).drop(columns=["_sort"])

    results = []
    for _, row in df.iterrows():
        apps     = 4 if str(row.get("VP_SD","VP")) == "SD" else 3
        n_app    = round(float(row["Pred_Dose_kgha"]) * apps / apps, 1)
        urea_app = round((n_app * float(row["Extent_Ha"])) / UREA_N, 1)
        interval = 365 // apps
        days     = int(row["Days_Until_Next"])
        if days < 0:   msg = f"Overdue by {abs(days)} days — apply immediately"
        elif days == 0: msg = "Due today — apply now"
        elif days <= 14: msg = f"Due soon in {days} days"
        else:           msg = f"Upcoming — next application in {days} days"
        results.append({
            "division":            str(row["Division"]),
            "field_no":            str(row["Field"]),
            "vp_sd":               str(row.get("VP_SD","VP")),
            "extent_ha":           float(row["Extent_Ha"]),
            "yield_kgha":          float(row["Annual_Yield_kgha"]) if pd.notna(row.get("Annual_Yield_kgha")) else None,
            "n_ratio_seas":        float(row["N_Ratio_Seas"]) if pd.notna(row.get("N_Ratio_Seas")) else None,
            "n_threshold":         float(row["N_Threshold"]) if pd.notna(row.get("N_Threshold")) else None,
            "fert_needed":         bool(row["Fert_Needed"]),
            "pred_dose_kgha":      float(row["Pred_Dose_kgha"]),
            "predicted_amount_kg": int(row["Pred_Amount_kg"]),
            "pred_cycle_days":     int(row["Pred_Cycle_Days"]),
            "days_until_next":     days,
            "next_app_date":       str(row["Next_App_Date"]),
            "status":              str(row["Schedule_Status"]),
            "priority_flag":       str(row.get("Priority_Flag","")),
            "apps_per_year":       apps,
            "n_per_app_kgha":      n_app,
            "urea_per_app_kg":     urea_app,
            "interval_days":       interval,
            "status_message":      msg,
        })
    return {
        "total":     len(results),
        "overdue":   sum(1 for r in results if r["status"] == "OVERDUE"),
        "due_today": sum(1 for r in results if r["status"] == "DUE TODAY"),
        "due_soon":  sum(1 for r in results if r["status"] == "DUE SOON"),
        "upcoming":  sum(1 for r in results if r["status"] == "UPCOMING"),
        "schedule":  results,
    }

@app.get("/fields")
def get_fields():
    fields    = sorted(STEMS_FIELDS["Field_No"].unique().tolist())
    divisions = STEMS_FIELDS.groupby("Field_No")["Division"].first().to_dict()
    return {"fields": [{"field_no": f, "division": divisions.get(f, "")} for f in fields]}


# ════════════════════════════════════════════════════════════════════
# 2. FERTILIZER — LOOKUP BASED (Division + Field_No only)
# ════════════════════════════════════════════════════════════════════

class FertilizerInput(BaseModel):
    division: Literal["AGO", "LDK", "LVO", "UDK", "UVO"]
    field_no: str


@app.post("/predict/fertilizer")
def predict_fertilizer(data: FertilizerInput):
    key    = (data.division.strip().upper(), str(data.field_no).strip())
    record = FERT_FIELD_LOOKUP.get(key)
    if record is None:
        raise HTTPException(status_code=404,
            detail=f"Field {data.field_no} not found in division {data.division}")
    apps     = 4 if record.get("vp_sd") == "SD" else 3
    n_annual = record["pred_dose_kgha"] * apps
    n_app    = round(n_annual / apps, 1)
    urea_app = round((n_app * record["extent_ha"]) / UREA_N, 1)
    interval = 365 // apps
    days     = record["days_until_next"]
    if days < 0:    msg = f"Overdue by {abs(days)} days — apply immediately"
    elif days == 0: msg = "Due today — apply now"
    elif days <= 14: msg = f"Due soon in {days} days"
    else:           msg = f"Upcoming — next application in {days} days"
    return {
        "division":            record["division"],
        "field_no":            str(record["field_no"]),
        "vp_sd":               record.get("vp_sd","VP"),
        "extent_ha":           record.get("extent_ha"),
        "yield_kgha":          record.get("yield_kgha"),
        "n_ratio_seas":        record.get("n_ratio_seas"),
        "n_threshold":         record.get("n_threshold"),
        "fert_needed":         record.get("fert_needed"),
        "pred_dose_kgha":      record.get("pred_dose_kgha"),
        "predicted_amount_kg": record.get("predicted_amount_kg"),
        "pred_cycle_days":     record.get("pred_cycle_days"),
        "days_until_next":     days,
        "next_app_date":       record.get("next_app_date"),
        "status":              record.get("status"),
        "priority_flag":       record.get("priority_flag",""),
        "apps_per_year":       apps,
        "n_per_app_kgha":      n_app,
        "urea_per_app_kg":     urea_app,
        "interval_days":       interval,
        "status_message":      msg,
        "status_code":         "success"
    }


# ════════════════════════════════════════════════════════════════════
# 3. SOIL — pH AND C% PREDICTOR (chained models)
# ════════════════════════════════════════════════════════════════════

class SoilInput(BaseModel):
    Estate:           str
    Category:         str
    VP_SD:            str
    Extent_Ha:        float
    Year_of_Planting: int
    Prediction_Year:  int
    Known_C:          Optional[float] = None

@app.post("/predict/soil")
def predict_soil(data: SoilInput):
    field_age  = data.Prediction_Year - data.Year_of_Planting
    c_pct      = data.Known_C if data.Known_C is not None else GLOBAL_C_MEAN

    est_enc_pH = ESTATE_PH_MAP.get(data.Estate,    GLOBAL_PH_MEAN)
    cat_enc_pH = CATEGORY_PH_MAP.get(data.Category, GLOBAL_PH_MEAN)

    c_age   = c_pct * field_age
    c_sq    = c_pct ** 2
    log_age = np.log1p(field_age)
    log_c   = np.log1p(c_pct)
    ha_c    = data.Extent_Ha * c_pct

    pH_row = pd.DataFrame([[
        data.Category, data.VP_SD, data.Estate,
        data.Extent_Ha, field_age, c_pct, c_age, c_sq,
        log_age, log_c, ha_c, est_enc_pH, cat_enc_pH
    ]], columns=CAT_COLS_PH + NUM_COLS_PH)

    pred_pH = round(float(SOIL_PH_MODEL.predict(pH_row)[0]), 3)

    est_enc_C = ESTATE_C_MAP.get(data.Estate,    GLOBAL_C_MEAN)
    cat_enc_C = CATEGORY_C_MAP.get(data.Category, GLOBAL_C_MEAN)
    pH_age    = pred_pH * field_age
    pH_sq     = pred_pH ** 2

    C_row = pd.DataFrame([[
        data.Category, data.VP_SD, data.Estate,
        data.Extent_Ha, field_age, pred_pH, pH_age, pH_sq,
        log_age, est_enc_C, cat_enc_C
    ]], columns=CAT_COLS_C + NUM_COLS_C)

    pred_C = round(float(SOIL_C_MODEL.predict(C_row)[0]), 3)

    ph_status = (
        "Optimal"    if 4.5 <= pred_pH <= 5.5 else
        "Acceptable" if (4.0 <= pred_pH < 4.5 or 5.5 < pred_pH <= 6.0) else
        "Poor"
    )
    c_status = "High" if pred_C >= 2.5 else "Medium" if pred_C >= 1.5 else "Low"

    return {
        "estate":           data.Estate,
        "category":         data.Category,
        "field_age_years":  field_age,
        "prediction_year":  data.Prediction_Year,
        "predicted_pH":     pred_pH,
        "pH_status":        ph_status,
        "pH_interpretation": (
            "Strongly acidic — lime application recommended." if pred_pH < 4.5 else
            "Moderately acidic — monitor and consider liming." if pred_pH < 5.5 else
            "Optimal range for tea (4.5-5.5)." if pred_pH < 6.0 else
            "Above optimal — monitor pH levels."
        ),
        "predicted_C_pct":  pred_C,
        "C_status":         c_status,
        "C_interpretation": (
            "High organic matter — excellent soil health." if c_status == "High" else
            "Medium organic matter — acceptable range." if c_status == "Medium" else
            "Low organic matter — consider organic amendments."
        ),
        "status": "success"
    }


# ════════════════════════════════════════════════════════════════════
# 4. SOIL — WET DAYS PREDICTOR
# ════════════════════════════════════════════════════════════════════

class SoilWetDaysInput(BaseModel):
    rainfall_mm: float
    month_num:   int

@app.post("/predict/soil_wetdays")
def predict_wet_days(data: SoilWetDaysInput):
    rain_sqrt = np.sqrt(data.rainfall_mm)
    X = pd.DataFrame([[data.rainfall_mm, data.month_num, rain_sqrt]],
                     columns=["Rainfall", "Month_num", "Rain_sqrt"])
    predicted_wet_days = round(float(SOIL_WET_MODEL.predict(X)[0]), 1)
    return {
        "rainfall_mm":        data.rainfall_mm,
        "month_num":          data.month_num,
        "predicted_wet_days": predicted_wet_days,
        "status":             "success"
    }


# ════════════════════════════════════════════════════════════════════
# 5. PRODUCTIVITY — LOOKUP BASED (year + month + workforce)
# ════════════════════════════════════════════════════════════════════

class ProductivityInput(BaseModel):
    year:             int
    month:            str
    female_workforce: float
    male_workforce:   float

@app.post("/predict/productivity")
def predict_productivity(data: ProductivityInput):
    rows = PROD_DATA[
        (PROD_DATA["year"].astype(int)  == int(data.year)) &
        (PROD_DATA["month"].astype(str) == str(data.month).capitalize())
    ]
    if len(rows) == 0:
        raise HTTPException(status_code=404,
            detail=f"No data found for {data.month} {data.year}. Available years: 2016-2025.")

    # yield column may be NaN for future months — that is fine, we are predicting it
    # Fill missing NDVI/EVI/irradiance/rainfall_lag_1 using medians
    row_data = rows.iloc[0].copy()
    month_name = str(data.month).capitalize()
    for col in ["NDVI","EVI","irradiance_SW_DWN","rainfall","wet_days"]:
        if pd.isna(row_data.get(col)):
            row_data[col] = PROD_MEDIANS.get(col, {}).get(month_name, 0)
    if pd.isna(row_data.get("rainfall_lag_1")):
        row_data["rainfall_lag_1"] = PROD_MEDIANS.get("rainfall_lag_1", 403.0)
    # Fix irradiance sentinel value -999
    if not pd.isna(row_data.get("irradiance_SW_DWN")):
        try:
            if float(row_data["irradiance_SW_DWN"]) == -999:
                row_data["irradiance_SW_DWN"] = PROD_MEDIANS.get("irradiance_SW_DWN", {}).get(month_name, 5.0)
        except:
            pass

    row          = row_data  # row_data has medians filled for missing values

    import math
    def _safe(val, fallback):
        try:
            v = float(val)
            return fallback if math.isnan(v) else v
        except:
            return fallback

    # Compute sin_month and cos_month at runtime from month_num
    month_num_val = int(row.get("month_num", 1)) if row.get("month_num") is not None else         {"January":1,"February":2,"March":3,"April":4,"May":5,"June":6,
         "July":7,"August":8,"September":9,"October":10,"November":11,"December":12
         }.get(str(data.month).capitalize(), 1)
    sin_month_val = math.sin(2 * math.pi * month_num_val / 12)
    cos_month_val = math.cos(2 * math.pi * month_num_val / 12)

    # Compute lag features at runtime from PROD_DATA sorted by time
    prod_sorted = PROD_DATA.sort_values(["year","month_num"]).reset_index(drop=True)
    req_idx = prod_sorted[(prod_sorted["year"]==int(data.year)) &
                          (prod_sorted["month"]==str(data.month).capitalize())].index
    if len(req_idx) > 0:
        idx = req_idx[0]
        def get_yield_at(offset):
            i = idx - offset
            if i >= 0:
                v = prod_sorted.iloc[i]["yield"]
                try:
                    f = float(v)
                    return f if not math.isnan(f) else np.nan
                except:
                    return np.nan
            return np.nan
        lag1_raw  = get_yield_at(1)
        lag2_raw  = get_yield_at(2)
        lag3_raw  = get_yield_at(3)
        lag12_raw = get_yield_at(12)
        rain_lag1_raw = np.nan
        i1 = idx - 1
        if i1 >= 0:
            try: rain_lag1_raw = float(prod_sorted.iloc[i1]["rainfall"])
            except: pass
    else:
        lag1_raw = lag2_raw = lag3_raw = lag12_raw = rain_lag1_raw = np.nan

    lag12    = _safe(lag12_raw, 35000.0)
    lag1     = _safe(lag1_raw,  lag12)
    lag2     = _safe(lag2_raw,  lag1)
    lag3     = _safe(lag3_raw,  lag2)
    momentum = lag1 - lag3
    rain_lag1_val = _safe(rain_lag1_raw, _safe(row.get("rainfall_lag_1"), 403.0))

    total_wf     = data.female_workforce + data.male_workforce
    female_ratio = data.female_workforce / total_wf if total_wf > 0 else 0.5
    # Clip ratio to training range to prevent extreme out-of-distribution predictions
    female_ratio = max(0.40, min(0.75, female_ratio))

    input_df = pd.DataFrame([{
        "rainfall":              _safe(row.get("rainfall"), 400.0),
        "wet_days":              _safe(row.get("wet_days"), 18.0),
        "female_workforceRatio": female_ratio,
        "yield_lag_1":           lag1,
        "yield_lag_2":           lag2,
        "yield_lag_3":           lag3,
        "yield_lag_12":          lag12,
        "rainfall_lag_1":        rain_lag1_val,
        "irradiance_SW_DWN":     _safe(row.get("irradiance_SW_DWN"), 5.0),
        "sin_month":             sin_month_val,
        "cos_month":             cos_month_val,
        "NDVI":                  _safe(row.get("NDVI"), 0.6),
        "EVI":                   _safe(row.get("EVI"), 0.54),
        "yield_momentum":        momentum,
    }])[PROD_SCALER_FEATURES]

    X_scaled        = PROD_SCALER.transform(input_df)
    raw_pred = float(PROD_MODEL.predict(X_scaled)[0])

    # If XGBoost extrapolates to an impossible value, fall back to seasonal estimate.
    # Seasonal estimate = 50% same month last year + 30% last month + 20% historical mean.
    # Historical monthly means computed from productivity_data.csv (2018-2025).
    MONTHLY_MEANS = {
        "January": 47481, "February": 34057, "March": 39886, "April": 35686,
        "May": 52434, "June": 38187, "July": 42073, "August": 28380,
        "September": 36932, "October": 32672, "November": 44562, "December": 44043
    }
    MIN_PLAUSIBLE = 16821
    MAX_PLAUSIBLE = 88699
    used_fallback = False

    if raw_pred < MIN_PLAUSIBLE or raw_pred > MAX_PLAUSIBLE:
        lag1       = lag1   # already filled above
        lag12      = lag12  # already filled above
        hist_mean  = MONTHLY_MEANS.get(data.month.capitalize(), 40000)
        raw_pred   = 0.5 * lag12 + 0.3 * lag1 + 0.2 * hist_mean
        used_fallback = True

    predicted_yield = round(max(MIN_PLAUSIBLE, min(MAX_PLAUSIBLE, raw_pred)))
    lower_bound     = round(max(MIN_PLAUSIBLE, predicted_yield - PROD_RMSE))
    upper_bound     = round(min(MAX_PLAUSIBLE, predicted_yield + PROD_RMSE))

    last_yr_rows = PROD_DATA[
        (PROD_DATA["year"].astype(int)  == int(data.year) - 1) &
        (PROD_DATA["month"].astype(str) == str(data.month).capitalize())
    ]
    last_year_yield = None
    yoy_change_pct  = None
    yoy_direction   = None
    if len(last_yr_rows) and not pd.isna(last_yr_rows.iloc[0]["yield"]):
        last_year_yield = round(float(last_yr_rows.iloc[0]["yield"]))
        yoy_change      = (predicted_yield - last_year_yield) / last_year_yield * 100
        yoy_change_pct  = round(yoy_change, 1)
        yoy_direction   = "up" if yoy_change > 0 else "down"

    return {
        "predicted_yield_kg":      predicted_yield,
        "lower_bound_kg":          lower_bound,
        "upper_bound_kg":          upper_bound,
        "predicted_month":         data.month,
        "predicted_year":          data.year,
        "last_year_same_month_kg": last_year_yield,
        "yoy_change_pct":          yoy_change_pct,
        "yoy_direction":           yoy_direction,
        "female_ratio_used":       round(female_ratio, 3),
        "used_seasonal_fallback":  used_fallback,
        "status":                  "success"
    }

@app.get("/productivity/months")
def get_productivity_months():
    available = PROD_DATA[PROD_DATA["yield"].notna() | PROD_DATA["year"].isin([2025,2026])][["year","month","month_num"]]
    available = available.drop_duplicates().sort_values(["year","month_num"])
    return {
        "available": [
            {"year": int(r["year"]), "month": r["month"]}
            for _, r in available.iterrows()
        ]
    }