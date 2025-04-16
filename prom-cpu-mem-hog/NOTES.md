# Various testing

Test

## First just want to see the metrics as they are exported from the stress-test pod

```
k apply -f prometheus.yaml -f stress-demo.yaml
kubectl port-forward -n monitoring svc/prometheus 9090:9090
```

```
> % curl http://localhost:9090/api/v1/query --data-urlencode 'query=stress_test_cpu_usage_percent{app="stress-demo"}' | jq
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100   407  100   343  100    64  25729   4800 --:--:-- --:--:-- --:--:-- 31307
{
  "status": "success",
  "data": {
    "resultType": "vector",
    "result": [
      {
        "metric": {
          "__name__": "stress_test_cpu_usage_percent",
          "app": "stress-demo",
          "instance": "10.1.1.0:8000",
          "job": "kubernetes-pods",
          "kubernetes_namespace": "monitoring",
          "kubernetes_pod_name": "stress-demo-5d5d9c8bcb-tqfqm",
          "pod_template_hash": "5d5d9c8bcb"
        },
        "value": [
          1744769910.355,
          "99.8"
        ]
      }
    ]
  }
}

curl -s -G http://localhost:9090/api/v1/query \
  --data-urlencode 'query=avg_over_time(stress_test_cpu_usage_percent{app="stress-demo"}[30s])' | jq

```




```

#For linux
#start=$(date -u -d '-10 seconds' +%s)

#For mac
start=$(date -u -v-10S +%s)

end=$(date -u +%s)

curl -s -G http://localhost:9090/api/v1/query_range \
  --data-urlencode "query=stress_test_cpu_usage_percent{app=\"stress-demo\"}" \
  --data-urlencode "start=$start" \
  --data-urlencode "end=$end" \
  --data-urlencode "step=1s" | jq '.data.result[0].values[][1]'

"299.2"
"299.2"
"299.2"
"399.8"
"399.8"
"399.8"
"399.8"
"399.8"
"399.8"
"399.8"
"399.8"
```

## Now incorporating the node-exporter

```
kubectl apply -f node-exporter.yaml
```

```

curl -s -G http://localhost:9090/api/v1/query \
  --data-urlencode 'query={app="node-exporter"}' | jq

```

## Showing active targets

```
-> % curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {scrapePool, health, labels}'

{
  "scrapePool": "kubernetes-pods",
  "health": "up",
  "labels": {
    "app": "stress-demo",
    "instance": "10.1.1.4:8000",
    "job": "kubernetes-pods",
    "kubernetes_namespace": "monitoring",
    "kubernetes_pod_name": "stress-demo-5d5d9c8bcb-wsl6p",
    "pod_template_hash": "5d5d9c8bcb"
  }
}
{
  "scrapePool": "prometheus",
  "health": "up",
  "labels": {
    "instance": "localhost:9090",
    "job": "prometheus"
  }
}
```

## my question to Warp

Can the node-exporter.yaml be configured to just look at the cpu/memory usage in a particular namespace? Or does it do it for the entire node?

Node-exporter is designed to collect system-level metrics from the entire node - it doesn't have namespace awareness because it operates at the host level. It collects metrics like:

•  Total CPU usage
•  Total memory usage
•  Disk I/O
•  Network statistics
•  System load

For namespace-specific container metrics, we need to use:
1. cAdvisor metrics (via kubelet)
2. Kubernetes metrics server
3. Or our own application metrics (like what we did with the stress demo)




* cAdvisor (Container Advisor): This is a resource usage collector embedded in the Kubernetes kubelet. It provides container-level metrics such as CPU, memory, and disk usage.
* Metrics Server and cAdvisor:
The metrics server collects resource metrics directly from cAdvisor via the kubelet.
While cAdvisor provides raw container-level metrics, the metrics server aggregates and standardizes these metrics for API consumption.

However:
from https://github.com/kubernetes-sigs/metrics-server
it says:

  Caution

  Metrics Server is meant only for autoscaling purposes. For example, don't use it to forward metrics to monitoring solutions, or as a source of monitoring solution metrics. In such cases please collect metrics from Kubelet /metrics/resource endpoint directly.



-> % k get --raw /api/v1/nodes/docker-desktop/proxy/metrics/resource | grep stress
container_cpu_usage_seconds_total{container="stress-test",namespace="monitoring",pod="stress-demo-5d5d9c8bcb-wsl6p"} 6765.751112 1744775165350
container_memory_working_set_bytes{container="stress-test",namespace="monitoring",pod="stress-demo-5d5d9c8bcb-wsl6p"} 3.4869248e+07 1744775165350
container_start_time_seconds{container="stress-test",namespace="monitoring",pod="stress-demo-5d5d9c8bcb-wsl6p"} 1.744770516e+09
pod_cpu_usage_seconds_total{namespace="monitoring",pod="stress-demo-5d5d9c8bcb-wsl6p"} 6752.988443 1744775162150
pod_memory_working_set_bytes{namespace="monitoring",pod="stress-demo-5d5d9c8bcb-wsl6p"} 3.5381248e+07 1744775162150


