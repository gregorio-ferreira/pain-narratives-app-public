from __future__ import annotations

import io
import zipfile
from functools import lru_cache
from pathlib import Path
from typing import BinaryIO

from markitdown import (
    FileConversionException,
    MarkItDown,
    MissingDependencyException,
    StreamInfo,
    UnsupportedFormatException,
)


@lru_cache(maxsize=1)
def _get_markitdown() -> MarkItDown:
    """Return a cached MarkItDown instance.

    Instantiating :class:`MarkItDown` is relatively expensive because it loads
    and registers a number of converters (and their dependencies).  Reusing a
    single instance keeps file uploads responsive without compromising
    performance. Uploaded files are processed only as in-memory streams.
    """

    return MarkItDown()


def file_to_markdown(file: BinaryIO, filename: str) -> str:
    """Convert an uploaded narrative file to Markdown text.

    Parameters
    ----------
    file:
        Binary file-like object positioned at the start of the uploaded data.
    filename:
        Original filename.  Used by MarkItDown to guess the correct converter.

    Returns
    -------
    str
        Extracted Markdown representation of the narrative.

    Raises
    ------
    RuntimeError
        If MarkItDown cannot convert the file because dependencies are
        missing or the content is unsupported.
    """

    # Reset the uploaded file pointer in case the caller has already read it.
    file.seek(0)
    suffix = Path(filename).suffix.lower()
    if suffix not in {".txt", ".pdf", ".docx"}:
        raise RuntimeError("Only PDF, DOCX and TXT narrative uploads are supported")
    payload = file.read(5 * 1024 * 1024 + 1)
    if len(payload) > 5 * 1024 * 1024:
        raise RuntimeError("Narrative uploads must be at most 5 MiB")
    if suffix == ".docx" and payload:
        try:
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                if sum(item.file_size for item in archive.infolist()) > 20 * 1024 * 1024:
                    raise RuntimeError("Expanded DOCX content exceeds the upload limit")
                if any(item.flag_bits & 1 for item in archive.infolist()):
                    raise RuntimeError("Encrypted DOCX files are unsupported")
        except zipfile.BadZipFile as exc:
            raise RuntimeError("Invalid DOCX upload") from exc

    if not payload:
        return ""

    stream = io.BytesIO(payload)
    stream.seek(0)

    suffix = Path(filename).suffix
    stream_info = StreamInfo(
        filename=Path(filename).name,
        extension=suffix.lower() if suffix else None,
    )

    try:
        result = _get_markitdown().convert_stream(stream, stream_info=stream_info)
    except MissingDependencyException as exc:  # pragma: no cover - defensive
        msg = "Optional dependencies required to process this file are missing."
        raise RuntimeError(msg) from exc
    except UnsupportedFormatException as exc:
        msg = f"Unsupported narrative format: '{suffix or 'unknown'}'."
        raise RuntimeError(msg) from exc
    except FileConversionException as exc:
        msg = "Failed to convert the uploaded file to Markdown."
        raise RuntimeError(msg) from exc

    return result.markdown.strip()
