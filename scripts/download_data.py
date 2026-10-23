
import json
from pathlib import Path

import requests

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)


def fetch_data(endpoint, params):
    url = f"{BASE_URL}/datasets/{endpoint}/stream"

    response = requests.get(url, params=params, timeout=60)
    print(f"\n{endpoint} status: {response.status_code}")
    print("Request URL:", response.url)

    response.raise_for_status()
    data = response.json()

    if not isinstance(data, list):
        raise ValueError(f"Unexpected response for {endpoint}")

    print(f"{endpoint} records fetched: {len(data)}")
    return data


def save_json(filename, data):
    path = DATA_DIR / filename

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    print(f"Saved {len(data)} records to {path}")


def main():
    # Forecasts published during January.
    forecasts = fetch_data(
        "WINDFOR",
        {
            "publishDateTimeFrom": "2025-12-30T00:00:00Z",
            "publishDateTimeTo": "2026-02-02T00:00:00Z",
        },
    )

    # Actual wind generation for January delivery dates.
    actuals = fetch_data(
        "FUELHH",
        {
            "settlementDateFrom": "2026-01-01",
            "settlementDateTo": "2026-01-31",
            "fuelType": ["WIND"],
        },
    )

    save_json("wind_forecasts.json", forecasts)
    save_json("wind_actuals.json", actuals)


if __name__ == "__main__":
    main()
