from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
import logging
from datetime import datetime
from pydantic import BaseModel, Field

from ..core.config import PipelineConfig
from ..core.exceptions import ValidationError
from ..models.analysis import AnalysisResult, AnalysisStatus
from ..pipeline.analyzer import SearchTermAnalyzer
from ..pipeline.optimizer import SearchTermOptimizer
from ..utils.monitoring import monitor_task
from ..core.constants import (
  ALLOWED_ORIGINS,
  MAX_BATCH_SIZE,
  APIRoutes,
  HTTPStatus
)

logger = logging.getLogger(__name__)

# Pydantic models for request/response
class SearchTermRequest(BaseModel):
  term: str
  campaign_id: str
  ad_group_id: str
  reference_terms: Optional[List[str]] = Field(default_factory=list)
  negative_terms: Optional[List[str]] = Field(default_factory=list)


class BatchAnalysisRequest(BaseModel):
  terms: List[SearchTermRequest]
  priority: Optional[int] = 0


class AnalysisResponse(BaseModel):
  request_id: str
  timestamp: datetime
  status: str
  results: Optional[List[Dict]] = None
  error: Optional[str] = None


# Initialize FastAPI app
app = FastAPI(
  title="Search Term Analyzer API",
  description="API for analyzing search terms and providing optimization recommendations",
  version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
  CORSMiddleware,
  allow_origins=list(ALLOWED_ORIGINS),
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

# OAuth2 scheme for authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# Dependency for getting analyzer instance
async def get_analyzer() -> SearchTermAnalyzer:
  config = PipelineConfig.load("config.json")
  return SearchTermAnalyzer(config)


@app.get(APIRoutes.HEALTH)
async def health_check() -> Dict:
  """Health check endpoint"""
  return {
      "status": "healthy",
      "timestamp": datetime.utcnow().isoformat(),
      "version": "1.0.0"
  }


@app.post(APIRoutes.ANALYZE)
@monitor_task
async def analyze_term(
  request: SearchTermRequest,
  background_tasks: BackgroundTasks,
  analyzer: SearchTermAnalyzer = Depends(get_analyzer),
  token: str = Depends(oauth2_scheme)
) -> AnalysisResponse:
  """Analyze a single search term"""
  try:
      # Create analysis context
      context = AnalysisContext(
          campaign_id=request.campaign_id,
          ad_group_id=request.ad_group_id,
          reference_terms=request.reference_terms,
          negative_terms=request.negative_terms,
          config=analyzer.config
      )

      # Perform analysis
      result = await analyzer.analyze_term(request.term, context)

      # Schedule background optimization
      background_tasks.add_task(
          optimize_result,
          result,
          analyzer.config
      )

      return AnalysisResponse(
          request_id=f"req_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
          timestamp=datetime.utcnow(),
          status=result.status.value,
          results=[result.to_dict()]
      )

  except ValidationError as e:
      raise HTTPException(
          status_code=HTTPStatus.BAD_REQUEST,
          detail=str(e)
      )
  except Exception as e:
      logger.error(f"Error analyzing term: {str(e)}")
      raise HTTPException(
          status_code=HTTPStatus.INTERNAL_ERROR,
          detail="Internal server error"
      )


@app.post(APIRoutes.BATCH)
@monitor_task
async def analyze_batch(
  request: BatchAnalysisRequest,
  background_tasks: BackgroundTasks,
  analyzer: SearchTermAnalyzer = Depends(get_analyzer),
  token: str = Depends(oauth2_scheme)
) -> AnalysisResponse:
  """Analyze a batch of search terms"""
  try:
      # Validate batch size
      if len(request.terms) > MAX_BATCH_SIZE:
          raise ValidationError(f"Batch size exceeds maximum of {MAX_BATCH_SIZE}")

      # Create analysis context for batch
      contexts = [
          AnalysisContext(
              campaign_id=term.campaign_id,
              ad_group_id=term.ad_group_id,
              reference_terms=term.reference_terms,
              negative_terms=term.negative_terms,
              config=analyzer.config
          )
          for term in request.terms
      ]

      # Process batch
      results = await analyzer.analyze_batch(
          [term.term for term in request.terms],
          contexts
      )

      # Schedule background optimization
      background_tasks.add_task(
          optimize_batch,
          results,
          analyzer.config,
          request.priority
      )

      return AnalysisResponse(
          request_id=f"batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
          timestamp=datetime.utcnow(),
          status=AnalysisStatus.COMPLETED.value,
          results=[r.to_dict() for r in results]
      )

  except ValidationError as e:
      raise HTTPException(
          status_code=HTTPStatus.BAD_REQUEST,
          detail=str(e)
      )
  except Exception as e:
      logger.error(f"Error processing batch: {str(e)}")
      raise HTTPException(
          status_code=HTTPStatus.INTERNAL_ERROR,
          detail="Internal server error"
      )


@app.get(APIRoutes.METRICS)
async def get_metrics(
  token: str = Depends(oauth2_scheme)
) -> Dict:
  """Get system metrics"""
  try:
      metrics = {
          "system": await get_system_metrics(),
          "analysis": await get_analysis_metrics(),
          "cache": await get_cache_metrics()
      }
      return metrics
  except Exception as e:
      logger.error(f"Error fetching metrics: {str(e)}")
      raise HTTPException(
          status_code=HTTPStatus.INTERNAL_ERROR,
          detail="Failed to fetch metrics"
      )


@app.get(APIRoutes.CONFIG)
async def get_configuration(
  token: str = Depends(oauth2_scheme)
) -> Dict:
  """Get current configuration"""
  try:
      config = PipelineConfig.load("config.json")
      return {
          "processing": config.processing.__dict__,
          "cache": config.cache.to_dict(),
          "analysis": config.analysis.__dict__,
          "monitoring": {
              k: str(v) if isinstance(v, Path) else v
              for k, v in config.monitoring.__dict__.items()
          }
      }
  except Exception as e:
      logger.error(f"Error fetching configuration: {str(e)}")
      raise HTTPException(
          status_code=HTTPStatus.INTERNAL_ERROR,
          detail="Failed to fetch configuration"
      )


# Background tasks
async def optimize_result(
  result: AnalysisResult,
  config: PipelineConfig
) -> None:
  """Optimize single analysis result"""
  try:
      optimizer = SearchTermOptimizer(config)
      await optimizer.optimize_results([result])
  except Exception as e:
      logger.error(f"Background optimization failed: {str(e)}")


async def optimize_batch(
  results: List[AnalysisResult],
  config: PipelineConfig,
  priority: int
) -> None:
  """Optimize batch results"""
  try:
      optimizer = SearchTermOptimizer(config)
      await optimizer.optimize_results(results, priority=priority)
  except Exception as e:
      logger.error(f"Background batch optimization failed: {str(e)}")


# Metric collection functions
async def get_system_metrics() -> Dict:
  """Get system performance metrics"""
  try:
      # Example implementation for system metrics
      cpu_usage = psutil.cpu_percent()
      memory_info = psutil.virtual_memory()
      return {
          "cpu_usage": cpu_usage,
          "memory_usage": memory_info.percent,
          "total_memory": memory_info.total,
          "available_memory": memory_info.available
      }
  except Exception as e:
      logger.error(f"Error collecting system metrics: {str(e)}")
      return {"error": "Failed to collect system metrics"}


async def get_analysis_metrics() -> Dict:
  """Get analysis performance metrics"""
  try:
      # Placeholder for actual analysis metrics
      return {
          "total_terms_analyzed": 1000,  # Example value
          "successful_analyses": 950,      # Example value
          "failed_analyses": 50             # Example value
      }
  except Exception as e:
      logger.error(f"Error collecting analysis metrics: {str(e)}")
      return {"error": "Failed to collect analysis metrics"}


async def get_cache_metrics() -> Dict:
    """Get cache performance metrics"""
    try:
        # Example implementation for cache metrics
        cache_hits = 200  # Example value
        cache_misses = 50  # Example value
        return {
            "cache_hits": cache_hits,
            "cache_misses": cache_misses,
            "hit_rate": cache_hits / (cache_hits + cache_misses) if (cache_hits + cache_misses) > 0 else 0
        }
    except Exception as e:
        logger.error(f"Error collecting cache metrics: {str(e)}")
        return {"error": "Failed to collect cache metrics"}