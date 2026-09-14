\set ON_ERROR_STOP on

BEGIN;

ALTER TABLE weather.observation
    DROP CONSTRAINT observation_value_state;

ALTER TABLE weather.observation
    ADD CONSTRAINT observation_value_state
    CHECK (
        value_state IN (
            'observed',
            'questionable',
            'missing',
            'not_observed'
        )
    );

COMMIT;