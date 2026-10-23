
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

for filename in ["wind_forecasts.json", "wind_actuals.json"]:
    path = DATA_DIR / filename

    with path.open("r", encoding="utf-8") as file:
        records = json.load(file)

    print(f"\n--- {filename} ---")
    print("Total records:", len(records))

    if records:
        print("First startTime:", min(r["startTime"] for r in records))
        print("Last startTime:", max(r["startTime"] for r in records))
        print("Unique delivery times:", len({r["startTime"] for r in records}))
        print("Missing generation:", sum(r.get("generation") is None for r in records))

import pandas as pd

with (DATA_DIR / "wind_forecasts.json").open(encoding="utf-8") as f:
    forecasts = json.load(f)

with (DATA_DIR / "wind_actuals.json").open(encoding="utf-8") as f:
    actuals = json.load(f)

forecast_times = sorted({
    pd.Timestamp(row["startTime"])
    for row in forecasts
})

actual_times = sorted({
    pd.Timestamp(row["startTime"])
    for row in actuals
})

print("\n--- Forecast time intervals ---")
print("First 15 unique forecast times:")
for t in forecast_times[:15]:
    print(t)

print("\n--- Actual time intervals ---")
print("First 15 actual times:")
for t in actual_times[:15]:
    print(t)
