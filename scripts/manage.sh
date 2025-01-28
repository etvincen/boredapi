#!/bin/bash

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    source "$PROJECT_ROOT/.env"
else
    echo "Error: .env file not found"
    exit 1
fi

# Set data path
DEV_DATA_PATH=${DEV_DATA_PATH:-"$PROJECT_ROOT/data"}

# Create data directories if they don't exist
mkdir -p "$DEV_DATA_PATH/elasticsearch"

# Get user and group IDs
uid=$(id -u)
gid=$(id -g)

# Set permissions for data directories
sudo chown -R $uid:$gid "$DEV_DATA_PATH/elasticsearch"
sudo chmod 700 "$DEV_DATA_PATH/elasticsearch"

# Function to check if a port is available
check_ports() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        return 1
    fi
    return 0
}

# Function to check service health
check_service_health() {
    local service=$1
    local max_attempts=$2
    local attempt=1
    
    echo "Checking $service health..."
    while [ $attempt -le $max_attempts ]; do
        if docker compose -f "$PROJECT_ROOT/docker/docker-compose.dev.yml" ps | grep -q "$service.*healthy"; then
            echo "$service is healthy"
            return 0
        fi
        echo "Waiting for $service to be healthy (attempt $attempt/$max_attempts)..."
        sleep 5
        attempt=$((attempt + 1))
    done
    
    echo "Error: $service service is not running"
    return 1
}

# Function to clean data directories
clean_data() {
    echo "Cleaning data directories..."
    sudo rm -rf "$DEV_DATA_PATH/elasticsearch"
    mkdir -p "$DEV_DATA_PATH/elasticsearch"
    sudo chown -R $uid:$gid "$DEV_DATA_PATH/elasticsearch"
    sudo chmod 700 "$DEV_DATA_PATH/elasticsearch"
    echo "Data directories cleaned"
}

# Command handling
case "$1" in
    start)
        # Check ports
        check_ports 9200 || { echo "Elasticsearch port (9200) is not available"; exit 1; }
        
        # Start services
        docker compose -f "$PROJECT_ROOT/docker/docker-compose.dev.yml" up -d
        
        # Check service health
        check_service_health "elasticsearch" 12
        ;;
        
    stop)
        docker compose -f "$PROJECT_ROOT/docker/docker-compose.dev.yml" down
        ;;
        
    clean)
        clean_data
        ;;
        
    status)
        docker compose -f "$PROJECT_ROOT/docker/docker-compose.dev.yml" ps
        ;;
        
    logs)
        docker compose -f "$PROJECT_ROOT/docker/docker-compose.dev.yml" logs -f
        ;;
        
    help)
        echo "Usage: $0 {start|stop|clean|status|logs|help}"
        echo
        echo "Commands:"
        echo "1. start  - Start all services"
        echo "2. stop   - Stop all services"
        echo "3. clean  - Clean data directories"
        echo "4. status - Show service status"
        echo "5. logs   - Show service logs"
        echo "6. help   - Show this help message"
        echo
        echo "Services:"
        echo "- Elasticsearch: http://localhost:9200"
        ;;
        
    *)
        echo "Unknown command: $1"
        echo "Run '$0 help' for usage information"
        exit 1
        ;;
esac 