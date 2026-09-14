from __future__ import annotations

import psycopg
from psycopg.types.json import Jsonb

from collector.models import SourceFileRecord


class SourceCatalogNotFoundError(RuntimeError):
    pass


def register_source_file(
    connection: psycopg.Connection,
    record: SourceFileRecord,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO weather.source_file (
            source_id,
            storage_path,
            sha256,
            retrieved_at,
            requested_start_date,
            requested_end_date,
            encoding,
            content_type,
            byte_size,
            source_row_count,
            collector_version,
            request_parameters,
            metadata
        )
        SELECT
            source.id,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        FROM weather.source
        WHERE source.source_key = %s
        ON CONFLICT (sha256) DO UPDATE
        SET sha256 = EXCLUDED.sha256
        RETURNING id
        """,
        (
            record.storage_path,
            record.sha256,
            record.retrieved_at,
            record.requested_start_date,
            record.requested_end_date,
            record.encoding,
            record.content_type,
            record.byte_size,
            record.source_row_count,
            record.collector_version,
            Jsonb(record.request_parameters),
            Jsonb(record.metadata),
            record.source_key,
        ),
    )

    row = cursor.fetchone()

    if row is None:
        raise SourceCatalogNotFoundError(
            f"Source is not registered: {record.source_key}"
        )

    return int(row[0])


def start_ingestion_run(
    connection: psycopg.Connection,
    source_file_id: int,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO weather.ingestion_run (
            source_file_id,
            status
        )
        VALUES (%s, 'running')
        RETURNING id
        """,
        (source_file_id,),
    )

    row = cursor.fetchone()

    if row is None:
        raise RuntimeError("Could not create ingestion run.")

    return int(row[0])

def finish_ingestion_run(
    connection: psycopg.Connection,
    ingestion_run_id: int,
    *,
    parsed: int,
    inserted: int,
    updated: int,
    unchanged: int,
    revisions: int,
) -> None:
    row = connection.execute(
        """
        UPDATE weather.ingestion_run
        SET
            status = 'succeeded',
            finished_at = now(),
            parsed_count = %s,
            inserted_count = %s,
            updated_count = %s,
            unchanged_count = %s,
            revision_count = %s,
            error_message = NULL
        WHERE id = %s
          AND status = 'running'
        RETURNING id
        """,
        (
            parsed,
            inserted,
            updated,
            unchanged,
            revisions,
            ingestion_run_id,
        ),
    ).fetchone()

    if row is None:
        raise RuntimeError(
            f"Running ingestion was not found: {ingestion_run_id}"
        )


def fail_ingestion_run(
    connection: psycopg.Connection,
    ingestion_run_id: int,
    error_message: str,
) -> None:
    row = connection.execute(
        """
        UPDATE weather.ingestion_run
        SET
            status = 'failed',
            finished_at = now(),
            error_message = %s
        WHERE id = %s
          AND status = 'running'
        RETURNING id
        """,
        (
            error_message,
            ingestion_run_id,
        ),
    ).fetchone()

    if row is None:
        raise RuntimeError(
            f"Running ingestion was not found: {ingestion_run_id}"
        )