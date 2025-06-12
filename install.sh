#!/bin/bash

# LLM DriftGuard Splunk App Installation Script
# This script helps install and configure the LLM DriftGuard app

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="llm_driftguard"
SPLUNK_HOME="${SPLUNK_HOME:-/opt/splunk}"
APP_DIR="$SPLUNK_HOME/etc/apps/$APP_NAME"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    log_info "Checking requirements..."
    
    # Check if Splunk is installed
    if [ ! -d "$SPLUNK_HOME" ]; then
        log_error "Splunk not found at $SPLUNK_HOME"
        log_error "Please set SPLUNK_HOME environment variable or install Splunk"
        exit 1
    fi
    
    # Check if Python 3 is available
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not found"
        exit 1
    fi
    
    # Check Python packages
    log_info "Checking Python dependencies..."
    python3 -c "import numpy, sys" 2>/dev/null || {
        log_warning "NumPy not found. Installing..."
        pip3 install numpy
    }
    
    log_success "Requirements check completed"
}

install_app() {
    log_info "Installing LLM DriftGuard app..."
    
    # Create app directory if it doesn't exist
    if [ ! -d "$APP_DIR" ]; then
        mkdir -p "$APP_DIR"
        log_info "Created app directory: $APP_DIR"
    fi
    
    # Copy app files
    if [ -d "./LLM_DriftGuard" ]; then
        cp -r ./LLM_DriftGuard/* "$APP_DIR/"
        log_success "App files copied successfully"
    else
        log_error "Source directory ./LLM_DriftGuard not found"
        exit 1
    fi
    
    # Set correct permissions
    chmod +x "$APP_DIR"/bin/*.py
    chmod 644 "$APP_DIR"/lookups/*.csv
    chmod 644 "$APP_DIR"/default/*.conf
    chmod 644 "$APP_DIR"/default/*.xml
    
    log_success "Permissions set correctly"
}

configure_indexes() {
    log_info "Configuring indexes..."
    
    # Create indexes.conf if it doesn't exist
    INDEXES_CONF="$SPLUNK_HOME/etc/system/local/indexes.conf"
    
    if ! grep -q "\[llm_logs\]" "$INDEXES_CONF" 2>/dev/null; then
        cat >> "$INDEXES_CONF" << EOF

[llm_logs]
homePath = \$SPLUNK_DB/llm_logs/db
coldPath = \$SPLUNK_DB/llm_logs/colddb
thawedPath = \$SPLUNK_DB/llm_logs/thaweddb
maxDataSize = auto_high_volume
maxHotBuckets = 10
maxWarmDBCount = 300

[llm_metrics]
homePath = \$SPLUNK_DB/llm_metrics/db
coldPath = \$SPLUNK_DB/llm_metrics/colddb
thawedPath = \$SPLUNK_DB/llm_metrics/thaweddb
maxDataSize = auto
maxHotBuckets = 3
maxWarmDBCount = 100

[llm_alerts]
homePath = \$SPLUNK_DB/llm_alerts/db
coldPath = \$SPLUNK_DB/llm_alerts/colddb
thawedPath = \$SPLUNK_DB/llm_alerts/thaweddb
maxDataSize = auto
maxHotBuckets = 2
maxWarmDBCount = 50
EOF
        log_success "Indexes configuration added"
    else
        log_warning "Indexes already configured"
    fi
}

setup_data_inputs() {
    log_info "Setting up data inputs..."
    
    # Create inputs.conf
    INPUTS_CONF="$APP_DIR/local/inputs.conf"
    mkdir -p "$APP_DIR/local"
    
    cat > "$INPUTS_CONF" << EOF
# Sample data inputs for LLM DriftGuard
# Modify these according to your data sources

[monitor:///var/log/llm/*.json]
disabled = false
sourcetype = llm_logs
index = llm_logs

[monitor:///var/log/llm/metrics/*.json]
disabled = false
sourcetype = llm_metrics
index = llm_metrics

[monitor:///var/log/llm/alerts/*.json]
disabled = false
sourcetype = llm_alerts
index = llm_alerts

# HTTP Event Collector for real-time data
[http://llm_logs]
disabled = false
token = your-hec-token-here
index = llm_logs
sourcetype = llm_logs
EOF
    
    log_success "Data inputs configuration created"
    log_warning "Please configure your actual data sources in $INPUTS_CONF"
}

initialize_baselines() {
    log_info "Initializing baseline data..."
    
    # The baseline CSV files are already included in the app
    # Just verify they exist
    if [ -f "$APP_DIR/lookups/model_baselines.csv" ]; then
        log_success "Baseline data files found"
    else
        log_error "Baseline data files missing"
        exit 1
    fi
}

restart_splunk() {
    log_info "Restarting Splunk to apply changes..."
    
    if [ -f "$SPLUNK_HOME/bin/splunk" ]; then
        "$SPLUNK_HOME/bin/splunk" restart
        log_success "Splunk restarted successfully"
    else
        log_warning "Could not restart Splunk automatically"
        log_warning "Please restart Splunk manually: $SPLUNK_HOME/bin/splunk restart"
    fi
}

verify_installation() {
    log_info "Verifying installation..."
    
    # Check if app is properly installed
    if [ -d "$APP_DIR" ] && [ -f "$APP_DIR/default/app.conf" ]; then
        log_success "App directory structure is correct"
    else
        log_error "App installation verification failed"
        exit 1
    fi
    
    # Check permissions
    if [ -x "$APP_DIR/bin/drift_detector.py" ]; then
        log_success "Python scripts are executable"
    else
        log_error "Python scripts are not executable"
        exit 1
    fi
    
    log_success "Installation verification completed"
}

print_next_steps() {
    cat << EOF

${GREEN}=== LLM DriftGuard Installation Completed ===${NC}

${BLUE}Next Steps:${NC}
1. Configure your data inputs in: $APP_DIR/local/inputs.conf
2. Update alert email settings in: $APP_DIR/local/app.conf
3. Access the app at: http://your-splunk-server:8000/app/llm_driftguard
4. Run the baseline calculation search to initialize monitoring
5. Configure alert thresholds in: $APP_DIR/lookups/alert_thresholds.csv

${BLUE}Key Features:${NC}
- Real-time semantic drift detection
- Performance monitoring dashboards
- Anomaly detection alerts
- Baseline comparison analysis
- Custom search commands

${BLUE}Documentation:${NC}
- App README: $APP_DIR/README.md
- Search commands help: available in Splunk search interface
- Sample searches: included in saved searches

${YELLOW}Important:${NC}
- Ensure your LLM logs are indexed in the 'llm_logs' index
- Configure data inputs to match your log format
- Set up email alerts for critical drift detection

For support and updates, check the project repository.

EOF
}

# Main installation process
main() {
    echo -e "${BLUE}Starting LLM DriftGuard Splunk App Installation${NC}"
    echo "=============================================="
    
    check_requirements
    install_app
    configure_indexes
    setup_data_inputs
    initialize_baselines
    verify_installation
    
    read -p "Do you want to restart Splunk now? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        restart_splunk
    else
        log_warning "Please restart Splunk manually to complete the installation"
    fi
    
    print_next_steps
    
    log_success "LLM DriftGuard installation completed successfully!"
}

# Check if script is run with proper permissions
if [ "$EUID" -ne 0 ] && [ ! -w "$SPLUNK_HOME" ]; then
    log_error "This script requires write access to $SPLUNK_HOME"
    log_error "Please run as root or ensure your user has write permissions"
    exit 1
fi

# Run main installation
main "$@"
