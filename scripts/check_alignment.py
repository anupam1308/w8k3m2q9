
import json
from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

with open(DATA_DIR / "wind_forecasts.json", encoding="utf-8") as f:
    forecasts = pd.DataFrame(json.load(f))

with open(DATA_DIR / "wind_actuals.json", encoding="utf-8") as f:
    actuals = pd.DataFrame(json.load(f))

forecasts["startTime"] = pd.to_datetime(forecasts["startTime"], utc=True)
forecasts["publishTime"] = pd.to_datetime(forecasts["publishTime"], utc=True)
actuals["startTime"] = pd.to_datetime(actuals["startTime"], utc=True)

# Inspect forecasts for consecutive hours
sample = forecasts[
    (forecasts["publishTime"] == pd.Timestamp("2026-01-01T07:30:00Z"))
    & (forecasts["startTime"] >= pd.Timestamp("2026-01-02T10:00:00Z"))
    & (forecasts["startTime"] <= pd.Timestamp("2026-01-02T14:00:00Z"))
].sort_values("startTime")

print("Forecast records from one publication:")
print(sample[["publishTime", "startTime", "generation"]].to_string(index=False))

print("\nActual generation around the same period:")
actual_sample = actuals[
    (actuals["startTime"] >= pd.Timestamp("2026-01-02T10:00:00Z"))
    & (actuals["startTime"] <= pd.Timestamp("2026-01-02T14:00:00Z"))
].sort_values("startTime")

print(actual_sample[["startTime", "generation"]].to_string(index=False))
