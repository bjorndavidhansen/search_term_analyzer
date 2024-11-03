from dataclasses import dataclass, field
from typing import Dict, Optional
from pathlib import Path
import json
from datetime import timedelta

@dataclass
class ProcessingConfig:
    """Configuration for processing settings"""
    batch_size: int = 32
    max_workers: int = 4
    timeout: float = 30.0
    retry_attempts: int = 3
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ProcessingConfig':
        return cls(**data)

@dataclass
class CacheConfig:
    """Configuration for caching behavior"""
    enabled: bool = True
    max_size: int = 10000
    ttl: timedelta = field(default_factory=lambda: timedelta(hours=1))
    
    def to_dict(self) -> Dict:
        return {
            'enabled': self.enabled,
            'max_size': self.max_size,
            'ttl_seconds': self.ttl.total_seconds()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CacheConfig':
        if 'ttl_seconds' in data:
            data['ttl'] = timedelta(seconds=data['ttl_seconds'])
            del data['ttl_seconds']
        return cls(**data)

@dataclass
class AnalysisConfig:
    """Configuration for analysis parameters"""
    relevance_threshold: float = 0.3
    confidence_threshold: float = 0.7
    weights: Dict[str, float] = field(default_factory=lambda: {
        'preprocessing': 0.1,
        'rule_based': 0.15,
        'fuzzy_match': 0.2,
        'ngram': 0.15,
        'similarity': 0.2,
        'semantic': 0.2
    })
    
    def validate_weights(self) -> bool:
        """Ensure weights sum to 1.0"""
        return abs(sum(self.weights.values()) - 1.0) < 1e-6

@dataclass
class MonitoringConfig:
    """Configuration for monitoring and metrics"""
    enabled: bool = True
    log_level: str = "INFO"
    metrics_interval: timedelta = field(
        default_factory=lambda: timedelta(minutes=5)
    )
    export_path: Optional[Path] = None

@dataclass
class PipelineConfig:
    """Main configuration class for the search term analyzer"""
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    distributed: bool = False
    
    @classmethod
    def load(cls, config_path: Path) -> 'PipelineConfig':
        """Load configuration from JSON file"""
        try:
            with open(config_path) as f:
                data = json.load(f)
            
            return cls(
                processing=ProcessingConfig.from_dict(data.get('processing', {})),
                cache=CacheConfig.from_dict(data.get('cache', {})),
                analysis=AnalysisConfig(**data.get('analysis', {})),
                monitoring=MonitoringConfig(**data.get('monitoring', {})),
                distributed=data.get('distributed', False)
            )
        except Exception as e:
            raise ValueError(f"Failed to load config from {config_path}: {str(e)}")
    
    def save(self, config_path: Path) -> None:
        """Save configuration to JSON file"""
        data = {
            'processing': self.processing.__dict__,
            'cache': self.cache.to_dict(),
            'analysis': self.analysis.__dict__,
            'monitoring': {
                k: str(v) if isinstance(v, Path) else v 
                for k, v in self.monitoring.__dict__.items()
            },
            'distributed': self.distributed
        }
        
        try:
            with open(config_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            raise ValueError(f"Failed to save config to {config_path}: {str(e)}")
    
    def validate(self) -> bool:
        """Validate entire configuration"""
        try:
            validations = [
                0 < self.analysis.relevance_threshold < 1,
                0 < self.analysis.confidence_threshold < 1,
                self.processing.batch_size > 0,
                self.processing.max_workers > 0,
                self.processing.timeout > 0,
                self.cache.max_size > 0,
                self.analysis.validate_weights()
            ]
            return all(validations)
        except Exception:
            return False