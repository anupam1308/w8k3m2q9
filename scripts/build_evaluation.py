
import json
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"

FORECAST_FILE = DATA_DIR / "wind_forecasts.json"
ACTUAL_FILE = DATA_DIR / "wind_actuals.json"
OUTPUT_FILE = DATA_DIR / "evaluation_dataset.csv"
LONDON_TZ = ZoneInfo("Europe/London")


def load_json(path: Path) -> pd.DataFrame:
    with path.open("r", encoding="utf-8") as file:
        return pd.DataFrame(json.load(file))


def decision_cutoff(delivery_time: pd.Timestamp) -> pd.Timestamp:
    """Return D-1 09:00 Europe/London for the local delivery date, in UTC.

    Delivery timestamps must be timezone-aware. The delivery date is derived
    after converting the timestamp to London time, so a late UTC hour that is
    already the next local calendar day gets the correct D-1 cutoff.
    """
    delivery_time = pd.Timestamp(delivery_time)
    if delivery_time.tzinfo is None:
        raise ValueError("delivery_time must be timezone-aware")

    local_delivery = delivery_time.to_pydatetime().astimezone(LONDON_TZ)
    previous_local_date = local_delivery.date() - timedelta(days=1)
    local_cutoff = datetime.combine(
        previous_local_date, time(9, 0), tzinfo=LONDON_TZ
    )
    return pd.Timestamp(local_cutoff.astimezone(timezone.utc))


def select_forecast(
    forecasts: pd.DataFrame, delivery_time: pd.Timestamp
) -> tuple[pd.Timestamp, pd.Series | None]:
    """Select the latest forecast for the containing UTC hour published by cutoff."""
    delivery_time = pd.Timestamp(delivery_time)
    cutoff = decision_cutoff(delivery_time)
    forecast_hour = delivery_time.floor("h")
    eligible = forecasts[
        (forecasts["startTime"] == forecast_hour)
        & (forecasts["publishTime"] <= cutoff)
    ]
    if eligible.empty:
        return cutoff, None
    selected = eligible.loc[eligible["publishTime"].idxmax()]
    return cutoff, selected


def main() -> None:
    forecasts = load_json(FORECAST_FILE)
    actuals = load_json(ACTUAL_FILE)

    for column in ["publishTime", "startTime"]:
        forecasts[column] = pd.to_datetime(
            forecasts[column], utc=True
        )

    actuals["startTime"] = pd.to_datetime(
        actuals["startTime"], utc=True
    )

    forecasts["generation"] = pd.to_numeric(
        forecasts["generation"], errors="coerce"
    )
    actuals["generation"] = pd.to_numeric(
        actuals["generation"], errors="coerce"
    )

    forecasts = forecasts.dropna(
        subset=["publishTime", "startTime", "generation"]
    )
    actuals = actuals.dropna(
        subset=["startTime", "generation"]
    )

    # Keep the forecast publication history: multiple versions
    # may exist for the same delivery hour.
    rows = []

    for _, actual in actuals.iterrows():
        delivery_time = actual["startTime"]
        # Provisional alignment: associate each half-hour actual
        # with the forecast for its containing hour.
        forecast_hour = delivery_time.floor("h")
        cutoff, selected = select_forecast(forecasts, delivery_time)

        if selected is None:
            rows.append({
                "delivery_time": delivery_time,
                "cutoff_time": cutoff,
                "actual_mw": actual["generation"],
                "forecast_hour": forecast_hour,
                "forecast_publish_time": pd.NaT,
                "forecast_mw": None,
            })
            continue

        rows.append({
            "delivery_time": delivery_time,
            "cutoff_time": cutoff,
            "actual_mw": actual["generation"],
            "forecast_hour": forecast_hour,
            "forecast_publish_time": selected["publishTime"],
            "forecast_mw": selected["generation"],
        })

    evaluation = pd.DataFrame(rows)
    evaluation["error_mw"] = (
        evaluation["forecast_mw"] - evaluation["actual_mw"]
    )
    evaluation["absolute_error_mw"] = evaluation["error_mw"].abs()

    evaluation.to_csv(OUTPUT_FILE, index=False)

    total = len(evaluation)
    available = int(evaluation["forecast_mw"].notna().sum())

    print("Evaluation dataset created:", OUTPUT_FILE)
    print("Actual intervals:", total)
    print("Intervals with forecast:", available)
    print("Intervals without forecast:", total - available)
    print(
        "Forecast coverage (%):",
        round(available / total * 100, 2) if total else 0,
    )
    print("\nSample rows:")
    print(evaluation.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
