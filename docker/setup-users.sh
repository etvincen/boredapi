#!/bin/bash

set -e  # Exit on error
set -x  # Enable debug mode

echo "Starting setup script..."

# Wait for Elasticsearch to be ready
echo "Waiting for Elasticsearch to be ready..."
until curl -s -u elastic:elastic123 http://localhost:9200/_cluster/health | grep -q '"status":"green"\|"status":"yellow"'; do
    echo "Waiting for Elasticsearch cluster to be healthy..."
    sleep 1
done
echo "Elasticsearch is ready"

# Set kibana_system user password
echo "Setting kibana_system user password..."
curl -X POST -u elastic:elastic123 \
    "http://localhost:9200/_security/user/kibana_system/_password" \
    -H "Content-Type: application/json" \
    -d '{"password": "kibana123"}'


# Verify kibana_system user and roles
echo "Verifying kibana_system user..."
curl -s -u elastic:elastic123 \
    "http://localhost:9200/_security/user/kibana_system" | grep -q "kibana_system" && \
    echo "Kibana system user verified"

echo "Kibana system user password set successfully"

# Get detailed info about kibana_system user
echo "Getting kibana_system user details..."
curl -s -u elastic:elastic123 \
    "http://localhost:9200/_security/user/kibana_system?pretty"

# Test specific endpoint access
echo "Testing nodes endpoint access..."
curl -s -u kibana_system:kibana123 \
    "http://localhost:9200/_nodes?filter_path=nodes.*.version" || echo "Failed to access nodes endpoint"
