#!/bin/bash

# Function to wait for a service
wait_for_service() {
    local host=$1
    local port=$2
    local service=$3
    
    echo "Waiting for $service to be ready..."
    while ! nc -z $host $port; do
        sleep 1
    done
    echo "$service is ready!"
}

if [ "$WAIT_FOR_ES" = "true" ]; then
    wait_for_service $ELASTICSEARCH_HOST 9200 "Elasticsearch"
fi

# Run the application based on the command
case "$1" in
    "api")
        exec uvicorn src.api:app --host 0.0.0.0 --port 8000
        ;;
    "crawler")
        exec python -m src.cli.crawler_cli
        ;;
    *)
        exec "$@"
        ;;
esac 