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

# Default values
KIBANA_HOST=${KIBANA_HOST:-"localhost"}
KIBANA_PORT=${KIBANA_PORT:-"5601"}
KIBANA_USER=${KIBANA_USER:-"elastic"}
KIBANA_PASSWORD=${KIBANA_PASSWORD:-"changeme"}

# Function to check if Kibana is ready
wait_for_kibana() {
    echo "Waiting for Kibana to be ready..."
    while ! curl -s "http://$KIBANA_HOST:$KIBANA_PORT/api/status" > /dev/null; do
        sleep 5
    done
    echo "Kibana is ready!"
}

# Function to import dashboards
import_dashboards() {
    local dashboard_file="$PROJECT_ROOT/kibana/dashboards/content_analysis.ndjson"
    
    if [ ! -f "$dashboard_file" ]; then
        echo "Error: Dashboard file not found at $dashboard_file"
        exit 1
    }
    
    echo "Importing Kibana dashboards..."
    
    # Import using Kibana API
    curl -X POST "http://$KIBANA_HOST:$KIBANA_PORT/api/saved_objects/_import" \
        -H "kbn-xsrf: true" \
        -H "Content-Type: multipart/form-data" \
        -F "file=@$dashboard_file" \
        -u "$KIBANA_USER:$KIBANA_PASSWORD"
        
    if [ $? -eq 0 ]; then
        echo "Successfully imported dashboards!"
        echo "You can now access them at:"
        echo "http://$KIBANA_HOST:$KIBANA_PORT/app/dashboards"
    else
        echo "Error importing dashboards"
        exit 1
    fi
}

# Main execution
echo "Setting up Kibana dashboards..."

# Wait for Kibana to be ready
wait_for_kibana

# Import dashboards
import_dashboards

# Print setup instructions
echo """
Setup complete! Here's what was created:

1. Content Overview Dashboard
   - Total pages count
   - Content length distribution
   - Sections per page distribution

2. Image Analysis Dashboard
   - Images per page distribution
   - Missing alt text analysis

3. Link Analysis Dashboard
   - Internal vs external link distribution
   - Most linked pages

To view the dashboards:
1. Open Kibana at http://$KIBANA_HOST:$KIBANA_PORT
2. Go to Dashboard section
3. Select one of the imported dashboards

Note: Make sure you have indexed some data first using:
$ python -m src.cli.ingest_data
""" 