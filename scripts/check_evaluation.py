
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILE = ROOT / "data" / "evaluation_dataset.csv"

df = pd.read_csv(FILE, parse_dates=[
    "delivery_time",
    "cutoff_time",
    "forecast_hour",
    "forecast_publish_time",
])

print("--- Evaluation validation ---")
print("Rows:", len(df))
print("Duplicate delivery times:", df["delivery_time"].duplicated().sum())
print("Missing actuals:", df["actual_mw"].isna().sum())
print("Missing forecasts:", df["forecast_mw"].isna().sum())

invalid_cutoffs = df[
    df["forecast_publish_time"].notna()
    & (df["forecast_publish_time"] > df["cutoff_time"])
]
print("Forecasts published after cutoff:", len(invalid_cutoffs))

print("\n--- Sample in chronological order ---")
print(
    df.sort_values("delivery_time")[
        [
            "delivery_time",
            "cutoff_time",
            "forecast_publish_time",
            "forecast_hour",
            "forecast_mw",
            "actual_mw",
        ]
    ].head(10).to_string(index=False)
)

print("\n--- Half-hour alignment check ---")
print(
    df.groupby(df["delivery_time"].dt.minute).size().to_string()
)

if not invalid_cutoffs.empty:
    print("\nWARNING: Some forecasts violate the cutoff.")
elif df["delivery_time"].duplicated().any():
    print("\nWARNING: Duplicate delivery times found.")
else:
    print("\nBasic validation passed.")
    print("Forecast-to-actual time alignment still needs confirmation.")
