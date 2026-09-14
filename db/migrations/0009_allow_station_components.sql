\set ON_ERROR_STOP on

BEGIN;

ALTER TABLE weather.station_version
    ADD COLUMN source_row_number integer NOT NULL;

ALTER TABLE weather.station_version
    ADD CONSTRAINT station_version_source_row_positive
    CHECK (source_row_number >= 2);

ALTER TABLE weather.station_version
    DROP CONSTRAINT station_version_station_effective_unique;

ALTER TABLE weather.station_version
    ADD CONSTRAINT station_version_station_effective_unique
    UNIQUE (
        station_id,
        effective_from,
        source_row_number
    );

ALTER TABLE weather.station_version
    DROP CONSTRAINT station_version_file_station_unique;

ALTER TABLE weather.station_version
    ADD CONSTRAINT station_version_source_row_unique
    UNIQUE (
        source_file_id,
        source_row_number
    );

COMMENT ON COLUMN weather.station_version.source_row_number IS
    'Original CSV row number; multiple rows may describe one station by observation component.';

COMMIT;
