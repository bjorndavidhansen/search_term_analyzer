from typing import List, Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum


class AnalysisPriority(int, Enum):
  """Priority levels for analysis requests"""
  LOW = 0
  MEDIUM = 5
  HIGH = 10
  CRITICAL = 20


class AnalysisStatus(str, Enum):
  """Status of analysis requests"""
  PENDING = "pending"
  PROCESSING = "processing"
  COMPLETED = "completed"
  FAILED = "failed"


class SearchTermRequest(BaseModel):
  """Request model for single search term analysis"""
  term: str = Field(..., min_length=3, max_length=100)
  campaign_id: str = Field(..., pattern=r'^[a-zA-Z0-9\-_]+$')
  ad_group_id: str = Field(..., pattern=r'^[a-zA-Z0-9\-_]+$')
  reference_terms: Optional[List[str]] = Field(default_factory=list)
  negative_terms: Optional[List[str]] = Field(default_factory=list)

  @validator('term')
  def validate_term(cls, v):
      if not v.strip():
          raise ValueError("Search term cannot be empty or whitespace")
      return v.strip()


class BatchAnalysisRequest(BaseModel):
  """Request model for batch analysis"""
  terms: List[SearchTermRequest] = Field(..., min_items=1, max_items=1000)
  priority: AnalysisPriority = Field(default=AnalysisPriority.LOW)
  batch_id: Optional[str] = None


class MetricsResponse(BaseModel):
  """Response model for analysis metrics"""
  relevance_score: float = Field(..., ge=0.0, le=1.0)
  confidence_score: float = Field(..., ge=0.0, le=1.0)
  component_scores: Dict[str, float] = Field(default_factory=dict)
  match_type: str = "broad"


class AnalysisResult(BaseModel):
  """Response model for analysis results"""
  search_term: str
  campaign_id: str
  ad_group_id: str
  metrics: MetricsResponse
  recommendations: List[str]
  timestamp: datetime
  status: AnalysisStatus
  error: Optional[str] = None


class AnalysisResponse(BaseModel):
  """Response model for API endpoints"""
  request_id: str
  timestamp: datetime
  status: AnalysisStatus
  results: Optional[List[AnalysisResult]] = None
  error: Optional[str] = None


class WorkerStatus(BaseModel):
  """Model for worker status information"""
  worker_id: str
  status: str
  current_batch: Optional[str]
  stats: Dict[str, Any]
  last_heartbeat: datetime


class SystemMetrics(BaseModel):
  """Model for system metrics"""
  cpu_usage: float
  memory_usage: float
  active_tasks: int
  queue_size: int


class CacheMetrics(BaseModel):
  """Model for cache metrics"""
  size: int
  hit_rate: float
  miss_rate: float
  eviction_count: int


class MetricsSnapshot(BaseModel):
  """Model for complete metrics snapshot"""
  timestamp: datetime
  system: SystemMetrics
  cache: CacheMetrics
  processing: Dict[str, Any]


class ConfigurationUpdate(BaseModel):
  """Model for configuration updates"""
  processing: Optional[Dict[str, Any]] = None
  analysis: Optional[Dict[str, Any]] = None
  cache: Optional[Dict[str, Any]] = None
  monitoring: Optional[Dict[str, Any]] = None

  @validator('*', pre=True)
  def validate_config_section(cls, v):
      if v is not None and not isinstance(v, dict):
          raise ValueError("Configuration section must be a dictionary")
      return v


# Error response models
class ErrorDetail(BaseModel):
  """Detailed error information"""
  code: str
  message: str
  details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
  """Standard error response"""
  error: ErrorDetail
  timestamp: datetime = Field(default_factory=datetime.utcnow)
  request_id: Optional[str] = None


# Feedback models
class FeedbackType(str, Enum):
  """Types of feedback"""
  RELEVANCE = "relevance"
  RECOMMENDATION = "recommendation"
  PERFORMANCE = "performance"
  ERROR = "error"


class FeedbackRequest(BaseModel):
  """Request model for submitting feedback"""
  search_term: str
  feedback_type: FeedbackType
  description: str
  suggested_score: Optional[float] = Field(None, ge=0.0, le=1.0)
  context: Optional[Dict[str, Any]] = None


class FeedbackResponse(BaseModel):
  """Response model for feedback submission"""
  feedback_id: str
  timestamp: datetime
  status: str
  message: str
  