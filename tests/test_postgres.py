import os
import pytest
from sqlalchemy import text
from openbil.db import engine, migrate, metadata
from test_pipeline import Fake, run


@pytest.mark.postgres
def test_postgres_migration_collect_and_lock():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL not configured")
    e = engine(url)
    # TEST_DATABASE_URL must refer to a disposable, isolated test database.
    with e.begin() as c:
        c.execute(text("DROP VIEW IF EXISTS current_observations"))
        metadata.drop_all(c)
    migrate(e)
    migrate(e)
    assert run(e, Fake())["status"] == "success"
    assert run(e, Fake())["datasets"] == ["unchanged"]
    with e.connect() as c:
        c.execute(text("SELECT pg_advisory_lock(875311)"))
        with pytest.raises(RuntimeError, match="Another collection"):
            run(e, Fake())
        c.execute(text("SELECT pg_advisory_unlock(875311)"))
    e.dispose()
