import importlib.util
from pathlib import Path
import pytest
from openbil.db import engine


def test_managed_postgresql_uri_uses_installed_driver():
    for uri in [
        "postgres://user:pass@localhost/db",
        "postgresql://user:pass@localhost/db",
    ]:
        db = engine(uri)
        assert db.dialect.driver == "psycopg"
        db.dispose()


def test_cloud_startup_roles_and_port():
    path = Path(__file__).resolve().parents[1] / "scripts/start_service.py"
    spec = importlib.util.spec_from_file_location("start_service", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.command("collector", "8080") == ["openbil", "schedule"]
    assert "--server.port=8080" in module.command("dashboard", "8080")
    with pytest.raises(ValueError):
        module.command("unknown", "8080")
    with pytest.raises(ValueError):
        module.command("dashboard", "0")
