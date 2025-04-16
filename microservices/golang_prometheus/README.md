# Test

```

```

## Prometheus Installation with Helm

This section describes how to install Prometheus in your Kubernetes cluster using Helm.

### Prerequisites

- Kubernetes cluster running
- Helm installed on your local machine
- `kubectl` configured to communicate with your cluster

### Installation Steps

1. Add the Prometheus community Helm repository:
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
```

2. Create a dedicated namespace for monitoring:
```bash
kubectl create namespace monitoring
```

3. Install the kube-prometheus-stack Helm chart:
```bash
helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring \
  --set prometheus-node-exporter.enabled=false
```

### Current Installation Details

- Release name: `prometheus`
- Namespace: `monitoring`
- Chart version: `kube-prometheus-stack-70.3.0`
- Prometheus app version: `v0.81.0`

### What's Included

The kube-prometheus-stack includes:
- Prometheus (time-series database for metrics)
- Grafana (visualization and dashboarding)
- AlertManager (handling alerts)
- Node Exporter (hardware and OS metrics)
- kube-state-metrics (Kubernetes object metrics)
- Various default ServiceMonitors and PrometheusRules

### Useful Commands

```bash
# To check status of the Prometheus installation
helm list -n monitoring

# To upgrade to the latest version
helm upgrade prometheus prometheus-community/kube-prometheus-stack -n monitoring

# To uninstall
helm uninstall prometheus -n monitoring

# To port-forward to Prometheus UI
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090

# To port-forward to Grafana UI (default credentials: admin/prom-operator)
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
```

### Configuring Services for Prometheus Monitoring

To monitor your application with Prometheus, create a ServiceMonitor:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: your-app-name
  labels:
    release: prometheus  # Important: This enables discovery
spec:
  selector:
    matchLabels:
      app: your-app-label  # Must match your service labels
  endpoints:
  - port: metrics         # Must match the name of the port in your service
    path: /metrics
    interval: 15s
```

Remember to add the same labels to your Service that the ServiceMonitor is selecting:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: your-service-name
  labels:
    app: your-app-label   # This must match the ServiceMonitor selector
```



### Example Prometheus rules

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: example-prometheus-rule
  namespace: monitoring
spec:
  groups:
  - name: example.rules
    rules:
    - alert: HighCPUUsage
      expr: avg(rate(process_cpu_seconds_total{job="example-app"}[5m])) > 0.9
      for: 2m
      labels:
        severity: warning
      annotations:
        summary: "High CPU usage detected"
        description: "CPU usage for {{ $labels.job }} is above 90% for 2 minutes. Value: {{ $value }}"
    - alert: InstanceDown
      expr: up{job="example-app"} == 0
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "Instance is down"
        description: "Instance {{ $labels.instance }} is down for 5 minutes."
```



