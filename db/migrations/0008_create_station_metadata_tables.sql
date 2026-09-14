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
    'jma_amedas_master',
    '気象庁',
    '地域気象観測所一覧',
    'https://www.jma.go.jp/jma/kishou/know/amedas/ame_master.zip',
    DATE '2026-09-14'
)
ON CONFLICT (source_key) DO UPDATE
SET
    provider_name = EXCLUDED.provider_name,
    product_name = EXCLUDED.product_name,
    base_url = EXCLUDED.base_url,
    terms_checked_on = EXCLUDED.terms_checked_on;

CREATE TABLE IF NOT EXISTS weather.station_version (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    station_id bigint NOT NULL
        REFERENCES weather.station(id),
    source_file_id bigint NOT NULL
        REFERENCES weather.source_file(id),

    effective_from date NOT NULL,
    effective_to date,

    station_type_code text NOT NULL,
    name text NOT NULL,
    kana_name text,
    information_name text,
    address text NOT NULL,

    location geography(Point, 4326) NOT NULL,
    elevation_m numeric(8, 2),
    wind_sensor_height_m numeric(8, 2),
    temperature_sensor_height_m numeric(8, 2),

    observation_started_on date,
    observation_start_raw text NOT NULL,
    remarks_1 text,
    remarks_2 text,
    raw_record jsonb NOT NULL,

    created_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT station_version_effective_period
        CHECK (
            effective_to IS NULL
            OR effective_to >= effective_from
        ),

    CONSTRAINT station_version_raw_record_object
        CHECK (
            jsonb_typeof(raw_record) = 'object'
        ),

    CONSTRAINT station_version_station_effective_unique
        UNIQUE (
            station_id,
            effective_from
        ),

    CONSTRAINT station_version_file_station_unique
        UNIQUE (
            source_file_id,
            station_id
        )
);

CREATE INDEX IF NOT EXISTS station_version_location_idx
    ON weather.station_version
    USING gist (location);

CREATE INDEX IF NOT EXISTS station_version_effective_idx
    ON weather.station_version (
        effective_from,
        effective_to
    );

COMMIT;