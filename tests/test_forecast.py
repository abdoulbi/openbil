import numpy as np
import pandas as pd
import pytest
from openbil.forecast import forecast


def frame(y=None):
    return pd.DataFrame(
        {
            "period": range(2000, 2020),
            "value": np.arange(20, dtype=float) if y is None else y,
            "data_status": "unspecified",
            "quality_status": "pass",
        }
    )


def test_drift_linear():
    r = forecast(frame())
    assert r["model"] == "drift"
    assert r["test_mae"] == 0
    assert r["future"].value.tolist() == [20, 21, 22]


def test_constant_naive():
    assert forecast(frame(np.ones(20)))["model"] == "naive"


def test_test_not_used_for_selection():
    a = frame()
    b = frame()
    b.loc[17:, "value"] = 9999
    x, y = forecast(a), forecast(b)
    assert x["validation_mae"] == y["validation_mae"]
    assert x["model"] == y["model"]
    assert y["test_mae"] > 0
    assert x["test"].prediction.tolist() == y["test"].prediction.tolist()


def test_gap_no_imputation():
    a = frame()
    a.loc[10, "value"] = np.nan
    with pytest.raises(ValueError, match="14 consecutive"):
        forecast(a)


def test_projected_excluded():
    a = frame()
    a.loc[19, "data_status"] = "projected"
    assert forecast(a)["training_end"] == 2018


def test_duplicates_rejected():
    with pytest.raises(ValueError, match="exactly one"):
        forecast(pd.concat([frame(), frame()]))


def test_models_and_validation_result():
    from openbil.forecast import CANDIDATES
    r = forecast(frame())
    assert set(r["validation_mae"]) == set(CANDIDATES)
    assert r["selection_method"] == "rolling_origin_one_step_mae"
    assert r["evaluation_status"] == "not_below_naive_on_holdout"


def test_trend_and_mean_predict():
    from openbil.forecast import predict
    assert predict([1, 3, 5, 7, 9], 2, "trend5") == pytest.approx([11, 13])
    assert predict([1, 2, 3, 6], 2, "mean3") == pytest.approx([11 / 3, 11 / 3])


def test_per_series_selects_different_models():
    assert forecast(frame())["model"] != forecast(frame(np.ones(20)))["model"]


def test_holdout_warning_does_not_change_selection():
    y = np.arange(20, dtype=float)
    y[-3:] = 0
    r = forecast(frame(y))
    assert r["model"] == "drift"
    assert r["evaluation_status"] == "below_naive_on_holdout"
