#!/bin/sh
echo "Starting stress test script..."
/app/stress.sh &
echo "Waiting for stress test to initialize..."
sleep 5
echo "Starting metrics exporter..."
python3 -u /app/prom-exporter.py
