import pytest
from openbil.db import engine, migrate


@pytest.fixture
def db(tmp_path):
    e = engine("sqlite:///" + str(tmp_path / "test.sqlite"))
    migrate(e)
    yield e
    e.dispose()
