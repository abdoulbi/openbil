"""Regenerate PostgreSQL SQL from authoritative SQLAlchemy migration 001."""

from pathlib import Path
from sqlalchemy.schema import CreateTable, CreateIndex
from sqlalchemy.dialects import postgresql
from openbil.db import metadata, CURRENT_SQL

sql = "-- OpenBIL schema 001; fresh database only; prefer openbil migrate.\nBEGIN;\n"
for table in metadata.sorted_tables:
    sql += str(CreateTable(table).compile(dialect=postgresql.dialect())) + ";\n"
    for index in table.indexes:
        sql += str(CreateIndex(index).compile(dialect=postgresql.dialect())) + ";\n"
sql += (
    CURRENT_SQL
    + ";\nINSERT INTO schema_migrations VALUES (1, CURRENT_TIMESTAMP::text);\nCOMMIT;\n"
)
Path("migrations/001_initial.sql").write_text(sql)
