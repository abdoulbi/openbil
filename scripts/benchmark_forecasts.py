"""Compare old two-model and new four-model forecasts on the SAME stored series.

Usage: python scripts/benchmark_forecasts.py --output data/forecast_benchmark.csv
Requires DATABASE_URL and an existing OpenBIL database with collected data.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import text

from openbil.db import engine
from openbil.forecast import forecast


def old_forecast(frame):
    """Original two-candidate protocol, kept unchanged for fair baseline."""
    df = frame.sort_values("period").copy()
    if df.period.duplicated().any():
        raise ValueError("Duplicate period")
    df = df[df.value.notna() & ~df.data_status.isin(["projected", "missing"]) & (df.quality_status != "rejected")]
    if df.empty:
        raise ValueError("No eligible history")
    gaps = np.flatnonzero(np.diff(df.period.to_numpy()) != 1)
    if len(gaps):
        df = df.iloc[gaps[-1] + 1:]
    if len(df) < 14:
        raise ValueError("At least 14 consecutive eligible annual values are required")
    y = df.value.to_numpy(dtype=float)
    if not np.isfinite(y).all():
        raise ValueError("Nonfinite history")
    split = len(y) - 3
    from openbil.forecast import predict
    scores = {
        model: float(np.mean([abs(y[t] - predict(y[:t], 1, model)[0])
                             for t in range(split - 4, split)]))
        for model in ("naive", "drift")
    }
    chosen = min(scores, key=scores.get)
    actual = y[split:]
    prediction = predict(y[:split], 3, chosen)
    naive_prediction = predict(y[:split], 3, "naive")
    return {
        "model": chosen,
        "test_mae": float(np.mean(abs(actual - prediction))),
        "naive_test_mae": float(np.mean(abs(actual - naive_prediction))),
        "test_rmse": float(np.sqrt(np.mean((actual - prediction) ** 2))),
    }


def compare(data):
    rows = []
    for (country, indicator), group in data.groupby(["country_id", "indicator_id"], sort=True):
        key = {"country_id": country, "indicator_id": indicator}
        try:
            old, new = old_forecast(group), forecast(group)
        except ValueError as exc:
            rows.append({**key, "eligible": False, "exclusion": str(exc)})
            continue
        rows.append({
            **key, "eligible": True, "exclusion": "",
            "old_model": old["model"], "new_model": new["model"],
            "old_test_mae": old["test_mae"], "new_test_mae": new["test_mae"],
            "old_test_rmse": old["test_rmse"], "new_test_rmse": new["test_rmse"],
            "naive_test_mae": old["naive_test_mae"],
            "old_below_naive": old["test_mae"] > old["naive_test_mae"] + 1e-12,
            "new_below_naive": new["test_mae"] > new["naive_test_mae"] + 1e-12,
            "improved": new["test_mae"] < old["test_mae"] - 1e-12,
            "worsened": new["test_mae"] > old["test_mae"] + 1e-12,
        })
    return pd.DataFrame(rows)


def main():
    import os
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/forecast_benchmark.csv")
    args = parser.parse_args()
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL must point to a populated OpenBIL database")
    e = engine(url)
    try:
        with e.connect() as conn:
            data = pd.read_sql(text("SELECT * FROM current_observations"), conn)
    finally:
        e.dispose()
    if data.empty:
        raise SystemExit("No collected observations available")
    results = compare(data)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(output, index=False)
    valid = results[results.eligible]
    print(f"Series: total={len(results)}, eligible={len(valid)}, excluded={len(results)-len(valid)}")
    if len(valid):
        print(f"Below naive: old={int(valid.old_below_naive.sum())}, new={int(valid.new_below_naive.sum())}")
        print(f"New vs old (MAE): improved={int(valid.improved.sum())}, worsened={int(valid.worsened.sum())}, tied={int((~valid.improved & ~valid.worsened).sum())}")
        print("Per-series details:", output)
    else:
        print("No evaluable series; no performance conclusion can be drawn.")


if __name__ == "__main__":
    main()
