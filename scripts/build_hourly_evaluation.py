"""Build the hourly evaluation view from half-hour observations.

The two half-hour actuals have equal duration and are recorded as MW. Their
arithmetic mean is therefore the hourly time-weighted average MW, suitable for
comparison with an hourly forecast expressed as average MW. The source files
do not explicitly say whether the hourly forecast is an interval average or a
point-in-time value; see docs/evaluation-methodology.md for this limitation.
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def aggregate_hourly_actuals(actuals: pd.DataFrame) -> pd.DataFrame:
    """Average equal-duration half-hour actual MW observations by UTC hour."""
    actuals = actuals.copy()
    actuals["hour"] = actuals["delivery_time"].dt.floor("h")
    return actuals.groupby("hour", as_index=False).agg(
        actual_mw=("actual_mw", "mean")
    )


def build_hourly_dataset(
    actuals: pd.DataFrame, hourly_forecasts: pd.DataFrame
) -> pd.DataFrame:
    """Join hourly actual averages with the already-selected hourly forecasts."""
    hourly_actuals = aggregate_hourly_actuals(actuals)
    result = hourly_actuals.merge(hourly_forecasts, on="hour", how="left")
    result["error_mw"] = result["forecast_mw"] - result["actual_mw"]
    result["absolute_error_mw"] = result["error_mw"].abs()
    return result


def main() -> None:
    actuals = pd.read_csv(
        DATA / "evaluation_dataset.csv", parse_dates=["delivery_time"]
    )

    # Forecasts are already selected in evaluation_dataset.csv. The same
    # hourly forecast is repeated on both half-hour actual rows.
    hourly_forecasts = (
        actuals.sort_values("delivery_time")
        .drop_duplicates("forecast_hour")
        .rename(columns={"forecast_hour": "hour"})
        [["hour", "forecast_mw", "forecast_publish_time", "cutoff_time"]]
    )

    result = build_hourly_dataset(actuals, hourly_forecasts)
    output = DATA / "hourly_evaluation_dataset.csv"
    result.to_csv(output, index=False)

    print("Hourly dataset:", output)
    print("Hourly intervals:", len(result))
    print("Missing forecasts:", result["forecast_mw"].isna().sum())
    print("\nFirst 5 rows:")
    print(result.head().to_string(index=False))


if __name__ == "__main__":
    main()
