"""
Custom exception classes for the Search Term Analyzer application.
These exceptions provide structured error handling for different failure modes.
"""

from typing import Optional, Any


class SearchTermAnalyzerError(Exception):
    """Base exception class for search term analyzer."""

    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message)
        self.details = details


class ConfigurationError(SearchTermAnalyzerError):
    """
    Raised when there's a configuration error.
    Examples: invalid config file, missing required settings
    """


class ProcessingError(SearchTermAnalyzerError):
    """
    Raised when there's an error during term processing.
    Examples: tokenization failure, analysis pipeline errors
    """


class CacheError(SearchTermAnalyzerError):
    """
    Raised when there's a caching error.
    Examples: cache corruption, storage failures
    """


class ValidationError(SearchTermAnalyzerError):
    """
    Raised when validation fails.
    Examples: invalid search terms, malformed input data
    """


class DistributedError(SearchTermAnalyzerError):
    """
    Raised when there's an error in distributed processing.
    Examples: worker node failures, communication errors
    """


class MonitoringError(SearchTermAnalyzerError):
    """
    Raised when there's an error in monitoring.
    Examples: metrics collection failures, reporting errors
    """


class APIError(SearchTermAnalyzerError):
    """
    Raised when there's an API-related error.
    Examples: invalid requests, authentication failures
    """


class RecoveryError(SearchTermAnalyzerError):
    """
    Raised when error recovery fails.
    Includes context about the original error and recovery attempts.
    """

    def __init__(
        self,
        message: str,
        original_error: Exception,
        recovery_attempt: int = 0
    ):
        super().__init__(message)
        self.original_error = original_error
        self.recovery_attempt = recovery_attempt


class ModelVersionError(SearchTermAnalyzerError):
    """
    Raised when there's an error with model versioning.
    Examples: version mismatch, incompatible model formats
    """