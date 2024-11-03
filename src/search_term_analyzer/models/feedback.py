from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import json
import uuid

class FeedbackType(Enum):
  """Types of feedback"""
  RELEVANCE = "relevance"
  RECOMMENDATION = "recommendation"
  PERFORMANCE = "performance"
  ERROR = "error"
  SUGGESTION = "suggestion"

class FeedbackStatus(Enum):
  """Status of feedback items"""
  PENDING = "pending"
  REVIEWED = "reviewed"
  IMPLEMENTED = "implemented"
  REJECTED = "rejected"

class FeedbackPriority(Enum):
  """Priority levels for feedback"""
  LOW = "low"
  MEDIUM = "medium"
  HIGH = "high"
  CRITICAL = "critical"

@dataclass
class FeedbackMetrics:
  """Metrics associated with feedback"""
  original_score: float
  suggested_score: Optional[float] = None
  confidence_delta: Optional[float] = None
  impact_score: float = 0.0
  affected_terms: int = 0
  
  def calculate_impact(self) -> float:
      """Calculate the potential impact of the feedback"""
      if self.suggested_score is None:
          return self.impact_score
      
      score_delta = abs(self.suggested_score - self.original_score)
      return score_delta * self.affected_terms

@dataclass
class FeedbackItem:
  """Individual feedback item"""
  feedback_id: str = field(default_factory=lambda: str(uuid.uuid4()))
  type: FeedbackType
  search_term: str
  description: str
  priority: FeedbackPriority = FeedbackPriority.MEDIUM
  status: FeedbackStatus = FeedbackStatus.PENDING
  metrics: Optional[FeedbackMetrics] = None
  created_at: datetime = field(default_factory=datetime.utcnow)
  updated_at: datetime = field(default_factory=datetime.utcnow)
  reviewed_at: Optional[datetime] = None
  reviewer: Optional[str] = None
  tags: List[str] = field(default_factory=list)
  context: Dict[str, Any] = field(default_factory=dict)
  
  def update_status(
      self,
      new_status: FeedbackStatus,
      reviewer: Optional[str] = None
  ) -> None:
      """Update feedback status"""
      self.status = new_status
      self.updated_at = datetime.utcnow()
      
      if new_status == FeedbackStatus.REVIEWED:
          self.reviewed_at = datetime.utcnow()
          self.reviewer = reviewer

  def add_tag(self, tag: str) -> None:
      """Add a tag to feedback"""
      if tag not in self.tags:
          self.tags.append(tag)
          self.updated_at = datetime.utcnow()

  def update_metrics(self, metrics: FeedbackMetrics) -> None:
      """Update feedback metrics"""
      self.metrics = metrics
      self.updated_at = datetime.utcnow()

  def to_dict(self) -> Dict[str, Any]:
      """Convert feedback item to dictionary"""
      return {
          "feedback_id": self.feedback_id,
          "type": self.type.value,
          "search_term": self.search_term,
          "description": self.description,
          "priority": self.priority.value,
          "status": self.status.value,
          "metrics": {
              "original_score": self.metrics.original_score,
              "suggested_score": self.metrics.suggested_score,
              "confidence_delta": self.metrics.confidence_delta,
              "impact_score": self.metrics.impact_score,
              "affected_terms": self.metrics.affected_terms
          } if self.metrics else None,
          "created_at": self.created_at.isoformat(),
          "updated_at": self.updated_at.isoformat(),
          "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
          "reviewer": self.reviewer,
          "tags": self.tags,
          "context": self.context
      }

@dataclass
class FeedbackCollection:
  """Collection of feedback items with aggregation capabilities"""
  items: List[FeedbackItem] = field(default_factory=list)
  
  def add_item(self, item: FeedbackItem) -> None:
      """Add feedback item to collection"""
      self.items.append(item)

  def get_by_status(self, status: FeedbackStatus) -> List[FeedbackItem]:
      """Get feedback items by status"""
      return [item for item in self.items if item.status == status]

  def get_by_priority(self, priority: FeedbackPriority) -> List[FeedbackItem]:
      """Get feedback items by priority"""
      return [item for item in self.items if item.priority == priority]

  def get_by_type(self, type: FeedbackType) -> List[FeedbackItem]:
      """Get feedback items by type"""
      return [item for item in self.items if item.type == type]

  def get_by_tag(self, tag: str) -> List[FeedbackItem]:
      """Get feedback items by tag"""
      return [item for item in self.items if tag in item.tags]

  def get_metrics_summary(self) -> Dict[str, Any]:
      """Get summary metrics for feedback collection"""
      total_items = len(self.items)
      if total_items == 0:
          return {
              "total_items": 0,
              "status_distribution": {},
              "priority_distribution": {},
              "type_distribution": {},
              "average_impact": 0.0
          }

      status_dist = {
          status: len(self.get_by_status(status)) / total_items
          for status in FeedbackStatus
      }
      
      priority_dist = {
          priority: len(self.get_by_priority(priority)) / total_items
          for priority in FeedbackPriority
      }
      
      type_dist = {
          type: len(self.get_by_type(type)) / total_items
          for type in FeedbackType
      }
      
      total_impact = sum(
          item.metrics.calculate_impact()
          for item in self.items
          if item.metrics is not None
      )
      
      return {
          "total_items": total_items,
          "status_distribution": status_dist,
          "priority_distribution": priority_dist,
          "type_distribution": type_dist,
          "average_impact": total_impact / total_items
      }

  def save(self, filepath: str) -> None:
      """Save feedback collection to file"""
      data = {
          "items": [item.to_dict() for item in self.items]
      }
      with open(filepath, 'w') as f:
          json.dump(data, f, indent=2)

  @classmethod
  def load(cls, filepath: str) -> 'FeedbackCollection':
      """Load feedback collection from file"""
      with open(filepath, 'r') as f:
          data = json.load(f)
      
      collection = cls()
      for item_data in data["items"]:
          metrics_data = item_data.pop("metrics", None)
          metrics = FeedbackMetrics(**metrics_data) if metrics_data else None
          
          # Convert string dates to datetime
          for date_field in ['created_at', 'updated_at', 'reviewed_at']:
              if item_data[date_field]:
                  item_data[date_field] = datetime.fromisoformat(
                      item_data[date_field]
                  )
          
          # Convert string enums
          item_data['type'] = FeedbackType(item_data['type'])
          item_data['priority'] = FeedbackPriority(item_data['priority'])
          item_data['status'] = FeedbackStatus(item_data['status'])
          
          item = FeedbackItem(**item_data)
          item.metrics = metrics
          collection.add_item(item)
      
      return collection