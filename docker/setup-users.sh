#!/bin/bash

# Wait for Elasticsearch to be ready
until curl -s -u elastic:elastic123 http://localhost:9200 >/dev/null; do
    echo "Waiting for Elasticsearch..."
    sleep 2
done

# Set password for kibana_system user
curl -X POST -u elastic:elastic123 'http://localhost:9200/_security/user/kibana_system/_password' -H 'Content-Type: application/json' -d '{
  "password": "kibana123"
}'

echo "Setup completed successfully" 