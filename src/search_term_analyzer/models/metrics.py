# src/search_term_analyzer/models/metrics.py
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime, timedelta

@dataclass
class PerformanceMetrics:
    """Performance metrics for search term analysis"""
    total_terms_processed: int = 0
    successful_analyses: int = 0
    failed_analyses: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    average_processing_time: float = 0.0
    
    def calculate_success_rate(self) -> float:
        """Calculate the success rate of analyses"""
        if self.total_terms_processed == 0:
            return 0.0
        return self.successful_analyses / self.total_terms_processed

    def calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total_cache_requests = self.cache_hits + self.cache_misses
        if total_cache_requests == 0:
            return 0.0
        return self.cache_hits / total_cache_requests

@dataclass
class ComponentMetrics:
    """Metrics for individual analysis components"""
    component_name: str
    processing_time: timedelta
    success_count: int = 0
    error_count: int = 0
    average_confidence: float = 0.0
    
    def get_error_rate(self) -> float:
        """Calculate error rate for the component"""
        total = self.success_count + self.error_count
        if total == 0:
            return 0.0
        return self.error_count / total

@dataclass
class BatchMetrics:
    """Metrics for batch processing"""
    batch_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    terms_count: int = 0
    performance: PerformanceMetrics = PerformanceMetrics()
    component_metrics: Dict[str, ComponentMetrics] = field(default_factory=dict)
    
    def get_processing_duration(self) -> Optional[timedelta]:
        """Calculate total processing duration"""
        if self.end_time is None:
            return None
        return self.end_time - self.start_time
    
    def add_component_metric(self, component: ComponentMetrics) -> None:
        """Add or update component metrics"""
        self.component_metrics[component.component_name] = component
    
    def to_dict(self) -> Dict:
        """Convert metrics to dictionary format"""
        return {
            "batch_id": self.batch_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "terms_count": self.terms_count,
            "performance": {
                "total_processed": self.performance.total_terms_processed,
                "success_rate": self.performance.calculate_success_rate(),
                "cache_hit_rate": self.performance.calculate_cache_hit_rate(),
                "avg_processing_time": self.performance.average_processing_time
            },
            "component_metrics": {
                name: {
                    "processing_time": str(cm.processing_time),
                    "success_count": cm.success_count,
                    "error_count": cm.error_count,
                    "error_rate": cm.get_error_rate(),
                    "average_confidence": cm.average_confidence
                }
                for name, cm in self.component_metrics.items()
            }
        }