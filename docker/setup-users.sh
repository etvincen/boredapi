#!/bin/bash

set -x  # Enable debug mode

echo "Starting setup script..."

# Ensure tokens directory exists and has correct permissions
echo "Creating tokens directory..."
mkdir -p /tokens
ls -la /
ls -la /tokens
chown -R 1000:1000 /tokens
chmod 777 /tokens
echo "Directory permissions set"

# Wait for Elasticsearch to be ready
echo "Waiting for Elasticsearch to be ready..."
until curl -s -u elastic:elastic123 http://localhost:9200 >/dev/null; do
    echo "Waiting for Elasticsearch..."
    sleep 2
done
echo "Elasticsearch is ready"

echo "Creating service account token for Kibana..."
TOKEN_RESPONSE=$(curl -s -X POST -u elastic:elastic123 \
    'http://localhost:9200/_security/service/elastic/kibana/credential/token/kibana-token' \
    -H 'Content-Type: application/json')
echo "Token response: $TOKEN_RESPONSE"

# Extract the token value
TOKEN_VALUE=$(echo "$TOKEN_RESPONSE" | grep -o '"value":"[^"]*"' | cut -d'"' -f4)

if [ -z "$TOKEN_VALUE" ]; then
    echo "Failed to create service account token"
    exit 1
fi

# Write token to file
echo "Writing token to file..."
echo "$TOKEN_VALUE" > /tokens/kibana_token
chmod 644 /tokens/kibana_token
ls -la /tokens
echo "Service account token created successfully"