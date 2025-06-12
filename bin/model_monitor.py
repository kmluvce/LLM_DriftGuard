#!/usr/bin/env python3
"""
LLM DriftGuard - Model Monitor and Anomaly Detection Command
Detects statistical anomalies in LLM behavior patterns
"""

import sys
import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime
import statistics
from collections import defaultdict, deque

# Splunk SDK imports
sys.path.insert(0, '/opt/splunk/lib/python3.9/site-packages')
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

class AnomalyDetector:
    """Statistical anomaly detection for LLM metrics."""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.metric_windows = defaultdict(lambda: deque(maxlen=window_size))
        self.logger = logging.getLogger(__name__)
    
    def detect_zscore_anomaly(self, value: float, field_name: str, threshold: float = 2.0) -> Tuple[bool, float, Dict[str, Any]]:
        """Detect anomalies using Z-score method."""
        window = self.metric_windows[field_name]
        window.append(value)
        
        if len(window) < 10:  # Need minimum samples
            return False, 0.0, {}
        
        values = list(window)
        mean_val = statistics.mean(values)
        stdev_val = statistics.stdev(values) if len(values) > 1 else 0.0
        
        if stdev_val == 0:
            return False, 0.0, {}
        
        zscore = (value - mean_val) / stdev_val
        is_anomaly = abs(zscore) > threshold
        
        analysis = {
            'mean': mean_val,
            'stdev': stdev_val,
            'zscore': zscore,
            'threshold': threshold,
            'sample_size': len(values)
        }
        
        return is_anomaly, abs(zscore), analysis
    
    def detect_iqr_anomaly(self, value: float, field_name: str, multiplier: float = 1.5) -> Tuple[bool, float, Dict[str, Any]]:
        """Detect anomalies using Interquartile Range method."""
        window = self.metric_windows[field_name]
        window.append(value)
        
        if len(window) < 10:
            return False, 0.0, {}
        
        values = sorted(list(window))
        n = len(values)
        
        q1 = values[n // 4]
        q3 = values[3 * n // 4]
        iqr = q3 - q1
        
        lower_bound = q1 - multiplier * iqr
        upper_bound = q3 + multiplier * iqr
        
        is_anomaly = value < lower_bound or value > upper_bound
        anomaly_score = 0.0
        
        if value < lower_bound:
            anomaly_score = (lower_bound - value) / max(iqr, 0.001)
        elif value > upper_bound:
            anomaly_score = (value - upper_bound) / max(iqr, 0.001)
        
        analysis = {
            'q1': q1,
            'q3': q3,
            'iqr': iqr,
            'lower_bound': lower_bound,
            'upper_bound': upper_bound,
            'multiplier': multiplier,
            'sample_size': len(values)
        }
        
        return is_anomaly, anomaly_score, analysis
    
    def detect_isolation_forest_anomaly(self, value: float, field_name: str) -> Tuple[bool, float, Dict[str, Any]]:
        """Simplified isolation forest-like anomaly detection."""
        window = self.metric_windows[field_name]
        window.append(value)
        
        if len(window) < 20:
            return False, 0.0, {}
        
        values = list(window)
        
        # Simple isolation score based on how far the value is from neighbors
        distances = [abs(value - v) for v in values if v != value]
        if not distances:
            return False, 0.0, {}
        
        avg_distance = statistics.mean(distances)
        std_distance = statistics.stdev(distances) if len(distances) > 1 else 0.0
        
        # Isolation score - higher means more isolated
        isolation_score = avg_distance / max(std_distance, 0.001)
        is_anomaly = isolation_score > 2.0
        
        analysis = {
            'avg_distance': avg_distance,
            'std_distance': std_distance,
            'isolation_score': isolation_score,
            'sample_size': len(values)
        }
        
        return is_anomaly, isolation_score, analysis
    
    def detect_trend_anomaly(self, value: float, field_name: str, window_size: int = 10) -> Tuple[bool, float, Dict[str, Any]]:
        """Detect anomalies based on trend analysis."""
        window = self.metric_windows[field_name]
        window.append(value)
        
        if len(window) < window_size:
            return False, 0.0, {}
        
        values = list(window)[-window_size:]
        
        # Calculate trend using linear regression
        x = list(range(len(values)))
        n = len(values)
        
        if n < 2:
            return False, 0.0, {}
        
        # Simple linear regression
        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(x[i] * values[i] for i in range(n))
        sum_x2 = sum(xi * xi for xi in x)
        
        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return False, 0.0, {}
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        intercept = (sum_y - slope * sum_x) / n
        
        # Predict current value based on trend
        predicted = slope * (n - 1) + intercept
        prediction_error = abs(value - predicted)
        
        # Calculate residuals for all points
        residuals = [values[i] - (slope * x[i] + intercept) for i in range(n)]
        residual_std = statistics.stdev(residuals) if len(residuals) > 1 else 0.0
        
        # Anomaly if prediction error is significantly larger than typical residuals
        is_anomaly = prediction_error > 2 * residual_std if residual_std > 0 else False
        anomaly_score = prediction_error / max(residual_std, 0.001)
        
        analysis = {
            'slope': slope,
            'intercept': intercept,
            'predicted_value': predicted,
            'prediction_error': prediction_error,
            'residual_std': residual_std,
            'anomaly_score': anomaly_score
        }
        
        return is_anomaly, anomaly_score, analysis

@Configuration()
class AnomalyDetectCommand(StreamingCommand):
    """
    Detect anomalies in LLM behavior patterns using statistical methods.
    
    Usage:
    | anomalydetect fields="response_time,token_count" method=zscore threshold=2.0
    """
    
    fields = Option(
        doc='Comma-separated list of fields to analyze for anomalies',
        require=True
    )
    
    method = Option(
        doc='Detection method: zscore, iqr, isolation, trend, all',
        require=False,
        default='zscore'
    )
    
    threshold = Option(
        doc='Threshold for anomaly detection (interpretation depends on method)',
        require=False,
        default=2.0,
        validate=validators.Float(0.1, 10.0)
    )
    
    window = Option(
        doc='Window size for rolling analysis',
        require=False,
        default=100,
        validate=validators.Integer(10, 1000)
    )
    
    include_analysis = Option(
        doc='Include detailed analysis information',
        require=False,
        default=True,
        validate=validators.Boolean()
    )
    
    def __init__(self):
        super(AnomalyDetectCommand, self).__init__()
        self.detector = AnomalyDetector(window_size=100)
        self.logger = logging.getLogger(__name__)
        self.field_list = []
    
    def stream(self, records):
        """Process each record and detect anomalies."""
        
        # Parse fields list
        self.field_list = [f.strip() for f in self.fields.split(',')]
        
        # Update detector window size
        self.detector.window_size = self.window
        
        for record in records:
            try:
                anomalies_detected = []
                anomaly_scores = {}
                anomaly_details = {}
                
                for field_name in self.field_list:
                    field_value = record.get(field_name)
                    
                    if field_value is None:
                        continue
                    
                    try:
                        numeric_value = float(field_value)
                    except (ValueError, TypeError):
                        continue
                    
                    # Apply selected detection method(s)
                    if self.method in ['zscore', 'all']:
                        is_anomaly, score, analysis = self.detector.detect_zscore_anomaly(
                            numeric_value, f"{field_name}_zscore", self.threshold
                        )
                        if is_anomaly:
                            anomalies_detected.append(f"{field_name}_zscore")
                            anomaly_scores[f"{field_name}_zscore"] = score
                            if self.include_analysis:
                                anomaly_details[f"{field_name}_zscore"] = analysis
                    
                    if self.method in ['iqr', 'all']:
                        is_anomaly, score, analysis = self.detector.detect_iqr_anomaly(
                            numeric_value, f"{field_name}_iqr", self.threshold
                        )
                        if is_anomaly:
                            anomalies_detected.append(f"{field_name}_iqr")
                            anomaly_scores[f"{field_name}_iqr"] = score
                            if self.include_analysis:
                                anomaly_details[f"{field_name}_iqr"] = analysis
                    
                    if self.method in ['isolation', 'all']:
                        is_anomaly, score, analysis = self.detector.detect_isolation_forest_anomaly(
                            numeric_value, f"{field_name}_isolation"
                        )
                        if is_anomaly:
                            anomalies_detected.append(f"{field_name}_isolation")
                            anomaly_scores[f"{field_name}_isolation"] = score
                            if self.include_analysis:
                                anomaly_details[f"{field_name}_isolation"] = analysis
                    
                    if self.method in ['trend', 'all']:
                        is_anomaly, score, analysis = self.detector.detect_trend_anomaly(
                            numeric_value, f"{field_name}_trend"
                        )
                        if is_anomaly:
                            anomalies_detected.append(f"{field_name}_trend")
                            anomaly_scores[f"{field_name}_trend"] = score
                            if self.include_analysis:
                                anomaly_details[f"{field_name}_trend"] = analysis
                
                # Add anomaly detection results to record
                record['anomaly_detected'] = len(anomalies_detected) > 0
                record['anomaly_count'] = len(anomalies_detected)
                record['anomaly_types'] = ','.join(anomalies_detected) if anomalies_detected else ''
                
                # Add severity based on number and scores of anomalies
                if anomalies_detected:
                    max_score = max(anomaly_scores.values()) if anomaly_scores else 0
                    record['anomaly_severity'] = self._calculate_severity(len(anomalies_detected), max_score)
                    record['max_anomaly_score'] = round(max_score, 4)
                    
                    # Add individual scores
                    for anomaly_type, score in anomaly_scores.items():
                        record[f'anomaly_score_{anomaly_type}'] = round(score, 4)
                else:
                    record['anomaly_severity'] = 'none'
                    record['max_anomaly_score'] = 0.0
                
                # Add detailed analysis if requested
                if self.include_analysis and anomaly_details:
                    record['anomaly_analysis'] = json.dumps(anomaly_details)
                
                # Add detection metadata
                record['anomaly_detection_time'] = datetime.now().isoformat()
                record['anomaly_detection_method'] = self.method
                record['anomaly_threshold'] = self.threshold
                
            except Exception as e:
                self.logger.error(f"Error detecting anomalies: {str(e)}")
                record['anomaly_detection_error'] = str(e)
                record['anomaly_detected'] = False
            
            yield record
    
    def _calculate_severity(self, anomaly_count: int, max_score: float) -> str:
        """Calculate anomaly severity based on count and scores."""
        if anomaly_count == 0:
            return 'none'
        elif anomaly_count == 1 and max_score < 3.0:
            return 'low'
        elif anomaly_count <= 2 and max_score < 5.0:
            return 'medium'
        elif anomaly_count <= 3 and max_score < 8.0:
            return 'high'
        else:
            return 'critical'

if __name__ == '__main__':
    dispatch(AnomalyDetectCommand, sys.argv, sys.stdin, sys.stdout, __name__)
