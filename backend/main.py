
from pathlib import Path
import logging

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT_DIR / "data" / "hourly_evaluation_dataset.csv"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Wind Forecast Accuracy API",
    description="API for Great Britain wind generation forecast evaluation.",
    version="1.0.0",
)

# Allow the local React development server to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_data() -> pd.DataFrame:
    if not DATA_FILE.exists():
        logger.error("Evaluation dataset not found: %s", DATA_FILE)
        raise HTTPException(
            status_code=500,
            detail="Evaluation dataset not found. Run the data preparation scripts first.",
        )

    try:
        df = pd.read_csv(DATA_FILE)
        required = {
            "hour",
            "actual_mw",
            "forecast_mw",
            "forecast_publish_time",
            "cutoff_time",
        }

        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Missing columns: {sorted(missing)}")

        df["hour"] = pd.to_datetime(df["hour"], utc=True, errors="coerce")
        df["actual_mw"] = pd.to_numeric(df["actual_mw"], errors="coerce")
        df["forecast_mw"] = pd.to_numeric(df["forecast_mw"], errors="coerce")
        df = df.dropna(subset=["hour", "actual_mw", "forecast_mw"])
        return df.sort_values("hour")

    except (OSError, ValueError, pd.errors.ParserError) as exc:
        logger.exception("Unable to read evaluation dataset")
        raise HTTPException(
            status_code=500,
            detail="Could not read a valid evaluation dataset.",
        ) from exc


def calculate_metrics(df: pd.DataFrame) -> dict:
    if df.empty:
        raise HTTPException(
            status_code=404,
            detail="No forecast and actual data found for the selected dates.",
        )

    error = df["forecast_mw"] - df["actual_mw"]
    absolute_error = error.abs()

    return {
        "intervals_evaluated": int(len(df)),
        "mae_mw": round(float(absolute_error.mean()), 2),
        "rmse_mw": round(float((error.pow(2).mean()) ** 0.5), 2),
        "bias_mw": round(float(error.mean()), 2),
        "median_absolute_error_mw": round(float(absolute_error.median()), 2),
        "p90_absolute_error_mw": round(float(absolute_error.quantile(0.90)), 2),
        "p95_absolute_error_mw": round(float(absolute_error.quantile(0.95)), 2),
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "wind-forecast-api"}


@app.get("/api/metrics")
def get_metrics(
    start_date: str | None = Query(default=None, description="Start date, YYYY-MM-DD"),
    end_date: str | None = Query(default=None, description="End date, YYYY-MM-DD"),
):
    df = load_data()

    try:
        if start_date:
            start = pd.Timestamp(start_date, tz="UTC")
            df = df[df["hour"] >= start]

        if end_date:
            # Include the entire end date.
            end = pd.Timestamp(end_date, tz="UTC") + pd.Timedelta(days=1)
            df = df[df["hour"] < end]

    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=400,
            detail="Dates must use YYYY-MM-DD format.",
        ) from exc

    return calculate_metrics(df)


@app.get("/api/forecasts")
def get_forecasts(
    start_date: str | None = Query(default=None, description="Start date, YYYY-MM-DD"),
    end_date: str | None = Query(default=None, description="End date, YYYY-MM-DD"),
):
    df = load_data()

    try:
        if start_date:
            start = pd.Timestamp(start_date, tz="UTC")
            df = df[df["hour"] >= start]

        if end_date:
            end = pd.Timestamp(end_date, tz="UTC") + pd.Timedelta(days=1)
            df = df[df["hour"] < end]

    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=400,
            detail="Dates must use YYYY-MM-DD format.",
        ) from exc

    records = df.copy()
    records["hour"] = records["hour"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "count": len(records),
        "data": records[
            [
                "hour",
                "actual_mw",
                "forecast_mw",
                "forecast_publish_time",
                "cutoff_time",
            ]
        ].to_dict(orient="records"),
    }
