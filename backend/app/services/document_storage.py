import hashlib
import os
import tempfile

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from uuid import UUID

from fastapi import UploadFile


class DocumentStorageError(Exception):
    """Base exception for document storage failures."""


class InvalidDocumentUpload(DocumentStorageError):
    """Raised when the uploaded document is invalid."""


class UploadSizeLimitExceeded(DocumentStorageError):
    """Raised when the upload exceeds its configured size limit."""


@dataclass(frozen=True)
class StoredPDF:
    """Information about a successfully stored PDF."""

    original_filename: str
    storage_key: str
    absolute_path: Path
    file_size_bytes: int
    sha256: str
    content_type: str = "application/pdf"


def _sanitize_filename(filename: str | None) -> str:
    """
    Retain only a safe filename.

    Client-provided directory paths are never retained.
    """

    if not filename:
        raise InvalidDocumentUpload(
            "A filename is required."
        )

    normalized = filename.replace("\\", "/")
    safe_name = PurePosixPath(normalized).name.strip()

    if not safe_name:
        raise InvalidDocumentUpload(
            "The filename is invalid."
        )

    if any(
        ord(character) < 32 or ord(character) == 127
        for character in safe_name
    ):
        raise InvalidDocumentUpload(
            "The filename contains invalid characters."
        )

    if not safe_name.lower().endswith(".pdf"):
        raise InvalidDocumentUpload(
            "Only PDF files are accepted."
        )

    # Keep metadata within the database column length.
    suffix = ".pdf"
    stem = safe_name[:-len(suffix)]

    max_stem_length = 255 - len(suffix)

    if len(safe_name) > 255:
        stem = stem[:max_stem_length]
        safe_name = stem + suffix

    return safe_name


def resolve_storage_path(
    storage_dir: Path,
    storage_key: str,
) -> Path:
    """
    Resolve a relative storage key safely.

    Prevents absolute paths and directory traversal.
    """

    if not storage_key or "\\" in storage_key:
        raise DocumentStorageError(
            "Invalid document storage key."
        )

    relative_path = PurePosixPath(storage_key)

    if (
        relative_path.is_absolute()
        or ".." in relative_path.parts
        or not relative_path.parts
    ):
        raise DocumentStorageError(
            "Unsafe document storage key."
        )

    root = storage_dir.resolve()

    candidate = root.joinpath(
        *relative_path.parts
    ).resolve()

    try:
        candidate.relative_to(root)

    except ValueError as exc:
        raise DocumentStorageError(
            "Storage path escapes the configured directory."
        ) from exc

    return candidate


def store_pdf(
    upload: UploadFile,
    *,
    storage_dir: Path,
    investigation_id: UUID,
    document_id: UUID,
    max_size_bytes: int,
) -> StoredPDF:
    """
    Stream an uploaded PDF to local storage.

    Validates file extension, PDF signature and file size.
    Computes SHA-256 while writing.

    The temporary file is atomically moved to its final
    location after successful validation.
    """

    if max_size_bytes <= 0:
        raise ValueError(
            "Maximum upload size must be positive."
        )

    original_filename = _sanitize_filename(
        upload.filename
    )

    root = storage_dir.expanduser().resolve()

    investigation_dir = root / str(investigation_id)
    investigation_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Ensure the directory has not escaped the storage root.
    resolved_directory = investigation_dir.resolve()

    try:
        resolved_directory.relative_to(root)

    except ValueError as exc:
        raise DocumentStorageError(
            "Invalid document storage directory."
        ) from exc

    storage_key = (
        f"{investigation_id}/{document_id}.pdf"
    )

    final_path = resolve_storage_path(
        root,
        storage_key,
    )

    temporary_path: Path | None = None

    digest = hashlib.sha256()
    file_size = 0

    try:
        upload.file.seek(0)

        # Keep the temporary file on the same filesystem
        # to support atomic replacement.
        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=".upload",
            prefix="proofchain-",
            dir=resolved_directory,
            delete=False,
        ) as temporary_file:

            temporary_path = Path(
                temporary_file.name
            )

            while True:
                chunk = upload.file.read(1024 * 1024)

                if not chunk:
                    break

                file_size += len(chunk)

                if file_size > max_size_bytes:
                    raise UploadSizeLimitExceeded(
                        "The uploaded file exceeds "
                        "the configured size limit."
                    )

                digest.update(chunk)
                temporary_file.write(chunk)

            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        if file_size == 0:
            raise InvalidDocumentUpload(
                "The uploaded file is empty."
            )

        # Validate the actual PDF signature.
        with temporary_path.open("rb") as file:
            header = file.read(1024)

        if b"%PDF-" not in header:
            raise InvalidDocumentUpload(
                "The uploaded file is not a valid PDF signature."
            )

        if final_path.exists():
            raise DocumentStorageError(
                "A document already exists at the generated storage key."
            )

        os.replace(
            temporary_path,
            final_path,
        )

        temporary_path = None

        return StoredPDF(
            original_filename=original_filename,
            storage_key=storage_key,
            absolute_path=final_path,
            file_size_bytes=file_size,
            sha256=digest.hexdigest(),
        )

    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

        raise


def delete_stored_file(
    storage_dir: Path,
    storage_key: str,
) -> None:
    """
    Delete a stored file using a validated storage key.
    """

    path = resolve_storage_path(
        storage_dir,
        storage_key,
    )

    path.unlink(missing_ok=True)
