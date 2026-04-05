import requests
from datetime import datetime, date

BASE_URL = "https://minuka-stems-backend.hf.space"
TIMEOUT  = 30


def _post(endpoint: str, payload: dict):
    try:
        resp = requests.post(f"{BASE_URL}{endpoint}", json=payload, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json(), None
    except requests.exceptions.Timeout:
        return None, "Request timed out. The backend may be starting up — please try again."
    except requests.exceptions.ConnectionError:
        return None, "Could not reach the backend. Please check your connection."
    except requests.exceptions.HTTPError as e:
        try:
            detail = resp.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        return None, f"Backend error ({resp.status_code}): {detail}"
    except Exception as e:
        return None, f"Unexpected error: {e}"


def _get(endpoint: str, params: dict = None):
    try:
        resp = requests.get(f"{BASE_URL}{endpoint}", params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json(), None
    except requests.exceptions.Timeout:
        return None, "Request timed out. The backend may be starting up — please try again."
    except requests.exceptions.ConnectionError:
        return None, "Could not reach the backend. Please check your connection."
    except requests.exceptions.HTTPError as e:
        return None, f"Backend error ({resp.status_code}): {e}"
    except Exception as e:
        return None, f"Unexpected error: {e}"


def predict_stems(field_no: str, last_harvest_date: str, target_month: str = None):
    target_month_formatted = None
    if target_month:
        try:
            month_num = datetime.strptime(target_month, "%B").month
            year = date.today().year
            target_month_formatted = f"{year}-{month_num:02d}"
        except Exception:
            target_month_formatted = None

    payload = {
        "field_no":          field_no,
        "last_harvest_date": last_harvest_date,
        "target_month":      target_month_formatted,
    }
    return _post("/predict/stems", payload)


def predict_fertilizer(division: str, field_no: str):
    payload = {
        "division": division,
        "field_no": field_no,
    }
    return _post("/predict/fertilizer", payload)


def get_fertilizer_schedule(division: str = None, status: str = None):
    params = {}
    if division:
        params["division"] = division
    if status:
        params["status"] = status
    return _get("/schedule", params=params if params else None)


def predict_soil(
    estate: str,
    category: str,
    vp_sd: str,
    extent_ha: float,
    year_of_planting: int,
    prediction_year: int,
    known_c: float = None,
):
    payload = {
        "Estate":           estate,
        "Category":         category,
        "VP_SD":            vp_sd,
        "Extent_Ha":        extent_ha,
        "Year_of_Planting": year_of_planting,
        "Prediction_Year":  prediction_year,
        "Known_C":          known_c,
    }
    return _post("/predict/soil", payload)


def predict_soil_wetdays(rainfall_mm: float, month_num: int):
    return _post("/predict/soil_wetdays", {
        "rainfall_mm": rainfall_mm,
        "month_num":   month_num,
    })


def predict_productivity(
    year: int,
    month: str,
    female_workforce: float,
    male_workforce: float,
):
    payload = {
        "year":             year,
        "month":            month,
        "female_workforce": female_workforce,
        "male_workforce":   male_workforce,
    }
    return _post("/predict/productivity", payload)


def get_fields():
    return _get("/fields")


def get_productivity_months():
    return _get("/productivity/months")