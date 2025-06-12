#!/usr/bin/env python3
"""
LLM DriftGuard - Semantic Analyzer Command
Compares semantic similarity between text fields
"""

import sys
import json
import numpy as np
from typing import List, Dict, Any, Optional
import logging
import hashlib
import re
from collections import Counter

# Splunk SDK imports
sys.path.insert(0, '/opt/splunk/lib/python3.9/site-packages')
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

class SemanticAnalyzer:
    """Semantic analysis utilities for text comparison."""
    
    def __init__(self):
        self.dim = 384
        
    def encode_text(self, text: str) -> np.ndarray:
        """Generate semantic embedding for text."""
        # Preprocess text
        text = self._preprocess_text(text)
        
        # Simple embedding based on character n-grams and word patterns
        features = []
        
        # Character-level features
        char_features = self._get_character_features(text)
        features.extend(char_features)
        
        # Word-level features  
        word_features = self._get_word_features(text)
        features.extend(word_features)
        
        # Semantic features
        semantic_features = self._get_semantic_features(text)
        features.extend(semantic_features)
        
        # Convert to numpy array and normalize
        vec = np.array(features[:self.dim], dtype=np.float32)
        if len(vec) < self.dim:
            vec = np.pad(vec, (0, self.dim - len(vec)), 'constant')
            
        # Normalize
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
            
        return vec
    
    def _preprocess_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Convert to lowercase
        text = text.lower()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\;\:]', '', text)
        
        return text.strip()
    
    def _get_character_features(self, text: str) -> List[float]:
        """Extract character-level features."""
        features = []
        
        # Character frequency distribution
        char_counts = Counter(text)
        total_chars = len(text)
        
        # Top 50 most common characters
        for i in range(50):
            char = chr(ord('a') + i % 26)  # a-z cycling
            freq = char_counts.get(char, 0) / max(total_chars, 1)
            features.append(freq)
        
        # Text statistics
        features.append(len(text) / 1000.0)  # Normalized length
        features.append(len(text.split()) / max(len(text), 1))  # Word density
        features.append(sum(1 for c in text if c.isupper()) / max(len(text), 1))  # Uppercase ratio
        
        return features
    
    def _get_word_features(self, text: str) -> List[float]:
        """Extract word-level features."""
        features = []
        words = text.split()
        
        # Word length statistics
        if words:
            word_lengths = [len(word) for word in words]
            features.append(np.mean(word_lengths) / 10.0)  # Average word length
            features.append(np.std(word_lengths) / 10.0)   # Word length variance
            features.append(len(set(words)) / len(words))  # Vocabulary diversity
        else:
            features.extend([0.0, 0.0, 0.0])
        
        # Common word patterns
        common_words = ['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of']
        for word in common_words:
            count = sum(1 for w in words if w == word)
            features.append(count / max(len(words), 1))
        
        return features
    
    def _get_semantic_features(self, text: str) -> List[float]:
        """Extract semantic-level features."""
        features = []
        
        # Sentence structure
        sentences = text.split('.')
        features.append(len(sentences) / max(len(text), 1))  # Sentence density
        
        # Question/answer patterns
        features.append(text.count('?') / max(len(text), 1))
        features.append(text.count('!') / max(len(text), 1))
        
        # Sentiment indicators (simple)
        positive_words = ['good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic']
        negative_words = ['bad', 'terrible', 'awful', 'horrible', 'disappointing', 'poor']
        
        pos_count = sum(1 for word in positive_words if word in text)
        neg_count = sum(1 for word in negative_words if word in text)
        
        features.append(pos_count / max(len(text.split()), 1))
        features.append(neg_count / max(len(text.split()), 1))
        
        # Topic indicators (simple)
        tech_words = ['algorithm', 'data', 'model', 'system', 'code', 'software']
        business_words = ['revenue', 'profit', 'customer', 'market', 'strategy', 'business']
        
        tech_count = sum(1 for word in tech_words if word in text)
        business_count = sum(1 for word in business_words if word in text)
        
        features.append(tech_count / max(len(text.split()), 1))
        features.append(business_count / max(len(text.split()), 1))
        
        return features
    
    def calculate_similarity(self, emb1: np.ndarray, emb2: np.ndarray, method: str = 'cosine') -> float:
        """Calculate similarity between embeddings."""
        if method == 'cosine':
            return float(np.dot(emb1, emb2))
        elif method == 'euclidean':
            return float(1.0 / (1.0 + np.linalg.norm(emb1 - emb2)))
        elif method == 'manhattan':
            return float(1.0 / (1.0 + np.sum(np.abs(emb1 - emb2))))
        else:
            return float(np.dot(emb1, emb2))  # Default to cosine
    
    def analyze_semantic_shift(self, text1: str, text2: str) -> Dict[str, Any]:
        """Analyze semantic shift between two texts."""
        emb1 = self.encode_text(text1)
        emb2 = self.encode_text(text2)
        
        similarity = self.calculate_similarity(emb1, emb2)
        
        # Additional analysis
        word_overlap = self._calculate_word_overlap(text1, text2)
        length_ratio = len(text2) / max(len(text1), 1)
        
        return {
            'similarity_score': similarity,
            'semantic_shift': 1.0 - similarity,
            'word_overlap': word_overlap,
            'length_ratio': length_ratio,
            'shift_magnitude': abs(1.0 - similarity),
            'shift_direction': 'expansion' if length_ratio > 1.2 else 'contraction' if length_ratio < 0.8 else 'stable'
        }
    
    def _calculate_word_overlap(self, text1: str, text2: str) -> float:
        """Calculate word overlap between two texts."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 and not words2:
            return 1.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0

@Configuration()
class SemanticCompareCommand(StreamingCommand):
    """
    Compare semantic similarity between text fields.
    
    Usage:
    | semanticcompare field1=prompt field2=response method=cosine
    """
    
    field1 = Option(
        doc='First text field for comparison',
        require=True,
        validate=validators.Fieldname()
    )
    
    field2 = Option(
        doc='Second text field for comparison',
        require=True,
        validate=validators.Fieldname()
    )
    
    method = Option(
        doc='Similarity calculation method (cosine, euclidean, manhattan)',
        require=False,
        default='cosine'
    )
    
    include_analysis = Option(
        doc='Include detailed semantic analysis',
        require=False,
        default=True,
        validate=validators.Boolean()
    )
    
    def __init__(self):
        super(SemanticCompareCommand, self).__init__()
        self.analyzer = SemanticAnalyzer()
        self.logger = logging.getLogger(__name__)
    
    def stream(self, records):
        """Process each record and add semantic comparison fields."""
        
        for record in records:
            try:
                # Get field values
                text1 = record.get(self.field1, '')
                text2 = record.get(self.field2, '')
                
                if not text1 or not text2:
                    record['similarity_score'] = 0.0
                    record['semantic_comparison_error'] = 'Empty text fields'
                    yield record
                    continue
                
                # Generate embeddings
                emb1 = self.analyzer.encode_text(text1)
                emb2 = self.analyzer.encode_text(text2)
                
                # Calculate similarity
                similarity = self.analyzer.calculate_similarity(emb1, emb2, self.method)
                
                # Add basic similarity fields
                record['similarity_score'] = round(similarity, 4)
                record['similarity_method'] = self.method
                record['semantic_distance'] = round(1.0 - similarity, 4)
                
                # Add detailed analysis if requested
                if self.include_analysis:
                    analysis = self.analyzer.analyze_semantic_shift(text1, text2)
                    
                    record['semantic_shift'] = round(analysis['semantic_shift'], 4)
                    record['word_overlap'] = round(analysis['word_overlap'], 4)
                    record['length_ratio'] = round(analysis['length_ratio'], 4)
                    record['shift_magnitude'] = round(analysis['shift_magnitude'], 4)
                    record['shift_direction'] = analysis['shift_direction']
                
                # Categorize similarity
                record['similarity_category'] = self._categorize_similarity(similarity)
                
            except Exception as e:
                self.logger.error(f"Error processing semantic comparison: {str(e)}")
                record['similarity_score'] = 0.0
                record['semantic_comparison_error'] = str(e)
            
            yield record
    
    def _categorize_similarity(self, similarity: float) -> str:
        """Categorize similarity score."""
        if similarity >= 0.9:
            return "very_high"
        elif similarity >= 0.7:
            return "high"
        elif similarity >= 0.5:
            return "medium"
        elif similarity >= 0.3:
            return "low"
        else:
            return "very_low"

if __name__ == '__main__':
    dispatch(SemanticCompareCommand, sys.argv, sys.stdin, sys.stdout, __name__)
