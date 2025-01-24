#!/bin/bash

# Start development environment
docker-compose up -d db elasticsearch grafana

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 10

# Run FastAPI development server
poetry run uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
