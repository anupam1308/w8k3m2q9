
import pandas as pd
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
FILE = ROOT / "data" / "hourly_evaluation_dataset.csv"

df = pd.read_csv(FILE)

# Keep only rows with valid actual and forecast values.
df = df.dropna(subset=["actual_mw", "forecast_mw"])

error = df["forecast_mw"] - df["actual_mw"]
absolute_error = error.abs()

metrics = {
    "Hourly intervals evaluated": len(df),
    "MAE (MW)": absolute_error.mean(),
    "RMSE (MW)": np.sqrt((error ** 2).mean()),
    "Mean Bias (MW)": error.mean(),
    "Median Absolute Error (MW)": absolute_error.median(),
    "P90 Absolute Error (MW)": absolute_error.quantile(0.90),
    "P95 Absolute Error (MW)": absolute_error.quantile(0.95),
}

print("\n--- Wind Forecast Accuracy Metrics ---")
for name, value in metrics.items():
    if isinstance(value, (int, np.integer)):
        print(f"{name}: {value}")
    else:
        print(f"{name}: {value:,.2f}")

print("\nInterpretation:")
print("MAE/RMSE/P90/P95 lower is generally better.")
print("Positive bias means forecasts tend to overpredict.")
print("Negative bias means forecasts tend to underpredict.")
