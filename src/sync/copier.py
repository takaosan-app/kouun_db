from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import psycopg
from psycopg import sql

from sync.tables import TableSpec


@dataclass(frozen=True)
class CopyResult:
    copied: int
    changed: int
    deleted: int


def copy_table(
    source: psycopg.Connection,
    target: psycopg.Connection,
    spec: TableSpec,
    station_ids: list[int],
    since: date | None,
) -> CopyResult:
    staging = sql.Identifier(f"staging_{spec.name}")
    target.execute(
        sql.SQL(
            "CREATE TEMP TABLE {staging} "
            "(LIKE weather.{table} INCLUDING DEFAULTS) ON COMMIT DROP"
        ).format(staging=staging, table=sql.Identifier(spec.name))
    )

    copied = _stream_rows(source, target, spec, staging, station_ids, since)
    changed = _upsert(target, spec, staging)
    deleted = (
        _delete_missing(target, spec, staging, station_ids)
        if spec.delete_missing
        else 0
    )
    return CopyResult(copied=copied, changed=changed, deleted=deleted)


def purge_expired(
    target: psycopg.Connection,
    spec: TableSpec,
) -> int:
    if spec.date_column is None or spec.retention is None:
        return 0

    cursor = target.execute(
        sql.SQL(
            "DELETE FROM weather.{table} "
            "WHERE {column} < current_date - {retention}::interval"
        ).format(
            table=sql.Identifier(spec.name),
            column=sql.Identifier(spec.date_column),
            retention=sql.Literal(spec.retention),
        )
    )
    return cursor.rowcount


def _stream_rows(
    source: psycopg.Connection,
    target: psycopg.Connection,
    spec: TableSpec,
    staging: sql.Identifier,
    station_ids: list[int],
    since: date | None,
) -> int:
    columns = sql.SQL(", ").join(map(sql.Identifier, spec.columns))
    conditions: list[sql.Composable] = [sql.SQL("TRUE")]
    params: list[object] = []

    if spec.station_scoped:
        conditions.append(sql.SQL("station_id = ANY(%s)"))
        params.append(station_ids)

    if spec.date_column is not None:
        column = sql.Identifier(spec.date_column)

        if spec.retention is not None:
            conditions.append(
                sql.SQL("{column} >= current_date - {retention}::interval").format(
                    column=column,
                    retention=sql.Literal(spec.retention),
                )
            )

        if since is not None:
            conditions.append(sql.SQL("{column} >= %s").format(column=column))
            params.append(since)

    select = sql.SQL(
        "COPY (SELECT {columns} FROM analysis.{table} WHERE {conditions}) TO STDOUT"
    ).format(
        columns=columns,
        table=sql.Identifier(spec.name),
        conditions=sql.SQL(" AND ").join(conditions),
    )
    insert = sql.SQL("COPY {staging} ({columns}) FROM STDIN").format(
        staging=staging,
        columns=columns,
    )

    with (
        source.cursor().copy(select, params) as reader,
        target.cursor().copy(insert) as writer,
    ):
        for data in reader:
            writer.write(data)

    return target.execute(
        sql.SQL("SELECT count(*) FROM {staging}").format(staging=staging)
    ).fetchone()[0]


def _upsert(
    target: psycopg.Connection,
    spec: TableSpec,
    staging: sql.Identifier,
) -> int:
    value_columns = [c for c in spec.columns if c not in spec.key_columns]
    columns = sql.SQL(", ").join(map(sql.Identifier, spec.columns))
    keys = sql.SQL(", ").join(map(sql.Identifier, spec.key_columns))
    assignments = sql.SQL(", ").join(
        sql.SQL("{column} = EXCLUDED.{column}").format(column=sql.Identifier(c))
        for c in value_columns
    )
    current = sql.SQL(", ").join(
        sql.SQL("target.{column}").format(column=sql.Identifier(c))
        for c in value_columns
    )
    incoming = sql.SQL(", ").join(
        sql.SQL("EXCLUDED.{column}").format(column=sql.Identifier(c))
        for c in value_columns
    )

    # Only rows whose values actually changed are written.
    cursor = target.execute(
        sql.SQL(
            "INSERT INTO weather.{table} AS target ({columns}) "
            "SELECT {columns} FROM {staging} "
            "ON CONFLICT ({keys}) DO UPDATE SET {assignments} "
            "WHERE ({current}) IS DISTINCT FROM ({incoming})"
        ).format(
            table=sql.Identifier(spec.name),
            columns=columns,
            staging=staging,
            keys=keys,
            assignments=assignments,
            current=current,
            incoming=incoming,
        )
    )
    return cursor.rowcount


def _delete_missing(
    target: psycopg.Connection,
    spec: TableSpec,
    staging: sql.Identifier,
    station_ids: list[int],
) -> int:
    match = sql.SQL(" AND ").join(
        sql.SQL("staging.{column} = target.{column}").format(
            column=sql.Identifier(c)
        )
        for c in spec.key_columns
    )
    cursor = target.execute(
        sql.SQL(
            "DELETE FROM weather.{table} AS target "
            "WHERE target.station_id = ANY(%s) "
            "AND NOT EXISTS (SELECT 1 FROM {staging} AS staging WHERE {match})"
        ).format(
            table=sql.Identifier(spec.name),
            staging=staging,
            match=match,
        ),
        (station_ids,),
    )
    return cursor.rowcount
