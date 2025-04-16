
helm template blah . -f example_custom_values.yaml


helm install -f example_custom_values.yaml test-monitor .

helm uninstall test-monitor

k port-forward service/golang-app-svc 8080:8080 -n rob-monitor
