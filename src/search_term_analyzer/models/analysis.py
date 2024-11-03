# src/search_term_analyzer/models/analysis.py
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum

class AnalysisStatus(Enum):
    """Status of search term analysis"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class ConfidenceLevel(Enum):
    """Confidence level of analysis results"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class SearchTermMetrics:
    """Metrics for a single search term"""
    term: str
    processed_term: str
    relevance_score: float
    confidence_score: float
    component_scores: Dict[str, float] = field(default_factory=dict)
    match_type: str = "broad"
    
    def get_confidence_level(self) -> ConfidenceLevel:
        """Determine confidence level based on score"""
        if self.confidence_score >= 0.8:
            return ConfidenceLevel.HIGH
        elif self.confidence_score >= 0.5:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW

@dataclass
class AnalysisResult:
    """Result of search term analysis"""
    search_term: str
    campaign_id: str
    ad_group_id: str
    metrics: SearchTermMetrics
    recommendations: List[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    status: AnalysisStatus = AnalysisStatus.COMPLETED
    error: Optional[str] = None

    def is_relevant(self, threshold: float) -> bool:
        """Check if search term meets relevance threshold"""
        return self.metrics.relevance_score >= threshold

    def to_dict(self) -> Dict:
        """Convert result to dictionary format"""
        return {
            "search_term": self.search_term,
            "campaign_id": self.campaign_id,
            "ad_group_id": self.ad_group_id,
            "metrics": {
                "relevance_score": self.metrics.relevance_score,
                "confidence_score": self.metrics.confidence_score,
                "component_scores": self.metrics.component_scores,
                "match_type": self.metrics.match_type
            },
            "recommendations": self.recommendations,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "error": self.error
        }