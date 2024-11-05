from typing import Any, Callable, Dict, Optional, TypeVar, Union
from functools import wraps
import time
import asyncio
import logging
import psutil
import threading
from datetime import datetime, timedelta
from prometheus_client import Counter, Gauge, Histogram, Summary
from ..core.exceptions import MonitoringError
from ..core.constants import MetricNames

logger = logging.getLogger(__name__)

# Type variable for generic function decoration
F = TypeVar('F', bound=Callable[..., Any])

# Prometheus metrics
PROCESSING_TIME = Histogram(
    'search_term_processing_seconds',
    'Time spent processing search terms',
    ['component']
)

ERROR_COUNTER = Counter(
    'search_term_errors_total',
    'Total number of processing errors',
    ['component', 'error_type']
)

ACTIVE_TASKS = Gauge(
    'search_term_active_tasks',
    'Number of currently active tasks',
    ['component']
)

MEMORY_USAGE = Gauge(
    'search_term_memory_bytes',
    'Memory usage in bytes',
    ['type']
)

CPU_USAGE = Gauge(
    'search_term_cpu_usage',
    'CPU usage percentage',
    ['type']
)


class PerformanceMetrics:
    """Collection of performance metrics"""

    def __init__(self):
        self.start_time = datetime.now()
        self.metrics: Dict[str, Dict[str, Union[int, float, timedelta]]] = {
            'processing': {
                'total_terms': 0,
                'successful': 0,
                'failed': 0,
                'avg_time': 0.0
            },
            'cache': {
                'hits': 0,
                'misses': 0,
                'evictions': 0
            },
            'system': {
                'cpu_percent': 0.0,
                'memory_percent': 0.0,
                'active_threads': 0
            }
        }
        self._lock = threading.Lock()

    def update(self, category: str, metric: str, value: Union[int, float]) -> None:
        """Update specific metric value"""
        with self._lock:
            if category in self.metrics and metric in self.metrics[category]:
                self.metrics[category][metric] = value

    def increment(self, category: str, metric: str, amount: int = 1) -> None:
        """Increment metric counter"""
        with self._lock:
            if category in self.metrics and metric in self.metrics[category]:
                current = self.metrics[category][metric]
                if isinstance(current, (int, float)):
                    self.metrics[category][metric] = current + amount

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        with self._lock:
            return {
                'timestamp': datetime.now().isoformat(),
                'uptime': str(datetime.now() - self.start_time),
                'metrics': self.metrics.copy()
            }


class TaskMonitor:
    """Monitor for individual task execution"""

    def __init__(self, task_name: str):
        self.task_name = task_name
        self.start_time = None
        self.end_time = None
        self.error = None
        self.metrics = {}

    def __enter__(self):
        """Start monitoring"""
        self.start_time = time.time()
        ACTIVE_TASKS.labels(component=self.task_name).inc()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End monitoring"""
        self.end_time = time.time()
        ACTIVE_TASKS.labels(component=self.task_name).dec()
        
        duration = self.end_time - self.start_time
        PROCESSING_TIME.labels(component=self.task_name).observe(duration)
        
        if exc_type:
            ERROR_COUNTER.labels(
                component=self.task_name,
                error_type=exc_type.__name__
            ).inc()
            self.error = str(exc_val)

    @property
    def duration(self) -> float:
        """Get task duration"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0


def monitor_task(func: F) -> F:
    """Decorator for monitoring task execution"""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        with TaskMonitor(func.__name__) as monitor:
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                monitor.error = str(e)
                raise

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        with TaskMonitor(func.__name__) as monitor:
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                monitor.error = str(e)
                raise

    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


class SystemMonitor:
    """Monitor system resources"""

    def __init__(self, interval: float = 60.0):
        self.interval = interval
        self._stop_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start system monitoring"""
        if self._monitor_thread is not None:
            return
            
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )
        self._monitor_thread.start()

    def stop(self) -> None:
        """Stop system monitoring"""
        if self._monitor_thread is None:
            return
            
        self._stop_event.set()
        self._monitor_thread.join()
        self._monitor_thread = None

    def _monitor_loop(self) -> None:
        """Main monitoring loop"""
        while not self._stop_event.is_set():
            try:
                self._collect_metrics()
                time.sleep(self.interval)
            except Exception as e:
                logger.error(f"Error collecting system metrics: {str(e)}")

    def _collect_metrics(self) -> None:
        """Collect system metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            CPU_USAGE.labels(type='system').set(cpu_percent)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            MEMORY_USAGE.labels(type='used').set(memory.used)
            MEMORY_USAGE.labels(type='available').set(memory.available)
            
            # Process-specific metrics
            process = psutil.Process()
            CPU_USAGE.labels(type='process').set(process.cpu_percent())
            MEMORY_USAGE.labels(type='process').set(process.memory_info().rss)
            
        except Exception as e:
            raise MonitoringError(f"Failed to collect system metrics: {str(e)}")


class MetricsCollector:
    """Collect and aggregate metrics"""

    def __init__(self):
        self.performance_metrics = PerformanceMetrics()
        self.system_monitor = SystemMonitor()
        self._start_time = datetime.now()

    def start(self) -> None:
        """Start metrics collection"""
        self.system_monitor.start()

    def stop(self) -> None:
        """Stop metrics collection"""
        self.system_monitor.stop()

    def record_processing_time(
        self,
        component: str,
        duration: float
    ) -> None:
        """Record processing time for a component"""
        PROCESSING_TIME.labels(component=component).observe(duration)

    def record_error(
        self,
        component: str,
        error_type: str
    ) -> None:
        """Record processing error"""
        ERROR_COUNTER.labels(
            component=component,
            error_type=error_type
        ).inc()

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics"""
        return {
            'timestamp': datetime.now().isoformat(),
            'uptime': str(datetime.now() - self._start_time),
            'performance': self.performance_metrics.get_metrics(),
            'system': {
                'cpu_usage': CPU_USAGE.collect(),
                'memory_usage': MEMORY_USAGE.collect(),
                'active_tasks': ACTIVE_TASKS.collect()
            }
        }