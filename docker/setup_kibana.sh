#!/bin/bash

set -e  # Exit on error

function log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

function wait_for_kibana() {
    log "Waiting for Kibana to be ready..."
    local max_attempts=12  # Increased timeout for proper initialization
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -I -u elastic:elastic123 "http://localhost:5601/api/status" | grep -q "200 OK"; then
            log "Kibana is ready"
            return 0
        fi
        log "Waiting for Kibana... Attempt $attempt/$max_attempts"
        sleep 10  # Increased sleep time
        attempt=$((attempt + 1))
    done
    
    log "ERROR: Kibana failed to start after $max_attempts attempts"
    return 1
}

function import_dashboard() {
    [ ! -r "/dashboards/content_analysis.ndjson" ] && return 1
    
    log "Importing dashboard..."
    curl -s -X POST "http://localhost:5601/api/saved_objects/_import?overwrite=true" \
        -H "kbn-xsrf: true" \
        -u elastic:elastic123 \
        --form file=@"/dashboards/content_analysis.ndjson"
    
    log "Dashboard import completed"
}

# Wait for Kibana to be ready and import dashboard
wait_for_kibana && import_dashboard 