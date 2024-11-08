"""
Core constants and configuration values for the Search Term Analyzer.
Contains system-wide settings, thresholds, and configuration values.
"""

from typing import Dict, FrozenSet, Set  # Keep Set for future use
from datetime import timedelta
from enum import Enum

# System-wide constants
VERSION: str = "0.1.0"
DEFAULT_ENCODING: str = "utf-8"
MAX_RETRIES: int = 3

# Timeouts and intervals (in seconds)
DEFAULT_PLUGIN_TIMEOUT: int = 30
DEFAULT_REQUEST_TIMEOUT: int = 60
WORKER_HEALTH_CHECK_INTERVAL: int = 30
METRICS_UPDATE_INTERVAL: int = 300  # 5 minutes
CACHE_CLEANUP_INTERVAL = 3600  # 1 hour
DEFAULT_BATCH_TIMEOUT = 300    # 5 minutes
HEARTBEAT_INTERVAL = 10

# Batch processing
MAX_BATCH_SIZE = 1000
MIN_BATCH_SIZE = 1
MAX_BATCH_RETRIES = 2
DEFAULT_BATCH_PRIORITY = 0
BATCH_PRIORITY_LEVELS: FrozenSet[int] = frozenset([0, 5, 10, 20])  # LOW, MEDIUM, HIGH, CRITICAL

# Cache settings
DEFAULT_CACHE_TTL = timedelta(hours=1)
MAX_CACHE_SIZE = 100_000
CACHE_CLEANUP_THRESHOLD = 0.9  # 90% full triggers cleanup

# Analysis thresholds
MIN_CONFIDENCE_THRESHOLD = 0.3
MAX_CONFIDENCE_THRESHOLD = 1.0
DEFAULT_RELEVANCE_THRESHOLD = 0.7
MIN_TERM_LENGTH = 3
MAX_TERM_LENGTH = 100

# API rate limiting
RATE_LIMIT_WINDOW = timedelta(minutes=1)
MAX_REQUESTS_PER_WINDOW = 1000
TOKEN_EXPIRE_TIME = timedelta(hours=24)

# Monitoring and logging
class LogLevel(str, Enum):
    """Logging level enumeration for the application."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

DEFAULT_LOG_LEVEL = LogLevel.INFO
DEFAULT_LOG_FORMAT = (
    "%(asctime)s - %(name)s - "
    "%(levelname)s - %(message)s"
)

# File paths and directories
CONFIG_FILE_NAME = "search_term_analyzer.json"
DEFAULT_LOG_DIR = "logs"
DEFAULT_CACHE_DIR = "cache"
DEFAULT_MODEL_DIR = "models"
DEFAULT_DATA_DIR = "data"

# Analysis component weights
DEFAULT_COMPONENT_WEIGHTS: Dict[str, float] = {
    "preprocessing": 0.1,
    "rule_based": 0.15,
    "fuzzy_match": 0.2,
    "ngram": 0.15,
    "similarity": 0.2,
    "semantic": 0.2
}

# Validation patterns
VALID_TERM_PATTERN = r"^[a-zA-Z0-9\s\-_'.]+$"
VALID_ID_PATTERN = r"^[a-zA-Z0-9\-_]+$"

# Error messages
class ErrorMessages:
    """Collection of standardized error messages used across the application."""
    INVALID_CONFIG = "Invalid configuration provided: {}"
    INVALID_BATCH_SIZE = (
        f"Batch size must be between "
        f"{MIN_BATCH_SIZE} and {MAX_BATCH_SIZE}"
    )
    INVALID_CONFIDENCE = f"Confidence threshold must be between {MIN_CONFIDENCE_THRESHOLD} and {MAX_CONFIDENCE_THRESHOLD}"
    INVALID_TERM = "Invalid search term format"
    BATCH_NOT_FOUND = "Batch ID {} not found"
    WORKER_CONNECTION_ERROR = "Failed to connect to worker at {}"
    CACHE_FULL = f"Cache exceeded {MAX_CACHE_SIZE} items"
    INVALID_WEIGHTS = "Component weights must sum to 1.0"

# HTTP Status codes
class HTTPStatus:
    """HTTP status codes used throughout the application."""
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    TOO_MANY_REQUESTS = 429
    INTERNAL_ERROR = 500
    SERVICE_UNAVAILABLE = 503

# Content types
class ContentType:
    """MIME content types supported by the API."""
    JSON = "application/json"
    TEXT = "text/plain"
    HTML = "text/html"
    CSV = "text/csv"

# Security
ALLOWED_ORIGINS: FrozenSet[str] = frozenset([
    "http://localhost:8000",
    "http://localhost:3000",
    "https://api.searchterm-analyzer.com"
])

JWT_ALGORITHM = "HS256"
MIN_PASSWORD_LENGTH = 8
SALT_ROUNDS = 12

# Metric names
class MetricNames:
    """Metric names for monitoring and tracking system performance."""
    BATCH_PROCESSING_TIME = "batch_processing_time"
    TERM_PROCESSING_TIME = "term_processing_time"
    CACHE_HIT_RATIO = "cache_hit_ratio"
    WORKER_UTILIZATION = "worker_utilization"
    ERROR_RATE = "error_rate"
    BATCH_SUCCESS_RATE = "batch_success_rate"
    API_LATENCY = "api_latency"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"

# Feature flags
class FeatureFlags:
    USE_SEMANTIC_ANALYSIS = "use_semantic_analysis"
    USE_FUZZY_MATCHING = "use_fuzzy_matching"
    ENABLE_CACHING = "enable_caching"
    ENABLE_RATE_LIMITING = "enable_rate_limiting"
    ENABLE_DISTRIBUTED = "enable_distributed"
    STRICT_VALIDATION = "strict_validation"

# Default feature flag values
DEFAULT_FEATURE_FLAGS: Dict[str, bool] = {
    FeatureFlags.USE_SEMANTIC_ANALYSIS: True,
    FeatureFlags.USE_FUZZY_MATCHING: True,
    FeatureFlags.ENABLE_CACHING: True,
    FeatureFlags.ENABLE_RATE_LIMITING: True,
    FeatureFlags.ENABLE_DISTRIBUTED: False,
    FeatureFlags.STRICT_VALIDATION: False,
}

# API Routes
class APIRoutes:
    """API route definitions and route generation methods."""
    
    BASE: str = "/api/v1"
    HEALTH: str = "/health"
    BATCH: str = "/batch"
    TERMS: str = "/terms"
    ANALYSIS: str = "/analysis"
    METRICS: str = "/metrics"
    
    @classmethod
    def get_batch_route(cls, batch_id: str) -> str:
        """
        Generate the route for a specific batch ID.
        
        Args:
            batch_id: Unique identifier for the batch
            
        Returns:
            str: Formatted route string
        """
        return f"{cls.BATCH}/{batch_id}"


# Add component weights validation
assert sum(DEFAULT_COMPONENT_WEIGHTS.values()) == 1.0, "Component weights must sum to 1.0"
assert all(0 <= w <= 1 for w in DEFAULT_COMPONENT_WEIGHTS.values()), (
    "Component weights must be between 0 and 1"
)