-> % kubectl get --raw /api/v1/nodes/$(kubectl get nodes -o jsonpath='{.items[0].metadata.name}')/proxy/metrics/cadvisor | \
grep -E "container_cpu_(usage|system|user).*stress" | \
awk '{printf "%s = %.2f seconds\n", $1, $2}'
container_cpu_system_seconds_total{container="",id="/kubepods/kubepods/besteffort/pod38296834-0dfd-410a-80da-82e0458a92eb",image="",name="",namespace="monitoring",pod="stress-demo-5d5d9c8bcb-wsl6p"} = 52.54 seconds
container_cpu_usage_seconds_total{container="",cpu="total",id="/kubepods/kubepods/besteffort/pod38296834-0dfd-410a-80da-82e0458a92eb",image="",name="",namespace="monitoring",pod="stress-demo-5d5d9c8bcb-wsl6p"} = 7042.43 seconds
container_cpu_user_seconds_total{container="",id="/kubepods/kubepods/besteffort/pod38296834-0dfd-410a-80da-82e0458a92eb",image="",name="",namespace="monitoring",pod="stress-demo-5d5d9c8bcb-wsl6p"} = 6989.89 seconds
robertmccabe@Roberts-Mac-mini [22:50:00] [~/k8s/K8sPlayG/monitoring/monitoring_solution] [master *]
-> % kubectl get --raw /api/v1/nodes/$(kubectl get nodes -o jsonpath='{.items[0].metadata.name}')/proxy/metrics/cadvisor | \
grep -E "container_memory_(usage_bytes|working_set_bytes|rss).*stress" | \
awk '{printf "%s = %.2f MB\n", $1, $2/1024/1024}'
container_memory_rss{container="",id="/kubepods/kubepods/besteffort/pod38296834-0dfd-410a-80da-82e0458a92eb",image="",name="",namespace="monitoring",pod="stress-demo-5d5d9c8bcb-wsl6p"} = 16.91 MB
container_memory_usage_bytes{container="",id="/kubepods/kubepods/besteffort/pod38296834-0dfd-410a-80da-82e0458a92eb",image="",name="",namespace="monitoring",pod="stress-demo-5d5d9c8bcb-wsl6p"} = 31.41 MB
container_memory_working_set_bytes{container="",id="/kubepods/kubepods/besteffort/pod38296834-0dfd-410a-80da-82e0458a92eb",image="",name="",namespace="monitoring",pod="stress-demo-5d5d9c8bcb-wsl6p"} = 31.36 MB

My Question to Copilot
how does that relate to the /api/v1/nodes/docker-desktop/proxy/metrics/cadvisor endpoint? There seems to be more information there

Its answer:

Great observation! The /metrics/resource and /metrics/cadvisor endpoints indeed serve related but distinct purposes, with /metrics/cadvisor often providing more detailed and lower-level metrics. Let me explain:
/metrics/resource
Purpose: This endpoint focuses on high-level resource usage metrics (CPU, memory, etc.) at the pod or container level.
Data Source: It aggregates resource metrics from cAdvisor and kubelet-internal APIs.
Scope: It provides data optimized for tools like the Kubernetes Metrics Server, which supports use cases like autoscaling.
Simplification: Filters out some of the fine-grained metrics to reduce overhead and focus on what Kubernetes typically needs for autoscaling or basic cluster monitoring.
/metrics/cadvisor
Purpose: This endpoint exposes raw, granular metrics collected directly by cAdvisor, embedded in the kubelet.
Data Source: cAdvisor monitors individual containers running on the node, collecting detailed resource metrics.
Scope: Provides much more detailed information, including:
Per-container CPU and memory usage
Disk I/O and filesystem stats
Network metrics
Various other metrics like container uptime, throttling stats, etc.
Use Case: Ideal for in-depth monitoring and debugging at the container level. If you're using Prometheus, the data from /metrics/cadvisor is often preferred for detailed performance analysis.
How They Relate
Shared Data Source: Both endpoints source metrics from cAdvisor, but /metrics/resource provides a subset of these metrics in a simplified form.
Different Consumers:
/metrics/resource is tailored for Kubernetes components (e.g., Metrics Server).
/metrics/cadvisor is meant for external monitoring tools like Prometheus that require more detail.
Should You Use /metrics/cadvisor?
If you're running Prometheus and want to track detailed per-container metrics for monitoring, the /metrics/cadvisor endpoint is the better choice. It has richer data for use cases like performance tuning or debugging.
Let me know if you'd like to set up Prometheus to scrape either of these endpoints or want to dive deeper into the data differences!
