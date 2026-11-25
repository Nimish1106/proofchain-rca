class InvestigationNotFoundError(Exception):
    """Raised when an investigation does not exist."""


class NoSourceDocumentsError(Exception):
    """Raised when an investigation has no uploaded documents."""


class NoRCAEvidenceError(Exception):
    """Raised when no usable evidence exists for RCA."""


class RCAContextLimitError(Exception):
    """Raised when the RCA context exceeds configured limits."""


class RCAOutputValidationError(Exception):
    """Raised when AI-generated RCA output fails validation."""
