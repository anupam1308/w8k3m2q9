import pandas as pd
import pytest

from backend.main import calculate_metrics
from scripts.build_evaluation import decision_cutoff, select_forecast
from scripts.build_hourly_evaluation import aggregate_hourly_actuals


@pytest.mark.parametrize(
    ("delivery_time", "expected_cutoff"),
    [
        # GMT: D-1 09:00 local is 09:00 UTC.
        ("2026-01-15T12:00:00Z", "2026-01-14T09:00:00Z"),
        # BST: D-1 09:00 local is 08:00 UTC.
        ("2026-07-15T12:00:00Z", "2026-07-14T08:00:00Z"),
        # On the first day after spring transition, D-1 is already a BST date.
        ("2026-03-30T12:00:00Z", "2026-03-29T08:00:00Z"),
        # On the first day after autumn transition, D-1 is a GMT date.
        ("2026-10-26T12:00:00Z", "2026-10-25T09:00:00Z"),
    ],
)
def test_cutoff_uses_london_wall_time_across_gmt_and_dst(
    delivery_time: str, expected_cutoff: str
) -> None:
    assert decision_cutoff(pd.Timestamp(delivery_time)) == pd.Timestamp(expected_cutoff)


def test_midnight_utc_delivery_uses_london_local_delivery_date() -> None:
    # 23:00 UTC on July 2 is midnight on July 3 in London.
    delivery = pd.Timestamp("2026-07-02T23:00:00Z")
    assert decision_cutoff(delivery) == pd.Timestamp("2026-07-02T08:00:00Z")


def test_naive_delivery_timestamp_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        decision_cutoff(pd.Timestamp("2026-07-15 12:00:00"))


def _forecast_rows(delivery: pd.Timestamp, publications: list[str]) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "startTime": delivery.floor("h"),
            "publishTime": pd.Timestamp(publication),
            "generation": value,
        }
        for value, publication in enumerate(publications, start=100)
    ])


def test_selects_latest_eligible_forecast() -> None:
    delivery = pd.Timestamp("2026-07-02T23:00:00Z")
    forecasts = _forecast_rows(delivery, [
        "2026-07-02T06:00:00Z",
        "2026-07-02T07:30:00Z",
    ])

    cutoff, selected = select_forecast(forecasts, delivery)

    assert cutoff == pd.Timestamp("2026-07-02T08:00:00Z")
    assert selected is not None
    assert selected["publishTime"] == pd.Timestamp("2026-07-02T07:30:00Z")
    assert selected["generation"] == 101


def test_publication_exactly_at_cutoff_is_eligible() -> None:
    delivery = pd.Timestamp("2026-07-02T23:00:00Z")
    forecasts = _forecast_rows(delivery, ["2026-07-02T08:00:00Z"])

    cutoff, selected = select_forecast(forecasts, delivery)

    assert selected is not None
    assert selected["publishTime"] == cutoff


def test_publication_just_after_cutoff_is_ineligible() -> None:
    delivery = pd.Timestamp("2026-07-02T23:00:00Z")
    forecasts = _forecast_rows(delivery, ["2026-07-02T08:00:00.000001Z"])

    cutoff, selected = select_forecast(forecasts, delivery)

    assert cutoff == pd.Timestamp("2026-07-02T08:00:00Z")
    assert selected is None


def test_averages_two_half_hour_actuals_per_utc_hour() -> None:
    actuals = pd.DataFrame({
        "delivery_time": pd.to_datetime([
            "2026-01-01T00:00:00Z",
            "2026-01-01T00:30:00Z",
            "2026-01-01T01:00:00Z",
            "2026-01-01T01:30:00Z",
        ], utc=True),
        "actual_mw": [10.0, 20.0, 40.0, 60.0],
    })

    hourly = aggregate_hourly_actuals(actuals)

    assert hourly["actual_mw"].tolist() == [15.0, 50.0]
    assert hourly["hour"].tolist() == [
        pd.Timestamp("2026-01-01T00:00:00Z"),
        pd.Timestamp("2026-01-01T01:00:00Z"),
    ]


def test_calculates_all_six_metrics_using_forecast_minus_actual() -> None:
    frame = pd.DataFrame({
        "actual_mw": [100.0, 100.0, 100.0, 100.0],
        "forecast_mw": [101.0, 102.0, 103.0, 104.0],
    })

    metrics = calculate_metrics(frame)

    assert metrics == {
        "intervals_evaluated": 4,
        "mae_mw": 2.5,
        "rmse_mw": 2.74,
        "bias_mw": 2.5,
        "median_absolute_error_mw": 2.5,
        "p90_absolute_error_mw": 3.7,
        "p95_absolute_error_mw": 3.85,
    }
