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
    "cpu_usage_percent": 0,
    "memory_usage_bytes": 0,
    "start_time": time.time()
}

lock = threading.lock()

# Update metrics in background
def update_metrics():
    global metrics
    global lock
    while True:
        with lock:
            try:
                metrics["cpu_usage_percent"] = psutil.cpu_percent()
                metrics["memory_usage_bytes"] = psutil.Process(os.getpid()).memory_info().rss
            except Exception as e:
                print(f"Error updating metrics: {e}")
        time.sleep(1)

# Start background thread
threading.Thread(target=update_metrics, daemon=True).start()

# HTTP server for metrics endpoint
class MetricsHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global metrics
        global lock
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()

            with lock:
                # Generate Prometheus metrics
                output = ""
                output += f"# HELP stress_test_uptime_seconds Uptime of the stress test in seconds\n"
                output += f"# TYPE stress_test_uptime_seconds counter\n"
                output += f"stress_test_uptime_seconds {time.time() - metrics['start_time']}\n"

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
