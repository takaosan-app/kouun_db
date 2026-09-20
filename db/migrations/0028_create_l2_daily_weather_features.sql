\set ON_ERROR_STOP on

BEGIN;

CREATE TABLE analysis.feature_calculation_version (
    calculation_version smallint PRIMARY KEY,

    version_name text NOT NULL UNIQUE,
    description text NOT NULL,
    effective_from timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT feature_calculation_version_positive
        CHECK (
            calculation_version > 0
        ),

    CONSTRAINT feature_calculation_version_name_format
        CHECK (
            version_name ~
                '^[a-z0-9][a-z0-9_-]*$'
        )
);

INSERT INTO analysis.feature_calculation_version (
    calculation_version,
    version_name,
    description,
    effective_from
)
VALUES (
    1,
    'initial',
    'Initial cumulative, threshold-day, streak, and climate-normal comparison calculations.',
    now()
);

CREATE TABLE analysis.station_daily_weather_feature (
    station_id bigint NOT NULL,
    observed_on date NOT NULL,

    calculation_version smallint NOT NULL
        REFERENCES
            analysis.feature_calculation_version (
                calculation_version
            ),

    climate_normal_release_id smallint
        REFERENCES analysis.climate_normal_release (
            climate_normal_release_id
        ),

    -- Cumulative observed values in the same
    -- 0.1-unit scale as L1.
    cumulative_mean_temperature integer NOT NULL,
    cumulative_max_temperature integer NOT NULL,
    cumulative_min_temperature integer NOT NULL,
    cumulative_precipitation integer NOT NULL,
    cumulative_sunshine_duration integer NOT NULL,
    cumulative_mean_relative_humidity integer NOT NULL,
    cumulative_mean_wind_speed integer NOT NULL,

    -- Cumulative counts of usable L1 values.
    valid_mean_temperature_days integer NOT NULL,
    valid_max_temperature_days integer NOT NULL,
    valid_min_temperature_days integer NOT NULL,
    valid_precipitation_days integer NOT NULL,
    valid_sunshine_duration_days integer NOT NULL,
    valid_mean_relative_humidity_days integer NOT NULL,
    valid_mean_wind_speed_days integer NOT NULL,

    -- Cumulative difference from the official
    -- daily climatological normal.
    cumulative_mean_temperature_anomaly integer NOT NULL,
    cumulative_max_temperature_anomaly integer NOT NULL,
    cumulative_min_temperature_anomaly integer NOT NULL,
    cumulative_precipitation_anomaly integer NOT NULL,
    cumulative_sunshine_duration_anomaly integer NOT NULL,

    -- Days where both the observation and normal
    -- were available.
    valid_mean_temperature_normal_days integer NOT NULL,
    valid_max_temperature_normal_days integer NOT NULL,
    valid_min_temperature_normal_days integer NOT NULL,
    valid_precipitation_normal_days integer NOT NULL,
    valid_sunshine_duration_normal_days integer NOT NULL,

    -- Cumulative threshold-day counts.
    cumulative_rain_days integer NOT NULL,
    cumulative_precipitation_ge_1mm_days integer NOT NULL,
    cumulative_precipitation_ge_5mm_days integer NOT NULL,
    cumulative_precipitation_ge_10mm_days integer NOT NULL,

    cumulative_max_temperature_ge_30c_days integer NOT NULL,
    cumulative_max_temperature_ge_35c_days integer NOT NULL,
    cumulative_min_temperature_ge_25c_days integer NOT NULL,
    cumulative_min_temperature_lt_0c_days integer NOT NULL,

    cumulative_sunshine_lt_1h_days integer NOT NULL,
    cumulative_sunshine_lt_3h_days integer NOT NULL,

    -- Current streak as of observed_on.
    consecutive_rain_days smallint,
    consecutive_dry_days smallint,
    consecutive_hot_days smallint,
    consecutive_cold_days smallint,
    consecutive_low_sunshine_days smallint,

    source_updated_at timestamptz NOT NULL,
    calculated_at timestamptz NOT NULL DEFAULT now(),

    PRIMARY KEY (
        station_id,
        observed_on
    ),

    CONSTRAINT station_daily_weather_feature_source_fk
        FOREIGN KEY (
            station_id,
            observed_on
        )
        REFERENCES analysis.station_daily_weather (
            station_id,
            observed_on
        )
        ON DELETE CASCADE,

    CONSTRAINT station_daily_weather_feature_valid_counts
        CHECK (
            valid_mean_temperature_days >= 0
            AND valid_max_temperature_days >= 0
            AND valid_min_temperature_days >= 0
            AND valid_precipitation_days >= 0
            AND valid_sunshine_duration_days >= 0
            AND valid_mean_relative_humidity_days >= 0
            AND valid_mean_wind_speed_days >= 0
            AND valid_mean_temperature_normal_days >= 0
            AND valid_max_temperature_normal_days >= 0
            AND valid_min_temperature_normal_days >= 0
            AND valid_precipitation_normal_days >= 0
            AND valid_sunshine_duration_normal_days >= 0
        ),

    CONSTRAINT station_daily_weather_feature_threshold_counts
        CHECK (
            cumulative_rain_days >= 0
            AND cumulative_precipitation_ge_1mm_days >= 0
            AND cumulative_precipitation_ge_5mm_days >= 0
            AND cumulative_precipitation_ge_10mm_days >= 0
            AND cumulative_max_temperature_ge_30c_days >= 0
            AND cumulative_max_temperature_ge_35c_days >= 0
            AND cumulative_min_temperature_ge_25c_days >= 0
            AND cumulative_min_temperature_lt_0c_days >= 0
            AND cumulative_sunshine_lt_1h_days >= 0
            AND cumulative_sunshine_lt_3h_days >= 0
        ),

    CONSTRAINT station_daily_weather_feature_streaks
        CHECK (
            (
                consecutive_rain_days IS NULL
                OR consecutive_rain_days >= 0
            )
            AND (
                consecutive_dry_days IS NULL
                OR consecutive_dry_days >= 0
            )
            AND (
                consecutive_hot_days IS NULL
                OR consecutive_hot_days >= 0
            )
            AND (
                consecutive_cold_days IS NULL
                OR consecutive_cold_days >= 0
            )
            AND (
                consecutive_low_sunshine_days IS NULL
                OR consecutive_low_sunshine_days >= 0
            )
        )
) PARTITION BY RANGE (observed_on);

