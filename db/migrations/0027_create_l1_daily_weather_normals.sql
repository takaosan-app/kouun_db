\set ON_ERROR_STOP on

BEGIN;

CREATE TABLE analysis.climate_normal_release (
    climate_normal_release_id smallint
        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    release_key text NOT NULL UNIQUE,
    name text NOT NULL,
    version text NOT NULL,

    statistics_started_on date NOT NULL,
    statistics_ended_on date NOT NULL,
    applicable_from date NOT NULL,
    applicable_to date NOT NULL,
    published_on date NOT NULL,

    source_updated_at timestamptz NOT NULL,
    refreshed_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT climate_normal_release_key_format
        CHECK (
            release_key ~
                '^[a-z0-9][a-z0-9_-]*$'
        ),

    CONSTRAINT climate_normal_release_statistics_period
        CHECK (
            statistics_ended_on >=
                statistics_started_on
        ),

    CONSTRAINT climate_normal_release_applicable_period
        CHECK (
            applicable_to >= applicable_from
        )
);

CREATE TABLE analysis.station_daily_weather_normal (
    climate_normal_release_id smallint NOT NULL
        REFERENCES analysis.climate_normal_release (
            climate_normal_release_id
        ),

    station_id bigint NOT NULL
        REFERENCES analysis.weather_station (
            station_id
        ),

    month smallint NOT NULL,
    day smallint NOT NULL,

    mean_temperature smallint,
    max_temperature smallint,
    min_temperature smallint,
    precipitation smallint,
    sunshine_duration smallint,
    max_snow_depth smallint,
    snowfall smallint,

    availability_mask smallint NOT NULL,

    source_updated_at timestamptz NOT NULL,
    refreshed_at timestamptz NOT NULL DEFAULT now(),

    PRIMARY KEY (
        climate_normal_release_id,
        station_id,
        month,
        day
    ),

    CONSTRAINT station_daily_weather_normal_month
        CHECK (
            month BETWEEN 1 AND 12
        ),

    CONSTRAINT station_daily_weather_normal_day
        CHECK (
            day BETWEEN 1 AND
                CASE
                    WHEN month = 2 THEN 29
                    WHEN month IN (4, 6, 9, 11)
                        THEN 30
                    ELSE 31
                END
        ),

    CONSTRAINT station_daily_weather_normal_availability
        CHECK (
            availability_mask BETWEEN 1 AND 127
        )
);

CREATE INDEX
    station_daily_weather_normal_lookup_idx
ON analysis.station_daily_weather_normal (
    station_id,
    month,
    day,
    climate_normal_release_id
);

SELECT format(
    'GRANT DELETE ON TABLE '
    'analysis.station_daily_weather_normal '
    'TO %I',
    :'analyzer_user'
)
\gexec

COMMENT ON TABLE
    analysis.climate_normal_release IS
    'L1 catalog of official JMA climatological-normal releases.';

COMMENT ON TABLE
    analysis.station_daily_weather_normal IS
    'L1 daily climatological normals stored as one compact row per release, station, month, and day.';

COMMENT ON COLUMN
    analysis.station_daily_weather_normal.mean_temperature IS
    'Daily mean temperature normal in 0.1 degC units.';

COMMENT ON COLUMN
    analysis.station_daily_weather_normal.max_temperature IS
    'Daily maximum temperature normal in 0.1 degC units.';

COMMENT ON COLUMN
    analysis.station_daily_weather_normal.min_temperature IS
    'Daily minimum temperature normal in 0.1 degC units.';

COMMENT ON COLUMN
    analysis.station_daily_weather_normal.precipitation IS
    'Daily precipitation normal in 0.1 mm units.';

COMMENT ON COLUMN
    analysis.station_daily_weather_normal.sunshine_duration IS
    'Daily sunshine-duration normal in 0.1 hour units.';

COMMENT ON COLUMN
    analysis.station_daily_weather_normal.max_snow_depth IS
    'Daily maximum snow-depth normal in 0.1 cm units.';

COMMENT ON COLUMN
    analysis.station_daily_weather_normal.snowfall IS
    'Daily snowfall normal in 0.1 cm units.';

COMMENT ON COLUMN
    analysis.station_daily_weather_normal.availability_mask IS
    $comment$Available-value bits: mean/max/min temperature=0/1/2;
precipitation=3; sunshine duration=4;
maximum snow depth=5; snowfall=6.$comment$;

COMMIT;
