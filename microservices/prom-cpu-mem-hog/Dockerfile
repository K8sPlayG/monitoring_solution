FROM python:3.12-alpine

RUN apk update && \
	apk add --no-cache \
		stress-ng \
		build-base \
		gcc \
		linux-headers && \
	pip install --no-cache-dir psutil

WORKDIR /app

COPY scripts/* .

CMD ["/app/start.sh"]

