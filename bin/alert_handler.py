#!/usr/bin/env python3
"""
LLM DriftGuard - Alert Handler and Baseline Comparison Command
Compares current metrics against established baselines
"""

import sys
import json
import csv
import numpy as np
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import os

# Splunk SDK imports
sys.path.insert(0, '/opt/splunk/lib/python3.9/site-packages')
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

class BaselineComparator:
    """Handles baseline comparison and alert generation."""
    
    def __init__(self):
        self.baselines = {}
        self.thresholds = {}
        self.logger = logging.getLogger(__name__)
        
    def load_baselines(self, baseline_file: str) -> Dict[str, Dict[str, float]]:
        """Load baseline metrics from CSV file."""
        baselines = {}
        try:
            app_path = '/opt/splunk/etc/apps/llm_driftguard/lookups/'
            file_path = os.path.join(app_path, baseline_file)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    model_id = row.get('model_id', 'default')
                    baselines[model_id] = {}
                    
                    # Load numeric baseline values
                    for key, value in row.items():
                        if key != 'model_id' and value:
                            try:
                                baselines[model_id][key] = float(value)
                            except ValueError:
                                baselines[model_id][key] = value
                                
        except FileNotFoundError:
            self.logger.warning(f"Baseline file {baseline_file} not found")
        except Exception as e:
            self.logger.error(f"Error loading baselines: {str(e)}")
            
        return baselines
    
    def load_thresholds(self, threshold_file: str) -> Dict[str, Dict[str, float]]:
        """Load alert thresholds from CSV file."""
        thresholds = {}
        try:
            app_path = '/opt/splunk/etc/apps/llm_driftguard/lookups/'
            file_path = os.path.join(app_path, threshold_file)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    metric_name = row.get('metric_name')
                    if metric_name:
                        thresholds[metric_name] = {
                            'threshold_type': row.get('threshold_type', 'upper'),
                            'warning_threshold': float(row.get('warning_threshold', 0)),
                            'critical_threshold': float(row.get('critical_threshold', 0)),
                            'unit': row.get('unit', ''),
                            'description': row.get('description', '')
                        }
                        
        except FileNotFoundError:
            self.logger.warning(f"Threshold file {threshold_file} not found")
        except Exception as e:
            self.logger.error(f"Error loading thresholds: {str(e)}")
            
        return thresholds
    
    def compare_with_baseline(self, current_value: float, baseline_value: float, 
                            metric_name: str, comparison_type: str = 'percentage') -> Dict[str, Any]:
        """Compare current value with baseline and calculate deviation."""
        
        if baseline_value == 0:
            if current_value == 0:
                return {
                    'deviation': 0.0,
                    'percentage_change': 0.0,
                    'status': 'normal',
                    'comparison_type': comparison_type
                }
            else:
                return {
                    'deviation': current_value,
                    'percentage_change': float('inf'),
                    'status': 'critical',
                    'comparison_type': comparison_type
                }
        
        # Calculate deviations
        absolute_deviation = current_value - baseline_value
        percentage_change = (absolute_deviation / baseline_value) * 100
        
        # Determine status based on thresholds
        status = self._determine_status(metric_name, current_value, baseline_value, percentage_change)
        
        # Additional metrics
        ratio = current_value / baseline_value
        z_score = self._calculate_z_score(current_value, baseline_value, metric_name)
        
        return {
            'current_value': current_value,
            'baseline_value': baseline_value,
            'absolute_deviation': absolute_deviation,
            'percentage_change': percentage_change,
            'ratio': ratio,
            'z_score': z_score,
            'status': status,
            'comparison_type': comparison_type,
            'metric_name': metric_name
        }
    
    def _determine_status(self, metric_name: str, current_value: float, 
                         baseline_value: float, percentage_change: float) -> str:
        """Determine alert status based on thresholds."""
        
        if metric_name not in self.thresholds:
            # Default thresholds if not specified
            if abs(percentage_change) > 50:
                return 'critical'
            elif abs(percentage_change) > 25:
                return 'warning'
            else:
                return 'normal'
        
        threshold_config = self.thresholds[metric_name]
        threshold_type = threshold_config['threshold_type']
        warning_threshold = threshold_config['warning_threshold']
        critical_threshold = threshold_config['critical_threshold']
        
        if threshold_type == 'upper':
            # Higher values are worse
            if current_value > critical_threshold:
                return 'critical'
            elif current_value > warning_threshold:
                return 'warning'
            else:
                return 'normal'
        elif threshold_type == 'lower':
            # Lower values are worse
            if current_value < critical_threshold:
                return 'critical'
            elif current_value < warning_threshold:
                return 'warning'
            else:
                return 'normal'
        else:
            # Percentage-based thresholds
            abs_change = abs(percentage_change)
            if abs_change > critical_threshold:
                return 'critical'
            elif abs_change > warning_threshold:
                return 'warning'
            else:
                return 'normal'
    
    def _calculate_z_score(self, current_value: float, baseline_value: float, metric_name: str) -> float:
        """Calculate Z-score if standard deviation is available."""
        # This would typically use historical standard deviation
        # For now, use a simple approximation
        estimated_std = baseline_value * 0.1  # Assume 10% standard deviation
        if estimated_std == 0:
            return 0.0
        return (current_value - baseline_value) / estimated_std
    
    def generate_alert_message(self, comparison_result: Dict[str, Any], model_id: str) -> str:
        """Generate human-readable alert message."""
        metric_name = comparison_result['metric_name']
        status = comparison_result['status']
        percentage_change = comparison_result['percentage_change']
        current_value = comparison_result['current_value']
        baseline_value = comparison_result['baseline_value']
        
        if status == 'normal':
            return f"Model {model_id}: {metric_name} is within normal range"
        
        direction = "increased" if percentage_change > 0 else "decreased"
        abs_change = abs(percentage_change)
        
        message = f"Model {model_id}: {metric_name} has {direction} by {abs_change:.1f}% "
        message += f"(current: {current_value:.3f}, baseline: {baseline_value:.3f})"
        
        if status == 'critical':
            message = f"CRITICAL - {message}"
        elif status == 'warning':
            message = f"WARNING - {message}"
            
        return message

