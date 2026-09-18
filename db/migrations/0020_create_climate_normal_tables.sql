\set ON_ERROR_STOP on

BEGIN;

INSERT INTO weather.source (
    source_key,
    provider_name,
    product_name,
    base_url,
    terms_checked_on
)
VALUES (
    'jma_amedas_normals',
    '気象庁',
    'アメダス平年値',
    'https://www.data.jma.go.jp/stats/data/mdrr/normal/',
    DATE '2026-09-18'
)
ON CONFLICT (source_key) DO UPDATE
SET
    provider_name = EXCLUDED.provider_name,
    product_name = EXCLUDED.product_name,
    base_url = EXCLUDED.base_url,
    terms_checked_on = EXCLUDED.terms_checked_on;

CREATE TABLE weather.climate_normal_release (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    release_key text NOT NULL UNIQUE,
    name text NOT NULL,
    version text NOT NULL,

    statistics_started_on date NOT NULL,
    statistics_ended_on date NOT NULL,
    applicable_from date NOT NULL,
    applicable_to date NOT NULL,
    published_on date NOT NULL,

    created_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT climate_normal_release_key_format
        CHECK (
            release_key ~ '^[a-z0-9][a-z0-9_-]*$'
        ),

    CONSTRAINT climate_normal_statistics_period
        CHECK (
            statistics_ended_on >= statistics_started_on
        ),

    CONSTRAINT climate_normal_applicable_period
        CHECK (
            applicable_to >= applicable_from
        )
);

INSERT INTO weather.climate_normal_release (
    release_key,
    name,
    version,
    statistics_started_on,
    statistics_ended_on,
    applicable_from,
    applicable_to,
    published_on
)
VALUES (
    'jma_amedas_2020_v5',
    'アメダス平年値 1991～2020年',
    '5',
    DATE '1991-01-01',
    DATE '2020-12-31',
    DATE '2021-01-01',
    DATE '2030-12-31',
    DATE '2025-05-21'
)
ON CONFLICT (release_key) DO UPDATE
SET
    name = EXCLUDED.name,
    version = EXCLUDED.version,
    statistics_started_on = EXCLUDED.statistics_started_on,
    statistics_ended_on = EXCLUDED.statistics_ended_on,
    applicable_from = EXCLUDED.applicable_from,
    applicable_to = EXCLUDED.applicable_to,
    published_on = EXCLUDED.published_on;

CREATE TABLE weather.climate_normal_series (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    release_id bigint NOT NULL
        REFERENCES weather.climate_normal_release(id),

    source_file_id bigint NOT NULL
        REFERENCES weather.source_file(id),

    station_id bigint
        REFERENCES weather.station(id),

    element_id bigint NOT NULL
        REFERENCES weather.element(id),

    source_station_id text NOT NULL,
    source_element_code text NOT NULL,

    month smallint NOT NULL,
    material_years smallint NOT NULL,

    daily_values numeric[] NOT NULL,
    daily_remarks smallint[] NOT NULL,

    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT climate_normal_station_id_format
        CHECK (
            source_station_id ~ '^[0-9]{5}$'
        ),

    CONSTRAINT climate_normal_element_code_format
        CHECK (
            source_element_code ~ '^[0-9]{4}$'
        ),

    CONSTRAINT climate_normal_month
        CHECK (
            month BETWEEN 1 AND 12
        ),

    CONSTRAINT climate_normal_material_years
        CHECK (
            material_years BETWEEN 0 AND 30
        ),

    CONSTRAINT climate_normal_daily_values_length
        CHECK (
            cardinality(daily_values) = 31
        ),

    CONSTRAINT climate_normal_daily_remarks_length
        CHECK (
            cardinality(daily_remarks) = 31
        ),

    CONSTRAINT climate_normal_daily_remarks_values
        CHECK (
            daily_remarks <@ ARRAY[0, 8]::smallint[]
            AND array_position(daily_remarks, NULL) IS NULL
        ),

    CONSTRAINT climate_normal_series_unique
        UNIQUE (
            release_id,
            source_station_id,
            source_element_code,
            month
        )
);

CREATE INDEX climate_normal_series_station_idx
    ON weather.climate_normal_series (
        station_id,
        element_id,
        month
    );

CREATE INDEX climate_normal_series_source_station_idx
    ON weather.climate_normal_series (
        source_station_id,
        source_element_code,
        month
    );

INSERT INTO weather.element_source_id (
    source_id,
    element_id,
    source_element_code,
    source_element_option
)
SELECT
    source.id,
    element.id,
    mapping.source_element_code,
    'daily_normal'
FROM weather.source
JOIN (
    VALUES
        ('daily_mean_temperature', '0500'),
        ('daily_max_temperature', '0600'),
        ('daily_min_temperature', '0700'),
        ('daily_sunshine_duration', '3500'),
        ('daily_precipitation', '4000'),
        ('daily_max_snow_depth', '6200'),
        ('daily_snowfall', '6300')
) AS mapping(element_key, source_element_code)
    ON true
JOIN weather.element
    ON element.element_key = mapping.element_key
WHERE source.source_key = 'jma_amedas_normals'
ON CONFLICT (
    source_id,
    element_id,
    source_element_code,
    source_element_option
) DO NOTHING;

COMMENT ON TABLE weather.climate_normal_release IS
    'Official climatological-normal releases published by JMA.';

COMMENT ON TABLE weather.climate_normal_series IS
    'Daily JMA normals stored as one 31-value array per station, element, and month.';

COMMENT ON COLUMN weather.climate_normal_series.daily_values IS
    'Values converted to their published units; unavailable values are null.';

COMMENT ON COLUMN weather.climate_normal_series.daily_remarks IS
    'JMA remarks corresponding to daily_values: 0 means unavailable and 8 means normal.';

COMMIT;
