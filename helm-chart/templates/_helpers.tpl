{{- define "pod.image" -}}
{{- if .pod.container_registry | default .pod_defaults.container_registry -}}
{{ .pod.container_registry | default .pod_defaults.container_registry }}/{{ .pod.image }}
{{- else -}}
{{ .pod.image }}
{{- end -}}{{ if .pod.image_tag | default .pod_defaults.image_tag }}:{{ .pod.image_tag | default .pod_defaults.image_tag }}{{ end }}
{{- end }}

{{- define "pod.spec" -}}
apiVersion: v1
kind: Pod
metadata:
  name: {{ .pod.name }}
  namespace: {{ .values.namespace }}
  labels:
    app: {{ .pod.name }}
spec:
  terminationGracePeriodSeconds: 0
  containers:
  - name: {{ .pod.name }}
    image: {{ include "pod.image" (dict "pod" .pod "pod_defaults" .values.pod_defaults) }}
    imagePullPolicy: {{ .pod.pullPolicy | default .values.pod_defaults.pullPolicy }}
    {{- if gt (int (.pod.prometheusScrapePort | default .values.pod_defaults.prometheusScrapePort)) 0 }}
    ports:
    - containerPort: {{ .pod.prometheusScrapePort | default .values.pod_defaults.prometheusScrapePort }}
    {{- end }}
{{- if gt (int (.pod.prometheusScrapePort | default .values.pod_defaults.prometheusScrapePort)) 0 }}
---
apiVersion: v1
kind: Service
metadata:
  name: {{ .pod.name }}-svc
  namespace: {{ .values.namespace }}
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "{{ .pod.prometheusScrapePort | default .values.pod_defaults.prometheusScrapePort }}"
    prometheus.io/path: "/metrics"
  labels:
    app: {{ .pod.name }}
spec:
  selector:
    app: {{ .pod.name }}
  ports:
  - protocol: TCP
    port: {{ .pod.prometheusScrapePort | default .values.pod_defaults.prometheusScrapePort }}
    targetPort: {{ .pod.prometheusScrapePort | default .values.pod_defaults.prometheusScrapePort }}
{{- end }}
{{- end }}
