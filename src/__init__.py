"""Search Term Analyzer for Google Ads optimization."""
from .core.config import PipelineConfig
from .pipeline.analyzer import SearchTermAnalyzer
from .distributed.client import AnalysisClient

__version__ = "0.1.0"
__author__ = "Bjorn David Hansen"
__email__ = "bjorndavidhansen@gmail.com"

__all__ = ["PipelineConfig", "SearchTermAnalyzer", "AnalysisClient"]