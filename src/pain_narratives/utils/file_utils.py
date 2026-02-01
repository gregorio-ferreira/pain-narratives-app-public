from __future__ import annotations

import io
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
    thread-safety—the Streamlit app runs in a single process.
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
    payload = file.read()

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
