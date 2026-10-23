# Wind forecast evaluation methodology

## Decision cutoff and forecast selection

For a target delivery hour, the delivery timestamp is converted to the
`Europe/London` timezone first. The decision cutoff is 09:00 on the previous
London calendar date, then converted to UTC for comparison with the UTC
publication timestamps. This makes the cutoff 09:00 UTC in GMT and 08:00 UTC
in BST, and handles UTC timestamps whose London local date differs from their
UTC date (for example, 23:00 UTC during BST).

Only forecast records for the target UTC delivery hour published at or before
that cutoff are eligible. Among eligible records, the latest publication is
selected. A publication exactly at the cutoff is eligible.

## Hourly actual aggregation

The hourly dataset keeps the existing method: group the two half-hour actual
observations by UTC hour and take their arithmetic mean. Each observation has
the same half-hour duration and is expressed as MW; their mean is thus the
time-weighted average power over that hour, which can be compared with an
hourly forecast expressed as average MW. If energy for the hour were the
target measure, the corresponding value would be average MW multiplied by one
hour, expressed in MWh.

The input files identify forecast values in MW but do not explicitly state
whether an hourly forecast is an average over the delivery hour or a
point-in-time value. The aggregation above is retained as requested; confirming
the forecast's interval semantics against the assignment or source data
definition remains an open specification question.

## Metrics

For every matched hour, error is `forecast_mw - actual_mw`. The reported
metrics are MAE, RMSE, mean error (bias), median absolute error, and the 90th
and 95th percentiles of absolute error. Percentiles use pandas' default linear
quantile interpolation. Metric formulas and rounding in the API are unchanged.
