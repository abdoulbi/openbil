from pathlib import Path
from streamlit.testing.v1 import AppTest
from test_pipeline import Fake, run


def test_dashboard_loaded(db, monkeypatch):
    run(db, Fake())
    monkeypatch.setenv("DATABASE_URL", str(db.url))
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run(
        timeout=30
    )
    assert not app.exception
    assert len(app.metric) == 4


def test_dashboard_empty(db, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", str(db.url))
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run(
        timeout=30
    )
    assert not app.exception
    assert any("Aucune donnée" in x.value for x in app.info)


def test_dashboard_filters(db, monkeypatch):
    from openbil.pipeline import collect

    collect(
        db,
        ["BFA", "GHA"],
        ["NY.GDP.MKTP.CD", "FP.CPI.TOTL.ZG"],
        2000,
        2025,
        connector=Fake(),
    )
    monkeypatch.setenv("DATABASE_URL", str(db.url))
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run(
        timeout=30
    )
    app.sidebar.multiselect[0].set_value(["BFA", "GHA"]).run()
    app.sidebar.selectbox[0].set_value("FP.CPI.TOTL.ZG").run()
    assert not app.exception
    app.sidebar.multiselect[0].set_value([]).run()
    assert not app.exception
