\set ON_ERROR_STOP on

BEGIN;

CREATE TABLE analysis.wind_direction (
    direction_code smallint PRIMARY KEY,
    direction_key text NOT NULL UNIQUE,
    name_ja text NOT NULL UNIQUE,

    CONSTRAINT wind_direction_code_range
        CHECK (direction_code BETWEEN 0 AND 16),

    CONSTRAINT wind_direction_key_format
        CHECK (direction_key ~ '^[a-z]+$')
);

INSERT INTO analysis.wind_direction (
    direction_code,
    direction_key,
    name_ja
)
VALUES
    (0, 'calm', '静穏'),
    (1, 'n', '北'),
    (2, 'nne', '北北東'),
    (3, 'ne', '北東'),
    (4, 'ene', '東北東'),
    (5, 'e', '東'),
    (6, 'ese', '東南東'),
    (7, 'se', '南東'),
    (8, 'sse', '南南東'),
    (9, 's', '南'),
    (10, 'ssw', '南南西'),
    (11, 'sw', '南西'),
    (12, 'wsw', '西南西'),
    (13, 'w', '西'),
    (14, 'wnw', '西北西'),
    (15, 'nw', '北西'),
    (16, 'nnw', '北北西');

CREATE TABLE analysis.station_daily_weather (
    station_id bigint NOT NULL
        REFERENCES weather.station(id),
    observed_on date NOT NULL,

    mean_temperature smallint,
    max_temperature smallint,
    min_temperature smallint,
    precipitation smallint,
    rain_observed boolean,
    sunshine_duration smallint,
    mean_station_pressure smallint,
    mean_sea_level_pressure smallint,
    mean_relative_humidity smallint,
    min_relative_humidity smallint,
    mean_wind_speed smallint,
    max_wind_speed smallint,
    max_wind_direction_code smallint
        REFERENCES analysis.wind_direction(direction_code),
    max_instantaneous_wind_speed smallint,
    max_instantaneous_wind_direction_code smallint
        REFERENCES analysis.wind_direction(direction_code),
    most_frequent_wind_direction_code smallint
        REFERENCES analysis.wind_direction(direction_code),
    max_snow_depth smallint,
    snowfall smallint,

    quality_mask bigint NOT NULL DEFAULT 0,
    source_updated_at timestamptz NOT NULL,
    refreshed_at timestamptz NOT NULL DEFAULT now(),

    PRIMARY KEY (station_id, observed_on),

    CONSTRAINT station_daily_weather_quality_mask
        CHECK (quality_mask >= 0)
) PARTITION BY RANGE (observed_on);

DO $partition$
DECLARE
    year_number integer;
BEGIN
    FOR year_number IN 1991..2035 LOOP
        EXECUTE format(
            'CREATE TABLE analysis.station_daily_weather_%s '
            'PARTITION OF analysis.station_daily_weather '
            'FOR VALUES FROM (%L) TO (%L)',
            year_number,
            make_date(year_number, 1, 1),
            make_date(year_number + 1, 1, 1)
        );
    END LOOP;
END
$partition$;

CREATE TABLE analysis.station_daily_weather_default
    PARTITION OF analysis.station_daily_weather DEFAULT;

CREATE INDEX station_daily_weather_date_brin_idx
    ON analysis.station_daily_weather
    USING brin (observed_on);

COMMENT ON TABLE analysis.wind_direction IS
    'Compact L1 code list for JMA daily wind directions.';

COMMENT ON TABLE analysis.station_daily_weather IS
    'L1 daily weather: one row per logical station and date, generated from L0 observations.';

COMMENT ON COLUMN analysis.station_daily_weather.mean_temperature IS
    'Daily mean temperature in 0.1 degC units.';

COMMENT ON COLUMN analysis.station_daily_weather.max_temperature IS
    'Daily maximum temperature in 0.1 degC units.';

COMMENT ON COLUMN analysis.station_daily_weather.min_temperature IS
    'Daily minimum temperature in 0.1 degC units.';

COMMENT ON COLUMN analysis.station_daily_weather.precipitation IS
    'Daily precipitation in 0.1 mm units.';

COMMENT ON COLUMN analysis.station_daily_weather.rain_observed IS
    'Whether precipitation occurred; preserves trace precipitation when the amount is 0.0 mm.';

COMMENT ON COLUMN analysis.station_daily_weather.quality_mask IS
    $comment$Questionable-value bits: temperature mean/max/min=0/1/2;
precipitation=3; sunshine=4; station/sea pressure=5/6;
humidity mean/min=7/8; wind mean/max=9/10; max direction=11;
instantaneous speed/direction=12/13; prevailing direction=14;
maximum snow depth=15; snowfall=16.$comment$;

COMMENT ON COLUMN analysis.station_daily_weather.source_updated_at IS
    'Latest L0 observation.updated_at included in this row.';

COMMIT;
