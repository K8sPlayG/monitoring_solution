import multiprocessing
import time
from kubernetes import client, config, watch
import os
from datetime import datetime, timezone

# Get environment variables
FIFO_PATH = os.getenv("LOG_FIFO_PATH", "test.fifo")
the_namespace = os.getenv("NAMESPACE_TO_MONITOR","default")
the_label_select = 'type='
the_label_select += os.getenv("POD_TYPE_TO_MONITOR", "application")

# Create the FIFO if it doesn't exist
if not os.path.exists(FIFO_PATH):
    os.mkfifo(FIFO_PATH)

# For local testing, use kubeconfig; inside Kubernetes cluster, use incluster config
try:
    # Load Kubernetes configuration
    config.load_incluster_config()
except config.config_exception.ConfigException:
    config.load_kube_config()

v1 = client.CoreV1Api()

# Track active processes
active_processes = {}

'''
podName:test-python-app-other,log: test-pyton-app-other:0 Hello from my Python app!
podName:test-python-app-other,log: test-pyton-app-other:0 another print
podName:test-python-app-other,log: test-pyton-app-other:0   and another another print
podName:test-python-app-other,log: test-pyton-app-other:0 One with multi-line
podName:test-python-app-other,log: The line
podName:test-python-app-other,log: test-pyton-app-other:0 One with multi-line and tab       The line
podName:test-python-app-other,log: test-pyton-app-other:1 Hello from my Python app!
podName:test-python-app-other,log: test-pyton-app-other:1 another print
podName:test-python-app-other,log: test-pyton-app-other:1   and another another print
podName:test-python-app-other,log: test-pyton-app-other:1 One with multi-line
podName:test-python-app-other,log: The line
podName:test-python-app,log: test-pyton-app:8 One with multi-line and tab   The line
podName:test-python-app,log: test-pyton-app:9 Hello from my Python app!
podName:test-python-app,log: test-pyton-app:9 another print
podName:test-python-app,log: test-pyton-app:9   and another another print
podName:test-python-app,log: test-pyton-app:9 One with multi-line
podName:test-python-app,log: The line


timestamp:2025-04-17T22:12:21.679164+00:00,podName:test-python-app,log: another print  and another another print
timestamp:2025-04-17T22:12:21.679313+00:00,podName:test-python-app,log: One with multi-line
timestamp:2025-04-17T22:12:21.679411+00:00,podName:test-python-app,log: The line
timestamp:2025-04-17T22:12:21.679477+00:00,podName:test-python-app,log: One with multi-line and tab    The line
timestamp:2025-04-17T22:12:21.677727+00:00,podName:test-python-app-other,log: a json snippet: {"cnt": 1, "theList": [1, {"hi": "there"}]}      another: {"cnt": 1, "theList": [1, {"hi": "there"}]}
timestamp:2025-04-17T22:12:21.679594+00:00,podName:test-python-app,log: a json snippet: {"cnt": 1, "theList": [1, {"hi": "there"}]}    another: {"cnt": 1, "theList": [1, {"hi": "there"}]}
timestamp:2025-04-17T22:12:26.682773+00:00,podName:test-python-app-other,log: Hello from my Python app!
timestamp:2025-04-17T22:12:26.782793+00:00,podName:test-python-app-other,log: another print  and another another print
timestamp:2025-04-17T22:12:26.782936+00:00,podName:test-python-app-other,log: One with multi-line
timestamp:2025-04-17T22:12:26.783018+00:00,podName:test-python-app-other,log: The line
timestamp:2025-04-17T22:12:26.783094+00:00,podName:test-python-app-other,log: One with multi-line and tab      The line
timestamp:2025-04-17T22:12:26.684163+00:00,podName:test-python-app,log: Hello from my Python app!
timestamp:2025-04-17T22:12:26.784279+00:00,podName:test-python-app,log: another print  and another another print
timestamp:2025-04-17T22:12:26.784586+00:00,podName:test-python-app,log: One with multi-line
timestamp:2025-04-17T22:12:26.784699+00:00,podName:test-python-app,log: The line
timestamp:2025-04-17T22:12:26.784805+00:00,podName:test-python-app,log: One with multi-line and tab    The line



'''
class MultlineLogHandler:
    def __init__(self, outfile):
        self.outfile = outfile
        self.outstandingLog = None

    def logLine(self, podName, msgLine):
        if not msgLine:
            return
        startsWithSpace = msgLine[0].isspace()
        if startsWithSpace:
            self.outstandingLog += msgLine
            #Can't write yet until we get a line with no space at beginning
        else:
            self.flush()
            #Prime up a new message
            timestamp = datetime.now(timezone.utc).isoformat()
            sanitizedMsg = msgLine.replace('\n', ' ')
            logMsg = f'timestamp:{timestamp},podName:{podName},log: ' + \
                    sanitizedMsg
            self.outstandingLog = logMsg
            #NOTE: cannot write this message yet because we don't know
            # if this function will be called later staring with a new line
        if len(self.outstandingLog) > 4096:
            #getting too big, just flush
            self.flush()

    def flush(self):
        if self.outstandingLog:
            self.outfile.write(self.outstandingLog + '\n')
            self.outfile.flush()
            self.outstandingLog = False


