#!/usr/bin/env python3
"""
LLM DriftGuard - Sample Data Generator
Generates realistic sample data for testing the LLM DriftGuard Splunk app
"""

import json
import random
import argparse
import datetime
from typing import List, Dict, Any
import uuid

class LLMSampleDataGenerator:
    """Generates realistic LLM interaction data for testing."""
    
    def __init__(self):
        self.models = [
            "gpt-4-turbo",
            "gpt-3.5-turbo", 
            "claude-3-sonnet",
            "claude-3-haiku",
            "llama-2-70b",
            "gemini-pro"
        ]
        
        self.sample_prompts = [
            "Explain the concept of machine learning",
            "Write a Python function to calculate fibonacci numbers",
            "Summarize the latest developments in AI",
            "How do neural networks work?",
            "What are the benefits of cloud computing?",
            "Create a marketing plan for a new product",
            "Analyze the stock market trends",
            "Write a creative story about robots",
            "Explain quantum computing in simple terms",
            "How to optimize database performance?",
            "What is the future of artificial intelligence?",
            "Design a RESTful API for user management",
            "Explain the difference between AI and ML",
            "Write a poem about technology",
            "How to implement secure authentication?",
            "What are microservices and their benefits?",
            "Explain blockchain technology",
            "Create a data visualization dashboard",
            "How to scale web applications?",
            "What is DevOps and its practices?"
        ]
        
        self.sample_responses = [
            "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed...",
            "Here's a Python function to calculate Fibonacci numbers: def fibonacci(n): if n <= 1: return n else: return fibonacci(n-1) + fibonacci(n-2)",
            "Recent developments in AI include advances in large language models, computer vision improvements, and breakthrough applications in healthcare...",
            "Neural networks are computing systems inspired by biological neural networks. They consist of interconnected nodes that process information...",
            "Cloud computing offers benefits including scalability, cost-effectiveness, accessibility, reliability, and reduced infrastructure management...",
            "A comprehensive marketing plan should include market analysis, target audience identification, positioning strategy, and measurement metrics...",
            "Current stock market trends show volatility influenced by inflation concerns, geopolitical events, and sector rotation patterns...",
            "In a world where robots had learned to dream, one small unit named Circuit began experiencing visions of electric sheep and digital meadows...",
            "Quantum computing uses quantum mechanical phenomena to process information differently than classical computers, potentially solving complex problems faster...",
            "Database optimization involves indexing strategies, query optimization, proper schema design, and regular maintenance procedures...",
            "The future of AI likely includes more sophisticated reasoning capabilities, better human-AI collaboration, and widespread integration across industries...",
            "A RESTful API for user management would include endpoints for CRUD operations: GET /users, POST /users, PUT /users/{id}, DELETE /users/{id}...",
            "AI is the broader concept of machines performing tasks intelligently, while ML is a subset focused on learning from data to improve performance...",
            "In circuits bright and screens aglow, Technology's dance begins to show, Ones and zeros in endless flight, Illuminating our digital night...",
            "Secure authentication requires strong password policies, multi-factor authentication, encrypted data transmission, and regular security audits...",
            "Microservices architecture breaks applications into small, independent services that communicate via APIs, offering scalability and maintainability...",
            "Blockchain is a distributed ledger technology that maintains a continuously growing list of records secured using cryptographic principles...",
            "An effective data visualization dashboard should focus on key metrics, use appropriate chart types, maintain visual hierarchy, and provide interactivity...",
            "Web application scaling involves horizontal scaling, load balancing, database optimization, caching strategies, and microservices architecture...",
            "DevOps is a culture and practice that emphasizes collaboration between development and operations teams to improve deployment frequency and reliability..."
        ]
        
        self.error_messages = [
            "Connection timeout",
            "API rate limit exceeded", 
            "Invalid request format",
            "Model overloaded",
            "Authentication failed",
            "Resource not found",
            "Internal server error",
            "Request too large"
        ]
    
    def generate_sample_record(self, timestamp: datetime.datetime = None, 
                             introduce_drift: bool = False,
                             introduce_anomaly: bool = False) -> Dict[str, Any]:
        """Generate a single sample LLM interaction record."""
        
        if timestamp is None:
            timestamp = datetime.datetime.now()
        
        model_id = random.choice(self.models)
        prompt = random.choice(self.sample_prompts)
        response = random.choice(self.sample_responses)
        
        # Base performance characteristics per model
        base_metrics = {
            "gpt-4-turbo": {"time": 2.1, "tokens": 145, "confidence": 0.89},
            "gpt-3.5-turbo": {"time": 1.3, "tokens": 120, "confidence": 0.85},
            "claude-3-sonnet": {"time": 1.8, "tokens": 160, "confidence": 0.91},
            "claude-3-haiku": {"time": 0.9, "tokens": 95, "confidence": 0.82},
            "llama-2-70b": {"time": 3.2, "tokens": 180, "confidence": 0.87},
            "gemini-pro": {"time": 2.5, "tokens": 155, "confidence": 0.88}
        }
        
        base = base_metrics[model_id]
        
        # Add normal variation
        response_time = max(0.1, base["time"] + random.gauss(0, base["time"] * 0.2))
        token_count = max(10, int(base["tokens"] + random.gauss(0, base["tokens"] * 0.3)))
        confidence_score = max(0.1, min(1.0, base["confidence"] + random.gauss(0, 0.1)))
        
        # Introduce drift if requested
        if introduce_drift:
            response_time *= random.uniform(1.5, 3.0)  # Significant slowdown
            confidence_score *= random.uniform(0.5, 0.8)  # Lower confidence
            response = self._modify_response_for_drift(response)
        
        # Introduce anomalies if requested
        if introduce_anomaly:
            if random.random() < 0.3:  # 30% chance of timeout
                response_time = random.uniform(20, 60)
            if random.random() < 0.2:  # 20% chance of very low confidence
                confidence_score = random.uniform(0.1, 0.3)
            if random.random() < 0.1:  # 10% chance of error
                return self._generate_error_record(timestamp, model_id, prompt)
        
        # Create metadata
        metadata = {
            "temperature": round(random.uniform(0.1, 1.0), 1),
            "max_tokens": random.choice([100, 200, 500, 1000]),
            "top_p": round(random.uniform(0.8, 1.0), 2),
            "frequency_penalty": round(random.uniform(0.0, 0.5), 2)
        }
        
        record = {
            "timestamp": timestamp.isoformat() + "Z",
            "model_id": model_id,
            "request_id": f"req_{uuid.uuid4().hex[:8]}",
            "prompt": prompt,
            "response": response,
            "response_time": round(response_time, 3),
            "token_count": token_count,
            "confidence_score": round(confidence_score, 3),
            "metadata": metadata
        }
        
        return record
    
    def _modify_response_for_drift(self, original_response: str) -> str:
        """Modify response to simulate semantic drift."""
        modifications = [
            lambda s: s.replace("machine learning", "algorithmic processes"),
            lambda s: s.replace("artificial intelligence", "computational systems"),
            lambda s: s.replace("optimization", "enhancement procedures"),
            lambda s: s.replace("analysis", "evaluation processes"),
            lambda s: s.replace("development", "construction activities"),
            lambda s: s + " [Note: This response may contain outdated information.]",
            lambda s: s.replace(".", ". Additionally, consider consulting recent sources."),
            lambda s: "Based on historical data, " + s.lower()
        ]
        
        # Apply 1-3 random modifications
        num_mods = random.randint(1, 3)
        result = original_response
        
        for _ in range(num_mods):
            mod = random.choice(modifications)
            result = mod(result)
        
        return result
    
    def _generate_error_record(self, timestamp: datetime.datetime, 
                             model_id: str, prompt: str) -> Dict[str, Any]:
        """Generate an error record."""
        return {
            "timestamp": timestamp.isoformat() + "Z",
            "model_id": model_id,
            "request_id": f"req_{uuid.uuid4().hex[:8]}",
            "prompt": prompt,
            "response": "",
            "response_time": random.uniform(0.1, 2.0),
            "token_count": 0,
            "confidence_score": 0.0,
            "error": random.choice(self.error_messages),
            "metadata": {"error_code": random.randint(400, 599)}
        }
    
    def generate_time_series_data(self, start_time: datetime.datetime,
                                end_time: datetime.datetime,
                                interval_minutes: int = 1,
                                records_per_interval: int = 5,
                                drift_probability: float = 0.05,
                                anomaly_probability: float = 0.02) -> List[Dict[str, Any]]:
        """Generate time series data with drift and anomalies."""
        
        records = []
        current_time = start_time
        
        while current_time < end_time:
            for _ in range(records_per_interval):
                # Add some randomness to timestamps within the interval
                record_time = current_time + datetime.timedelta(
                    seconds=random.randint(0, interval_minutes * 60 - 1)
                )
                
                introduce_drift = random.random() < drift_probability
                introduce_anomaly = random.random() < anomaly_probability
                
                record = self.generate_sample_record(
                    record_time, introduce_drift, introduce_anomaly
                )
                records.append(record)
            
            current_time += datetime.timedelta(minutes=interval_minutes)
        
        return records
    
    def save_to_file(self, records: List[Dict[str, Any]], filename: str):
        """Save records to a JSON file."""
        with open(filename, 'w') as f:
            for record in records:
                f.write(json.dumps(record) + '\n')
        print(f"Generated {len(records)} records and saved to {filename}")

