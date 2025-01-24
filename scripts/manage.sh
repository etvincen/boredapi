#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Environment selection
ENV=${ENV:-dev}  # Default to dev environment if not set
DEV_DATA_PATH=${DEV_DATA_PATH:-"$PROJECT_ROOT/data"}  # Default data path for development

# Function to check if .env file exists
check_env_file() {
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        echo "Error: .env file not found!"
        echo "Please create a .env file from .env.example"
        exit 1
    fi
}

# Function to initialize development data directories
init_dev_data() {
    if [ "$ENV" = "dev" ]; then
        echo "Initializing development data directories..."
        mkdir -p "$DEV_DATA_PATH/postgres"
        mkdir -p "$DEV_DATA_PATH/elasticsearch"
        
        # Get current user and group ID
        local uid=$(id -u)
        local gid=$(id -g)
        
        # Set permissions for PostgreSQL
        sudo chown -R $uid:$gid "$DEV_DATA_PATH/postgres"
        chmod 700 "$DEV_DATA_PATH/postgres"
        
        # Set permissions for Elasticsearch
        sudo chown -R $uid:$gid "$DEV_DATA_PATH/elasticsearch"
        chmod 755 "$DEV_DATA_PATH/elasticsearch"
        
        echo "Development data will be stored in: $DEV_DATA_PATH"
        echo "Permissions set for user $uid:$gid"
    fi
}

# Function to clean development data
clean_dev_data() {
    if [ "$ENV" = "dev" ]; then
        echo "Warning: This will delete all development data in $DEV_DATA_PATH"
        read -p "Are you sure? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "Cleaning development data..."
            rm -rf "$DEV_DATA_PATH/postgres"
            rm -rf "$DEV_DATA_PATH/elasticsearch"
            echo "Development data cleaned"
        fi
    else
        echo "Clean data only available in development environment"
    fi
}

# Function to run tests
run_tests() {
    docker build -t web-scraper-test -f "$PROJECT_ROOT/docker/Dockerfile.test" "$PROJECT_ROOT"
    docker run --rm web-scraper-test
}

# Function to check if ports are available
check_ports() {
    local port=$1
    if lsof -i ":$port" >/dev/null 2>&1; then
        echo "Error: Port $port is already in use"
        echo "Please ensure no other services are using this port"
        echo "You can check what's using it with: lsof -i :$port"
        return 1
    fi
    return 0
}

# Function to start environment
start_env() {
    local compose_file="docker/docker-compose.${ENV}.yml"
    
    # Check required ports
    echo "Checking if required ports are available..."
    check_ports 5432 || { echo "PostgreSQL port (5432) is not available"; exit 1; }
    check_ports 9200 || { echo "Elasticsearch port (9200) is not available"; exit 1; }
    
    if [ "$ENV" = "dev" ]; then
        init_dev_data
    fi
    echo "Starting $ENV environment..."
    docker compose -f "$PROJECT_ROOT/$compose_file" up -d
}

# Function to stop environment
stop_env() {
    local compose_file="docker/docker-compose.${ENV}.yml"
    echo "Stopping $ENV environment..."
    docker compose -f "$PROJECT_ROOT/$compose_file" down
}

# Function to show logs
show_logs() {
    local compose_file="docker/docker-compose.${ENV}.yml"
    docker compose -f "$PROJECT_ROOT/$compose_file" logs -f
}

# Add this function
check_services() {
    echo "Checking if required services are running..."
    local compose_file="docker/docker-compose.${ENV}.yml"
    
    if ! docker compose -f "$PROJECT_ROOT/$compose_file" ps | grep -q "elasticsearch.*running"; then
        echo "Error: Elasticsearch service is not running"
        echo "Please start services first with: $0 start"
        exit 1
    fi
    
    if ! docker compose -f "$PROJECT_ROOT/$compose_file" ps | grep -q "db.*running"; then
        echo "Error: PostgreSQL service is not running"
        echo "Please start services first with: $0 start"
        exit 1
    fi
}

run_crawler() {
    if [ "$ENV" = "dev" ]; then
        echo "Running crawler in development mode..."
        poetry run python -m src.cli.crawler_cli
    else
        echo "Running crawler in production mode..."
        docker compose -f "$PROJECT_ROOT/docker/docker-compose.prod.yml" exec crawler python -m src.cli.crawler_cli
    fi
}

run_ingestion() {
    if [ "$ENV" = "dev" ]; then
        echo "Running ingestion in development mode..."
        poetry run python -m src.cli.ingest_data
    else
        echo "Running ingestion in production mode..."
        docker compose -f "$PROJECT_ROOT/docker/docker-compose.prod.yml" exec crawler python -m src.cli.ingest_data
    fi
}

# Main script
case "$1" in
    "test")
        run_tests
        ;;
    "start")
        check_env_file
        start_env
        ;;
    "stop")
        stop_env
        ;;
    "logs")
        show_logs
        ;;
    "clean-data")
        clean_dev_data
        ;;
    "crawler")
        check_env_file
        check_services
        run_crawler
        ;;
    "ingest")
        check_env_file
        check_services
        
        echo "Starting data ingestion process in $ENV environment..."
        echo "This will:"
        echo "1. Find the latest crawl results in crawl_results/"
        echo "2. Store documents in Elasticsearch"
        echo "3. Record metadata in PostgreSQL"
        echo ""
        
        if run_ingestion; then
            echo "Ingestion completed successfully!"
            echo "You can verify the data with:"
            if [ "$ENV" = "dev" ]; then
                echo "- Elasticsearch: curl http://localhost:9200/content/_count"
                echo "- PostgreSQL: psql -U \$POSTGRES_USER -d \$POSTGRES_DB"
            else
                echo "- Elasticsearch: docker compose exec elasticsearch curl http://localhost:9200/content/_count"
                echo "- PostgreSQL: docker compose exec db psql -U \$POSTGRES_USER -d \$POSTGRES_DB"
            fi
        else
            echo "Error: Ingestion failed. Check logs for details."
            exit 1
        fi
        ;;
    *)
        echo "Usage: ENV={dev|prod} $0 {test|start|stop|logs|crawler|ingest|clean-data}"
        echo "Default environment is 'dev' if ENV is not specified"
        echo ""
        echo "Environment variables:"
        echo "  ENV            - Environment to use (dev|prod)"
        echo "  DEV_DATA_PATH  - Path to store development data (default: ./data)"
        exit 1
        ;;
esac 