DO $partition$
DECLARE
    year_number integer;
BEGIN
    FOR year_number IN 1991..2035 LOOP
        EXECUTE format(
            'CREATE TABLE '
            'analysis.station_daily_weather_feature_%s '
            'PARTITION OF '
            'analysis.station_daily_weather_feature '
            'FOR VALUES FROM (%L) TO (%L)',
            year_number,
            make_date(year_number, 1, 1),
            make_date(year_number + 1, 1, 1)
        );
    END LOOP;
END
$partition$;

CREATE TABLE
    analysis.station_daily_weather_feature_default
PARTITION OF
    analysis.station_daily_weather_feature
DEFAULT;

CREATE INDEX
    station_daily_weather_feature_date_brin_idx
ON analysis.station_daily_weather_feature
USING brin (observed_on);

SELECT format(
    'GRANT DELETE ON TABLE '
    'analysis.station_daily_weather_feature '
    'TO %I',
    :'analyzer_user'
)
\gexec

COMMENT ON TABLE
    analysis.feature_calculation_version IS
    'Versions of the L2 weather-feature calculation rules.';

COMMENT ON TABLE
    analysis.station_daily_weather_feature IS
    'L2 cumulative and consecutive daily weather features generated from L1.';

COMMENT ON COLUMN
    analysis.station_daily_weather_feature.cumulative_mean_temperature IS
    'Cumulative daily mean temperature in 0.1 degC units.';

COMMENT ON COLUMN
    analysis.station_daily_weather_feature.cumulative_precipitation IS
    'Cumulative precipitation in 0.1 mm units.';

COMMENT ON COLUMN
    analysis.station_daily_weather_feature.cumulative_mean_temperature_anomaly IS
    'Cumulative observed-minus-normal daily mean temperature in 0.1 degC units.';

COMMENT ON COLUMN
    analysis.station_daily_weather_feature.cumulative_precipitation_anomaly IS
    'Cumulative observed-minus-normal precipitation in 0.1 mm units.';

COMMENT ON COLUMN
    analysis.station_daily_weather_feature.cumulative_rain_days IS
    'Cumulative number of days with rain_observed=true.';

COMMENT ON COLUMN
    analysis.station_daily_weather_feature.consecutive_rain_days IS
    'Consecutive rainy days ending on observed_on; null when precipitation availability is unknown.';

COMMENT ON COLUMN
    analysis.station_daily_weather_feature.source_updated_at IS
    'Latest L1 observation or climate-normal update included in the calculation.';

COMMIT;
