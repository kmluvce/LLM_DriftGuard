#!/usr/bin/env python3
"""
LLM DriftGuard - LLM Metrics Collector Command
Calculates comprehensive performance metrics for LLM interactions
"""

import sys
import json
import numpy as np
from typing import List, Dict, Any, Optional
import logging
import re
from datetime import datetime
import statistics

# Splunk SDK imports
sys.path.insert(0, '/opt/splunk/lib/python3.9/site-packages')
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

class LLMMetricsCalculator:
    """Calculator for LLM performance and quality metrics."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def calculate_response_quality(self, response: str, prompt: str = None) -> Dict[str, float]:
        """Calculate quality metrics for LLM response."""
        metrics = {}
        
        # Basic text metrics
        metrics['response_length'] = len(response)
        metrics['word_count'] = len(response.split())
        metrics['sentence_count'] = len([s for s in response.split('.') if s.strip()])
        metrics['avg_word_length'] = np.mean([len(word) for word in response.split()]) if response.split() else 0
        
        # Readability metrics (simplified)
        metrics['readability_score'] = self._calculate_readability(response)
        
        # Coherence indicators
        metrics['coherence_score'] = self._calculate_coherence(response)
        
        # Completeness indicators
        metrics['completeness_score'] = self._calculate_completeness(response, prompt)
        
        # Language quality
        metrics['language_quality'] = self._calculate_language_quality(response)
        
        # Information density
        metrics['information_density'] = self._calculate_information_density(response)
        
        return metrics
    
    def calculate_performance_metrics(self, response_time: float, token_count: int, 
                                    confidence_score: float = None) -> Dict[str, float]:
        """Calculate performance-related metrics."""
        metrics = {}
        
        # Time metrics
        metrics['response_time'] = response_time
        metrics['tokens_per_second'] = token_count / max(response_time, 0.001)
        
        # Efficiency metrics
        metrics['time_per_token'] = response_time / max(token_count, 1)
        metrics['token_count'] = token_count
        
        # Performance categories
        metrics['performance_category'] = self._categorize_performance(response_time, token_count)
        
        # Confidence metrics
        if confidence_score is not None:
            metrics['confidence_score'] = confidence_score
            metrics['confidence_category'] = self._categorize_confidence(confidence_score)
        
        return metrics
    
    def calculate_trend_metrics(self, current_metrics: Dict[str, float], 
                              historical_metrics: List[Dict[str, float]]) -> Dict[str, float]:
        """Calculate trend and comparison metrics."""
        trends = {}
        
        if not historical_metrics:
            return trends
        
        # Calculate trends for key metrics
        key_metrics = ['response_time', 'token_count', 'confidence_score', 'coherence_score']
        
        for metric in key_metrics:
            if metric in current_metrics:
                historical_values = [m.get(metric, 0) for m in historical_metrics if metric in m]
                
                if historical_values:
                    avg_historical = np.mean(historical_values)
                    current_value = current_metrics[metric]
                    
                    # Percentage change
                    pct_change = ((current_value - avg_historical) / max(avg_historical, 0.001)) * 100
                    trends[f'{metric}_trend_pct'] = pct_change
                    
                    # Trend direction
                    trends[f'{metric}_trend_direction'] = 'improving' if pct_change > 5 else 'declining' if pct_change < -5 else 'stable'
                    
                    # Volatility (standard deviation)
                    if len(historical_values) > 1:
                        trends[f'{metric}_volatility'] = np.std(historical_values)
        
        return trends
    
    def _calculate_readability(self, text: str) -> float:
        """Calculate simplified readability score."""
        if not text:
            return 0.0
        
        sentences = [s for s in text.split('.') if s.strip()]
        words = text.split()
        
        if not sentences or not words:
            return 0.0
        
        # Simplified Flesch-like score
        avg_sentence_length = len(words) / len(sentences)
        avg_word_length = np.mean([len(word) for word in words])
        
        # Normalize to 0-1 scale (lower is more readable)
        readability = 1.0 - min(1.0, (avg_sentence_length / 20 + avg_word_length / 6) / 2)
        return max(0.0, readability)
    
    def _calculate_coherence(self, text: str) -> float:
        """Calculate coherence score based on text structure."""
        if not text:
            return 0.0
        
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        
        if len(sentences) < 2:
            return 1.0
        
        # Check for transition words and coherence indicators
        transition_words = ['however', 'therefore', 'furthermore', 'additionally', 'moreover', 
                          'consequently', 'meanwhile', 'similarly', 'in contrast', 'for example']
        
        transition_count = sum(1 for word in transition_words if word in text.lower())
        
        # Check for pronoun consistency and reference
        pronouns = ['it', 'this', 'that', 'these', 'those', 'they', 'them']
        pronoun_count = sum(1 for word in pronouns if word in text.lower().split())
        
        # Simple coherence score
        coherence = min(1.0, (transition_count * 0.1 + pronoun_count * 0.05) / len(sentences))
        return coherence
    
    def _calculate_completeness(self, response: str, prompt: str = None) -> float:
        """Calculate response completeness."""
        if not response:
            return 0.0
        
        # Basic completeness indicators
        has_conclusion = any(word in response.lower() for word in ['conclusion', 'summary', 'finally', 'therefore'])
        has_examples = any(word in response.lower() for word in ['example', 'instance', 'such as', 'for example'])
        has_structure = len([s for s in response.split('.') if s.strip()]) >= 2
        
        completeness = 0.0
        if has_conclusion:
            completeness += 0.4
        if has_examples:
            completeness += 0.3
        if has_structure:
            completeness += 0.3
        
        # If prompt is available, check relevance
        if prompt:
            # Simple keyword overlap
            prompt_words = set(prompt.lower().split())
            response_words = set(response.lower().split())
            overlap = len(prompt_words.intersection(response_words)) / max(len(prompt_words), 1)
            completeness = (completeness + overlap) / 2
        
        return min(1.0, completeness)
    
    def _calculate_language_quality(self, text: str) -> float:
        """Calculate language quality score."""
        if not text:
            return 0.0
        
        # Check for common language issues
        repeated_words = self._check_repetition(text)
        grammar_score = self._simple_grammar_check(text)
        vocabulary_diversity = self._calculate_vocabulary_diversity(text)
        
        # Combine scores
        quality = (grammar_score * 0.5 + vocabulary_diversity * 0.3 + (1 - repeated_words) * 0.2)
        return max(0.0, min(1.0, quality))
    
    def _calculate_information_density(self, text: str) -> float:
        """Calculate information density of the text."""
        if not text:
            return 0.0
        
        words = text.split()
        
        # Count content words (non-stop words)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were'}
        content_words = [word for word in words if word.lower() not in stop_words]
        
        # Information density = content words / total words
        return len(content_words) / max(len(words), 1)
    
    def _check_repetition(self, text: str) -> float:
        """Check for excessive word repetition."""
        words = text.lower().split()
        if len(words) < 2:
            return 0.0
        
        word_counts = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        # Calculate repetition ratio
        max_count = max(word_counts.values())
        repetition_ratio = max_count / len(words)
        
        # Return high repetition score for problematic repetition
        return max(0.0, repetition_ratio - 0.1)  # Allow 10% repetition as normal
    
    def _simple_grammar_check(self, text: str) -> float:
        """Simple grammar quality check."""
        # Check for basic grammar patterns
        has_capital_start = text and text[0].isupper()
        has_proper_punctuation = text.endswith('.') or text.endswith('!') or text.endswith('?')
        
        # Check sentence structure
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        proper_sentences = sum(1 for s in sentences if s and s[0].isupper())
        sentence_quality = proper_sentences / max(len(sentences), 1)
        
        # Simple score
        grammar_score = 0.0
        if has_capital_start:
            grammar_score += 0.3
        if has_proper_punctuation:
            grammar_score += 0.3
        grammar_score += sentence_quality * 0.4
        
        return min(1.0, grammar_score)
    
    def _calculate_vocabulary_diversity(self, text: str) -> float:
        """Calculate vocabulary diversity (Type-Token Ratio)."""
        words = text.lower().split()
        if not words:
            return 0.0
        
        unique_words = len(set(words))
        total_words = len(words)
        
        # Type-Token Ratio
        return unique_words / total_words
    
    def _categorize_performance(self, response_time: float, token_count: int) -> str:
        """Categorize overall performance."""
        tokens_per_second = token_count / max(response_time, 0.001)
        
        if response_time < 1.0 and tokens_per_second > 100:
            return "excellent"
        elif response_time < 3.0 and tokens_per_second > 50:
            return "good"
        elif response_time < 10.0 and tokens_per_second > 20:
            return "acceptable"
        else:
            return "poor"
    
    def _categorize_confidence(self, confidence: float) -> str:
        """Categorize confidence score."""
        if confidence >= 0.9:
            return "very_high"
        elif confidence >= 0.7:
            return "high"
        elif confidence >= 0.5:
            return "medium"
        elif confidence >= 0.3:
            return "low"
        else:
            return "very_low"

@Configuration()
class LLMMetricsCommand(StreamingCommand):
    """
    Calculate comprehensive LLM performance and quality metrics.
    
    Usage:
    | llmmetrics response_field=response time_field=response_time token_field=token_count
    """
    
    response_field = Option(
        doc='Field containing model responses',
        require=True,
        validate=validators.Fieldname()
    )
    
    prompt_field = Option(
        doc='Field containing prompts (optional)',
        require=False,
        validate=validators.Fieldname()
    )
    
    time_field = Option(
        doc='Field containing response times',
        require=False,
        validate=validators.Fieldname()
    )
    
    token_field = Option(
        doc='Field containing token counts',
        require=False,
        validate=validators.Fieldname()
    )
    
    confidence_field = Option(
        doc='Field containing confidence scores',
        require=False,
        validate=validators.Fieldname()
    )
    
    include_trends = Option(
        doc='Include trend analysis (requires historical data)',
        require=False,
        default=False,
        validate=validators.Boolean()
    )
    
    def __init__(self):
        super(LLMMetricsCommand, self).__init__()
        self.calculator = LLMMetricsCalculator()
        self.historical_metrics = []
        self.logger = logging.getLogger(__name__)
    
    def stream(self, records):
        """Process each record and add LLM metrics."""
        
        for record in records:
            try:
                # Get field values
                response = record.get(self.response_field, '')
                prompt = record.get(self.prompt_field, '') if self.prompt_field else None
                response_time = float(record.get(self.time_field, 0)) if self.time_field else None
                token_count = int(record.get(self.token_field, 0)) if self.token_field else None
                confidence = float(record.get(self.confidence_field, 0)) if self.confidence_field else None
                
                if not response:
                    record['llm_metrics_error'] = 'Empty response field'
                    yield record
                    continue
                
                # Calculate quality metrics
                quality_metrics = self.calculator.calculate_response_quality(response, prompt)
                
                # Add quality metrics to record
                for key, value in quality_metrics.items():
                    record[f'quality_{key}'] = round(value, 4)
                
                # Calculate performance metrics if available
                if response_time is not None and token_count is not None:
                    perf_metrics = self.calculator.calculate_performance_metrics(
                        response_time, token_count, confidence
                    )
                    
                    for key, value in perf_metrics.items():
                        if isinstance(value, (int, float)):
                            record[f'perf_{key}'] = round(value, 4)
                        else:
                            record[f'perf_{key}'] = value
                
                # Calculate trend metrics if enabled
                if self.include_trends and self.historical_metrics:
                    current_metrics = {**quality_metrics}
                    if response_time is not None:
                        current_metrics['response_time'] = response_time
                    if token_count is not None:
                        current_metrics['token_count'] = token_count
                    if confidence is not None:
                        current_metrics['confidence_score'] = confidence
                    
                    trend_metrics = self.calculator.calculate_trend_metrics(
                        current_metrics, self.historical_metrics
                    )
                    
                    for key, value in trend_metrics.items():
                        if isinstance(value, (int, float)):
                            record[f'trend_{key}'] = round(value, 4)
                        else:
                            record[f'trend_{key}'] = value
                    
                    # Add current metrics to historical data
                    self.historical_metrics.append(current_metrics)
                    if len(self.historical_metrics) > 100:  # Keep last 100 records
                        self.historical_metrics = self.historical_metrics[-100:]
                
                # Calculate overall quality score
                quality_score = np.mean([
                    quality_metrics.get('readability_score', 0),
                    quality_metrics.get('coherence_score', 0),
                    quality_metrics.get('completeness_score', 0),
                    quality_metrics.get('language_quality', 0)
                ])
                record['overall_quality_score'] = round(quality_score, 4)
                
                # Add timestamp
                record['metrics_calculated_at'] = datetime.now().isoformat()
                
            except Exception as e:
                self.logger.error(f"Error calculating LLM metrics: {str(e)}")
                record['llm_metrics_error'] = str(e)
            
            yield record

if __name__ == '__main__':
    dispatch(LLMMetricsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
