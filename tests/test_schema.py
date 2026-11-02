from pathlib import Path
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable, CreateIndex
from openbil.db import metadata, CURRENT_SQL


def test_postgres_ddl_matches_generated_file():
    sql = (
        "-- OpenBIL schema 001; fresh database only; prefer openbil migrate.\nBEGIN;\n"
    )
    for t in metadata.sorted_tables:
        sql += str(CreateTable(t).compile(dialect=postgresql.dialect())) + ";\n"
        for index in t.indexes:
            sql += str(CreateIndex(index).compile(dialect=postgresql.dialect())) + ";\n"
    sql += (
        CURRENT_SQL
        + ";\nINSERT INTO schema_migrations VALUES (1, CURRENT_TIMESTAMP::text);\nCOMMIT;\n"
    )
    assert (
        sql
        == (
            Path(__file__).resolve().parents[1] / "migrations/001_initial.sql"
        ).read_text()
    )
