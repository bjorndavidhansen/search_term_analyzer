from typing import Optional, Any

class SearchTermAnalyzerError(Exception):
    """Base exception class for search term analyzer"""
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message)
        self.details = details

class ConfigurationError(SearchTermAnalyzerError):
    """Raised when there's a configuration error"""
    pass

class ProcessingError(SearchTermAnalyzerError):
    """Raised when there's an error during term processing"""
    pass

class CacheError(SearchTermAnalyzerError):
    """Raised when there's a caching error"""
    pass

class ValidationError(SearchTermAnalyzerError):
    """Raised when validation fails"""
    pass

class DistributedError(SearchTermAnalyzerError):
    """Raised when there's an error in distributed processing"""
    pass

class MonitoringError(SearchTermAnalyzerError):
    """Raised when there's an error in monitoring"""
    pass

class APIError(SearchTermAnalyzerError):
    """Raised when there's an API-related error"""
    pass

class RecoveryError(SearchTermAnalyzerError):
    """Raised when error recovery fails"""
    def __init__(self, message: str, original_error: Exception, 
                 recovery_attempt: int = 0):
        super().__init__(message)
        self.original_error = original_error
        self.recovery_attempt = recovery_attempt

class ModelVersionError(SearchTermAnalyzerError):
    """Raised when there's an error with model versioning"""
    pass