def stream_logs(pod_name, namespace):
    """Stream logs for a given pod in a separate process."""
    with open(FIFO_PATH, 'w') as fifo:
        w = watch.Watch()
        logHandler = MultlineLogHandler(fifo)
        print(f"Starting log stream for {pod_name} in {namespace}")

        try:
            for log_line in w.stream(v1.read_namespaced_pod_log, name=pod_name, namespace=namespace):
                print(f"[{pod_name}] {log_line}")
                logHandler.logLine(pod_name, log_line)
        except Exception as e:
            print(f"[{pod_name}] Log stream terminated: {e}")
        finally:
            logHandler.flush()

        # Remove from active processes when it exits
        active_processes.pop(pod_name, None)

def manage_log_streams(namespace, label_selector):
    """Manage log streaming jobs dynamically."""
    global active_processes

    while True:
        pods = v1.list_namespaced_pod(namespace, label_selector=label_selector)
        pod_names = {pod.metadata.name for pod in pods.items}

        # Start new log jobs for pods that don’t have a running process
        for pod_name in pod_names:
            if pod_name not in active_processes:
                print(f"Starting log stream for new pod: {pod_name}")
                p = multiprocessing.Process(target=stream_logs, args=(pod_name, namespace))
                p.start()
                active_processes[pod_name] = p

        # Stop log jobs for pods that no longer exist
        for pod_name in list(active_processes.keys()):
            if pod_name not in pod_names:
                print(f"Stopping log stream for removed pod: {pod_name}")
                active_processes[pod_name].terminate()
                active_processes[pod_name].join()
                del active_processes[pod_name]

        # Restart failed jobs (detect stopped processes)
        for pod_name, process in list(active_processes.items()):
            if not process.is_alive():
                print(f"Restarting log stream for pod: {pod_name}")
                p = multiprocessing.Process(target=stream_logs, args=(pod_name, namespace))
                p.start()
                active_processes[pod_name] = p

        time.sleep(5)  # Poll every 5 seconds

def main():
    manage_log_streams(the_namespace, the_label_select)

if __name__ == "__main__":
    main()

