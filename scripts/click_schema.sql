CREATE DATABASE IF NOT EXISTS txt2sql;

CREATE TABLE IF NOT EXISTS txt2sql.struct_code (
    struct_code String,
    struct_lvl  LowCardinality(String),
    tb_id       String,
    gosb_id     String,
    tb_name     String,
    gosb_name   String,
    vsp_name    String
) ENGINE = MergeTree()
ORDER BY (struct_lvl, struct_code);

CREATE TABLE IF NOT EXISTS txt2sql.metrics_dict (
    metric_id   Int32,
    metric_name String
) ENGINE = MergeTree()
ORDER BY metric_id;

CREATE TABLE IF NOT EXISTS txt2sql.metrics_facts (
    metric_id    Int32,
    metric_level LowCardinality(String),
    struct_code  String,
    period_type  LowCardinality(String),
    metric_type  LowCardinality(String),
    report_dt    Date,
    value        Float64
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(report_dt)
ORDER BY (metric_id, struct_code, report_dt, period_type, metric_type);