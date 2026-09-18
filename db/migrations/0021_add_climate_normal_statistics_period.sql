\set ON_ERROR_STOP on

BEGIN;

ALTER TABLE weather.climate_normal_series
    ADD COLUMN statistics_started_year smallint,
    ADD COLUMN statistics_ended_year smallint;

ALTER TABLE weather.climate_normal_series
    ADD CONSTRAINT climate_normal_statistics_years_presence
    CHECK (
        (
            material_years = 0
            AND statistics_started_year IS NULL
            AND statistics_ended_year IS NULL
        )
        OR
        (
            material_years > 0
            AND statistics_started_year IS NOT NULL
            AND statistics_ended_year IS NOT NULL
        )
    );

ALTER TABLE weather.climate_normal_series
    ADD CONSTRAINT climate_normal_statistics_years_range
    CHECK (
        statistics_started_year IS NULL
        OR (
            statistics_started_year BETWEEN 1991 AND 2020
            AND statistics_ended_year
                BETWEEN statistics_started_year AND 2020
            AND material_years <= (
                statistics_ended_year
                - statistics_started_year
                + 1
            )
        )
    );

COMMENT ON COLUMN
    weather.climate_normal_series.statistics_started_year IS
    'First year of the source period; null when no normal is available.';

COMMENT ON COLUMN
    weather.climate_normal_series.statistics_ended_year IS
    'Last year of the source period; null when no normal is available.';

COMMIT;
