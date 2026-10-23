from math import sqrt

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import backend.main as api


EXPECTED_METRIC_KEYS = {
    "intervals_evaluated",
    "mae_mw",
    "rmse_mw",
    "bias_mw",
    "median_absolute_error_mw",
    "p90_absolute_error_mw",
    "p95_absolute_error_mw",
}
EXPECTED_FORECAST_KEYS = {
    "hour",
    "actual_mw",
    "forecast_mw",
    "forecast_publish_time",
    "cutoff_time",
}


@pytest.fixture
def evaluation_frame() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "hour": "2026-01-01T00:00:00Z",
            "actual_mw": 100.0,
            "forecast_mw": 101.0,
            "forecast_publish_time": "2025-12-31T07:30:00Z",
            "cutoff_time": "2025-12-31T09:00:00Z",
        },
        {
            "hour": "2026-01-01T12:00:00Z",
            "actual_mw": 100.0,
            "forecast_mw": 102.0,
            "forecast_publish_time": "2025-12-31T07:30:00Z",
            "cutoff_time": "2025-12-31T09:00:00Z",
        },
        {
            "hour": "2026-01-02T00:00:00Z",
            "actual_mw": 100.0,
            "forecast_mw": 103.0,
            "forecast_publish_time": "2026-01-01T07:30:00Z",
            "cutoff_time": "2026-01-01T09:00:00Z",
        },
        {
            "hour": "2026-01-02T23:00:00Z",
            "actual_mw": 100.0,
            "forecast_mw": 104.0,
            "forecast_publish_time": "2026-01-01T07:30:00Z",
            "cutoff_time": "2026-01-01T09:00:00Z",
        },
    ])


@pytest.fixture
def client(tmp_path, monkeypatch, evaluation_frame):
    csv_path = tmp_path / "hourly_evaluation_dataset.csv"
    evaluation_frame.to_csv(csv_path, index=False)
    monkeypatch.setattr(api, "DATA_FILE", csv_path)
    with TestClient(api.app) as test_client:
        yield test_client


def expected_metrics(frame: pd.DataFrame) -> dict[str, float | int]:
    errors = frame["forecast_mw"] - frame["actual_mw"]
    absolute_errors = errors.abs()
    return {
        "intervals_evaluated": int(len(frame)),
        "mae_mw": round(float(absolute_errors.mean()), 2),
        "rmse_mw": round(float(sqrt((errors.pow(2)).mean())), 2),
        "bias_mw": round(float(errors.mean()), 2),
        "median_absolute_error_mw": round(float(absolute_errors.median()), 2),
        "p90_absolute_error_mw": round(float(absolute_errors.quantile(0.90)), 2),
        "p95_absolute_error_mw": round(float(absolute_errors.quantile(0.95)), 2),
    }


def filter_frame(frame: pd.DataFrame, params: dict[str, str]) -> pd.DataFrame:
    hours = pd.to_datetime(frame["hour"], utc=True)
    mask = pd.Series(True, index=frame.index)
    if "start_date" in params:
        start = pd.Timestamp(params["start_date"], tz="UTC")
        mask &= hours >= start
    if "end_date" in params:
        end = pd.Timestamp(params["end_date"], tz="UTC") + pd.Timedelta(days=1)
        mask &= hours < end
    return frame.loc[mask]


def test_health_returns_ok_and_expected_service(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "wind-forecast-api"}


def test_metrics_returns_dataset_calculated_metrics(client, evaluation_frame):
    response = client.get("/api/metrics")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == EXPECTED_METRIC_KEYS
    assert body == expected_metrics(evaluation_frame)


@pytest.mark.parametrize(
    ("params", "expected_hours"),
    [
        ({"start_date": "2026-01-02"}, 2),
        ({"end_date": "2026-01-01"}, 2),
        ({"start_date": "2026-01-02", "end_date": "2026-01-02"}, 2),
    ],
)
def test_metrics_date_filters_are_inclusive_and_applied(client, evaluation_frame, params, expected_hours):
    response = client.get("/api/metrics", params=params)

    selected = filter_frame(evaluation_frame, params)

    assert response.status_code == 200
    assert response.json()["intervals_evaluated"] == expected_hours
    assert response.json() == expected_metrics(selected)


def test_metrics_empty_range_returns_clear_404(client):
    response = client.get(
        "/api/metrics",
        params={"start_date": "2025-12-01", "end_date": "2025-12-02"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "No forecast and actual data found for the selected dates."


@pytest.mark.parametrize("endpoint", ["/api/metrics", "/api/forecasts"])
@pytest.mark.parametrize("date_param", ["start_date", "end_date"])
def test_invalid_date_returns_400(client, endpoint, date_param):
    response = client.get(endpoint, params={date_param: "not-a-date"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Dates must use YYYY-MM-DD format."


def test_forecasts_returns_count_and_expected_fields(client):
    response = client.get("/api/forecasts")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 4
    assert len(body["data"]) == 4
    assert all(set(record) == EXPECTED_FORECAST_KEYS for record in body["data"])


@pytest.mark.parametrize(
    ("params", "expected_hours"),
    [
        ({"start_date": "2026-01-02"}, ["2026-01-02T00:00:00Z", "2026-01-02T23:00:00Z"]),
        ({"end_date": "2026-01-01"}, ["2026-01-01T00:00:00Z", "2026-01-01T12:00:00Z"]),
        ({"start_date": "2026-01-02", "end_date": "2026-01-02"}, ["2026-01-02T00:00:00Z", "2026-01-02T23:00:00Z"]),
    ],
)
def test_forecasts_date_filters_restrict_inclusive_range(client, params, expected_hours):
    response = client.get("/api/forecasts", params=params)

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == len(expected_hours)
    assert [record["hour"] for record in body["data"]] == expected_hours


def test_forecasts_empty_range_returns_empty_collection(client):
    response = client.get(
        "/api/forecasts",
        params={"start_date": "2025-12-01", "end_date": "2025-12-02"},
    )

    assert response.status_code == 200
    assert response.json() == {"count": 0, "data": []}


def test_missing_dataset_returns_clear_http_500(client, monkeypatch, tmp_path):
    missing_path = tmp_path / "missing.csv"
    monkeypatch.setattr(api, "DATA_FILE", missing_path)

    response = client.get("/api/metrics")

    assert response.status_code == 500
    assert "Evaluation dataset not found" in response.json()["detail"]


def test_malformed_dataset_returns_clear_http_500(client, monkeypatch, tmp_path):
    malformed_path = tmp_path / "malformed.csv"
    malformed_path.write_text("unexpected_column\nvalue\n", encoding="utf-8")
    monkeypatch.setattr(api, "DATA_FILE", malformed_path)

    response = client.get("/api/forecasts")

    assert response.status_code == 500
    assert response.json()["detail"] == "Could not read a valid evaluation dataset."
