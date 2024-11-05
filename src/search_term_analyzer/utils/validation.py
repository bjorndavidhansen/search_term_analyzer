from typing import List, Dict, Optional, Union, Any
import re
from pathlib import Path
import json
from datetime import datetime
from ..core.exceptions import ValidationError
from ..core.constants import (
  MIN_TERM_LENGTH,
  MAX_TERM_LENGTH,
  VALID_TERM_PATTERN,
  VALID_ID_PATTERN,
  MIN_BATCH_SIZE,
  MAX_BATCH_SIZE,
  MIN_CONFIDENCE_THRESHOLD,
  MAX_CONFIDENCE_THRESHOLD
)

def validate_term(
  term: str,
  min_length: int = MIN_TERM_LENGTH,
  max_length: int = MAX_TERM_LENGTH
) -> bool:
  """
  Validate search term format and length
  
  Args:
      term: Search term to validate
      min_length: Minimum allowed length
      max_length: Maximum allowed length
      
  Returns:
      bool: True if term is valid
      
  Raises:
      ValidationError: If term is invalid
  """
  if not isinstance(term, str):
      raise ValidationError("Term must be a string")
      
  if not min_length <= len(term) <= max_length:
      raise ValidationError(
          f"Term length must be between {min_length} and {max_length} characters"
      )
      
  if not re.match(VALID_TERM_PATTERN, term):
      raise ValidationError("Term contains invalid characters")
      
  return True

def validate_batch_size(size: int) -> bool:
  """
  Validate batch size is within allowed limits
  
  Args:
      size: Batch size to validate
      
  Returns:
      bool: True if size is valid
      
  Raises:
      ValidationError: If size is invalid
  """
  if not isinstance(size, int):
      raise ValidationError("Batch size must be an integer")
      
  if not MIN_BATCH_SIZE <= size <= MAX_BATCH_SIZE:
      raise ValidationError(
          f"Batch size must be between {MIN_BATCH_SIZE} and {MAX_BATCH_SIZE}"
      )
      
  return True

def validate_confidence_threshold(threshold: float) -> bool:
  """
  Validate confidence threshold is within allowed range
  
  Args:
      threshold: Confidence threshold to validate
      
  Returns:
      bool: True if threshold is valid
      
  Raises:
      ValidationError: If threshold is invalid
  """
  if not isinstance(threshold, (int, float)):
      raise ValidationError("Confidence threshold must be a number")
      
  if not MIN_CONFIDENCE_THRESHOLD <= threshold <= MAX_CONFIDENCE_THRESHOLD:
      raise ValidationError(
          f"Confidence threshold must be between {MIN_CONFIDENCE_THRESHOLD} and {MAX_CONFIDENCE_THRESHOLD}"
      )
      
  return True

def validate_campaign_id(campaign_id: str) -> bool:
  """
  Validate campaign ID format
  
  Args:
      campaign_id: Campaign ID to validate
      
  Returns:
      bool: True if ID is valid
      
  Raises:
      ValidationError: If ID is invalid
  """
  if not isinstance(campaign_id, str):
      raise ValidationError("Campaign ID must be a string")
      
  if not re.match(VALID_ID_PATTERN, campaign_id):
      raise ValidationError("Invalid campaign ID format")
      
  return True

def validate_ad_group_id(ad_group_id: str) -> bool:
  """
  Validate ad group ID format
  
  Args:
      ad_group_id: Ad group ID to validate
      
  Returns:
      bool: True if ID is valid
      
  Raises:
      ValidationError: If ID is invalid
  """
  if not isinstance(ad_group_id, str):
      raise ValidationError("Ad group ID must be a string")
      
  if not re.match(VALID_ID_PATTERN, ad_group_id):
      raise ValidationError("Invalid ad group ID format")
      
  return True

def validate_config_file(config_path: Path) -> bool:
  """
  Validate configuration file format and required fields
  
  Args:
      config_path: Path to config file
      
  Returns:
      bool: True if config is valid
      
  Raises:
      ValidationError: If config is invalid
  """
  if not config_path.exists():
      raise ValidationError(f"Config file not found: {config_path}")
      
  try:
      with open(config_path) as f:
          config = json.load(f)
          
      required_sections = {'processing', 'cache', 'analysis', 'monitoring'}
      if not all(section in config for section in required_sections):
          raise ValidationError(
              f"Config must contain sections: {required_sections}"
          )
          
      return True
      
  except json.JSONDecodeError:
      raise ValidationError("Invalid JSON format in config file")
  except Exception as e:
      raise ValidationError(f"Config validation failed: {str(e)}")

def validate_metrics_data(metrics: Dict[str, Any]) -> bool:
  """
  Validate metrics data structure
  
  Args:
      metrics: Metrics dictionary to validate
      
  Returns:
      bool: True if metrics are valid
      
  Raises:
      ValidationError: If metrics are invalid
  """
  required_fields = {
      'timestamp',
      'component_scores',
      'relevance_score',
      'confidence_score'
  }
  
  if not all(field in metrics for field in required_fields):
      raise ValidationError(
          f"Metrics must contain fields: {required_fields}"
      )
      
  try:
      datetime.fromisoformat(metrics['timestamp'])
  except ValueError:
      raise ValidationError("Invalid timestamp format")
      
  for score in ['relevance_score', 'confidence_score']:
      if not 0 <= metrics[score] <= 1:
          raise ValidationError(f"{score} must be between 0 and 1")
          
  return True

def validate_batch_results(results: List[Dict[str, Any]]) -> bool:
  """
  Validate batch processing results
  
  Args:
      results: List of result dictionaries to validate
      
  Returns:
      bool: True if results are valid
      
  Raises:
      ValidationError: If results are invalid
  """
  if not isinstance(results, list):
      raise ValidationError("Results must be a list")
      
  required_fields = {
      'search_term',
      'campaign_id',
      'ad_group_id',
      'metrics',
      'status'
  }
  
  for result in results:
      if not all(field in result for field in required_fields):
          raise ValidationError(
              f"Each result must contain fields: {required_fields}"
          )
          
      validate_term(result['search_term'])
      validate_campaign_id(result['campaign_id'])
      validate_ad_group_id(result['ad_group_id'])
      validate_metrics_data(result['metrics'])
      
  return True

def validate_worker_config(config: Dict[str, Any]) -> bool:
  """
  Validate worker configuration
  
  Args:
      config: Worker config dictionary to validate
      
  Returns:
      bool: True if config is valid
      
  Raises:
      ValidationError: If config is invalid
  """
  required_fields = {
      'worker_id',
      'max_tasks',
      'timeout',
      'retry_limit'
  }
  
  if not all(field in config for field in required_fields):
      raise ValidationError(
          f"Worker config must contain fields: {required_fields}"
      )
      
  if not isinstance(config['max_tasks'], int) or config['max_tasks'] <= 0:
      raise ValidationError("max_tasks must be a positive integer")
      
  if not isinstance(config['timeout'], (int, float)) or config['timeout'] <= 0:
      raise ValidationError("timeout must be a positive number")
      
  if not isinstance(config['retry_limit'], int) or config['retry_limit'] < 0:
      raise ValidationError("retry_limit must be a non-negative integer")
      
  return True