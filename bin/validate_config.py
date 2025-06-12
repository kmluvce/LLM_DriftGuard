#!/usr/bin/env python3
"""
LLM DriftGuard - Configuration Validation Script
Validates the installation and configuration of the LLM DriftGuard Splunk app
"""

import os
import sys
import json
import csv
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Tuple

class ConfigValidator:
    """Validates LLM DriftGuard app configuration."""
    
    def __init__(self, splunk_home: str = "/opt/splunk"):
        self.splunk_home = Path(splunk_home)
        self.app_home = self.splunk_home / "etc" / "apps" / "llm_driftguard"
        self.errors = []
        self.warnings = []
        self.info = []
        
    def log_error(self, message: str):
        """Log an error message."""
        self.errors.append(f"❌ ERROR: {message}")
        
    def log_warning(self, message: str):
        """Log a warning message."""
        self.warnings.append(f"⚠️  WARNING: {message}")
        
    def log_info(self, message: str):
        """Log an info message."""
        self.info.append(f"ℹ️  INFO: {message}")
        
    def validate_directory_structure(self) -> bool:
        """Validate that required directories exist."""
        self.log_info("Validating directory structure...")
        
        required_dirs = [
            "bin",
            "default", 
            "static",
            "lookups",
            "metadata",
            "default/data/ui/views",
            "default/data/ui/nav"
        ]
        
        success = True
        for dir_path in required_dirs:
            full_path = self.app_home / dir_path
            if not full_path.exists():
                self.log_error(f"Required directory missing: {full_path}")
                success = False
            elif not full_path.is_dir():
                self.log_error(f"Path exists but is not a directory: {full_path}")
                success = False
                
        if success:
            self.log_info("Directory structure validation passed")
        
        return success
    
    def validate_configuration_files(self) -> bool:
        """Validate that required configuration files exist and are valid."""
        self.log_info("Validating configuration files...")
        
        required_files = {
            "default/app.conf": self._validate_app_conf,
            "default/commands.conf": self._validate_commands_conf,
            "default/props.conf": self._validate_props_conf,
            "default/savedsearches.conf": self._validate_savedsearches_conf,
            "metadata/default.meta": self._validate_metadata
        }
        
        success = True
        for file_path, validator in required_files.items():
            full_path = self.app_home / file_path
            if not full_path.exists():
                self.log_error(f"Required configuration file missing: {full_path}")
                success = False
            elif not full_path.is_file():
                self.log_error(f"Path exists but is not a file: {full_path}")
                success = False
            else:
                try:
                    if validator and not validator(full_path):
                        success = False
                except Exception as e:
                    self.log_error(f"Error validating {file_path}: {str(e)}")
                    success = False
        
        return success
    
    def validate_python_scripts(self) -> bool:
        """Validate Python scripts are executable and have correct syntax."""
        self.log_info("Validating Python scripts...")
        
        required_scripts = [
            "bin/drift_detector.py",
            "bin/semantic_analyzer.py", 
            "bin/llm_metrics_collector.py",
            "bin/model_monitor.py",
            "bin/alert_handler.py"
        ]
        
        success = True
        for script_path in required_scripts:
            full_path = self.app_home / script_path
            
            if not full_path.exists():
                self.log_error(f"Required Python script missing: {full_path}")
                success = False
                continue
                
            # Check if executable
            if not os.access(full_path, os.X_OK):
                self.log_warning(f"Python script not executable: {full_path}")
                
            # Check syntax
            try:
                result = subprocess.run([
                    sys.executable, "-m", "py_compile", str(full_path)
                ], capture_output=True, text=True)
                
                if result.returncode != 0:
                    self.log_error(f"Python syntax error in {script_path}: {result.stderr}")
                    success = False
                    
            except Exception as e:
                self.log_error(f"Could not validate Python syntax for {script_path}: {str(e)}")
                success = False
        
        return success
    
    def validate_lookup_tables(self) -> bool:
        """Validate lookup table files."""
        self.log_info("Validating lookup tables...")
        
        required_lookups = {
            "lookups/model_baselines.csv": ["model_id", "avg_response_time", "avg_confidence"],
            "lookups/semantic_categories.csv": ["prompt_type", "category", "description"],
            "lookups/alert_thresholds.csv": ["metric_name", "warning_threshold", "critical_threshold"]
        }
        
        success = True
        for lookup_path, required_columns in required_lookups.items():
            full_path = self.app_home / lookup_path
            
            if not full_path.exists():
                self.log_error(f"Required lookup table missing: {full_path}")
                success = False
                continue
                
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    headers = reader.fieldnames
                    
                    if not headers:
                        self.log_error(f"Lookup table has no headers: {lookup_path}")
                        success = False
                        continue
                        
                    missing_columns = set(required_columns) - set(headers)
                    if missing_columns:
                        self.log_error(f"Missing columns in {lookup_path}: {missing_columns}")
                        success = False
                    
                    # Check for data
                    row_count = sum(1 for _ in reader)
                    if row_count == 0:
                        self.log_warning(f"Lookup table is empty: {lookup_path}")
                    else:
                        self.log_info(f"Lookup table {lookup_path}: {row_count} rows")
                        
            except Exception as e:
                self.log_error(f"Error reading lookup table {lookup_path}: {str(e)}")
                success = False
        
        return success
    
    def validate_dashboards(self) -> bool:
        """Validate dashboard XML files."""
        self.log_info("Validating dashboards...")
        
        required_dashboards = [
            "default/data/ui/views/overview_dashboard.xml",
            "default/data/ui/views/semantic_drift_analysis.xml", 
            "default/data/ui/views/model_performance_tracking.xml",
            "default/data/ui/views/anomaly_detection.xml",
            "default/data/ui/views/alert_management.xml"
        ]
        
        success = True
        for dashboard_path in required_dashboards:
            full_path = self.app_home / dashboard_path
            
            if not full_path.exists():
                self.log_error(f"Required dashboard missing: {full_path}")
                success = False
                continue
                
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Basic XML validation
                if not content.strip().startswith('<'):
                    self.log_error(f"Dashboard file doesn't appear to be XML: {dashboard_path}")
                    success = False
                elif '<form>' not in content and '<dashboard>' not in content:
                    self.log_warning(f"Dashboard might not be properly formatted: {dashboard_path}")
                    
            except Exception as e:
                self.log_error(f"Error reading dashboard {dashboard_path}: {str(e)}")
                success = False
        
        return success
    
    def validate_dependencies(self) -> bool:
        """Validate Python dependencies."""
        self.log_info("Validating Python dependencies...")
        
        required_packages = ["numpy"]
        optional_packages = ["pandas", "scipy", "scikit-learn"]
        
        success = True
        
        for package in required_packages:
            try:
                __import__(package)
                self.log_info(f"Required package available: {package}")
            except ImportError:
                self.log_error(f"Required Python package missing: {package}")
                success = False
                
        for package in optional_packages:
            try:
                __import__(package)
                self.log_info(f"Optional package available: {package}")
            except ImportError:
                self.log_info(f"Optional package not available: {package}")
        
        return success
    
    def validate_splunk_connection(self) -> bool:
        """Validate Splunk is running and accessible."""
        self.log_info("Validating Splunk connection...")
        
        try:
            splunk_cmd = self.splunk_home / "bin" / "splunk"
            if not splunk_cmd.exists():
                self.log_error(f"Splunk command not found: {splunk_cmd}")
                return False
                
            # Check if Splunk is running
            result = subprocess.run([
                str(splunk_cmd), "status"
            ], capture_output=True, text=True)
            
            if "splunkd is running" in result.stdout:
                self.log_info("Splunk is running")
                return True
            else:
                self.log_warning("Splunk may not be running")
                return False
                
        except Exception as e:
            self.log_error(f"Could not check Splunk status: {str(e)}")
            return False
    
    def _validate_app_conf(self, file_path: Path) -> bool:
        """Validate app.conf file."""
        # Basic validation - ensure it has required sections
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        required_sections = ["[install]", "[ui]", "[launcher]"]
        for section in required_sections:
            if section not in content:
                self.log_error(f"Missing section {section} in app.conf")
                return False
        
        return True
    
    def _validate_commands_conf(self, file_path: Path) -> bool:
        """Validate commands.conf file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        required_commands = ["[driftdetect]", "[semanticcompare]", "[llmmetrics]"]
        for command in required_commands:
            if command not in content:
                self.log_error(f"Missing command {command} in commands.conf")
                return False
        
        return True
    
    def _validate_props_conf(self, file_path: Path) -> bool:
        """Validate props.conf file."""
        # Basic validation
        return True
    
    def _validate_savedsearches_conf(self, file_path: Path) -> bool:
        """Validate savedsearches.conf file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if "[LLM" not in content:
            self.log_warning("No LLM saved searches found in savedsearches.conf")
        
        return True
    
    def _validate_metadata(self, file_path: Path) -> bool:
        """Validate metadata file."""
        # Basic validation
        return True
    
    def run_validation(self) -> bool:
        """Run all validation checks."""
        print("🔍 Starting LLM DriftGuard configuration validation...\n")
        
        # Check if app directory exists
        if not self.app_home.exists():
            self.log_error(f"App directory does not exist: {self.app_home}")
            self._print_results()
            return False
        
        all_checks = [
            self.validate_directory_structure,
            self.validate_configuration_files,
            self.validate_python_scripts,
            self.validate_lookup_tables,
            self.validate_dashboards,
            self.validate_dependencies,
            self.validate_splunk_connection
        ]
        
        results = []
        for check in all_checks:
            try:
                result = check()
                results.append(result)
            except Exception as e:
                self.log_error(f"Validation check failed with exception: {str(e)}")
                results.append(False)
        
        self._print_results()
        return all(results)
    
    def _print_results(self):
        """Print validation results."""
        print("\n" + "="*60)
        print("📋 VALIDATION RESULTS")
        print("="*60)
        
        if self.errors:
            print("\n🔴 ERRORS:")
            for error in self.errors:
                print(f"  {error}")
        
        if self.warnings:
            print("\n🟡 WARNINGS:")
            for warning in self.warnings:
                print(f"  {warning}")
        
        if self.info:
            print("\n🟢 INFO:")
            for info in self.info:
                print(f"  {info}")
        
        print(f"\n📊 SUMMARY:")
        print(f"  Errors: {len(self.errors)}")
        print(f"  Warnings: {len(self.warnings)}")
        print(f"  Info: {len(self.info)}")
        
        if not self.errors:
            print("\n✅ Configuration validation PASSED!")
            print("The LLM DriftGuard app appears to be properly configured.")
        else:
            print("\n❌ Configuration validation FAILED!")
            print("Please fix the errors above before using the app.")
        
        print("\n" + "="*60)

def main():
    parser = argparse.ArgumentParser(description='Validate LLM DriftGuard configuration')
    parser.add_argument('--splunk-home', type=str, default='/opt/splunk',
                       help='Path to Splunk installation directory')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    validator = ConfigValidator(args.splunk_home)
    success = validator.run_validation()
    
    if success:
        print("\n🎉 Ready to monitor LLM drift and performance!")
        sys.exit(0)
    else:
        print("\n🔧 Please fix the configuration issues and run validation again.")
        sys.exit(1)

if __name__ == "__main__":
    main()
