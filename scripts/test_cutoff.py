
import json
from pathlib import Path

import pandas as pd

from build_evaluation import select_forecast

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_json(filename):
    path = DATA_DIR / filename
    with path.open(encoding="utf-8") as file:
        return pd.DataFrame(json.load(file))


def main():
    forecasts = load_json("wind_forecasts.json")
    actuals = load_json("wind_actuals.json")

    # Parse timestamps consistently in UTC.
    forecasts["publishTime"] = pd.to_datetime(
        forecasts["publishTime"], utc=True
    )
    forecasts["startTime"] = pd.to_datetime(
        forecasts["startTime"], utc=True
    )
    actuals["startTime"] = pd.to_datetime(
        actuals["startTime"], utc=True
    )

    # 1. Test one delivery interval.
    delivery_time = pd.Timestamp("2026-01-02T12:00:00Z")
    cutoff, selected = select_forecast(forecasts, delivery_time)

    print("--- Example cutoff test ---")
    print("Delivery time (UTC):", delivery_time)
    print("Decision cutoff (UTC):", cutoff)

    if selected is not None:
        print("Selected publication:", selected["publishTime"])
        print("Forecast generation (MW):", selected["generation"])
    else:
        print("No forecast available by cutoff.")

    # 2. Check coverage for all January actual intervals.
    results = []

    for delivery_time in actuals["startTime"]:
        cutoff, selected = select_forecast(forecasts, delivery_time)

        results.append({
            "delivery_time": delivery_time,
            "cutoff": cutoff,
            "forecast_available": selected is not None,
            "forecast_generation": (
                selected["generation"] if selected is not None else None
            ),
            "forecast_publish_time": (
                selected["publishTime"] if selected is not None else None
            ),
        })

    coverage = pd.DataFrame(results)
    missing = coverage[~coverage["forecast_available"]]

    available = int(coverage["forecast_available"].sum())
    total = len(coverage)

    print("\n--- First 20 intervals without forecasts ---")
    if missing.empty:
        print("No missing intervals.")
    else:
        print(missing["delivery_time"].head(20).to_string(index=False))

    print("\n--- Missing intervals by minute ---")
    if missing.empty:
        print("No missing intervals.")
    else:
        print(
            missing["delivery_time"]
            .dt.minute.value_counts()
            .sort_index()
            .to_string()
        )

    print("\n--- January Forecast Coverage ---")
    print("Actual intervals:", total)
    print("Intervals with forecast:", available)
    print("Intervals without forecast:", total - available)
    print(
        "Coverage (%):",
        round(available / total * 100, 2) if total else 0,
    )


if __name__ == "__main__":
    main()
