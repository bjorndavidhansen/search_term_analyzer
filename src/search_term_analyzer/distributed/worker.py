from typing import Dict, Optional, Any, List
import asyncio
import logging
import psutil
from datetime import datetime, timedelta
from distributed import Worker
from ..core.config import ProcessingConfig
from ..core.exceptions import DistributedError, ProcessingError
from ..models.analysis import AnalysisBatch, AnalysisStatus, SearchTerm
from ..pipeline.analyzer import SearchTermAnalyzer
from ..pipeline.processor import TermProcessor
from ..utils.monitoring import monitor_task, MetricsCollector
from ..core.constants import (
    WORKER_HEALTH_CHECK_INTERVAL,
    HEARTBEAT_INTERVAL,
    DEFAULT_PLUGIN_TIMEOUT
)

logger = logging.getLogger(__name__)


class AnalysisWorker:
    """Worker node for distributed search term analysis"""
    
    def __init__(
        self,
        worker_id: str,
        config: ProcessingConfig,
        scheduler_address: str
    ):
        self.worker_id = worker_id
        self.config = config
        self.scheduler_address = scheduler_address
        self.worker: Optional[Worker] = None
        self.analyzer: Optional[SearchTermAnalyzer] = None
        self.processor: Optional[TermProcessor] = None
        self.current_batch: Optional[AnalysisBatch] = None
        self.metrics_collector = MetricsCollector()
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._health_check_task: Optional[asyncio.Task] = None
        self.stats: Dict[str, Any] = {
            'tasks_completed': 0,
            'tasks_failed': 0,
            'start_time': datetime.now(),
            'last_heartbeat': None,
            'processing_times': [],
            'memory_usage': [],
            'cpu_usage': []
        }

    async def start(self) -> None:
        """Start the worker node"""
        try:
            # Initialize distributed worker
            self.worker = await Worker(
                self.scheduler_address,
                name=self.worker_id,
                nthreads=self.config.max_workers
            )

            # Initialize processing components
            self.analyzer = SearchTermAnalyzer(self.config)
            self.processor = TermProcessor(self.config)

            # Start monitoring tasks
            self.metrics_collector.start()
            self._start_monitoring_tasks()

            logger.info(f"Worker {self.worker_id} started successfully")
        except Exception as e:
            raise DistributedError(f"Failed to start worker: {str(e)}")

    async def stop(self) -> None:
        """Stop the worker node"""
        try:
            # Stop monitoring tasks
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
            if self._health_check_task:
                self._health_check_task.cancel()

            # Stop metrics collector
            self.metrics_collector.stop()

            # Close worker connection
            if self.worker:
                await self.worker.close()

            logger.info(f"Worker {self.worker_id} stopped")
        except Exception as e:
            logger.error(f"Error stopping worker: {str(e)}")

    def _start_monitoring_tasks(self) -> None:
        """Start monitoring background tasks"""
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._health_check_task = asyncio.create_task(self._health_check_loop())

    @monitor_task
    async def process_batch(self, batch: AnalysisBatch) -> AnalysisBatch:
        """Process a batch of search terms"""
        try:
            self.current_batch = batch
            self.current_batch.status = AnalysisStatus.PROCESSING
            start_time = datetime.now()

            # Process each term in the batch
            results = []
            for term in batch.terms:
                try:
                    # Process term
                    processed_term = await self.processor.process_term(term.term)
                    
                    # Analyze processed term
                    result = await self.analyzer.analyze_term(
                        processed_term.processed,
                        term.context
                    )
                    
                    results.append(result)
                    self.stats['tasks_completed'] += 1
                except Exception as e:
                    logger.error(f"Error processing term {term}: {str(e)}")
                    self.stats['tasks_failed'] += 1
                    results.append(self._create_error_result(term, str(e)))

            # Update batch with results
            batch.results = results
            batch.status = AnalysisStatus.COMPLETED
            batch.completed_at = datetime.now()

            # Update processing statistics
            processing_time = (batch.completed_at - start_time).total_seconds()
            self.stats['processing_times'].append(processing_time)

            return batch

        except Exception as e:
            batch.status = AnalysisStatus.FAILED
            batch.error = str(e)
            raise ProcessingError(f"Batch processing failed: {str(e)}")
        finally:
            self.current_batch = None

    def _create_error_result(self, term: SearchTerm, error: str) -> Dict:
        """Create error result for failed term processing"""
        return {
            'term': term.term,
            'status': AnalysisStatus.FAILED.value,
            'error': error,
            'timestamp': datetime.now().isoformat()
        }

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats to scheduler"""
        while True:
            try:
                await self.heartbeat()
                await asyncio.sleep(HEARTBEAT_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {str(e)}")
                await asyncio.sleep(HEARTBEAT_INTERVAL)

    async def _health_check_loop(self) -> None:
        """Perform periodic health checks"""
        while True:
            try:
                await self._check_health()
                await asyncio.sleep(WORKER_HEALTH_CHECK_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {str(e)}")
                await asyncio.sleep(WORKER_HEALTH_CHECK_INTERVAL)

    async def _check_health(self) -> None:
        """Check worker health metrics"""
        try:
            # Update system metrics
            self.stats['cpu_usage'].append(psutil.cpu_percent())
            self.stats['memory_usage'].append(psutil.Process().memory_percent())

            # Cleanup old metrics (keep last hour)
            self.stats['processing_times'] = self.stats['processing_times'][-3600:]
            self.stats['cpu_usage'] = self.stats['cpu_usage'][-3600:]
            self.stats['memory_usage'] = self.stats['memory_usage'][-3600:]

        except Exception as e:
            logger.error(f"Error collecting health metrics: {str(e)}")

    async def heartbeat(self) -> Dict[str, Any]:
        """Send heartbeat status to scheduler"""
        self.stats['last_heartbeat'] = datetime.now()
        
        return {
            'worker_id': self.worker_id,
            'status': 'active',
            'current_batch': (
                self.current_batch.batch_id if self.current_batch else None
            ),
            'stats': {
                'tasks_completed': self.stats['tasks_completed'],
                'tasks_failed': self.stats['tasks_failed'],
                'uptime': str(datetime.now() - self.stats['start_time']),
                'avg_processing_time': (
                    sum(self.stats['processing_times']) / 
                    len(self.stats['processing_times'])
                    if self.stats['processing_times'] else 0
                ),
                'cpu_usage': (
                    sum(self.stats['cpu_usage'][-10:]) / 10 
                    if self.stats['cpu_usage'] else 0
                ),
                'memory_usage': (
                    sum(self.stats['memory_usage'][-10:]) / 10 
                    if self.stats['memory_usage'] else 0
                ),
                'last_heartbeat': self.stats['last_heartbeat'].isoformat()
            }
        }

    async def get_status(self) -> Dict[str, Any]:
        """Get detailed worker status"""
        return {
            'worker_id': self.worker_id,
            'status': 'active', 
            'current_batch': (
                self.current_batch.batch_id if self.current_batch else None
            ),
            'stats': self.stats,
            'metrics': await self.metrics_collector.get_metrics_summary()
        }