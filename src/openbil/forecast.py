"""Chronological model selection, untouched final test, no imputation."""

import numpy as np
import pandas as pd


def predict(y, horizon, model):
    if model == "naive":
        return np.repeat(y[-1], horizon)
    if model == "drift":
        return y[-1] + np.arange(1, horizon + 1) * (y[-1] - y[0]) / (len(y) - 1)
    raise ValueError("Unknown model")


def forecast(frame, horizon=3):
    if not 1 <= horizon <= 5:
        raise ValueError("Horizon must be 1..5")
    df = frame.sort_values("period").copy()
    if df["period"].duplicated().any():
        raise ValueError("Choose exactly one country and indicator")
    df = df[
        (df.value.notna())
        & (~df.data_status.isin(["projected", "missing"]))
        & (df.quality_status != "rejected")
    ]
    if df.empty:
        raise ValueError("No eligible history")
    # Keep only last contiguous annual segment, never bridge a gap.
    gaps = np.flatnonzero(np.diff(df.period.to_numpy()) != 1)
    if len(gaps):
        df = df.iloc[gaps[-1] + 1 :]
    if len(df) < 14:
        raise ValueError("At least 14 consecutive eligible annual values are required")
    y = df.value.to_numpy(dtype=float)
    if not np.isfinite(y).all():
        raise ValueError("Nonfinite history")
    test_size = 3
    validation_size = 4
    split = len(y) - test_size
    scores = {}
    for model in ["naive", "drift"]:
        errors = [
            abs(y[t] - predict(y[:t], 1, model)[0])
            for t in range(split - validation_size, split)
        ]
        scores[model] = float(np.mean(errors))
    selected = min(scores, key=scores.get)
    # Fixed-origin holdout: NO refitting using the three test observations.
    predicted = predict(y[:split], test_size, selected)
    actual = y[split:]
    naive = predict(y[:split], test_size, "naive")
    test = pd.DataFrame(
        {
            "period": df.period.iloc[split:].to_numpy(),
            "actual": actual,
            "prediction": predicted,
            "naive": naive,
        }
    )
    points = predict(y, horizon, selected)
    future = pd.DataFrame(
        {
            "period": np.arange(
                int(df.period.iloc[-1]) + 1, int(df.period.iloc[-1]) + horizon + 1
            ),
            "value": points,
            "data_status": "projected",
            "model": selected,
        }
    )
    return dict(
        model=selected,
        validation_mae=scores,
        test_mae=float(np.abs(actual - predicted).mean()),
        test_rmse=float(np.sqrt(((actual - predicted) ** 2).mean())),
        naive_test_mae=float(np.abs(actual - naive).mean()),
        test=test,
        future=future,
        training_start=int(df.period.iloc[0]),
        training_end=int(df.period.iloc[-1]),
        warning="Point forecasts only: no calibrated uncertainty interval. Latest-vintage backtest, not a real-time vintage backtest. No causal interpretation.",
    )
