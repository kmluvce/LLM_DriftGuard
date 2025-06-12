# LLM DriftGuard Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the LLM DriftGuard Splunk app in production environments.

## Prerequisites

### System Requirements
- Splunk Enterprise 8.2+ or Splunk Cloud
- Python 3.7+ with NumPy
- Minimum 4GB RAM available for Splunk
- 10GB+ disk space for logs and metrics storage

### Network Requirements
- Splunk Web interface access (port 8000)
- Splunk management port access (port 8089)
- Network connectivity to LLM services for log collection

### Access Requirements
- Splunk admin access for installation
- Write permissions to Splunk apps directory
- Email server access for alerting (optional)

## Installation Methods

### Method 1: Automated Installation (Recommended)

1. **Download the app package**
   ```bash
   git clone <repository-url>
   cd LLM_DriftGuard
   ```

2. **Run the installation script**
   ```bash
   chmod +x install.sh
   sudo ./install.sh
   ```

3. **Follow the prompts** to configure indexes and data inputs

### Method 2: Manual Installation

1. **Copy app to Splunk**
   ```bash
   cp -r LLM_DriftGuard /opt/splunk/etc/apps/llm_driftguard
   chown -R splunk:splunk /opt/splunk/etc/apps/llm_driftguard
   ```

2. **Configure indexes** (add to `$SPLUNK_HOME/etc/system/local/indexes.conf`):
   ```ini
   [llm_logs]
   homePath = $SPLUNK_DB/llm_logs/db
   coldPath = $SPLUNK_DB/llm_logs/colddb
   maxDataSize = auto_high_volume
   
   [llm_metrics]
   homePath = $SPLUNK_DB/llm_metrics/db
   coldPath = $SPLUNK_DB/llm_metrics/colddb
   maxDataSize = auto
   
   [llm_alerts]
   homePath = $SPLUNK_DB/llm_alerts/db
   coldPath = $SPLUNK_DB/llm_alerts/colddb
   maxDataSize = auto
   ```

3. **Restart Splunk**
   ```bash
   /opt/splunk/bin/splunk restart
   ```

## Data Source Configuration

### LLM Log Format

The app expects JSON-formatted logs with the following structure:

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

### Data Input Methods

#### 1. File Monitoring
Configure Splunk to monitor log files:

```ini
[monitor:///var/log/llm/*.json]
disabled = false
sourcetype = llm_logs
index = llm_logs
```

#### 2. HTTP Event Collector (HEC)
Set up HEC for real-time data ingestion:

1. Enable HEC in Splunk Web: Settings > Data Inputs > HTTP Event Collector
2. Create new token for LLM logs
3. Configure your LLM service to send data to HEC endpoint:
   ```
   https://your-splunk-server:8088/services/collector/event
   ```

#### 3. Splunk Universal Forwarder
Deploy Universal Forwarders on LLM servers:

1. Install Universal Forwarder on LLM servers
2. Configure inputs.conf to monitor log files
3. Forward to your Splunk indexer

### Sample Data Generation

For testing purposes, use the included sample data generator:

```python
# Run sample data generator
python3 bin/sample_data_generator.py --count 1000 --output /tmp/sample_llm_logs.json
```

## Configuration

### 1. Alert Thresholds

Edit `lookups/alert_thresholds.csv` to customize alert thresholds:

| Metric | Warning | Critical | Description |
|--------|---------|----------|-------------|
| drift_score | 0.3 | 0.5 | Semantic drift detection |
| response_time | 5.0 | 10.0 | Response time in seconds |
| confidence_score | 0.6 | 0.3 | Minimum confidence level |

### 2. Baseline Configuration

Initial baselines are calculated automatically. To manually update:

1. Run the "LLM Baseline Calculator" saved search
2. Or upload custom baselines to `lookups/model_baselines.csv`

### 3. Email Alerting

Configure email settings in `local/app.conf`:

```ini
[custom_settings]
alert_email_enabled = true
alert_email_recipients = admin@company.com,team@company.com
```

Configure Splunk email settings:
1. Go to Settings > System Settings > Email Settings
2. Configure SMTP server details
3. Test email configuration

## Security Considerations

### 1. Access Control

Configure role-based access:

