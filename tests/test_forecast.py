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
