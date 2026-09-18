\set ON_ERROR_STOP on

BEGIN;

CREATE TABLE weather.station_observation_area (
    station_id bigint NOT NULL
        REFERENCES weather.station(id)
        ON DELETE CASCADE,
    area_code text NOT NULL
        REFERENCES weather.observation_area(area_code),
    created_at timestamptz NOT NULL DEFAULT now(),

    PRIMARY KEY (
        station_id,
        area_code
    )
);

INSERT INTO weather.station_observation_area (
    station_id,
    area_code
)
SELECT
    station.id,
    station.observation_area_code
FROM weather.station AS station
WHERE station.observation_area_code IS NOT NULL
ON CONFLICT DO NOTHING;

INSERT INTO weather.station_observation_area (
    station_id,
    area_code
)
SELECT DISTINCT
    profile.station_id,
    profile.area_code
FROM weather.jma_obsdl_station_profile AS profile
WHERE profile.station_id IS NOT NULL
ON CONFLICT DO NOTHING;

CREATE INDEX station_observation_area_area_idx
    ON weather.station_observation_area (
        area_code,
        station_id
    );

COMMENT ON TABLE weather.station_observation_area IS
    'Many-to-many membership between logical stations and JMA observation-selection areas.';

COMMENT ON COLUMN
    weather.station_observation_area.station_id IS
    'Logical observation station.';

COMMENT ON COLUMN
    weather.station_observation_area.area_code IS
    'JMA observation-selection area containing the station.';

COMMIT;
