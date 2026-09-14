\set ON_ERROR_STOP on

BEGIN;

CREATE TABLE IF NOT EXISTS weather.source_file (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_id bigint NOT NULL
        REFERENCES weather.source(id),
    storage_path text NOT NULL UNIQUE,
    sha256 char(64) NOT NULL UNIQUE,
    retrieved_at timestamptz NOT NULL,
    requested_start_date date,
    requested_end_date date,
    encoding text NOT NULL,
    content_type text,
    byte_size bigint NOT NULL,
    source_row_count integer NOT NULL,
    collector_version text NOT NULL,
    request_parameters jsonb NOT NULL DEFAULT '{}'::jsonb,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT source_file_sha256_format
        CHECK (sha256 ~ '^[0-9a-f]{64}$'),

    CONSTRAINT source_file_nonnegative_size
        CHECK (byte_size >= 0),

    CONSTRAINT source_file_nonnegative_rows
        CHECK (source_row_count >= 0),

    CONSTRAINT source_file_requested_period
        CHECK (
            requested_start_date IS NULL
            OR requested_end_date IS NULL
            OR requested_end_date >= requested_start_date
        )
);

CREATE INDEX IF NOT EXISTS source_file_source_retrieved_idx
    ON weather.source_file (source_id, retrieved_at DESC);

CREATE TABLE IF NOT EXISTS weather.ingestion_run (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_file_id bigint NOT NULL
        REFERENCES weather.source_file(id),
    status text NOT NULL,
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    parsed_count integer NOT NULL DEFAULT 0,
    inserted_count integer NOT NULL DEFAULT 0,
    updated_count integer NOT NULL DEFAULT 0,
    unchanged_count integer NOT NULL DEFAULT 0,
    revision_count integer NOT NULL DEFAULT 0,
    error_message text,

    CONSTRAINT ingestion_run_status
        CHECK (status IN ('running', 'succeeded', 'failed')),

    CONSTRAINT ingestion_run_finished_state
        CHECK (
            (status = 'running' AND finished_at IS NULL)
            OR
            (status IN ('succeeded', 'failed') AND finished_at IS NOT NULL)
        ),

    CONSTRAINT ingestion_run_nonnegative_counts
        CHECK (
            parsed_count >= 0
            AND inserted_count >= 0
            AND updated_count >= 0
            AND unchanged_count >= 0
            AND revision_count >= 0
        )
);

CREATE INDEX IF NOT EXISTS ingestion_run_source_file_idx
    ON weather.ingestion_run (source_file_id, started_at DESC);

CREATE TABLE IF NOT EXISTS weather.observation (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_id bigint NOT NULL
        REFERENCES weather.source(id),
    station_id bigint NOT NULL
        REFERENCES weather.station(id),
    element_id bigint NOT NULL
        REFERENCES weather.element(id),
    source_file_id bigint NOT NULL
        REFERENCES weather.source_file(id),
    granularity text NOT NULL DEFAULT 'daily',
    observed_on date NOT NULL,
    value numeric,
    raw_value text NOT NULL,
    value_state text NOT NULL,
    quality_code text,
    homogeneity_number text,
    no_phenomenon boolean,
    first_seen_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT observation_granularity_format
        CHECK (granularity ~ '^[a-z][a-z0-9_]*$'),

    CONSTRAINT observation_value_state
        CHECK (
            value_state IN (
                'observed',
                'missing',
                'not_observed'
            )
        ),

    CONSTRAINT observation_value_consistency
        CHECK (
            (value_state = 'observed' AND value IS NOT NULL)
            OR
            (value_state <> 'observed' AND value IS NULL)
        ),

    CONSTRAINT observation_unique_value
        UNIQUE (
            source_id,
            station_id,
            element_id,
            granularity,
            observed_on
        )
);

CREATE INDEX IF NOT EXISTS observation_station_date_idx
    ON weather.observation (
        station_id,
        observed_on DESC
    );

CREATE INDEX IF NOT EXISTS observation_element_date_idx
    ON weather.observation (
        element_id,
        observed_on DESC
    );

CREATE TABLE IF NOT EXISTS weather.observation_revision (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    observation_id bigint NOT NULL
        REFERENCES weather.observation(id),
    previous_source_file_id bigint NOT NULL
        REFERENCES weather.source_file(id),
    replacement_source_file_id bigint NOT NULL
        REFERENCES weather.source_file(id),
    previous_record jsonb NOT NULL,
    replacement_record jsonb NOT NULL,
    changed_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT observation_revision_previous_object
        CHECK (jsonb_typeof(previous_record) = 'object'),

    CONSTRAINT observation_revision_replacement_object
        CHECK (jsonb_typeof(replacement_record) = 'object')
);

CREATE INDEX IF NOT EXISTS observation_revision_observation_idx
    ON weather.observation_revision (
        observation_id,
        changed_at DESC
    );

COMMIT;