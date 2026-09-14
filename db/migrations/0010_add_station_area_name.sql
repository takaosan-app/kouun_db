\set ON_ERROR_STOP on

BEGIN;

ALTER TABLE weather.station_version
    ADD COLUMN area_name text NOT NULL;

CREATE INDEX station_version_area_name_idx
    ON weather.station_version (
        area_name,
        effective_from DESC
    );

COMMENT ON COLUMN weather.station_version.area_name IS
    'Area name from the JMA AMeDAS master, normally a prefecture name.';

COMMIT;