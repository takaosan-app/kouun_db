\set ON_ERROR_STOP on

BEGIN;

ALTER TABLE weather.jma_obsdl_station_profile
    RENAME COLUMN prefecture_code TO area_code;

ALTER TABLE weather.jma_obsdl_station_profile
    RENAME CONSTRAINT
        jma_obsdl_prefecture_code_format
    TO jma_obsdl_area_code_format;

COMMENT ON COLUMN
    weather.jma_obsdl_station_profile.area_code IS
    'JMA observation-selection area code; not a JIS prefecture code.';

COMMIT;
