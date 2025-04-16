package main

import (
	"fmt"
	"log"
	"math/rand"
	"net/http"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

var (
	// Counter metric to track the number of HTTP requests
	httpRequestsTotal = promauto.NewCounter(prometheus.CounterOpts{
		Name: "http_requests_total",
		Help: "Total number of HTTP requests",
	})

	// Gauge metric for an example random value
	randomValue = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "example_random_value",
		Help: "Example gauge showing a random value between 0 and 100",
	})

	// Counter metrics for the CPU and memory spikes
	cpuSpikeCounter = promauto.NewCounter(prometheus.CounterOpts{
		Name: "cpu_spike_total",
		Help: "Total number of CPU spike events",
	})

	memorySpikeCounter = promauto.NewCounter(prometheus.CounterOpts{
		Name: "memory_spike_total",
		Help: "Total number of memory spike events",
	})

	// Gauge metrics to track active spikes
	cpuSpikeActive = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "cpu_spike_active",
		Help: "Indicates if a CPU spike is currently active (1) or not (0)",
	})

	memorySpikeActive = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "memory_spike_active",
		Help: "Indicates if a memory spike is currently active (1) or not (0)",
	})
)

func loggingMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Print out a log when the /metrics endpoint is hit
		if r.URL.Path == "/metrics" {
			fmt.Printf("Endpoint '/metrics' hit at %v\n", time.Now())
		}
		next.ServeHTTP(w, r)
	})
}

// isPrime checks if a number is prime (CPU-intensive function for the CPU spike)
func isPrime(n int) bool {
	if n <= 1 {
		return false
	}
	if n <= 3 {
		return true
	}
	if n%2 == 0 || n%3 == 0 {
		return false
	}
	i := 5
	for i*i <= n {
		if n%i == 0 || n%(i+2) == 0 {
			return false
		}
		i += 6
	}
	return true
}

func main() {
	// Update the random value gauge every 5 seconds
	go func() {
		for {
			randomValue.Set(float64(rand.Intn(100)))
			time.Sleep(5 * time.Second)
		}
	}()

	// Define routes
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		// Increment the request counter
		httpRequestsTotal.Inc()
		w.Write([]byte("Hello, World! Visit /metrics to see Prometheus metrics."))
	})

	metricsHandler := promhttp.Handler()

	// Expose metrics endpoint
	http.Handle("/metrics", loggingMiddleware(metricsHandler))

	// CPU spike endpoint
	http.HandleFunc("/cpu-spike", func(w http.ResponseWriter, r *http.Request) {
		httpRequestsTotal.Inc()
		cpuSpikeCounter.Inc()

		// Parse duration parameter (default: 5 seconds)
		durationStr := r.URL.Query().Get("duration")
		duration := 30 * time.Second
		if durationStr != "" {
			parsedDuration, err := time.ParseDuration(durationStr)
			if err == nil && parsedDuration > 0 && parsedDuration <= 30*time.Second {
				duration = parsedDuration
			}
		}

		log.Printf("CPU spike started for %v\n", duration)

		// Run CPU spike in a goroutine to avoid blocking the HTTP response
		go func() {
			cpuSpikeActive.Set(1) // Set the active gauge to 1

			// End time calculation
			endTime := time.Now().Add(duration)

			// CPU-intensive operation - calculating primes
			for time.Now().Before(endTime) {
				// Perform CPU-intensive calculation (find large primes)
				for i := 0; i < 1000000; i++ {
					isPrime(i)
				}
			}

			cpuSpikeActive.Set(0) // Reset the active gauge to 0
			log.Println("CPU spike completed")
		}()

		w.Write([]byte(fmt.Sprintf("CPU spike triggered for %v\n", duration)))
	})

	// Memory spike endpoint
	http.HandleFunc("/memory-spike", func(w http.ResponseWriter, r *http.Request) {
		httpRequestsTotal.Inc()
		memorySpikeCounter.Inc()

		// Parse duration parameter (default: 5 seconds)
		durationStr := r.URL.Query().Get("duration")
		duration := 30 * time.Second
		if durationStr != "" {
			parsedDuration, err := time.ParseDuration(durationStr)
			if err == nil && parsedDuration > 0 && parsedDuration <= 30*time.Second {
				duration = parsedDuration
			}
		}

		// Parse size parameter (default: 500MB, max: 1GB)
		sizeStr := r.URL.Query().Get("size")
		sizeMB := 500
		if sizeStr != "" {
			if parsedSize, err := fmt.Sscanf(sizeStr, "%d", &sizeMB); err == nil && parsedSize > 0 {
				if sizeMB > 1000 {
					sizeMB = 1000 // Cap at 1GB to prevent OOM
				}
			}
		}

		log.Printf("Memory spike started: %d MB for %v\n", sizeMB, duration)

		// Run memory spike in a goroutine
		go func() {
			memorySpikeActive.Set(1) // Set the active gauge to 1

			// Allocate memory (sizeMB in megabytes)
			memoryAllocation := make([]byte, sizeMB*1024*1024)

			// Write to the memory to ensure it's actually allocated
			for i := 0; i < len(memoryAllocation); i += 4096 {
				memoryAllocation[i] = 1
			}

			// Hold the memory for the specified duration
			time.Sleep(duration)

			// Release memory (Go's GC will handle this when the slice goes out of scope)
			memoryAllocation = nil

			memorySpikeActive.Set(0) // Reset the active gauge to 0
			log.Println("Memory spike completed")
		}()

		w.Write([]byte(fmt.Sprintf("Memory spike triggered: %d MB for %v\n", sizeMB, duration)))
	})

	// Start the server
	log.Println("Starting server on :8080")

	go func() {
		cnt := 0
		for {
			fmt.Printf("Counter = %d\n", cnt)
			time.Sleep(5 * time.Second)
			cnt += 1
		}
	}()
	log.Fatal(http.ListenAndServe(":8080", nil))
}
