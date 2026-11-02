from datetime import datetime, timezone, timedelta
from openbil.free_hosting import ensure_data
from test_pipeline import Fake


def test_free_cache_reuses_successful_collection(tmp_path):
    class Counting(Fake):
        calls = 0

        def collect(self, *args):
            self.calls += 1
            return super().collect(*args)

    client = Counting()
    first = ensure_data(tmp_path, connector=client)
    assert first["status"] == "success"
    assert first["refreshed"] is True
    assert client.calls == 11
    second = ensure_data(tmp_path, connector=client)
    assert second["refreshed"] is False
    assert client.calls == 11
    third = ensure_data(
        tmp_path, connector=client, clock=datetime.now(timezone.utc) + timedelta(days=2)
    )
    assert third["refreshed"] is True
    assert client.calls == 22


def test_free_failures_are_throttled(tmp_path):
    first = ensure_data(tmp_path, connector=Fake(fail=True))
    assert first["status"] == "failed"
    second = ensure_data(tmp_path, connector=Fake())
    assert second["status"] == "failed"
    assert second["refreshed"] is False


def test_free_app_has_no_exception(tmp_path, monkeypatch):
    import openbil.free_hosting as free
    from streamlit.testing.v1 import AppTest
    from pathlib import Path

    original = free.ensure_data
    monkeypatch.setattr(
        free, "ensure_data", lambda: original(tmp_path, connector=Fake())
    )
    app = AppTest.from_file(
        str(Path(__file__).resolve().parents[1] / "app_free.py")
    ).run(timeout=30)
    assert not app.exception
    assert any("Version gratuite" in x.value for x in app.info)
    assert any("ne garantit pas une exécution" in x.value for x in app.caption)


def test_refresh_eligibility_tracks_status(tmp_path):
    success = ensure_data(tmp_path / "ok", connector=Fake())
    failure = ensure_data(tmp_path / "error", connector=Fake(fail=True))
    for state, hours in [(success, 24), (failure, 1)]:
        start = datetime.fromisoformat(state["last_attempt_at"])
        end = datetime.fromisoformat(state["next_eligible_at"])
        assert end - start == timedelta(hours=hours)
