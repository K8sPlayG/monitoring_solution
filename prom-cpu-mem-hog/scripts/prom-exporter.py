#!/usr/bin/env python3
# Simple Prometheus metrics exporter for stress testing

import http.server
import socketserver
import time
import os
import subprocess
import psutil
import threading

# Global metrics
metrics = {
}

lock = threading.Lock()

# Update metrics in background
def update_metrics():
    total_cpu_percent = 0
    total_memory_usage_bytes = 0
    metrics = {}
    # Iterate through all processes
    for proc in psutil.process_iter(attrs=['name', 'cpu_percent', 'memory_info']):
        try:
            # Check if process name starts with "stress-ng"
            if proc.info['name'] and proc.info['name'].startswith("stress-ng"):
                # Accumulate CPU and memory usage
                total_cpu_percent += proc.info['cpu_percent']
                total_memory_usage_bytes += proc.info['memory_info'].rss
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # Skip processes that are not accessible or have terminated
            continue
    metrics["cpu_usage_percent"] = total_cpu_percent
    metrics["memory_usage_bytes"] = total_memory_usage_bytes
    return metrics

def run_metrics_thread():
    global lock
    global metrics
    while True:
        new_metrics = update_metrics()
        if new_metrics:
            with lock:
                if new_metrics['cpu_usage_percent'] == 0:
                    time.sleep(0.2)
                    new_metrics = update_metrics()
                metrics = new_metrics
                print(f'new_metrics = {new_metrics}')
        time.sleep(1)

# Start background thread
threading.Thread(target=run_metrics_thread, daemon=True).start()

# HTTP server for metrics endpoint
class MetricsHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global metrics
        global lock
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()

            output = ""
            with lock:
                # Generate Prometheus metrics
                if metrics:
                    output += f"# HELP stress_test_cpu_usage_percent Current CPU usage percent\n"
                    output += f"# TYPE stress_test_cpu_usage_percent gauge\n"
                    output += f"stress_test_cpu_usage_percent {metrics['cpu_usage_percent']}\n"

                    output += f"# HELP stress_test_memory_usage_bytes Current memory usage in bytes\n"
                    output += f"# TYPE stress_test_memory_usage_bytes gauge\n"
                    output += f"stress_test_memory_usage_bytes {metrics['memory_usage_bytes']}\n"

            self.wfile.write(output.encode())
        else:
            self.send_response(404)
            self.end_headers()

# Run HTTP server
httpd = socketserver.TCPServer(('', 8000), MetricsHandler)
print("Server started at localhost:8000")
httpd.serve_forever()
