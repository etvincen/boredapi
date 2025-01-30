#!/bin/bash

set -e  # Exit on error

function log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

function wait_for_token() {
    log "Waiting for Kibana token file..."
    until [ -r /tokens/kibana_token ]; do
        log "Token file not yet available, waiting..."
        sleep 2
    done
    log "Token file found"
}

function verify_token() {
    TOKEN=$(cat /tokens/kibana_token)
    [ -z "$TOKEN" ] && return 1
    
    # Check authentication and role
    RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" \
        "http://elasticsearch:9200/_security/_authenticate")
    
    echo "Token authentication response: $RESPONSE"
    echo "$RESPONSE" | grep -q "custom_kibana_admin"
}

# | grep -q "elastic/kibana" && \
# log "$RESPONSE" | grep -q "custom_kibana_admin"

function wait_for_kibana() {
    log "Waiting for Kibana to be ready..."
    local max_attempts=4
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

function import_dashboard() {
    TOKEN=$(cat /tokens/kibana_token)
    [ ! -r "/dashboards/content_analysis.ndjson" ] && return 1
    
    curl -s -X POST "http://localhost:5601/api/saved_objects/_import?overwrite=true" \
        -H "kbn-xsrf: true" \
        -H "Authorization: Bearer $TOKEN" \
        --form file=@"/dashboards/content_analysis.ndjson"
}

case "$1" in
    "wait-for-token")
        until [ -r /tokens/kibana_token ] && verify_token; do sleep 1; done
        (import_dashboard &)
        ;;
    "verify")
        verify_token
        ;;
    *)
        echo "Usage: $0 {wait-for-token|verify}"
        exit 1
        ;;
esac 