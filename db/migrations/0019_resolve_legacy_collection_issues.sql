\set ON_ERROR_STOP on

BEGIN;

UPDATE weather.collection_issue
SET
    resolved_at = CURRENT_TIMESTAMP,
    details = details || jsonb_build_object(
        'resolution',
        'superseded_by_station_fallback',
        'resolved_by',
        'migration_0019'
    )
WHERE resolved_at IS NULL
  AND (
      (
          issue_code = 'no_available_observations'
          AND area_code = '35'
          AND capability_code = '100000'
          AND details ->> 'source_station_id' = 'a1678'
      )
      OR
      (
          issue_code = 'collection_job_failed'
          AND area_code = '35'
          AND capability_code = '100000'
          AND requested_start_date = DATE '2025-01-01'
          AND requested_end_date = DATE '2025-01-03'
      )
  );

COMMIT;
