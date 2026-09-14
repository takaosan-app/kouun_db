\set ON_ERROR_STOP on

BEGIN;

ALTER TABLE weather.element
    ADD COLUMN value_kind text NOT NULL DEFAULT 'numeric';

ALTER TABLE weather.element
    ADD CONSTRAINT element_value_kind
    CHECK (
        value_kind IN (
            'numeric',
            'direction',
            'text'
        )
    );

ALTER TABLE weather.observation
    ADD COLUMN text_value text;

ALTER TABLE weather.observation
    DROP CONSTRAINT observation_value_consistency;

ALTER TABLE weather.observation
    ADD CONSTRAINT observation_value_consistency
    CHECK (
        (
            value_state IN ('observed', 'questionable')
            AND (
                (
                    value IS NOT NULL
                    AND text_value IS NULL
                )
                OR
                (
                    value IS NULL
                    AND text_value IS NOT NULL
                )
            )
        )
        OR
        (
            value_state IN ('missing', 'not_observed')
            AND value IS NULL
            AND text_value IS NULL
        )
    );

COMMENT ON COLUMN weather.observation.value IS
    'Normalized numeric value; NULL for direction and text elements.';

COMMENT ON COLUMN weather.observation.text_value IS
    'Normalized direction or text value; NULL for numeric elements.';

COMMIT;
