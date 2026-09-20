\set ON_ERROR_STOP on

BEGIN;

-- area master table
CREATE TABLE analysis.weather_area (
    area_code text PRIMARY KEY,
    area_name text NOT NULL UNIQUE,

    CONSTRAINT weather_area_code_format
        CHECK (area_code ~ '^[0-9]{2}$')
);

-- station master table
CREATE TABLE analysis.weather_station (
    station_id bigint PRIMARY KEY,

    station_key text NOT NULL UNIQUE,
    obsdl_station_id text UNIQUE,
    official_station_number text,

    name text NOT NULL,
    kana_name text,
    station_type_code text NOT NULL,

    location geography(Point, 4326) NOT NULL,
    elevation integer,

    observation_started_on date,
    observation_ended_on date,

    metadata_effective_from date NOT NULL,
    source_updated_at timestamptz NOT NULL,
    refreshed_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT weather_station_key_format
        CHECK (station_key ~ '^[a-z0-9][a-z0-9_-]*$'),
    CONSTRAINT weather_station_observation_period
        CHECK (
            observation_started_on IS NULL
            OR observation_ended_on IS NULL
            OR observation_ended_on >= observation_started_on
        )
);

CREATE INDEX weather_station_location_idx
    ON analysis.weather_station
    USING gist (location);

-- relationship between area and station
CREATE TABLE analysis.weather_station_area (
    station_id bigint NOT NULL
        REFERENCES analysis.weather_station(station_id)
        ON DELETE CASCADE,

    area_code text NOT NULL
        REFERENCES analysis.weather_area(area_code),

    PRIMARY KEY (
        station_id,
        area_code
    )
);

CREATE INDEX weather_station_area_area_idx
    ON analysis.weather_station_area (
        area_code,
        station_id
    );

-- weather element master table
CREATE TABLE analysis.weather_element (
    element_code smallint PRIMARY KEY,
    element_key text NOT NULL UNIQUE,
    column_name text NOT NULL UNIQUE,

    display_name text NOT NULL,
    unit text NOT NULL,
    value_kind text NOT NULL,

    scale_divisor smallint NOT NULL DEFAULT 10,
    decimal_places smallint NOT NULL DEFAULT 1,
    quality_bit_position smallint,
    display_order smallint NOT NULL,

    CONSTRAINT weather_element_key_format
        CHECK (element_key ~ '^[a-z0-9][a-z0-9_-]*$'),

    CONSTRAINT weather_element_column_format
        CHECK (column_name ~ '^[a-z][a-z0-9_]*$'),

    CONSTRAINT weather_element_value_kind
        CHECK (
            value_kind IN (
                'numeric',
                'direction'
            )
        ),

    CONSTRAINT weather_element_scale
        CHECK (scale_divisor > 0),

    CONSTRAINT weather_element_decimal_places
        CHECK (decimal_places BETWEEN 0 AND 3),

    CONSTRAINT weather_element_quality_bit
        CHECK (
            quality_bit_position IS NULL
            OR quality_bit_position BETWEEN 0 AND 62
        )
);

CREATE UNIQUE INDEX weather_element_quality_bit_idx
    ON analysis.weather_element (
        quality_bit_position
    )
    WHERE quality_bit_position IS NOT NULL;

-- relationship between station and element
CREATE TABLE analysis.station_element_capability (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    station_id bigint NOT NULL
        REFERENCES analysis.weather_station(station_id)
        ON DELETE CASCADE,

    element_code smallint NOT NULL
        REFERENCES analysis.weather_element(element_code),

    valid_from date,
    valid_to date,

    source_updated_at timestamptz NOT NULL,
    refreshed_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT station_element_capability_period
        CHECK (
            valid_from IS NULL
            OR valid_to IS NULL
            OR valid_to >= valid_from
        ),

    CONSTRAINT station_element_capability_unique
        UNIQUE NULLS NOT DISTINCT (
            station_id,
            element_code,
            valid_from
        )
);

CREATE INDEX station_element_capability_element_idx
    ON analysis.station_element_capability (
        element_code,
        station_id
    );

COMMIT;
