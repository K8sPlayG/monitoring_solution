FROM python:3.9-slim

WORKDIR /app

# Install Python dependencies (for Kubernetes API client)
RUN pip install kubernetes

# Copy log collector script
COPY log-collector.py /log-collector.py

ENTRYPOINT ["python3", "-u", "/log-collector.py"]
