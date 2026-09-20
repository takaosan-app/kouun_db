\set ON_ERROR_STOP on

BEGIN;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM analysis.station_daily_weather AS daily
        LEFT JOIN analysis.weather_station AS station
            ON station.station_id = daily.station_id
        WHERE station.station_id IS NULL
    ) THEN
        RAISE EXCEPTION
            'station_daily_weather contains station IDs '
            'that do not exist in analysis.weather_station';
    END IF;
END
$$;

ALTER TABLE analysis.station_daily_weather
    DROP CONSTRAINT
        station_daily_weather_station_id_fkey;

ALTER TABLE analysis.station_daily_weather
    ADD CONSTRAINT
        station_daily_weather_station_id_fkey
    FOREIGN KEY (station_id)
    REFERENCES analysis.weather_station(station_id);

COMMENT ON CONSTRAINT
    station_daily_weather_station_id_fkey
    ON analysis.station_daily_weather IS
    'Links L1 daily weather rows to the L1 weather station catalog.';

COMMIT;
