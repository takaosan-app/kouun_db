\set ON_ERROR_STOP on

BEGIN;

-- weather.station_observation_area (0015) is the source of truth for
-- station-area membership. This single-valued column was filled only for
-- stations known at 0013, cannot express stations in several areas
-- (e.g. Mt. Fuji in Yamanashi and Shizuoka), and is no longer maintained.
-- Its foreign key and index (station_observation_area_idx) are dropped with it.
ALTER TABLE weather.station
    DROP COLUMN observation_area_code;

COMMIT;
