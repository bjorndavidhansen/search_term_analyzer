from typing import List, Optional, Dict, Any, Tuple
import asyncio
import logging
from datetime import datetime, timedelta
import backoff
from distributed import Client, TimeoutError, CancelledError, WorkerError
from ..core.config import PipelineConfig
from ..core.exceptions import DistributedError, ConfigurationError
from ..models.analysis import AnalysisBatch, SearchTerm, AnalysisStatus
from ..utils.monitoring import monitor_task
from ..utils.validation import validate_batch_size
from ..core.constants import (
    DEFAULT_PLUGIN_TIMEOUT,
    WORKER_HEALTH_CHECK_INTERVAL,
    MAX_BATCH_RETRIES,
    BATCH_PRIORITY_LEVELS
)

logger = logging.getLogger(__name__)

class BatchPriority:
    LOW = 0
    MEDIUM = 5
    HIGH = 10
    CRITICAL = 20

class AnalysisClient:
    """Client for distributed search term analysis"""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.client: Optional[Client] = None
        self.active_batches: Dict[str, AnalysisBatch] = {}
        self._connection_retries = 0
        self.MAX_RETRIES = 3
        self.BATCH_TIMEOUT = 300  # 5 minutes
        self._health_check_task: Optional[asyncio.Task] = None
        self._worker_health: Dict[str, Dict[str, Any]] = {}

    # ... [Previous methods remain the same until _initialize_client] ...

    async def _initialize_client(self) -> None:
        """Initialize client configuration and start health monitoring"""
        if not self.client:
            return

        try:
            # Register worker plugin with timeout
            await asyncio.wait_for(
                self.client.register_worker_plugin(
                    "search_term_analyzer",
                    {"config": self.config.processing.__dict__}
                ),
                timeout=DEFAULT_PLUGIN_TIMEOUT
            )
            
            # Start health monitoring
            self._health_check_task = asyncio.create_task(
                self._monitor_worker_health()
            )
            
        except asyncio.TimeoutError:
            raise ConfigurationError("Worker plugin registration timed out")
        except Exception as e:
            raise ConfigurationError(f"Failed to initialize client: {str(e)}")

    async def _monitor_worker_health(self) -> None:
        """Continuously monitor worker health"""
        while True:
            try:
                if self.client:
                    worker_info = await self.client.scheduler_info()
                    workers = worker_info.get('workers', {})
                    
                    for worker_id, info in workers.items():
                        self._worker_health[worker_id] = {
                            'last_seen': datetime.now(),
                            'status': info.get('status', 'unknown'),
                            'memory': info.get('memory', 0),
                            'cpu': info.get('cpu', 0),
                            'active_tasks': len(info.get('tasks', []))
                        }
                
                # Clean up old worker entries
                self._cleanup_worker_health()
                
            except Exception as e:
                logger.error(f"Error monitoring worker health: {str(e)}")
            
            await asyncio.sleep(WORKER_HEALTH_CHECK_INTERVAL)

    def _cleanup_worker_health(self) -> None:
        """Clean up old worker health entries"""
        now = datetime.now()
        stale_threshold = now - timedelta(minutes=5)
        
        for worker_id in list(self._worker_health.keys()):
            if self._worker_health[worker_id]['last_seen'] < stale_threshold:
                del self._worker_health[worker_id]

    async def get_worker_status(self) -> Dict[str, Any]:
        """Get current status of all workers"""
        return {
            'total_workers': len(self._worker_health),
            'active_workers': sum(
                1 for w in self._worker_health.values()
                if w['status'] == 'running'
            ),
            'workers': self._worker_health
        }

    async def _submit_with_retry(
        self,
        batch: AnalysisBatch,
        priority: int
    ) -> Any:
        """Submit batch with retry logic and enhanced error handling"""
        if priority not in BATCH_PRIORITY_LEVELS:
            raise ValueError(f"Invalid priority level. Must be one of {BATCH_PRIORITY_LEVELS}")
            
        for attempt in range(self.MAX_RETRIES):
            try:
                return await self.client.submit(
                    self._process_batch,
                    batch,
                    key=batch.batch_id,
                    priority=priority,
                    retries=MAX_BATCH_RETRIES,
                    timeout=self.BATCH_TIMEOUT,
                    resources={'memory': f"{self.config.processing.batch_size * 10}MB"}
                )
            except (TimeoutError, ConnectionError) as e:
                if attempt == self.MAX_RETRIES - 1:
                    raise DistributedError(f"Failed to submit batch after {self.MAX_RETRIES} attempts: {str(e)}")
                logger.warning(f"Retry {attempt + 1} for batch {batch.batch_id}: {str(e)}")
                await asyncio.sleep(1 * (attempt + 1))
            except WorkerError as e:
                raise DistributedError(f"Worker error processing batch: {str(e)}")
            except Exception as e:
                raise DistributedError(f"Unexpected error submitting batch: {str(e)}")

    async def get_batch_metrics(self) -> Dict[str, Any]:
        """Get aggregate metrics across all batches"""
        metrics = {
            'total_batches': len(self.active_batches),
            'status_counts': {},
            'total_terms': 0,
            'processed_terms': 0,
            'failed_terms': 0,
            'average_processing_time': 0.0
        }
        
        processing_times = []
        
        for batch in self.active_batches.values():
            # Update status counts
            status = batch.status.value
            metrics['status_counts'][status] = \
                metrics['status_counts'].get(status, 0) + 1
            
            # Update term counts
            metrics['total_terms'] += len(batch.terms)
            metrics['processed_terms'] += len(batch.results)
            
            # Calculate processing time if completed
            if batch.completed_at:
                processing_time = (batch.completed_at - batch.created_at).total_seconds()
                processing_times.append(processing_time)
        
        # Calculate average processing time
        if processing_times:
            metrics['average_processing_time'] = sum(processing_times) / len(processing_times)
        
        return metrics

    # ... [Previous methods for batch status, cancellation, results, and cleanup remain the same] ...