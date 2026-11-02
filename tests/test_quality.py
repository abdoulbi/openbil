import pytest
from openbil.quality import normalize, finish_quality

CODE = "NY.GDP.MKTP.CD"


def row(value=1, **kw):
    return {
        "indicator": {"id": CODE},
        "countryiso3code": "BFA",
        "date": "2020",
        "value": value,
        **kw,
    }


def norm(records):
    return normalize(
        CODE,
        ["BFA"],
        2020,
        2021,
        [(r, "https://api.worldbank.org/test") for r in records],
        "u",
    )


def test_missing_and_unknown():
    rows = norm([row()])
    assert rows[0]["data_status"] == "unspecified"
    assert rows[1]["value"] is None
    assert rows[1]["data_status"] == "missing"


def test_forecast_flag():
    assert norm([row(obs_status="F")])[0]["data_status"] == "projected"


def test_duplicate():
    with pytest.raises(ValueError, match="Duplicate"):
        norm([row(), row()])


@pytest.mark.parametrize("value", [float("nan"), float("inf"), "2", True])
def test_invalid_value(value):
    with pytest.raises(ValueError, match="Nonfinite"):
        norm([row(value)])


def test_negative_gdp_rejected():
    assert finish_quality(norm([row(-1)]))[0]["quality_status"] == "rejected"


def test_definition_change():
    assert (
        "definition_changed_review" in finish_quality(norm([row()]), True)[0]["flags"]
    )


def test_wrong_country():
    with pytest.raises(ValueError, match="Unexpected"):
        norm([row(countryiso3code="USA")])
