
import requests
import json

url = "https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH/stream"

params = {
    "settlementDateFrom": "2026-01-01",
    "settlementDateTo": "2026-01-01",
    "fuelType": ["WIND"],
}

try:
    response = requests.get(url, params=params, timeout=30)

    print("Request URL:", response.url)
    print("Status code:", response.status_code)
    response.raise_for_status()

    data = response.json()

    print("Response type:", type(data).__name__)
    print("Number of records:", len(data) if isinstance(data, list) else "Not a list")

    if isinstance(data, list) and data:
        print("\nFields:", list(data[0].keys()))
        print("\nFirst 3 records:")
        print(json.dumps(data[:3], indent=2))

    elif isinstance(data, list):
        print("No records returned for this window.")

    else:
        print(json.dumps(data, indent=2)[:2000])

except requests.RequestException as error:
    print("API request failed:", error)
except ValueError as error:
    print("Invalid JSON response:", error)

if isinstance(data, list) and data:
    target = data[0]["startTime"]

    matching = [
        row for row in data
        if row["startTime"] == target
    ]

    print("\nTarget delivery time:", target)
    print("Forecast versions:", len(matching))

    for row in matching:
        print(
            "Published:", row["publishTime"],
            "| Generation:", row["generation"]
        )

if isinstance(data, list) and data:
    publish_times = {row["publishTime"] for row in data}
    delivery_times = {row["startTime"] for row in data}

    print("\nUnique publication times:", len(publish_times))
    print("Unique delivery intervals:", len(delivery_times))
