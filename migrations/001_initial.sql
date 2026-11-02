-- OpenBIL schema 001; fresh database only; prefer openbil migrate.
BEGIN;

CREATE TABLE collection_runs (
	id VARCHAR NOT NULL, 
	started_at VARCHAR NOT NULL, 
	finished_at VARCHAR, 
	status VARCHAR NOT NULL, 
	parameters TEXT NOT NULL, 
	error TEXT, 
	software_version VARCHAR NOT NULL, 
	PRIMARY KEY (id)
)

;

CREATE TABLE countries (
	id VARCHAR(3) NOT NULL, 
	name TEXT NOT NULL, 
	region TEXT NOT NULL, 
	PRIMARY KEY (id)
)

;

CREATE TABLE schema_migrations (
	version SERIAL NOT NULL, 
	applied_at VARCHAR NOT NULL, 
	PRIMARY KEY (version)
)

;

CREATE TABLE sources (
	id VARCHAR NOT NULL, 
	name TEXT NOT NULL, 
	url TEXT NOT NULL, 
	terms_url TEXT NOT NULL, 
	license TEXT NOT NULL, 
	reviewed_at VARCHAR NOT NULL, 
	PRIMARY KEY (id)
)

;

CREATE TABLE datasets (
	id VARCHAR NOT NULL, 
	source_id VARCHAR NOT NULL, 
	title TEXT NOT NULL, 
	citation TEXT NOT NULL, 
	license_note TEXT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(source_id) REFERENCES sources (id)
)

;

CREATE TABLE dataset_versions (
	id VARCHAR NOT NULL, 
	dataset_id VARCHAR NOT NULL, 
	run_id VARCHAR NOT NULL, 
	collected_at VARCHAR NOT NULL, 
	digest VARCHAR(64) NOT NULL, 
	scope TEXT NOT NULL, 
	raw_manifest TEXT NOT NULL, 
	metadata_json TEXT NOT NULL, 
	source_updated_at VARCHAR, 
	transform_version VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(dataset_id) REFERENCES datasets (id), 
	FOREIGN KEY(run_id) REFERENCES collection_runs (id)
)

;
CREATE INDEX ix_version_dataset_time ON dataset_versions (dataset_id, collected_at);

CREATE TABLE indicators (
	id VARCHAR NOT NULL, 
	dataset_id VARCHAR NOT NULL, 
	label TEXT NOT NULL, 
	unit TEXT NOT NULL, 
	methodology TEXT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(dataset_id) REFERENCES datasets (id)
)

;

CREATE TABLE observations (
	id VARCHAR NOT NULL, 
	version_id VARCHAR NOT NULL, 
	source_id VARCHAR NOT NULL, 
	indicator_id VARCHAR NOT NULL, 
	country_id VARCHAR(3) NOT NULL, 
	period INTEGER NOT NULL, 
	value FLOAT, 
	unit TEXT NOT NULL, 
	source_url TEXT NOT NULL, 
	collected_at VARCHAR NOT NULL, 
	published_at VARCHAR, 
	data_status VARCHAR NOT NULL, 
	quality_status VARCHAR NOT NULL, 
	source_status TEXT NOT NULL, 
	footnote TEXT NOT NULL, 
	flags TEXT NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_observation UNIQUE (version_id, country_id, indicator_id, period), 
	CONSTRAINT ck_period CHECK (period >= 1900 AND period <= 2200), 
	CONSTRAINT ck_data_status CHECK (data_status IN ('observed','estimated','projected','missing','unspecified')), 
	CONSTRAINT ck_quality CHECK (quality_status IN ('pass','warning','missing','rejected')), 
	CONSTRAINT ck_missing CHECK ((value IS NULL AND data_status='missing') OR (value IS NOT NULL AND data_status<>'missing')), 
	FOREIGN KEY(version_id) REFERENCES dataset_versions (id), 
	FOREIGN KEY(source_id) REFERENCES sources (id), 
	FOREIGN KEY(indicator_id) REFERENCES indicators (id), 
	FOREIGN KEY(country_id) REFERENCES countries (id)
)

;
CREATE INDEX ix_observation_current ON observations (indicator_id, country_id, period, collected_at);

CREATE TABLE quality_checks (
	id VARCHAR NOT NULL, 
	run_id VARCHAR NOT NULL, 
	version_id VARCHAR, 
	indicator_id VARCHAR, 
	check_name VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	details TEXT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(run_id) REFERENCES collection_runs (id), 
	FOREIGN KEY(version_id) REFERENCES dataset_versions (id)
)

;
CREATE VIEW current_observations AS
SELECT id, version_id, source_id, indicator_id, country_id, period, value, unit,
source_url, collected_at, published_at, data_status, quality_status, source_status, footnote, flags
FROM (SELECT o.*, ROW_NUMBER() OVER (
PARTITION BY source_id, indicator_id, country_id, period ORDER BY collected_at DESC, version_id DESC) AS rn
FROM observations o) ranked WHERE rn=1;
INSERT INTO schema_migrations VALUES (1, CURRENT_TIMESTAMP::text);
COMMIT;
