\set ON_ERROR_STOP on

CREATE INDEX CONCURRENTLY IF NOT EXISTS
    observation_station_element_date_idx
ON weather.observation (
    station_id,
    element_id,
    observed_on DESC
);

COMMENT ON INDEX
    weather.observation_station_element_date_idx
IS
    'Supports Viewer queries by station, element, and observation date.';
