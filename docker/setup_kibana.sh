#!/bin/bash

set -e  # Exit on error

function log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

function wait_for_kibana() {
    log "Waiting for Kibana to be ready..."
    sleep 30  # Initial wait for Kibana to fully start
    
    local max_attempts=12
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -I "http://localhost:5601/api/status" | grep -q "200 OK"; then
            log "Kibana is ready"
            return 0
        fi
        log "Waiting for Kibana... Attempt $attempt/$max_attempts"
        sleep 5
        attempt=$((attempt + 1))
    done
    
    log "ERROR: Kibana failed to start after $max_attempts attempts"
    return 1
}

function create_data_view() {
    log "Creating data view..."
    
    default_id="dv_content_id"
    # First, try to delete existing data view
    curl -X DELETE \
        "http://localhost:5601/api/data_views/data_view/${default_id}" \
        -H "kbn-xsrf: true" \
        -u elastic:elastic123
    
    # Small pause to ensure deletion is processed
    sleep 2
    
    # Create new data view with proper registration
    response=$(curl -s -X POST \
        "http://localhost:5601/api/data_views/data_view" \
        -H "kbn-xsrf: true" \
        -H "Content-Type: application/json" \
        -u elastic:elastic123 \
        -d "{
            \"data_view\": {
                \"title\": \"roc_eclerc_content\",
                \"name\": \"Roc Eclerc Content\",
                \"id\": \"${default_id}\",
                \"type\": \"data_view\",
                \"timeFieldName\": \"\",
                \"fields\": {},
                \"sourceFilters\": [],
                \"fieldFormats\": {},
                \"runtimeFieldMap\": {}
            }
        }" \
        --write-out "\n%{http_code}")
    
    http_code=$(echo "$response" | tail -n1)
    response_body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" -eq 200 ]; then
        log "Data view created successfully"
    else
        log "Data view creation failed with code $http_code"
        log "Response: $response_body"
        return 1
    fi
}

function import_dashboard() {
    [ ! -r "/dashboards/roc_eclerc_dashboard.ndjson" ] && return 1
    
    log "Importing dashboard..."
    response=$(curl -s -X POST \
        "http://localhost:5601/api/saved_objects/_import?overwrite=true" \
        -H "kbn-xsrf: true" \
        -u elastic:elastic123 \
        -F "file=@/dashboards/roc_eclerc_dashboard.ndjson" \
        --write-out "\n%{http_code}")
    
    http_code=$(echo "$response" | tail -n1)
    response_body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" -eq 200 ]; then
        log "Dashboard import successful"
    else
        log "Dashboard import failed with code $http_code"
        log "Response: $response_body"
        return 1
    fi
}

# Main execution
if wait_for_kibana; then
    create_data_view && import_dashboard
else
    log "Failed to setup Kibana"
    exit 1
fi