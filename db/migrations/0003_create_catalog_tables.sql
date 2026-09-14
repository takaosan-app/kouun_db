\set ON_ERROR_STOP on

BEGIN;

CREATE TABLE IF NOT EXISTS weather.source (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_key text NOT NULL UNIQUE,
    provider_name text NOT NULL,
    product_name text NOT NULL,
    base_url text NOT NULL,
    terms_checked_on date,
    created_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT source_key_format
        CHECK (source_key ~ '^[a-z0-9][a-z0-9_-]*$')
);

CREATE TABLE IF NOT EXISTS weather.station (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    station_key text NOT NULL UNIQUE,
    name text NOT NULL,
    country_code char(2) NOT NULL DEFAULT 'JP',
    created_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT station_key_format
        CHECK (station_key ~ '^[a-z0-9][a-z0-9_-]*$')
);

CREATE TABLE IF NOT EXISTS weather.station_source_id (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_id bigint NOT NULL
        REFERENCES weather.source(id),
    station_id bigint NOT NULL
        REFERENCES weather.station(id),
    source_station_id text NOT NULL,
    valid_from date,
    valid_to date,
    created_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT station_source_id_valid_period
        CHECK (
            valid_from IS NULL
            OR valid_to IS NULL
            OR valid_to >= valid_from
        ),

    CONSTRAINT station_source_id_unique
        UNIQUE NULLS NOT DISTINCT (
            source_id,
            source_station_id,
            valid_from
        )
);

CREATE INDEX IF NOT EXISTS station_source_id_station_idx
    ON weather.station_source_id (station_id);

CREATE TABLE IF NOT EXISTS weather.element (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    element_key text NOT NULL UNIQUE,
    name text NOT NULL,
    unit text NOT NULL,
    aggregation text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT element_key_format
        CHECK (element_key ~ '^[a-z0-9][a-z0-9_-]*$')
);

CREATE TABLE IF NOT EXISTS weather.element_source_id (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_id bigint NOT NULL
        REFERENCES weather.source(id),
    element_id bigint NOT NULL
        REFERENCES weather.element(id),
    source_element_code text NOT NULL,
    source_element_option text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT element_source_id_unique
        UNIQUE (
            source_id,
            source_element_code,
            source_element_option
        )
);

CREATE INDEX IF NOT EXISTS element_source_id_element_idx
    ON weather.element_source_id (element_id);

INSERT INTO weather.source (
    source_key,
    provider_name,
    product_name,
    base_url,
    terms_checked_on
)
VALUES (
    'jma_obsdl',
    '気象庁',
    '過去の気象データ・ダウンロード',
    'https://www.data.jma.go.jp/risk/obsdl/show/table',
    DATE '2026-09-12'
)
ON CONFLICT (source_key) DO UPDATE
SET
    provider_name = EXCLUDED.provider_name,
    product_name = EXCLUDED.product_name,
    base_url = EXCLUDED.base_url,
    terms_checked_on = EXCLUDED.terms_checked_on;

INSERT INTO weather.station (
    station_key,
    name
)
VALUES (
    'shizuoka',
    '静岡'
)
ON CONFLICT (station_key) DO UPDATE
SET name = EXCLUDED.name;

INSERT INTO weather.station_source_id (
    source_id,
    station_id,
    source_station_id
)
SELECT
    source.id,
    station.id,
    's47656'
FROM weather.source
CROSS JOIN weather.station
WHERE source.source_key = 'jma_obsdl'
  AND station.station_key = 'shizuoka'
ON CONFLICT (
    source_id,
    source_station_id,
    valid_from
) DO UPDATE
SET station_id = EXCLUDED.station_id;

INSERT INTO weather.element (
    element_key,
    name,
    unit,
    aggregation
)
VALUES
    ('daily_mean_temperature', '日平均気温', 'degC', 'mean'),
    ('daily_max_temperature', '日最高気温', 'degC', 'maximum'),
    ('daily_min_temperature', '日最低気温', 'degC', 'minimum'),
    ('daily_precipitation', '日降水量', 'mm', 'sum')
ON CONFLICT (element_key) DO UPDATE
SET
    name = EXCLUDED.name,
    unit = EXCLUDED.unit,
    aggregation = EXCLUDED.aggregation;

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
    ''
FROM weather.source
JOIN (
    VALUES
        ('daily_mean_temperature', '201'),
        ('daily_max_temperature', '202'),
        ('daily_min_temperature', '203'),
        ('daily_precipitation', '101')
) AS mapping(element_key, source_element_code)
    ON true
JOIN weather.element
    ON element.element_key = mapping.element_key
WHERE source.source_key = 'jma_obsdl'
ON CONFLICT (
    source_id,
    source_element_code,
    source_element_option
) DO UPDATE
SET element_id = EXCLUDED.element_id;

COMMIT;