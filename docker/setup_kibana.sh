#!/bin/bash

# Maximum number of attempts to wait for Kibana
MAX_ATTEMPTS=60
attempt=0

# Wait for Kibana to be ready
echo "Waiting for Kibana to start..."
until curl -s -I http://localhost:5601/api/status | grep -q "200 OK" || [ $attempt -ge $MAX_ATTEMPTS ]; do
    attempt=$((attempt + 1))
    echo "Waiting for Kibana... Attempt $attempt/$MAX_ATTEMPTS"
    sleep 5
done

if [ $attempt -ge $MAX_ATTEMPTS ]; then
    echo "Timeout waiting for Kibana to start"
    exit 1
fi

echo "Kibana is up and running"

# Wait a bit more to ensure the security system is fully initialized
sleep 10

# Get the service account token
TOKEN=$(cat /usr/share/kibana/tokens/kibana_token)
if [ -z "$TOKEN" ]; then
    echo "Failed to read service account token"
    exit 1
fi

echo "Importing dashboard..."
dashboard_file="/dashboards/content_analysis.ndjson"

if [ ! -f "$dashboard_file" ]; then
    echo "Dashboard file not found at $dashboard_file"
    exit 1
fi

# Import the dashboard using the Kibana API
response=$(curl -s -X POST "http://localhost:5601/api/saved_objects/_import?overwrite=true" \
    -H "kbn-xsrf: true" \
    -H "Authorization: Bearer $TOKEN" \
    --form file=@"$dashboard_file")

if echo "$response" | grep -q "\"success\":true"; then
    echo "Dashboard imported successfully"
    exit 0
else
    echo "Failed to import dashboard"
    echo "Response: $response"
    exit 1
fi 