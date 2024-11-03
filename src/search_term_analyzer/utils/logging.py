import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import json
from datetime import datetime
import structlog
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from ..core.config import MonitoringConfig
from ..core.exceptions import MonitoringError
from ..core.constants import (
  LogLevel,
  DEFAULT_LOG_FORMAT,
  DEFAULT_LOG_DIR
)

class SearchTermLogger:
  """Custom logger for search term analyzer"""
  
  def __init__(
      self,
      config: MonitoringConfig,
      log_dir: Optional[Path] = None
  ):
      self.config = config
      self.log_dir = log_dir or Path(DEFAULT_LOG_DIR)
      self._loggers: Dict[str, logging.Logger] = {}
      self._initialize_logging()

  def _initialize_logging(self) -> None:
      """Initialize logging configuration"""
      try:
          # Create log directory if it doesn't exist
          self.log_dir.mkdir(parents=True, exist_ok=True)
          
          # Configure structlog
          structlog.configure(
              processors=[
                  structlog.processors.TimeStamper(fmt="iso"),
                  structlog.stdlib.add_log_level,
                  structlog.processors.StackInfoRenderer(),
                  structlog.processors.format_exc_info,
                  structlog.processors.JSONRenderer()
              ],
              context_class=dict,
              logger_factory=structlog.stdlib.LoggerFactory(),
              wrapper_class=structlog.stdlib.BoundLogger,
              cache_logger_on_first_use=True,
          )
          
          # Configure root logger
          self._setup_root_logger()
          
          # Set up component loggers
          self._setup_component_loggers()
          
      except Exception as e:
          raise MonitoringError(f"Failed to initialize logging: {str(e)}")

  def _setup_root_logger(self) -> None:
      """Configure root logger"""
      root_logger = logging.getLogger()
      root_logger.setLevel(self.config.log_level)
      
      # Console handler
      console_handler = logging.StreamHandler(sys.stdout)
      console_handler.setFormatter(
          logging.Formatter(DEFAULT_LOG_FORMAT)
      )
      root_logger.addHandler(console_handler)
      
      # File handler
      file_handler = RotatingFileHandler(
          self.log_dir / "search_term_analyzer.log",
          maxBytes=10*1024*1024,  # 10MB
          backupCount=5
      )
      file_handler.setFormatter(
          logging.Formatter(DEFAULT_LOG_FORMAT)
      )
      root_logger.addHandler(file_handler)

  def _setup_component_loggers(self) -> None:
      """Set up loggers for different components"""
      components = [
          "analyzer",
          "processor",
          "cache",
          "api",
          "distributed"
      ]
      
      for component in components:
          logger = logging.getLogger(f"search_term_analyzer.{component}")
          
          # Component-specific file handler
          handler = TimedRotatingFileHandler(
              self.log_dir / f"{component}.log",
              when="midnight",
              interval=1,
              backupCount=7
          )
          handler.setFormatter(
              logging.Formatter(DEFAULT_LOG_FORMAT)
          )
          logger.addHandler(handler)
          
          self._loggers[component] = logger

  def get_logger(self, name: str) -> logging.Logger:
      """Get logger by name"""
      if name not in self._loggers:
          self._loggers[name] = logging.getLogger(
              f"search_term_analyzer.{name}"
          )
      return self._loggers[name]

class JsonFormatter(logging.Formatter):
  """JSON formatter for log records"""
  
  def format(self, record: logging.LogRecord) -> str:
      """Format log record as JSON"""
      log_data = {
          "timestamp": datetime.fromtimestamp(record.created).isoformat(),
          "level": record.levelname,
          "logger": record.name,
          "message": record.getMessage(),
          "module": record.module,
          "function": record.funcName,
          "line": record.lineno
      }
      
      # Add exception info if present
      if record.exc_info:
          log_data["exception"] = self.formatException(record.exc_info)
          
      # Add custom fields
      if hasattr(record, "extra"):
          log_data.update(record.extra)
          
      return json.dumps(log_data)

class MetricsLogger:
  """Logger for metrics and performance data"""
  
  def __init__(
      self,
      config: MonitoringConfig,
      log_dir: Optional[Path] = None
  ):
      self.config = config
      self.log_dir = log_dir or Path(DEFAULT_LOG_DIR)
      self.metrics_file = self.log_dir / "metrics.jsonl"
      self._setup_metrics_logging()

  def _setup_metrics_logging(self) -> None:
      """Set up metrics logging"""
      metrics_handler = RotatingFileHandler(
          self.metrics_file,
          maxBytes=50*1024*1024,  # 50MB
          backupCount=10
      )
      metrics_handler.setFormatter(JsonFormatter())
      
      self.logger = logging.getLogger("search_term_analyzer.metrics")
      self.logger.addHandler(metrics_handler)
      self.logger.setLevel(logging.INFO)

  def log_metric(
      self,
      metric_name: str,
      value: Any,
      tags: Optional[Dict[str, str]] = None
  ) -> None:
      """Log a metric value"""
      metric_data = {
          "metric": metric_name,
          "value": value,
          "timestamp": datetime.utcnow().isoformat()
      }
      
      if tags:
          metric_data["tags"] = tags
          
      self.logger.info(
          "metric_logged",
          extra=metric_data
      )

  def log_batch_metrics(
      self,
      batch_id: str,
      metrics: Dict[str, Any]
  ) -> None:
      """Log metrics for a batch"""
      self.logger.info(
          "batch_metrics",
          extra={
              "batch_id": batch_id,
              "metrics": metrics,
              "timestamp": datetime.utcnow().isoformat()
          }
      )

class AuditLogger:
  """Logger for audit trail"""
  
  def __init__(
      self,
      config: MonitoringConfig,
      log_dir: Optional[Path] = None
  ):
      self.config = config
      self.log_dir = log_dir or Path(DEFAULT_LOG_DIR)
      self.audit_file = self.log_dir / "audit.jsonl"
      self._setup_audit_logging()

  def _setup_audit_logging(self) -> None:
      """Set up audit logging"""
      audit_handler = TimedRotatingFileHandler(
          self.audit_file,
          when="midnight",
          interval=1,
          backupCount=30  # Keep 30 days of audit logs
      )
      audit_handler.setFormatter(JsonFormatter())
      
      self.logger = logging.getLogger("search_term_analyzer.audit")
      self.logger.addHandler(audit_handler)
      self.logger.setLevel(logging.INFO)

  def log_event(
      self,
      event_type: str,
      details: Dict[str, Any],
      user: Optional[str] = None
  ) -> None:
      """Log an audit event"""
      self.logger.info(
          event_type,
          extra={
              "event_type": event_type,
              "details": details,
              "user": user,
              "timestamp": datetime.utcnow().isoformat()
          }
      )

def setup_logging(
  config: MonitoringConfig,
  log_dir: Optional[Path] = None
) -> tuple[SearchTermLogger, MetricsLogger, AuditLogger]:
  """Set up all logging components"""
  search_term_logger = SearchTermLogger(config, log_dir)
  metrics_logger = MetricsLogger(config, log_dir)
  audit_logger = AuditLogger(config, log_dir)
  
  return search_term_logger, metrics_logger, audit_logger