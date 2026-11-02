import numpy as np
import pandas as pd

from scripts.benchmark_forecasts import old_forecast, compare
from openbil.forecast import forecast


def sample(values, country="BFA"):
    return pd.DataFrame({
        "country_id": country,
        "indicator_id": "NY.GDP.MKTP.CD",
        "period": list(range(2000, 2000 + len(values))),
        "value": np.asarray(values, dtype=float),
        "data_status": "unspecified",
        "quality_status": "pass",
    })


def test_original_baseline_reproduces_naive_drift_selection():
    df = sample(np.arange(20))
    original = old_forecast(df)
    assert original["model"] == "drift"
    assert original["test_mae"] == 0


def test_paired_compare_matches_same_final_naive_benchmark():
    data = pd.concat([sample(np.arange(20)), sample(np.ones(20), "KEN")])
    result = compare(data)
    assert len(result) == 2
    assert result.eligible.all()
    assert (result.old_test_mae == 0).all()
    assert (result.new_test_mae == 0).all()
    assert (result.naive_test_mae >= 0).all()


def test_exclusions_retained():
    bad = sample(np.arange(10))
    result = compare(bad)
    assert len(result) == 1
    assert not bool(result.iloc[0]["eligible"])
    assert "14 consecutive" in result.iloc[0]["exclusion"]
