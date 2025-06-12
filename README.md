# LLM DriftGuard - Splunk App

## Overview

LLM DriftGuard is a comprehensive Splunk application designed to monitor semantic drift and model behavior changes in Large Language Models (LLMs). It provides real-time monitoring, alerting, and analysis capabilities to ensure your LLM deployments maintain consistent performance and behavior over time.

## Features

### Core Monitoring Capabilities
- **Semantic Drift Detection**: Track changes in model outputs and semantic consistency
- **Performance Metrics Tracking**: Monitor response times, token usage, and success rates
- **Anomaly Detection**: Identify unusual patterns in model behavior
- **Baseline Comparison**: Compare current performance against established baselines
- **Real-time Alerting**: Automated alerts for significant drift or performance degradation

### Dashboards
- **Overview Dashboard**: High-level metrics and status indicators
- **Semantic Drift Analysis**: Detailed analysis of semantic changes over time
- **Model Performance Tracking**: Performance metrics and trends
- **Anomaly Detection**: Visual identification of outliers and anomalies
- **Alert Management**: Configure and manage drift detection alerts

### Custom Search Commands
- `| driftdetect`: Analyze semantic drift in LLM outputs
- `| semanticcompare`: Compare semantic similarity between text samples
- `| llmmetrics`: Calculate and display LLM performance metrics
- `| anomalydetect`: Identify anomalies in model behavior
- `| baselinecompare`: Compare current metrics against baselines

## Installation

1. Download or clone this repository
2. Copy the `LLM_DriftGuard` folder to your Splunk apps directory
3. Restart Splunk
4. Configure data inputs for your LLM logs
5. Set up baseline metrics using the provided saved searches

## Configuration

### Data Sources
The app expects LLM data in the following format:
```json
{
  "timestamp": "2025-06-11T10:30:00Z",
  "model_id": "gpt-4-turbo",
  "request_id": "req_12345",
  "prompt": "User input text",
  "response": "Model response text",
  "response_time": 1.25,
  "token_count": 150,
  "confidence_score": 0.95,
  "metadata": {
    "temperature": 0.7,
    "max_tokens": 200
  }
}
```

### Initial Setup
1. Run the baseline calculation search: `| savedsearch "LLM Baseline Calculator"`
2. Configure alert thresholds in `lookups/alert_thresholds.csv`
3. Set up data inputs to index your LLM interaction logs

## Usage Examples

### Detect Semantic Drift
```spl
index=llm_logs 
| driftdetect field=response baseline_file="model_baselines.csv" threshold=0.8
| where drift_score > 0.3
```

### Monitor Performance Trends
```spl
index=llm_logs 
| timechart span=1h avg(response_time) avg(token_count) avg(confidence_score)
```

### Compare Against Baseline
```spl
index=llm_logs 
| baselinecompare metric=response_time baseline_field=avg_response_time
| where percentage_change > 25
```

## Custom Commands Reference

### driftdetect
Analyzes semantic drift in text fields
- `field`: Text field to analyze
- `baseline_file`: CSV file containing baseline embeddings
- `threshold`: Similarity threshold (0-1)
- `window`: Time window for comparison

### semanticcompare
Compares semantic similarity between texts
- `field1`: First text field
- `field2`: Second text field  
- `method`: Comparison method (cosine, euclidean)

### llmmetrics
Calculates comprehensive LLM metrics
- `response_field`: Field containing model responses
- `time_field`: Field containing response times
- `token_field`: Field containing token counts

## Alert Configuration

Alerts are configured in `savedsearches.conf` and can be customized:
- **High Drift Alert**: Triggers when drift score exceeds threshold
- **Performance Degradation**: Monitors response time increases
- **Low Confidence Alert**: Detects drops in model confidence
- **Anomaly Alert**: Identifies statistical anomalies

## Troubleshooting

### Common Issues
1. **No data appearing**: Check index configuration and data format
2. **Drift detection not working**: Verify baseline files are populated
3. **Performance issues**: Consider sampling large datasets

### Support
- Check Splunk logs for error messages
- Verify Python dependencies are installed
- Ensure proper permissions on lookup files

## License

MIT License - see LICENSE file for details

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request with tests and documentation
