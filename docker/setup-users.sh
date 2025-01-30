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

# Step 1: Create role with full privileges
echo "Creating custom_kibana_admin role..."
curl -X PUT -u elastic:elastic123 \
    "http://localhost:9200/_security/role/custom_kibana_admin" \
    -H "Content-Type: application/json" \
    -d '{
      "cluster": ["all"],
      "indices": [{"names": ["*"], "privileges": ["all"]}],
      "applications": [{"application": "kibana-.kibana", "privileges": ["all"], "resources": ["*"]}]
    }'

# Step 2: Create service account (testing different endpoint)
echo "Creating service account..."
curl -X PUT -u elastic:elastic123 \
    "http://localhost:9200/_security/service_account/elastic/kibana" \
    -H "Content-Type: application/json" \
    -d '{
      "roles": ["custom_kibana_admin"]
    }'

# Step 3: Create token (only if previous steps succeeded)
if [ $? -eq 0 ]; then
    echo "Creating service account token..."
    TOKEN_RESPONSE=$(curl -s -X POST -u elastic:elastic123 \
        'http://localhost:9200/_security/service/elastic/kibana/credential/token/kibana-token')
    
    echo "Token response: $TOKEN_RESPONSE"
    
    TOKEN_VALUE=$(echo "$TOKEN_RESPONSE" | grep -o '"value":"[^"]*"' | cut -d'"' -f4)
    [ -z "$TOKEN_VALUE" ] && { echo "Token creation failed: $TOKEN_RESPONSE"; exit 1; }
    
    echo "$TOKEN_VALUE" > /tokens/kibana_token
    echo "Service account token created successfully"
fi
