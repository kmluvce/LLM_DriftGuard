#!/usr/bin/env python3
"""
LLM DriftGuard - Semantic Drift Detection Command
Detects semantic drift in LLM outputs using embedding similarity
"""

import sys
import json
import csv
import numpy as np
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import hashlib

# Splunk SDK imports
sys.path.insert(0, '/opt/splunk/lib/python3.9/site-packages')
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

# Simple embedding simulation (in production, use sentence-transformers or similar)
class SimpleEmbedder:
    """Simple text embedding for demonstration. In production, use proper embeddings."""
    
    def __init__(self, dim: int = 384):
        self.dim = dim
        
    def encode(self, text: str) -> np.ndarray:
        """Generate a simple hash-based embedding for text."""
        # This is a simplified approach for demo purposes
        # In production, use sentence-transformers, OpenAI embeddings, etc.
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()
        
        # Convert to normalized vector
        vec = np.frombuffer(hash_bytes[:self.dim//8], dtype=np.uint8)
        vec = vec.astype(np.float32) / 255.0
        
        # Pad or truncate to desired dimension
        if len(vec) < self.dim:
            vec = np.pad(vec, (0, self.dim - len(vec)), 'constant')
        else:
            vec = vec[:self.dim]
            
        # Normalize
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
            
        return vec
    
    def similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Calculate cosine similarity between embeddings."""
        return float(np.dot(emb1, emb2))

@Configuration()
class DriftDetectCommand(StreamingCommand):
    """
    Streaming command to detect semantic drift in text fields.
    
    Usage:
    | driftdetect field=response baseline_file="model_baselines.csv" threshold=0.8
    """
    
    field = Option(
        doc='Text field to analyze for drift',
        require=True,
        validate=validators.Fieldname()
    )
    
    baseline_file = Option(
        doc='CSV file containing baseline embeddings',
        require=False,
        default="model_baselines.csv"
    )
    
    threshold = Option(
        doc='Similarity threshold for drift detection (0-1)',
        require=False,
        default=0.8,
        validate=validators.Float(0.0, 1.0)
    )
    
    window_size = Option(
        doc='Number of recent samples to compare against',
        require=False,
        default=100,
        validate=validators.Integer(1, 10000)
    )
    
    def __init__(self):
        super(DriftDetectCommand, self).__init__()
        self.embedder = SimpleEmbedder()
        self.baseline_embeddings = []
        self.logger = logging.getLogger(__name__)
        
    def load_baseline(self, baseline_file: str) -> List[np.ndarray]:
        """Load baseline embeddings from CSV file."""
        baselines = []
        try:
            # In Splunk, lookup files are in $SPLUNK_HOME/etc/apps/appname/lookups/
            app_path = '/opt/splunk/etc/apps/llm_driftguard/lookups/'
            file_path = app_path + baseline_file
            
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'embedding' in row:
                        # Parse embedding from string representation
                        emb_str = row['embedding'].strip('[]')
                        emb_values = [float(x) for x in emb_str.split(',')]
                        baselines.append(np.array(emb_values))
                    elif 'text' in row:
                        # Generate embedding from text
                        embedding = self.embedder.encode(row['text'])
                        baselines.append(embedding)
                        
        except FileNotFoundError:
            self.logger.warning(f"Baseline file {baseline_file} not found. Using empty baseline.")
        except Exception as e:
            self.logger.error(f"Error loading baseline: {str(e)}")
            
        return baselines
    
    def calculate_drift_score(self, text: str, baselines: List[np.ndarray]) -> float:
        """Calculate drift score for given text against baselines."""
        if not baselines:
            return 0.0
            
        current_embedding = self.embedder.encode(text)
        
        # Calculate similarities with all baselines
        similarities = []
        for baseline in baselines:
            sim = self.embedder.similarity(current_embedding, baseline)
            similarities.append(sim)
        
        # Drift score is 1 - max_similarity (higher means more drift)
        max_similarity = max(similarities) if similarities else 0.0
        drift_score = 1.0 - max_similarity
        
        return drift_score
    
    def stream(self, records):
        """Process each record and add drift detection fields."""
        
        # Load baselines once
        if not self.baseline_embeddings:
            self.baseline_embeddings = self.load_baseline(self.baseline_file)
            
        recent_embeddings = []
        
        for record in records:
            try:
                # Get text field value
                text_value = record.get(self.field, '')
                
                if not text_value:
                    record['drift_score'] = 0.0
                    record['drift_detected'] = False
                    record['baseline_similarity'] = 0.0
                    yield record
                    continue
                
                # Calculate drift against baselines
                drift_score = self.calculate_drift_score(text_value, self.baseline_embeddings)
                
                # Calculate similarity with recent samples (for trending)
                recent_similarity = 1.0
                if recent_embeddings:
                    current_emb = self.embedder.encode(text_value)
                    recent_sims = [
                        self.embedder.similarity(current_emb, emb) 
                        for emb in recent_embeddings[-min(10, len(recent_embeddings)):]
                    ]
                    recent_similarity = np.mean(recent_sims) if recent_sims else 1.0
                    
                    # Add current embedding to recent samples
                    recent_embeddings.append(current_emb)
                    if len(recent_embeddings) > self.window_size:
                        recent_embeddings = recent_embeddings[-self.window_size:]
                else:
                    # First sample - add to recent embeddings
                    recent_embeddings.append(self.embedder.encode(text_value))
                
                # Add drift detection fields
                record['drift_score'] = round(drift_score, 4)
                record['drift_detected'] = drift_score > (1.0 - self.threshold)
                record['baseline_similarity'] = round(1.0 - drift_score, 4)
                record['recent_similarity'] = round(recent_similarity, 4)
                record['drift_severity'] = self._get_drift_severity(drift_score)
                
                # Add timestamp for drift event
                if record['drift_detected']:
                    record['drift_event_time'] = datetime.now().isoformat()
                
            except Exception as e:
                self.logger.error(f"Error processing record: {str(e)}")
                record['drift_score'] = 0.0
                record['drift_detected'] = False
                record['drift_error'] = str(e)
            
            yield record
    
    def _get_drift_severity(self, drift_score: float) -> str:
        """Categorize drift severity based on score."""
        if drift_score < 0.1:
            return "minimal"
        elif drift_score < 0.3:
            return "low"
        elif drift_score < 0.5:
            return "medium"
        elif drift_score < 0.7:
            return "high"
        else:
            return "critical"

if __name__ == '__main__':
    dispatch(DriftDetectCommand, sys.argv, sys.stdin, sys.stdout, __name__)