@Configuration()
class BaselineCompareCommand(StreamingCommand):
    """
    Compare current metrics against established baselines.
    
    Usage:
    | baselinecompare metric=response_time baseline_field=avg_response_time threshold=25
    """
    
    metric = Option(
        doc='Field containing current metric values',
        require=True,
        validate=validators.Fieldname()
    )
    
    baseline_field = Option(
        doc='Field containing baseline values (or use baseline_file)',
        require=False,
        validate=validators.Fieldname()
    )
    
    baseline_file = Option(
        doc='CSV file containing baseline values',
        require=False,
        default='model_baselines.csv'
    )
    
    threshold_file = Option(
        doc='CSV file containing alert thresholds',
        require=False,
        default='alert_thresholds.csv'
    )
    
    comparison = Option(
        doc='Comparison type: percentage, absolute, zscore',
        require=False,
        default='percentage'
    )
    
    model_field = Option(
        doc='Field containing model identifier',
        require=False,
        default='model_id'
    )
    
    generate_alerts = Option(
        doc='Generate alert messages',
        require=False,
        default=True,
        validate=validators.Boolean()
    )
    
    def __init__(self):
        super(BaselineCompareCommand, self).__init__()
        self.comparator = BaselineComparator()
        self.logger = logging.getLogger(__name__)
        
    def stream(self, records):
        """Process each record and compare against baselines."""
        
        # Load baselines and thresholds
        if self.baseline_file:
            baselines = self.comparator.load_baselines(self.baseline_file)
        else:
            baselines = {}
            
        thresholds = self.comparator.load_thresholds(self.threshold_file)
        self.comparator.thresholds = thresholds
        
        for record in records:
            try:
                # Get current metric value
                current_value = record.get(self.metric)
                if current_value is None:
                    record['baseline_comparison_error'] = f'Missing metric field: {self.metric}'
                    yield record
                    continue
                
                try:
                    current_value = float(current_value)
                except (ValueError, TypeError):
                    record['baseline_comparison_error'] = f'Invalid numeric value for {self.metric}: {current_value}'
                    yield record
                    continue
                
                # Get baseline value
                baseline_value = None
                model_id = record.get(self.model_field, 'default')
                
                if self.baseline_field and self.baseline_field in record:
                    # Use baseline from record
                    try:
                        baseline_value = float(record[self.baseline_field])
                    except (ValueError, TypeError):
                        pass
                
                if baseline_value is None and baselines:
                    # Use baseline from file
                    model_baselines = baselines.get(model_id, baselines.get('default', {}))
                    baseline_key = self.metric.replace('current_', '').replace('avg_', '')
                    baseline_value = model_baselines.get(f'avg_{baseline_key}', model_baselines.get(baseline_key))
                
                if baseline_value is None:
                    record['baseline_comparison_error'] = f'No baseline found for metric {self.metric}'
                    yield record
                    continue
                
                # Perform comparison
                comparison_result = self.comparator.compare_with_baseline(
                    current_value, baseline_value, self.metric, self.comparison
                )
                
                # Add comparison results to record
                record['baseline_comparison_status'] = comparison_result['status']
                record['baseline_current_value'] = round(comparison_result['current_value'], 4)
                record['baseline_reference_value'] = round(comparison_result['baseline_value'], 4)
                record['baseline_absolute_deviation'] = round(comparison_result['absolute_deviation'], 4)
                record['baseline_percentage_change'] = round(comparison_result['percentage_change'], 2)
                record['baseline_ratio'] = round(comparison_result['ratio'], 4)
                record['baseline_z_score'] = round(comparison_result['z_score'], 2)
                
                # Generate alert message if requested
                if self.generate_alerts and comparison_result['status'] != 'normal':
                    alert_message = self.comparator.generate_alert_message(comparison_result, model_id)
                    record['baseline_alert_message'] = alert_message
                    record['baseline_alert_severity'] = comparison_result['status']
                    record['baseline_alert_time'] = datetime.now().isoformat()
                
                # Add threshold information if available
                if self.metric in thresholds:
                    threshold_info = thresholds[self.metric]
                    record['baseline_warning_threshold'] = threshold_info['warning_threshold']
                    record['baseline_critical_threshold'] = threshold_info['critical_threshold']
                    record['baseline_threshold_type'] = threshold_info['threshold_type']
                
                # Categorize deviation magnitude
                abs_pct_change = abs(comparison_result['percentage_change'])
                if abs_pct_change < 5:
                    deviation_category = 'minimal'
                elif abs_pct_change < 15:
                    deviation_category = 'small'
                elif abs_pct_change < 30:
                    deviation_category = 'moderate'
                elif abs_pct_change < 50:
                    deviation_category = 'large'
                else:
                    deviation_category = 'extreme'
                
                record['baseline_deviation_category'] = deviation_category
                
                # Add trend indication
                if comparison_result['percentage_change'] > 5:
                    record['baseline_trend'] = 'increasing'
                elif comparison_result['percentage_change'] < -5:
                    record['baseline_trend'] = 'decreasing'
                else:
                    record['baseline_trend'] = 'stable'
                
                # Add metadata
                record['baseline_comparison_time'] = datetime.now().isoformat()
                record['baseline_comparison_method'] = self.comparison
                
            except Exception as e:
                self.logger.error(f"Error in baseline comparison: {str(e)}")
                record['baseline_comparison_error'] = str(e)
            
            yield record

if __name__ == '__main__':
    dispatch(BaselineCompareCommand, sys.argv, sys.stdin, sys.stdout, __name__)
