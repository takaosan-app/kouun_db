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
    'jma_obsdl_station',
    '気象庁',
    '過去の気象データ・ダウンロード 地点選択',
    'https://www.data.jma.go.jp/risk/obsdl/top/station',
    DATE '2026-09-14'
)
ON CONFLICT (source_key) DO UPDATE
SET
    provider_name = EXCLUDED.provider_name,
    product_name = EXCLUDED.product_name,
    base_url = EXCLUDED.base_url,
    terms_checked_on = EXCLUDED.terms_checked_on;

CREATE TABLE weather.jma_obsdl_station_profile (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    source_file_id bigint NOT NULL
        REFERENCES weather.source_file(id),

    station_id bigint
        REFERENCES weather.station(id),

    source_station_id text NOT NULL,
    prefecture_code text NOT NULL,
    name text NOT NULL,
    kana_name text NOT NULL,
    capability_code text NOT NULL,

    location geography(Point, 4326) NOT NULL,
    elevation_m numeric(8, 2),
    observation_ended_on date,

    raw_record jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT jma_obsdl_station_id_format
        CHECK (
            source_station_id ~ '^[as][0-9]{4,5}$'
        ),

    CONSTRAINT jma_obsdl_prefecture_code_format
        CHECK (
            prefecture_code ~ '^[0-9]{2}$'
        ),

    CONSTRAINT jma_obsdl_capability_code_format
        CHECK (
            capability_code ~ '^[012]{6}$'
        ),

    CONSTRAINT jma_obsdl_active_station_matched
        CHECK (
            observation_ended_on IS NOT NULL
            OR station_id IS NOT NULL
        ),

    CONSTRAINT jma_obsdl_raw_record_object
        CHECK (
            jsonb_typeof(raw_record) = 'object'
        ),

    CONSTRAINT jma_obsdl_profile_file_station_unique
        UNIQUE (
            source_file_id,
            source_station_id
        )
);

CREATE INDEX jma_obsdl_profile_station_idx
    ON weather.jma_obsdl_station_profile (
        station_id
    );

CREATE INDEX jma_obsdl_profile_source_file_idx
    ON weather.jma_obsdl_station_profile (
        source_file_id
    );

CREATE INDEX jma_obsdl_profile_location_idx
    ON weather.jma_obsdl_station_profile
    USING gist (location);

COMMENT ON TABLE weather.jma_obsdl_station_profile IS
    'Station entries parsed from the JMA obsdl station-selection HTML.';

COMMENT ON COLUMN
    weather.jma_obsdl_station_profile.capability_code IS
    'Six digits: precipitation, wind, temperature, sunshine, snow, and other.';

COMMENT ON COLUMN
    weather.jma_obsdl_station_profile.station_id IS
    'Logical station; null only when an ended station cannot be matched safely.';

COMMIT;
