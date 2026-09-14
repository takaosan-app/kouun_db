from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


class SourceMetadataError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ValidatedSourceArtifact:
    metadata: dict[str, object]
    storage_path: str
    content: bytes
    sha256: str
    byte_size: int


def validate_source_artifact(
    *,
    metadata_path: Path,
    content_path: Path,
    raw_root: Path,
    content_label: str,
) -> ValidatedSourceArtifact:
    metadata = read_metadata(metadata_path)

    if metadata_path.stem != content_path.stem:
        raise SourceMetadataError(
            f"{content_label} and metadata filenames "
            "do not match."
        )

    try:
        storage_path = content_path.resolve().relative_to(
            raw_root.resolve()
        )
    except ValueError as error:
        raise SourceMetadataError(
            f"{content_label} is outside the raw data "
            "directory."
        ) from error

    content = content_path.read_bytes()
    actual_sha256 = hashlib.sha256(content).hexdigest()
    recorded_sha256 = require_str(
        metadata,
        "sha256",
    )

    if actual_sha256 != recorded_sha256:
        raise SourceMetadataError(
            f"{content_label} SHA-256 does not match "
            "metadata."
        )

    byte_size = require_int(
        metadata,
        "byte_size",
    )

    if len(content) != byte_size:
        raise SourceMetadataError(
            f"{content_label} byte size does not match "
            "metadata."
        )

    return ValidatedSourceArtifact(
        metadata=metadata,
        storage_path=storage_path.as_posix(),
        content=content,
        sha256=recorded_sha256,
        byte_size=byte_size,
    )


def read_metadata(
    path: Path,
) -> dict[str, object]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
    ) as error:
        raise SourceMetadataError(
            f"Could not read metadata: {path}"
        ) from error

    if not isinstance(value, dict):
        raise SourceMetadataError(
            "Metadata root must be an object."
        )

    return value


def require_str(
    metadata: dict[str, object],
    key: str,
) -> str:
    value = metadata.get(key)

    if not isinstance(value, str) or not value:
        raise SourceMetadataError(
            f"Metadata field {key!r} must be a "
            "non-empty string."
        )

    return value


def optional_str(
    metadata: dict[str, object],
    key: str,
) -> str | None:
    value = metadata.get(key)

    if value is None:
        return None

    if not isinstance(value, str):
        raise SourceMetadataError(
            f"Metadata field {key!r} must be a "
            "string or null."
        )

    return value


def require_int(
    metadata: dict[str, object],
    key: str,
) -> int:
    value = metadata.get(key)

    if isinstance(value, bool) or not isinstance(value, int):
        raise SourceMetadataError(
            f"Metadata field {key!r} must be an integer."
        )

    return value


def require_dict(
    metadata: dict[str, object],
    key: str,
) -> dict[str, object]:
    value = metadata.get(key)

    if not isinstance(value, dict):
        raise SourceMetadataError(
            f"Metadata field {key!r} must be an object."
        )

    return value


def parse_date(
    value: str,
    field: str,
) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise SourceMetadataError(
            f"Metadata field {field!r} is not a "
            "valid date."
        ) from error


def parse_datetime(
    value: str,
    field: str,
) -> datetime:
    try:
        result = datetime.fromisoformat(value)
    except ValueError as error:
        raise SourceMetadataError(
            f"Metadata field {field!r} is not a "
            "valid datetime."
        ) from error

    if result.tzinfo is None:
        raise SourceMetadataError(
            f"Metadata field {field!r} has no timezone."
        )

    return result