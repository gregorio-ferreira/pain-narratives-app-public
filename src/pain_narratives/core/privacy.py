"""Public errors identify failures without exposing provider bodies or SQL values."""

import logging
import uuid

logger = logging.getLogger(__name__)


def safe_error(error: BaseException) -> str:
    reference = getattr(error, "_pain_reference", None)
    if reference is None:
        reference = uuid.uuid4().hex[:12]
        setattr(error, "_pain_reference", reference)
        logger.error("Operation failed: reference=%s category=%s", reference, type(error).__name__)
    return f"Operation failed (reference {reference})"
