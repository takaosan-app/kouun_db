\set ON_ERROR_STOP on

BEGIN;

WITH ranked_issues AS (
    SELECT
        id,
        row_number() OVER (
            PARTITION BY
                issue_code,
                area_code,
                capability_code,
                requested_start_date,
                requested_end_date,
                station_id,
                observed_on,
                element_id
            ORDER BY
                created_at DESC,
                id DESC
        ) AS duplicate_number
    FROM weather.collection_issue
    WHERE resolved_at IS NULL
)
UPDATE weather.collection_issue AS issue
SET resolved_at = CURRENT_TIMESTAMP
FROM ranked_issues
WHERE ranked_issues.id = issue.id
  AND ranked_issues.duplicate_number > 1;

CREATE UNIQUE INDEX
    collection_issue_unresolved_identity_uidx
ON weather.collection_issue (
    issue_code,
    COALESCE(area_code, ''),
    COALESCE(capability_code, ''),
    COALESCE(
        requested_start_date,
        DATE '-infinity'
    ),
    COALESCE(
        requested_end_date,
        DATE '-infinity'
    ),
    COALESCE(station_id, 0),
    COALESCE(
        observed_on,
        DATE '-infinity'
    ),
    COALESCE(element_id, 0)
)
WHERE resolved_at IS NULL;

COMMENT ON INDEX
    weather.collection_issue_unresolved_identity_uidx
IS
    'Prevents duplicate unresolved issues for the same collection target.';

COMMIT;
