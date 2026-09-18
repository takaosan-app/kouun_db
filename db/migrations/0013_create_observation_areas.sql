\set ON_ERROR_STOP on

BEGIN;

CREATE TABLE weather.observation_area (
    area_code text PRIMARY KEY,
    area_name text NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT observation_area_code_format
        CHECK (area_code ~ '^[0-9]{2}$')
);

INSERT INTO weather.observation_area (
    area_code,
    area_name
)
VALUES (
    '50',
    '静岡'
)
ON CONFLICT (area_code) DO UPDATE
SET area_name = EXCLUDED.area_name;

ALTER TABLE weather.station
    ADD COLUMN observation_area_code text
        REFERENCES weather.observation_area(area_code);

WITH station_area AS (
    SELECT
        profile.station_id,
        MIN(profile.prefecture_code) AS area_code
    FROM weather.jma_obsdl_station_profile AS profile
    WHERE profile.station_id IS NOT NULL
    GROUP BY profile.station_id
    HAVING COUNT(
        DISTINCT profile.prefecture_code
    ) = 1
)
UPDATE weather.station AS station
SET observation_area_code = station_area.area_code
FROM station_area
WHERE station.id = station_area.station_id;

CREATE INDEX station_observation_area_idx
    ON weather.station (
        observation_area_code,
        station_key
    );

COMMENT ON TABLE weather.observation_area IS
    'JMA observation-selection areas; Hokkaido is divided into regional areas.';

COMMENT ON COLUMN weather.observation_area.area_code IS
    'JMA obsdl area code, not a JIS prefecture code.';

COMMENT ON COLUMN weather.observation_area.area_name IS
    'JMA area name, such as 静岡, 石狩, or 十勝.';

COMMENT ON COLUMN weather.station.observation_area_code IS
    'Current JMA observation-selection area for the logical station.';

COMMIT;