def main():
    parser = argparse.ArgumentParser(description='Generate sample LLM data for testing')
    parser.add_argument('--count', type=int, default=100, 
                       help='Number of records to generate')
    parser.add_argument('--output', type=str, default='sample_llm_data.json',
                       help='Output filename')
    parser.add_argument('--time-series', action='store_true',
                       help='Generate time series data')
    parser.add_argument('--hours', type=int, default=24,
                       help='Hours of data for time series (default: 24)')
    parser.add_argument('--drift-rate', type=float, default=0.05,
                       help='Probability of drift in each record (0.0-1.0)')
    parser.add_argument('--anomaly-rate', type=float, default=0.02,
                       help='Probability of anomalies in each record (0.0-1.0)')
    
    args = parser.parse_args()
    
    generator = LLMSampleDataGenerator()
    
    if args.time_series:
        end_time = datetime.datetime.now()
        start_time = end_time - datetime.timedelta(hours=args.hours)
        
        records = generator.generate_time_series_data(
            start_time=start_time,
            end_time=end_time,
            interval_minutes=5,  # One record every 5 minutes
            records_per_interval=3,  # 3 records per interval
            drift_probability=args.drift_rate,
            anomaly_probability=args.anomaly_rate
        )
    else:
        records = []
        for i in range(args.count):
            # Distribute records over the last hour
            timestamp = datetime.datetime.now() - datetime.timedelta(
                minutes=random.randint(0, 60)
            )
            
            introduce_drift = random.random() < args.drift_rate
            introduce_anomaly = random.random() < args.anomaly_rate
            
            record = generator.generate_sample_record(
                timestamp, introduce_drift, introduce_anomaly
            )
            records.append(record)
    
    generator.save_to_file(records, args.output)
    
    print(f"Sample data generation completed:")
    print(f"  Total records: {len(records)}")
    print(f"  Drift records: {sum(1 for r in records if 'drift' in str(r))}")
    print(f"  Error records: {sum(1 for r in records if 'error' in r)}")
    print(f"  Output file: {args.output}")
    print(f"\nTo ingest into Splunk:")
    print(f"  1. Copy file to Splunk server")
    print(f"  2. Use: index=llm_logs sourcetype=llm_logs {args.output}")

if __name__ == "__main__":
    main()