```bash
# Create custom role for LLM monitoring
splunk add role llm_monitor -capability "list_default"
splunk edit role llm_monitor -srchIndexesAllowed "llm_logs,llm_metrics,llm_alerts"
```

### 2. Data Privacy

- Ensure sensitive data is masked in logs
- Configure data retention policies
- Implement encryption for data in transit

### 3. Network Security

- Use HTTPS for Splunk Web interface
- Secure HEC endpoints with authentication
- Implement firewall rules for Splunk ports

## Performance Optimization

### 1. Index Optimization

```ini
# High-volume optimization
[llm_logs]
maxDataSize = auto_high_volume
maxHotBuckets = 10
maxWarmDBCount = 300
```

### 2. Search Optimization

- Use summary indexing for frequently accessed metrics
- Configure data model acceleration
- Implement search head clustering for high availability

### 3. Resource Allocation

- Allocate adequate CPU/RAM for search heads
- Configure appropriate disk I/O for indexers
- Monitor resource usage via Monitoring Console

## Monitoring and Maintenance

### 1. Health Monitoring

Monitor app health using:
- Splunk Monitoring Console
- Custom health checks in saved searches
- External monitoring tools

### 2. Regular Maintenance Tasks

**Daily:**
- Review alert status
- Check data ingestion rates
- Monitor system performance

**Weekly:**
- Update baseline calculations
- Review and tune alert thresholds
- Clean up old data per retention policy

**Monthly:**
- Performance review and optimization
- Security audit
- App updates and patches

### 3. Troubleshooting

Common issues and solutions:

| Issue | Symptoms | Solution |
|-------|----------|----------|
| No data appearing | Empty dashboards | Check data inputs and index configuration |
| High memory usage | Slow searches | Optimize search queries, increase memory |
| Alert flooding | Too many alerts | Tune alert thresholds |
| Drift detection errors | Command failures | Check Python dependencies |

## Scaling for Production

### 1. Distributed Deployment

For large-scale deployments:

```
Search Head Cluster (3+ nodes)
├── Load Balancer
├── Search Head 1
├── Search Head 2
└── Search Head 3

Indexer Cluster (3+ nodes)
├── Cluster Master
├── Indexer 1
├── Indexer 2
└── Indexer 3

Universal Forwarders
├── LLM Server 1
├── LLM Server 2
└── LLM Server N
```

### 2. Capacity Planning

Calculate requirements based on:
- Daily log volume (GB/day)
- Search frequency and complexity
- Retention requirements
- Number of concurrent users

### 3. High Availability

Implement:
- Search head clustering
- Indexer clustering with replication
- Geographic data replication
- Automated failover procedures

## Integration Examples

### 1. API Integration

```python
# Send data via HEC
import requests
import json

def send_llm_metrics(data):
    headers = {
        'Authorization': 'Splunk your-hec-token',
        'Content-Type': 'application/json'
    }
    response = requests.post(
        'https://splunk-server:8088/services/collector/event',
        headers=headers,
        data=json.dumps({'event': data})
    )
    return response.status_code == 200
```

### 2. Webhook Alerts

Configure webhook endpoints for external systems:

```json
{
  "webhook_url": "https://slack.com/api/chat.postMessage",
  "alert_payload": {
    "channel": "#llm-alerts",
    "text": "Drift detected in model: $result.model_id$"
  }
}
```

## Backup and Recovery

### 1. Backup Strategy

- Configuration files: Daily backup
- Lookup tables: Daily backup  
- Splunk indexes: Per retention policy
- Custom scripts: Version control

### 2. Recovery Procedures

1. **App Recovery:**
   ```bash
   # Restore from backup
   cp -r backup/llm_driftguard /opt/splunk/etc/apps/
   /opt/splunk/bin/splunk restart
   ```

2. **Data Recovery:**
   ```bash
   # Restore index data
   splunk restore /path/to/backup/llm_logs
   ```

## Support and Updates

### Getting Support
- Check logs in `$SPLUNK_HOME/var/log/splunk/`
- Review app documentation
- Contact support team

### Updates
- Test updates in staging environment
- Backup configuration before updates
- Follow semantic versioning for compatibility

This deployment guide provides a comprehensive foundation for implementing LLM DriftGuard in production environments. Customize the configuration based on your specific requirements and infrastructure.