'''

[INPUT]
    Name              tail
    Path              /var/log/pods/*.log
    #TODO: do we need multiline here? Is that redundant
    # given the multiline parser?
    Parser            multiline
    Tag               kube.*

[PARSER]
    Name              multiline
    Format            regex
    #What to change this to do extract the
    # * "timestamp"; and
    # * "podName"
    #fields from messages such as 
    #  "timestamp: 123, podName: myPod, log: someLogMessage
    #Where someLogMessge can be anything Could be json, multiline, etc
    Regex             ^(?<timestamp>[^ ]+) (?<message>.+)
    Skip_Empty_Lines  On

For example if fluent-bit gets two messages like this:
    - timestamp: 123, podName: myPod1, log: blah {"hi": "there"}
    AND
    - timestamp: 123, podName: myPod2, log: some\ntext
I would like it to emit two log messages 
    {"timestamp": 1234, "podName": "myPod1", "log": "{\"hi\": \"there\"}
AND
    {"timestamp": 1234, "podName": "myPod2", "log": "some\ntext"}

[FILTER]
    Name       concat
    Match      *
    Key        timestamp
    Key        podName
    Separator  "\n"
    Adjust     true

[OUTPUT]
    TODO


----
 AI answer

[INPUT]
    Name              tail
    Path              /var/log/application-logs.fifo
    Parser            my_parser  # Use the parser you define below
    Tag               kube.*
    #Don't need this anymore. the log-collector handles the multiline grouping of logs.
    # Multiline         On
    # Parser_Firstline  multiline_pods

[PARSER]
    Name              my_parser
    Format            regex
    Regex             ^timestamp:(?<timestamp>[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:.+-]+),podName:(?<podName>[^,]+),log:(?<log>.+)
    Skip_Empty_Lines  On
# [PARSER]
#     Name              my_parser
#     Format            regex
#     Regex             ^timestamp:(?<timestamp>[0-9]+),podName:(?<podName>[^,]+),log:(?<log>.+)
#     Skip_Empty_Lines  On

#TODO: Do i need this?
# [FILTER]
#     Name       modify
#     Match      kube.*
#     Rename     timestamp @timestamp

[OUTPUT]
    Name          loki
    Match         kube.*
    #TODO: need to replace "logging' with the namespace name
    Host          loki.logging.svc.cluster.local
    Port          3100
    Labels        podName=$podName
    LabelKeys     timestamp,podName

#For debugging
[OUTPUT]
    Name          stdout
    Match         *
    Format        json


---
New way I modified this script to group logs that belong together:

[INPUT]
    Name              tail
    #TODO: this will be the path to the fifo
    Path              /var/log/pods/*.log
    Parser            multiline_pods  # Use the parser you define below
    Tag               kube.*
    Multiline         On
    Parser_Firstline  multiline_pods

[PARSER]
    Name              multiline_pods
    Format            regex
    Regex             ^timestamp: (?<timestamp>[0-9]+), podName: (?<podName>[^,]+), log: (?<log>.+)
    Skip_Empty_Lines  On

[FILTER]
    Name       modify
    Match      kube.*
    Rename     timestamp @timestamp

[OUTPUT]
    #What to put here to send stuff to loki


K8s config
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: logger-sa
  namespace: my-namespace
---

apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: logger-role
  namespace: my-namespace
rules:
  - apiGroups: [""]
    resources:
      - pods
      - pods/log
    verbs: ["get", "list", "watch"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: logger-rolebinding
  namespace: my-namespace
subjects:
  - kind: ServiceAccount
    name: logger-sa
    namespace: my-namespace
roleRef:
  kind: Role
  name: logger-role
  apiGroup: rbac.authorization.k8s.io
---
apiVersion: v1
kind: Pod
metadata:
  name: namespace-logger
  namespace: my-namespace
  labels:
    app: namespace-logger
spec:
  serviceAccountName: logger-sa
  volumes:
    - name: logs-volume
      emptyDir: {}

  initContainers:
    - name: create-fifo
      image: busybox
      command: ["sh", "-c", "mkfifo /var/log/application-logs.fifo"]
      volumeMounts:
        - name: logs-volume
          mountPath: /var/log

  containers:
    - name: log-collector
      image: python:3.9-slim
      command:
        - python3
        - /log-collector.py
      env:
        - name: LOG_FIFO_PATH
          value: "/var/log/application-logs.fifo"
      volumeMounts:
        - name: logs-volume
          mountPath: /var/log

    - name: fluent-bit
      image: fluent/fluent-bit:latest
      args:
        - -i
        - tail
        - -p
        - path=/var/log/application-logs.fifo
        - -o
        - es
        - -p
        - host=elasticsearch-logging.svc.cluster.local
        - -p
        - port=9200
        - -p
        - index=namespace-logs
      volumeMounts:
        - name: logs-volume
          mountPath: /var/log

---

Dockerfile for this pod:

FROM python:3.9-slim

WORKDIR /app

# Install Python dependencies (for Kubernetes API client)
RUN pip install kubernetes

# Copy log collector script
COPY log-collector.py /log-collector.py

ENTRYPOINT ["python3", "-u", "/log-collector.py"]
'''
