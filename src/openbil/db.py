import os
from datetime import datetime, timezone
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    String,
    Integer,
    Float,
    Text,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Index,
    text,
)

metadata = MetaData()


def now():
    return datetime.now(timezone.utc).isoformat()


def engine(url=None):
    configured = url or os.environ.get(
        "DATABASE_URL", "postgresql+psycopg://openbil:openbil@localhost:5432/openbil"
    )
    # Managed providers generally supply a driver-neutral PostgreSQL URI.
    if configured.startswith("postgres://"):
        configured = "postgresql+psycopg://" + configured[len("postgres://") :]
    elif configured.startswith("postgresql://"):
        configured = "postgresql+psycopg://" + configured[len("postgresql://") :]
    e = create_engine(configured, pool_pre_ping=True)
    if e.dialect.name == "sqlite":
        from sqlalchemy import event

        @event.listens_for(e, "connect")
        def foreign_keys(db, _):
            db.execute("PRAGMA foreign_keys=ON")

    return e


sources = Table(
    "sources",
    metadata,
    Column("id", String, primary_key=True),
    Column("name", Text, nullable=False),
    Column("url", Text, nullable=False),
    Column("terms_url", Text, nullable=False),
    Column("license", Text, nullable=False),
    Column("reviewed_at", String, nullable=False),
)
datasets = Table(
    "datasets",
    metadata,
    Column("id", String, primary_key=True),
    Column("source_id", ForeignKey("sources.id"), nullable=False),
    Column("title", Text, nullable=False),
    Column("citation", Text, nullable=False),
    Column("license_note", Text, nullable=False),
)
indicators = Table(
    "indicators",
    metadata,
    Column("id", String, primary_key=True),
    Column("dataset_id", ForeignKey("datasets.id"), nullable=False),
    Column("label", Text, nullable=False),
    Column("unit", Text, nullable=False),
    Column("methodology", Text, nullable=False),
)
countries = Table(
    "countries",
    metadata,
    Column("id", String(3), primary_key=True),
    Column("name", Text, nullable=False),
    Column("region", Text, nullable=False),
)
collection_runs = Table(
    "collection_runs",
    metadata,
    Column("id", String, primary_key=True),
    Column("started_at", String, nullable=False),
    Column("finished_at", String),
    Column("status", String, nullable=False),
    Column("parameters", Text, nullable=False),
    Column("error", Text),
    Column("software_version", String, nullable=False),
)
dataset_versions = Table(
    "dataset_versions",
    metadata,
    Column("id", String, primary_key=True),
    Column("dataset_id", ForeignKey("datasets.id"), nullable=False),
    Column("run_id", ForeignKey("collection_runs.id"), nullable=False),
    Column("collected_at", String, nullable=False),
    Column("digest", String(64), nullable=False),
    Column("scope", Text, nullable=False),
    Column("raw_manifest", Text, nullable=False),
    Column("metadata_json", Text, nullable=False),
    Column("source_updated_at", String),
    Column("transform_version", String, nullable=False),
)
observations = Table(
    "observations",
    metadata,
    Column("id", String, primary_key=True),
    Column("version_id", ForeignKey("dataset_versions.id"), nullable=False),
    Column("source_id", ForeignKey("sources.id"), nullable=False),
    Column("indicator_id", ForeignKey("indicators.id"), nullable=False),
    Column("country_id", ForeignKey("countries.id"), nullable=False),
    Column("period", Integer, nullable=False),
    Column("value", Float),
    Column("unit", Text, nullable=False),
    Column("source_url", Text, nullable=False),
    Column("collected_at", String, nullable=False),
    Column("published_at", String),
    Column("data_status", String, nullable=False),
    Column("quality_status", String, nullable=False),
    Column("source_status", Text, nullable=False),
    Column("footnote", Text, nullable=False),
    Column("flags", Text, nullable=False),
    UniqueConstraint(
        "version_id", "country_id", "indicator_id", "period", name="uq_observation"
    ),
    CheckConstraint("period >= 1900 AND period <= 2200", name="ck_period"),
    CheckConstraint(
        "data_status IN ('observed','estimated','projected','missing','unspecified')",
        name="ck_data_status",
    ),
    CheckConstraint(
        "quality_status IN ('pass','warning','missing','rejected')", name="ck_quality"
    ),
    CheckConstraint(
        "(value IS NULL AND data_status='missing') OR (value IS NOT NULL AND data_status<>'missing')",
        name="ck_missing",
    ),
)
quality_checks = Table(
    "quality_checks",
    metadata,
    Column("id", String, primary_key=True),
    Column("run_id", ForeignKey("collection_runs.id"), nullable=False),
    Column("version_id", ForeignKey("dataset_versions.id")),
    Column("indicator_id", String),
    Column("check_name", String, nullable=False),
    Column("status", String, nullable=False),
    Column("details", Text, nullable=False),
)
schema_migrations = Table(
    "schema_migrations",
    metadata,
    Column("version", Integer, primary_key=True),
    Column("applied_at", String, nullable=False),
)
Index(
    "ix_observation_current",
    observations.c.indicator_id,
    observations.c.country_id,
    observations.c.period,
    observations.c.collected_at,
)
Index(
    "ix_version_dataset_time",
    dataset_versions.c.dataset_id,
    dataset_versions.c.collected_at,
)
CURRENT_SQL = """CREATE VIEW current_observations AS
SELECT id, version_id, source_id, indicator_id, country_id, period, value, unit,
source_url, collected_at, published_at, data_status, quality_status, source_status, footnote, flags
FROM (SELECT o.*, ROW_NUMBER() OVER (
PARTITION BY source_id, indicator_id, country_id, period ORDER BY collected_at DESC, version_id DESC) AS rn
FROM observations o) ranked WHERE rn=1"""


def migrate(e):
    with e.begin() as c:
        if e.dialect.name == "postgresql":
            c.execute(text("SELECT pg_advisory_xact_lock(875310)"))
        metadata.create_all(c)
        if not c.execute(
            schema_migrations.select().where(schema_migrations.c.version == 1)
        ).first():
            c.execute(text(CURRENT_SQL))
            c.execute(schema_migrations.insert().values(version=1, applied_at=now()))
