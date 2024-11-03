from typing import List, Dict, Optional, Set
import re
import unicodedata
import logging
from dataclasses import dataclass
from datetime import datetime
import spacy
from sklearn.feature_extraction.text import CountVectorizer
from ..core.config import ProcessingConfig
from ..core.exceptions import ProcessingError, ValidationError
from ..utils.validation import validate_term
from ..utils.monitoring import monitor_task
from ..core.constants import (
  MIN_TERM_LENGTH,
  MAX_TERM_LENGTH,
  VALID_TERM_PATTERN
)

logger = logging.getLogger(__name__)

@dataclass
class ProcessedTerm:
  """Container for processed term data"""
  original: str
  processed: str
  tokens: List[str]
  ngrams: Dict[int, List[str]]
  metadata: Dict[str, any]
  timestamp: datetime = datetime.utcnow()

class TermProcessor:
  """Handles preprocessing and processing of search terms"""
  
  def __init__(self, config: ProcessingConfig):
      self.config = config
      self._initialize_components()
      
  def _initialize_components(self) -> None:
      """Initialize NLP and processing components"""
      try:
          # Initialize spaCy for NLP tasks
          self.nlp = spacy.load("en_core_web_sm")
          
          # Initialize n-gram vectorizer
          self.ngram_vectorizer = CountVectorizer(
              ngram_range=(2, 3),
              token_pattern=r'[a-zA-Z0-9]+',
          )
          
          # Common preprocessing patterns
          self.patterns = {
              'whitespace': re.compile(r'\s+'),
              'special_chars': re.compile(r'[^a-zA-Z0-9\s-]'),
              'numbers': re.compile(r'\d+'),
              'urls': re.compile(
                  r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
              )
          }
          
      except Exception as e:
          raise ProcessingError(f"Failed to initialize processor components: {str(e)}")

  @monitor_task
  async def process_term(self, term: str) -> ProcessedTerm:
      """Process a single search term"""
      try:
          # Validate input
          if not validate_term(term, MIN_TERM_LENGTH, MAX_TERM_LENGTH):
              raise ValidationError(f"Invalid search term: {term}")

          # Basic preprocessing
          processed = await self._preprocess_term(term)
          
          # Tokenization and NLP processing
          tokens = await self._tokenize_term(processed)
          
          # Generate n-grams
          ngrams = await self._generate_ngrams(processed)
          
          # Extract metadata
          metadata = await self._extract_metadata(term, processed, tokens)
          
          return ProcessedTerm(
              original=term,
              processed=processed,
              tokens=tokens,
              ngrams=ngrams,
              metadata=metadata
          )
          
      except Exception as e:
          logger.error(f"Error processing term '{term}': {str(e)}")
          raise ProcessingError(f"Term processing failed: {str(e)}")

  async def _preprocess_term(self, term: str) -> str:
      """Perform basic preprocessing on term"""
      try:
          # Convert to lowercase
          processed = term.lower()
          
          # Remove URLs
          processed = self.patterns['urls'].sub('', processed)
          
          # Normalize unicode characters
          processed = unicodedata.normalize('NFKD', processed)
          processed = processed.encode('ASCII', 'ignore').decode('ASCII')
          
          # Remove special characters
          processed = self.patterns['special_chars'].sub(' ', processed)
          
          # Normalize whitespace
          processed = self.patterns['whitespace'].sub(' ', processed)
          
          # Strip leading/trailing whitespace
          processed = processed.strip()
          
          return processed
          
      except Exception as e:
          raise ProcessingError(f"Preprocessing failed: {str(e)}")

  async def _tokenize_term(self, term: str) -> List[str]:
      """Tokenize and process term using spaCy"""
      doc = self.nlp(term)
      return [
          token.text for token in doc
          if not token.is_stop and not token.is_punct
      ]

  async def _generate_ngrams(self, term: str) -> Dict[int, List[str]]:
      """Generate n-grams from term"""
      ngrams = {}
      
      # Generate character n-grams
      for n in range(2, 4):
          ngrams[n] = [
              term[i:i+n]
              for i in range(len(term) - n + 1)
          ]
      
      return ngrams

  async def _extract_metadata(
      self,
      original: str,
      processed: str,
      tokens: List[str]
  ) -> Dict[str, any]:
      """Extract metadata about the term"""
      return {
          'length': len(original),
          'processed_length': len(processed),
          'token_count': len(tokens),
          'has_numbers': bool(self.patterns['numbers'].search(original)),
          'character_types': self._get_character_types(original),
          'language': self._detect_language(processed)
      }

  def _get_character_types(self, text: str) -> Dict[str, bool]:
      """Analyze character types in text"""
      return {
          'alphabetic': any(c.isalpha() for c in text),
          'numeric': any(c.isdigit() for c in text),
          'spaces': any(c.isspace() for c in text),
          'special': any(not c.isalnum() and not c.isspace() for c in text)
      }

  def _detect_language(self, text: str) -> str:
      """Simple language detection"""
      try:
          doc = self.nlp(text)
          return doc.lang_
      except:
          return 'unknown'

  @monitor_task
  async def process_batch(
      self,
      terms: List[str]
  ) -> Dict[str, ProcessedTerm]:
      """Process a batch of search terms"""
      results = {}
      
      for term in terms:
          try:
              processed = await self.process_term(term)
              results[term] = processed
          except Exception as e:
              logger.error(f"Failed to process term '{term}': {str(e)}")
              continue
              
      return results

  async def get_processing_stats(self) -> Dict[str, any]:
      """Get processor statistics"""
      return {
          'total_processed': 0,  # Implement counter
          'failed_terms': 0,     # Implement counter
          'average_processing_time': 0.0,  # Implement timing
          'cache_hits': 0,       # Implement caching
          'cache_misses': 0      # Implement caching
      }