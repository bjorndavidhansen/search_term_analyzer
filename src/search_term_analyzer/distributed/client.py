from typing import List, Optional, Dict, Any
import asyncio
import logging
from datetime import datetime, timedelta
from distributed import Client
from distributed.utils_test import TimeoutError  # Updated import path
from distributed.worker import WorkerError      # Updated import path

from search_term_analyzer.core.config import PipelineConfig
from search_term_analyzer.core.exceptions import DistributedError, ConfigurationError  
from search_term_analyzer.models.analysis import AnalysisBatch, SearchTerm, AnalysisStatus
from search_term_analyzer.utils.monitoring import monitor_task
from search_term_analyzer.utils.validation import validate_batch_size
from search_term_analyzer.core.constants import (
    DEFAULT_PLUGIN_TIMEOUT,
    WORKER_HEALTH_CHECK_INTERVAL,
    MAX_BATCH_RETRIES,
    BATCH_PRIORITY_LEVELS
)

logger = logging.getLogger(__name__)


class BatchPriority:
    """Priority levels for batch processing"""
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
        self.max_retries = 3  # Changed from MAX_RETRIES
        self.batch_timeout = 300  # Changed from BATCH_TIMEOUT
        self._health_check_task: Optional[asyncio.Task] = None
        self._worker_health: Dict[str, Dict[str, Any]] = {}

    async def connect(self, scheduler_address: str) -> None:
        """Connect to the distributed scheduler"""
        try:
            self.client = await Client(scheduler_address, asynchronous=True)
            await self._initialize_client()
            logger.info("Successfully connected to distributed scheduler")
        except Exception as e:
            self._connection_retries += 1
            if self._connection_retries >= self.max_retries:
                raise DistributedError(
                    f"Failed to connect after {self.max_retries} attempts: {str(e)}"
                )
            await asyncio.sleep(1)
            await self.connect(scheduler_address)

    async def disconnect(self) -> None:
        """Disconnect from the distributed scheduler"""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        if self.client:
            await self.client.close()
            logger.info("Disconnected from distributed scheduler")

    async def _initialize_client(self) -> None:
        """Initialize client configuration and start health monitoring"""
        if not self.client:
            return

        try:
            await asyncio.wait_for(
                self.client.register_worker_plugin(
                    "search_term_analyzer",
                    {"config": self.config.processing.__dict__}
                ),
                timeout=DEFAULT_PLUGIN_TIMEOUT
            )
            
            self._health_check_task = asyncio.create_task(
                self._monitor_worker_health()
            )
            
        except asyncio.TimeoutError:
            raise ConfigurationError("Worker plugin registration timed out")
        except Exception as e:
            raise ConfigurationError(f"Failed to initialize client: {str(e)}")

    @monitor_task
    async def submit_batch(
        self,
        terms: List[SearchTerm],
        priority: int = BatchPriority.LOW
    ) -> str:
        """Submit a batch of search terms for analysis"""
        if not self.client:
            raise DistributedError("Not connected to scheduler")
            
        try:
            if not validate_batch_size(len(terms)):
                raise ValueError(f"Invalid batch size: {len(terms)}")
            
            batch = AnalysisBatch(
                terms=terms,
                batch_id=f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                created_at=datetime.now()
            )
            
            future = await self._submit_with_retry(batch, priority)
            self.active_batches[batch.batch_id] = batch
            
            return batch.batch_id
            
        except Exception as e:
            raise DistributedError(f"Failed to submit batch: {str(e)}")

    async def _submit_with_retry(
        self,
        batch: AnalysisBatch,
        priority: int
    ) -> Any:
        """Submit batch with retry logic and enhanced error handling"""
        if priority not in BATCH_PRIORITY_LEVELS:
            raise ValueError(
                f"Invalid priority level. Must be one of {BATCH_PRIORITY_LEVELS}"
            )
            
        for attempt in range(self.max_retries):
            try:
                return await self.client.submit(
                    self._process_batch,
                    batch,
                    key=batch.batch_id,
                    priority=priority,
                    retries=MAX_BATCH_RETRIES,
                    timeout=self.batch_timeout,
                    resources={'memory': f"{self.config.processing.batch_size * 10}MB"}
                )
            except (TimeoutError, ConnectionError) as e:
                if attempt == self.max_retries - 1:
                    raise DistributedError(
                        f"Failed to submit batch after {self.max_retries} attempts: {str(e)}"
                    )
                logger.warning(
                    f"Retry {attempt + 1} for batch {batch.batch_id}: {str(e)}"
                )
                await asyncio.sleep(1 * (attempt + 1))
            except WorkerError as e:
                raise DistributedError(f"Worker error processing batch: {str(e)}")
            except Exception as e:
                raise DistributedError(f"Unexpected error submitting batch: {str(e)}")

    async def get_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """Get status of a submitted batch"""
        if batch_id not in self.active_batches:
            raise DistributedError(f"Unknown batch ID: {batch_id}")
            
        batch = self.active_batches[batch_id]
        return {
            'batch_id': batch_id,
            'status': batch.status.value,
            'total_terms': len(batch.terms),
            'processed_terms': len(batch.results),
            'created_at': batch.created_at.isoformat(),
            'completed_at': batch.completed_at.isoformat() if batch.completed_at else None
        }

    async def get_results(self, batch_id: str) -> AnalysisBatch:
        """Get results for a completed batch"""
        if batch_id not in self.active_batches:
            raise DistributedError(f"Unknown batch ID: {batch_id}")
            
        batch = self.active_batches[batch_id]
        if not batch.is_complete():
            raise DistributedError(f"Batch {batch_id} is not complete")
            
        return batch

    async def cancel_batch(self, batch_id: str) -> None:
        """Cancel a running batch"""
        if batch_id not in self.active_batches:
            raise DistributedError(f"Unknown batch ID: {batch_id}")
            
        try:
            await self.client.cancel(batch_id)
            batch = self.active_batches[batch_id]
            batch.status = AnalysisStatus.FAILED
            batch.error = "Cancelled by user"
        except Exception as e:
            raise DistributedError(f"Failed to cancel batch: {str(e)}")

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
            status = batch.status.value
            metrics['status_counts'][status] = \
                metrics['status_counts'].get(status, 0) + 1
            
            metrics['total_terms'] += len(batch.terms)
            metrics['processed_terms'] += len(batch.results)
            
            if batch.completed_at:
                processing_time = (
                    batch.completed_at - batch.created_at
                ).total_seconds()
                processing_times.append(processing_time)
        
        if processing_times:
            metrics['average_processing_time'] = sum(processing_times) / len(
                processing_times
            )
        
        return metrics

    async def cleanup_old_batches(
        self,
        max_age: timedelta = timedelta(days=1)
    ) -> None:
        """Clean up old completed batches"""
        now = datetime.now()
        for batch_id in list(self.active_batches.keys()):
            batch = self.active_batches[batch_id]
            if batch.is_complete() and (now - batch.created_at) > max_age:
                del self.active_batches[batch_id]