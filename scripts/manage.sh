#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Function to check if .env file exists
check_env_file() {
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        echo "Error: .env file not found!"
        echo "Please create a .env file from .env.example"
        exit 1
    fi
}

# Function to run tests
run_tests() {
    docker build -t web-scraper-test -f "$PROJECT_ROOT/docker/Dockerfile.test" "$PROJECT_ROOT"
    docker run --rm web-scraper-test
}

# Function to start production environment
start_prod() {
    docker-compose -f "$PROJECT_ROOT/docker/docker-compose.prod.yml" up -d
}

# Function to stop production environment
stop_prod() {
    docker-compose -f "$PROJECT_ROOT/docker/docker-compose.prod.yml" down
}

# Function to show logs
show_logs() {
    docker-compose -f "$PROJECT_ROOT/docker/docker-compose.prod.yml" logs -f
}

# Main script
case "$1" in
    "test")
        run_tests
        ;;
    "start")
        check_env_file
        start_prod
        ;;
    "stop")
        stop_prod
        ;;
    "logs")
        show_logs
        ;;
    *)
        echo "Usage: $0 {test|start|stop|logs}"
        exit 1
        ;;
esac 