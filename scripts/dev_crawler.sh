#!/bin/bash

# Ensure we're in the project root
cd "$(dirname "$0")/.."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Please create a .env file with required configuration."
    exit 1
fi

# Load environment variables
set -a
source .env
set +a

# Ensure the virtual environment is active
if [ -z "$VIRTUAL_ENV" ]; then
    if [ ! -d ".venv" ]; then
        echo "Creating virtual environment..."
        poetry install
    fi
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Install Playwright browsers if not already installed
if ! playwright install chromium --with-deps >/dev/null 2>&1; then
    echo "Installing Playwright browsers..."
    playwright install chromium --with-deps
fi

# Create logs directory
mkdir -p logs

# Run the crawler with logging
echo "Starting crawler..."
poetry run python -m src.cli.crawler_cli 2>&1 | tee "logs/crawler_$(date +%Y%m%d_%H%M%S).log" 