"""Narrow Databricks SQL schemas; credentials never belong in these files."""

TABLE_DDL = {
    "change_events": """CREATE TABLE IF NOT EXISTS change_events (event_id STRING, repository STRING, commit STRING, parent_commit STRING, captured_at TIMESTAMP, changed_files ARRAY<STRING>, changed_symbols ARRAY<STRING>, change_types ARRAY<STRING>, data_kind STRING, source STRING) USING DELTA""",
    "test_events": """CREATE TABLE IF NOT EXISTS test_events (event_id STRING, repository STRING, commit STRING, captured_at TIMESTAMP, test_command STRING, test_scope STRING, result STRING, duration_ms BIGINT, failure_summary STRING, data_kind STRING, source STRING) USING DELTA""",
    "impact_snapshots": """CREATE TABLE IF NOT EXISTS impact_snapshots (snapshot_id STRING, repository STRING, commit STRING, symbol STRING, impacted_symbol STRING, relationship STRING, confidence DOUBLE, resolution STRING, trust_classification STRING, source_file STRING, source_line BIGINT, captured_at TIMESTAMP, data_kind STRING, source STRING) USING DELTA""",
}
