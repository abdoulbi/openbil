"""Per-series forecasting with chronological validation and untouched final holdout."""

import numpy as np
import pandas as pd

CANDIDATES = ("naive", "drift", "mean3", "trend5")


def predict(y, horizon, model):
    y = np.asarray(y, dtype=float)
    if len(y) == 0 or horizon < 1:
        raise ValueError("History and positive horizon required")
    if model == "naive":
        return np.repeat(y[-1], horizon)
    if model == "drift":
        if len(y) < 2:
            raise ValueError("Drift needs at least two observations")
        return y[-1] + np.arange(1, horizon + 1) * (y[-1] - y[0]) / (len(y) - 1)
    if model == "mean3":
        if len(y) < 3:
            raise ValueError("Mean3 needs three observations")
        return np.repeat(np.mean(y[-3:]), horizon)
    if model == "trend5":
        if len(y) < 5:
            raise ValueError("Trend5 needs five observations")
        slope = np.polyfit(np.arange(5), y[-5:], 1)[0]
        return y[-1] + np.arange(1, horizon + 1) * slope
    raise ValueError("Unknown model")


def forecast(frame, horizon=3):
    if not 1 <= horizon <= 5:
        raise ValueError("Horizon must be 1..5")
    df = frame.sort_values("period").copy()
    if df["period"].duplicated().any():
        raise ValueError("Choose exactly one country and indicator")
    df = df[
        df.value.notna()
        & (~df.data_status.isin(["projected", "missing"]))
        & (df.quality_status != "rejected")
    ]
    if df.empty:
        raise ValueError("No eligible history")
    gaps = np.flatnonzero(np.diff(df.period.to_numpy()) != 1)
    if len(gaps):
        df = df.iloc[gaps[-1] + 1 :]
    if len(df) < 14:
        raise ValueError("At least 14 consecutive eligible annual values are required")
    y = df.value.to_numpy(dtype=float)
    if not np.isfinite(y).all():
        raise ValueError("Nonfinite history")

    test_size, validation_size = 3, 4
    split = len(y) - test_size
    scores = {}
    for model in CANDIDATES:
        errors = [
            abs(y[t] - predict(y[:t], 1, model)[0])
            for t in range(split - validation_size, split)
        ]
        scores[model] = float(np.mean(errors))
    selected = min(CANDIDATES, key=lambda model: scores[model])

    actual = y[split:]
    predicted = predict(y[:split], test_size, selected)
    naive = predict(y[:split], test_size, "naive")
    test_mae = float(np.mean(np.abs(actual - predicted)))
    naive_test_mae = float(np.mean(np.abs(actual - naive)))
    # Final test is diagnostic only: no reselection using its observations.
    status = (
        "below_naive_on_holdout"
        if test_mae > naive_test_mae + 1e-12
        else "not_below_naive_on_holdout"
    )
    test = pd.DataFrame({
        "period": df.period.iloc[split:].to_numpy(),
        "actual": actual, "prediction": predicted, "naive": naive,
    })
    future = pd.DataFrame({
        "period": np.arange(int(df.period.iloc[-1]) + 1, int(df.period.iloc[-1]) + horizon + 1),
        "value": predict(y, horizon, selected),
        "data_status": "projected", "model": selected,
    })
    return dict(
        model=selected,
        selection_method="rolling_origin_one_step_mae",
        candidates=list(CANDIDATES),
        validation_mae=scores,
        test_mae=test_mae,
        test_rmse=float(np.sqrt(np.mean((actual - predicted) ** 2))),
        naive_test_mae=naive_test_mae,
        evaluation_status=status,
        test=test, future=future,
        training_start=int(df.period.iloc[0]),
        training_end=int(df.period.iloc[-1]),
        warning="Point forecasts only; no calibrated interval. Latest-vintage backtest; no causal interpretation.",
    )
