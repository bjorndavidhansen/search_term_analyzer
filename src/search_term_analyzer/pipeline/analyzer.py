from typing import List, Dict, Optional, Tuple
import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import Levenshtein
from ..core.config import AnalysisConfig
from ..core.exceptions import ProcessingError, ValidationError
from ..models.analysis import (
  SearchTermMetrics,
  AnalysisResult,
  AnalysisStatus,
  ConfidenceLevel
)
from ..utils.validation import validate_term
from ..utils.monitoring import monitor_task
from ..core.constants import (
  MIN_TERM_LENGTH,
  MAX_TERM_LENGTH,
  DEFAULT_COMPONENT_WEIGHTS
)

logger = logging.getLogger(__name__)

@dataclass
class AnalysisContext:
  """Context for search term analysis"""
  campaign_id: str
  ad_group_id: str
  reference_terms: List[str]
  negative_terms: List[str]
  config: AnalysisConfig

class SearchTermAnalyzer:
  """Core analyzer for search terms"""
  
  def __init__(self, config: AnalysisConfig):
      self.config = config
      self.vectorizer = TfidfVectorizer(
          analyzer='char_wb',
          ngram_range=(2, 3),
          min_df=1
      )
      self._initialize_components()

  def _initialize_components(self) -> None:
      """Initialize analysis components"""
      self.components = {
          'preprocessing': self._preprocess_term,
          'rule_based': self._apply_rules,
          'fuzzy_match': self._fuzzy_match,
          'ngram': self._ngram_analysis,
          'similarity': self._similarity_analysis,
          'semantic': self._semantic_analysis
      }
      
      # Validate component weights
      weights_sum = sum(self.config.weights.values())
      if abs(weights_sum - 1.0) > 1e-6:
          raise ValidationError(
              f"Component weights must sum to 1.0, got {weights_sum}"
          )

  @monitor_task
  async def analyze_term(
      self,
      term: str,
      context: AnalysisContext
  ) -> AnalysisResult:
      """Analyze a single search term"""
      try:
          # Validate input
          if not validate_term(term, MIN_TERM_LENGTH, MAX_TERM_LENGTH):
              raise ValidationError(f"Invalid search term: {term}")

          # Initialize metrics
          metrics = SearchTermMetrics(
              term=term,
              processed_term="",
              relevance_score=0.0,
              confidence_score=0.0,
              component_scores={}
          )

          # Run analysis components
          component_results = await asyncio.gather(
              *[
                  self._run_component(
                      component_name,
                      component_func,
                      term,
                      context,
                      metrics
                  )
                  for component_name, component_func in self.components.items()
              ]
          )

          # Aggregate results
          for result in component_results:
              metrics.component_scores.update(result)

          # Calculate final scores
          metrics.relevance_score = self._calculate_relevance_score(
              metrics.component_scores
          )
          metrics.confidence_score = self._calculate_confidence_score(
              metrics.component_scores
          )

          # Generate recommendations
          recommendations = self._generate_recommendations(metrics, context)

          return AnalysisResult(
              search_term=term,
              campaign_id=context.campaign_id,
              ad_group_id=context.ad_group_id,
              metrics=metrics,
              recommendations=recommendations,
              timestamp=datetime.utcnow(),
              status=AnalysisStatus.COMPLETED
          )

      except Exception as e:
          logger.error(f"Error analyzing term '{term}': {str(e)}")
          return AnalysisResult(
              search_term=term,
              campaign_id=context.campaign_id,
              ad_group_id=context.ad_group_id,
              metrics=metrics,
              recommendations=[],
              status=AnalysisStatus.FAILED,
              error=str(e)
          )

  async def _run_component(
      self,
      name: str,
      func: callable,
      term: str,
      context: AnalysisContext,
      metrics: SearchTermMetrics
  ) -> Dict[str, float]:
      """Run analysis component with monitoring"""
      try:
          result = await func(term, context, metrics)
          return {name: result}
      except Exception as e:
          logger.error(f"Component {name} failed: {str(e)}")
          return {name: 0.0}

  async def _preprocess_term(
      self,
      term: str,
      context: AnalysisContext,
      metrics: SearchTermMetrics
  ) -> float:
      """Preprocess search term"""
      processed = term.lower().strip()
      metrics.processed_term = processed
      return 1.0 if processed else 0.0

  async def _apply_rules(
      self,
      term: str,
      context: AnalysisContext,
      metrics: SearchTermMetrics
  ) -> float:
      """Apply rule-based analysis"""
      score = 1.0
      
      # Length penalty
      if len(term) < 4:
          score *= 0.7
      
      # Check for negative terms
      if any(neg in term.lower() for neg in context.negative_terms):
          score *= 0.3
          
      return score

  async def _fuzzy_match(
      self,
      term: str,
      context: AnalysisContext,
      metrics: SearchTermMetrics
  ) -> float:
      """Perform fuzzy matching"""
      if not context.reference_terms:
          return 0.0
          
      max_ratio = max(
          Levenshtein.ratio(term.lower(), ref.lower())
          for ref in context.reference_terms
      )
      return max_ratio

  async def _ngram_analysis(
      self,
      term: str,
      context: AnalysisContext,
      metrics: SearchTermMetrics
  ) -> float:
      """Perform n-gram analysis"""
      if not context.reference_terms:
          return 0.0
          
      term_vector = self.vectorizer.fit_transform([term])
      ref_vectors = self.vectorizer.transform(context.reference_terms)
      
      similarities = cosine_similarity(term_vector, ref_vectors)
      return float(np.max(similarities))

  async def _similarity_analysis(
      self,
      term: str,
      context: AnalysisContext,
      metrics: SearchTermMetrics
  ) -> float:
      """Analyze term similarity"""
      # Implement more sophisticated similarity analysis here
      return 0.8  # Placeholder for demonstration

  async def _semantic_analysis(
      self,
      term: str,
      context: AnalysisContext,
      metrics: SearchTermMetrics
  ) -> float:
      """Perform semantic analysis"""
      # Implement semantic analysis here
      return 0.7  # Placeholder for demonstration

  def _calculate_relevance_score(
      self,
      component_scores: Dict[str, float]
  ) -> float:
      """Calculate overall relevance score"""
      weighted_scores = [
          score * self.config.weights.get(component, 0.0)
          for component, score in component_scores.items()
      ]
      return sum(weighted_scores)

  def _calculate_confidence_score(
      self,
      component_scores: Dict[str, float]
  ) -> float:
      """Calculate confidence score"""
      # Use standard deviation of component scores as confidence indicator
      scores = list(component_scores.values())
      return 1.0 - float(np.std(scores))

  def _generate_recommendations(
      self,
      metrics: SearchTermMetrics,
      context: AnalysisContext
  ) -> List[str]:
      """Generate recommendations based on analysis"""
      recommendations = []
      
      # High relevance recommendations
      if metrics.relevance_score >= 0.8:
          if metrics.confidence_score >= 0.7:
              recommendations.append(
                  f"Add '{metrics.term}' as exact match keyword"
              )
          else:
              recommendations.append(
                  f"Monitor '{metrics.term}' performance"
              )
              
      # Low relevance recommendations
      elif metrics.relevance_score <= 0.3:
          if metrics.confidence_score >= 0.7:
              recommendations.append(
                  f"Add '{metrics.term}' as negative keyword"
              )
          else:
              recommendations.append(
                  f"Review '{metrics.term}' manually"
              )
              
      # Medium relevance recommendations
      else:
          recommendations.append(
              f"Continue gathering data for '{metrics.term}'"
          )
          
      return recommendations

  async def analyze_batch(
      self,
      terms: List[str],
      context: AnalysisContext
  ) -> List[AnalysisResult]:
      """Analyze a batch of search terms"""
      tasks = [
          self.analyze_term(term, context)
          for term in terms
      ]
      return await asyncio.gather(*tasks)