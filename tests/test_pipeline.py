from sqlalchemy import text, select, func
from openbil.pipeline import collect
from openbil.db import (
    dataset_versions,
    observations,
    collection_runs,
    quality_checks,
    migrate,
)

CODE = "NY.GDP.MKTP.CD"


class Fake:
    def __init__(self, value=10, fail=False, definition="v1"):
        self.value = value
        self.fail = fail
        self.definition = definition

    def collect(self, code, countries, start, end):
        if self.fail:
            raise RuntimeError("fixture unavailable")
        records = [
            (
                {
                    "indicator": {"id": code},
                    "countryiso3code": c,
                    "date": str(y),
                    "value": self.value,
                },
                "https://api.worldbank.org/test",
            )
            for c in countries
            for y in range(start, end + 1)
        ]
        return (
            {"id": code, "sourceNote": self.definition},
            {"lastupdated": "2026-01-01"},
            records,
            [],
        )


def run(db, connector, **kw):
    return collect(db, ["BFA"], [CODE], 2020, 2021, connector=connector, **kw)


def test_idempotency_revision_and_reversion(db):
    assert run(db, Fake())["status"] == "success"
    assert run(db, Fake())["datasets"] == ["unchanged"]
    run(db, Fake(20))
    run(db, Fake(10))
    assert run(db, Fake(10))["datasets"] == ["unchanged"]
    with db.connect() as c:
        assert c.scalar(select(func.count()).select_from(dataset_versions)) == 3
        assert c.scalar(select(func.count()).select_from(observations)) == 6
        assert c.execute(
            text("SELECT value FROM current_observations")
        ).scalars().all() == [10, 10]


def test_failure_retains_previous(db):
    run(db, Fake())
    assert run(db, Fake(fail=True))["status"] == "failed"
    with db.connect() as c:
        assert c.scalar(select(func.count()).select_from(dataset_versions)) == 1
        assert c.scalar(select(func.count()).select_from(collection_runs)) == 2
        assert (
            c.execute(select(quality_checks.c.status)).scalars().all()[-1] == "failed"
        )


def test_definition_change(db):
    run(db, Fake())
    run(db, Fake(definition="new definition"))
    with db.connect() as c:
        assert all(
            "definition_changed_review" in r
            for r in c.execute(text("SELECT flags FROM current_observations")).scalars()
        )


def test_different_scopes_preserve_latest(db):
    run(db, Fake())
    collect(db, ["BFA", "KEN"], [CODE], 2020, 2021, connector=Fake(30))
    run(db, Fake(10))
    with db.connect() as c:
        assert c.execute(
            text("SELECT value FROM current_observations WHERE country_id='BFA'")
        ).scalars().all() == [10, 10]
        assert c.execute(
            text("SELECT value FROM current_observations WHERE country_id='KEN'")
        ).scalars().all() == [30, 30]


def test_migrations_repeat(db):
    migrate(db)
    migrate(db)


def test_invalid_scope(db):
    import pytest

    with pytest.raises(ValueError):
        collect(db, ["USA"], [CODE], 2020, 2021, connector=Fake())


def test_partial_and_retry(db):
    class Partial(Fake):
        def collect(self, code, *a):
            if code == "FP.CPI.TOTL.ZG":
                raise RuntimeError("timeout")
            return super().collect(code, *a)

    assert (
        collect(db, ["BFA"], [CODE, "FP.CPI.TOTL.ZG"], 2020, 2021, connector=Partial())[
            "status"
        ]
        == "partial"
    )
    assert collect(db, ["BFA"], [CODE, "FP.CPI.TOTL.ZG"], 2020, 2021, connector=Fake())[
        "datasets"
    ] == ["unchanged", "created"]


def test_invalid_dataset_rolls_back(db):
    class Invalid(Fake):
        def collect(self, *a):
            meta, header, records, manifest = super().collect(*a)
            records.append(records[0])
            return meta, header, records, manifest

    assert run(db, Invalid())["status"] == "failed"
    with db.connect() as c:
        assert c.scalar(select(func.count()).select_from(dataset_versions)) == 0
        assert c.scalar(select(func.count()).select_from(observations)) == 0


def test_missing_revision_replaces_value(db):
    run(db, Fake(10))
    run(db, Fake(None))
    with db.connect() as c:
        assert c.execute(
            text("SELECT value FROM current_observations")
        ).scalars().all() == [None, None]
        assert c.scalar(select(func.count()).select_from(observations)) == 4
