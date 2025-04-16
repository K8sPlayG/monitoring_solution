#!/bin/sh
# Script to create predictable CPU and memory patterns
# for Alpine Linux with stress-ng

# Helper functions for logging
log_info() {
	echo "[$(date +"%Y-%m-%d %H:%M:%S")] [INFO] $1"
}

# Check if stress-ng is installed
if ! command -v stress-ng >/dev/null 2>&1; then
	log_error "stress-ng not found, please install it first"
	exit 1
fi

log_info "Starting stress patterns for Prometheus monitoring..."

# Run forever
while true; do
	log_info "Starting CPU ramp-up phase"

	# CPU ramp-up: gradually increase load over 60 seconds
	for i in 1 2 3 4; do
		# Use stress-ng to consume CPU with increasing workers
		log_info "CPU load at $i workers"
		stress-ng --cpu $i --timeout 15 -q
	done

	log_info "Starting memory ramp-up phase"

	# Memory ramp-up: gradually allocate and free memory
	for i in 1 2 3; do
		# Allocate varying amounts of memory (in MB)
		MEM_MB=$((i * 50))
		log_info "Allocating ${MEM_MB}MB of memory"
		stress-ng --vm 1 --vm-bytes ${MEM_MB}M --timeout 15 -q
	done

	log_info "Cool down period - sleeping for 30 seconds"
	sleep 30
done
