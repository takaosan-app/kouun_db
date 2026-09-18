\set ON_ERROR_STOP on

BEGIN;

CREATE TABLE weather.collection_issue (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    severity text NOT NULL,
    issue_code text NOT NULL,

    area_code text
        REFERENCES weather.observation_area(area_code),

    capability_code text,

    requested_start_date date,
    requested_end_date date,

    station_id bigint
        REFERENCES weather.station(id),

    observed_on date,

    element_id bigint
        REFERENCES weather.element(id),

    source_file_id bigint
        REFERENCES weather.source_file(id),

    ingestion_run_id bigint
        REFERENCES weather.ingestion_run(id),

    message text NOT NULL,
    details jsonb NOT NULL DEFAULT '{}'::jsonb,

    created_at timestamptz NOT NULL DEFAULT now(),
    resolved_at timestamptz,

    CONSTRAINT collection_issue_severity
        CHECK (
            severity IN (
                'warning',
                'error',
                'fatal'
            )
        ),

    CONSTRAINT collection_issue_code_format
        CHECK (
            issue_code ~ '^[a-z][a-z0-9_]*$'
        ),

    CONSTRAINT collection_issue_capability_format
        CHECK (
            capability_code IS NULL
            OR capability_code ~ '^[0-9]{6}$'
        ),

    CONSTRAINT collection_issue_requested_period
        CHECK (
            (
                requested_start_date IS NULL
                AND requested_end_date IS NULL
            )
            OR
            (
                requested_start_date IS NOT NULL
                AND requested_end_date IS NOT NULL
                AND requested_end_date
                    >= requested_start_date
            )
        ),

    CONSTRAINT collection_issue_details_object
        CHECK (
            jsonb_typeof(details) = 'object'
        ),

    CONSTRAINT collection_issue_resolution_time
        CHECK (
            resolved_at IS NULL
            OR resolved_at >= created_at
        )
);

CREATE INDEX collection_issue_unresolved_idx
    ON weather.collection_issue (
        severity,
        created_at DESC
    )
    WHERE resolved_at IS NULL;

CREATE INDEX collection_issue_area_period_idx
    ON weather.collection_issue (
        area_code,
        requested_start_date,
        requested_end_date
    );

CREATE INDEX collection_issue_station_date_idx
    ON weather.collection_issue (
        station_id,
        observed_on DESC
    )
    WHERE station_id IS NOT NULL;

CREATE INDEX collection_issue_ingestion_run_idx
    ON weather.collection_issue (
        ingestion_run_id
    )
    WHERE ingestion_run_id IS NOT NULL;

COMMENT ON TABLE weather.collection_issue IS
    'Warnings and errors detected while collecting or importing source data.';

COMMENT ON COLUMN weather.collection_issue.severity IS
    'Issue severity: warning, error, or fatal.';

COMMENT ON COLUMN weather.collection_issue.issue_code IS
    'Stable machine-readable issue identifier.';

COMMENT ON COLUMN weather.collection_issue.resolved_at IS
    'Time when the issue was reviewed or resolved; null while unresolved.';

COMMIT;
