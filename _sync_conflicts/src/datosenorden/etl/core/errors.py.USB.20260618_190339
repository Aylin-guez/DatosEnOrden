class EtlError(Exception):
    """Base exception for ETL failures."""


class ExtractError(EtlError):
    """Raised when a source cannot be retrieved safely."""


class NormalizeError(EtlError):
    """Raised when source data cannot be normalized into contracts."""


class LoadError(EtlError):
    """Raised when normalized data cannot be persisted."""
