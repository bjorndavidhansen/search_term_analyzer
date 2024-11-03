# src/search_term_analyzer/distributed/worker.py
import asyncio
from typing import Dict, Optional, Any
from datetime import datetime
import logging
from distributed import Worker
from ..core.config import ProcessingConfig
from ..core.exceptions import DistributedError
from ..models.analysis import AnalysisBatch, AnalysisStatus
from ..utils.monitoring import monitor_task

logger = logging.getLogger(__name__)

class AnalysisWorker:
    """Worker node for distributed analysis processing"""
    
    def __init__(self, 
                 worker_id: str,
                 config: ProcessingConfig,
                 scheduler_address: str):
        self.worker_id = worker_id
        self.config = config
        self.scheduler_address = scheduler_address
        self.worker: Optional[Worker] = None
        self.current_batch: Optional[AnalysisBatch] = None
        self.stats: Dict[str, Any] = {
            'tasks_completed': 0,
            'tasks_failed': 0,
            'start_time': datetime.now(),
            'last_heartbeat': None
        }

    async def start(self) -> None:
        """Start the worker node"""
        try:
            self.worker = await Worker(
                self.scheduler_address,
                name=self.worker_id,
                nthreads=self.config.max_workers
            )
            logger.info(f"Worker {self.worker_id} started successfully")
        except Exception as e:
            raise DistributedError(f"Failed to start worker: {str(e)}")

    async def stop(self) -> None:
        """Stop the worker node"""
        if self.worker:
            await self.worker.close()
            logger.info(f"Worker {self.worker_id} stopped")

    @monitor_task
    async def process_batch(self, batch: AnalysisBatch) -> AnalysisBatch:
        """Process a batch of search terms"""
        try:
            self.current_batch = batch
            self.current_batch.status = AnalysisStatus.PROCESSING
            
            # Process each term in the batch
            for term in batch.terms:
                try:
                    result = await self._analyze_term(term)
                    batch.results.append(result)
                    self.stats['tasks_completed'] += 1
                except Exception as e:
                    logger.error(f"Error processing term {term}: {str(e)}")
                    self.stats['tasks_failed'] += 1
            
            batch.status = AnalysisStatus.COMPLETED
            batch.completed_at = datetime.now()
            return batch
            
        except Exception as e:
            batch.status = AnalysisStatus.FAILED
            raise DistributedError(f"Batch processing failed: {str(e)}")
        finally:
            self.current_batch = None

    async def _analyze_term(self, term: str) -> Dict:
        """Analyze individual search term"""
        # Implementation of term analysis
        raise NotImplementedError
    
    async def heartbeat(self) -> Dict[str, Any]:
        """Send heartbeat status to scheduler"""
        self.stats['last_heartbeat'] = datetime.now()
        return {
            'worker_id': self.worker_id,
            'status': 'active',
            'stats': self.stats,
            'current_batch': self.current_batch.batch_id if self.current_batch else None
        }

# src/search_term_analyzer/distributed/client.py
from typing import List, Optional, Dict, Any
import asyncio
import logging
from datetime import datetime
from distributed import Client
from ..core.config import PipelineConfig
from ..core.exceptions import DistributedError
from ..models.analysis import AnalysisBatch, SearchTerm

logger = logging.getLogger(__name__)

class AnalysisClient:
    """Client for distributed search term analysis"""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.client: Optional[Client] = None
        self.active_batches: Dict[str, AnalysisBatch] = {}
        self._connection_retries = 0
        self.MAX_RETRIES = 3

    async def connect(self, scheduler_address: str) -> None:
        """Connect to the distributed scheduler"""
        try:
            self.client = await Client(scheduler_address, asynchronous=True)
            logger.info("Successfully connected to distributed scheduler")
        except Exception as e:
            self._connection_retries += 1
            if self._connection_retries >= self.MAX_RETRIES:
                raise DistributedError(f"Failed to connect to scheduler after {self.MAX_RETRIES} attempts: {str(e)}")
            await asyncio.sleep(1)  # Brief delay before retry
            await self.connect(scheduler_address)

    async def disconnect(self) -> None:
        """Disconnect from the distributed scheduler"""
        if self.client:
            await self.client.close()
            logger.info("Disconnected from distributed scheduler")

    async def submit_batch(self, terms: List[SearchTerm]) -> str:
        """Submit a batch of search terms for analysis"""
        if not self.client:
            raise DistributedError("Not connected to scheduler")
            
        try:
            # Create analysis batch
            batch = AnalysisBatch(
                terms=terms,
                batch_id=f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                created_at=datetime.now()
            )
            
            # Submit to scheduler
            future = await self.client.submit(
                self._process_batch,
                batch,
                key=batch.batch_id
            )
            
            # Track active batch
            self.active_batches[batch.batch_id] = batch
            
            return batch.batch_id
            
        except Exception as e:
            raise DistributedError(f"Failed to submit batch: {str(e)}")

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

    @staticmethod
    async def _process_batch(batch: AnalysisBatch) -> AnalysisBatch:
        """Process a batch of search terms (runs on worker)"""
        # Implementation would be handled by worker nodes
        raise NotImplementedError