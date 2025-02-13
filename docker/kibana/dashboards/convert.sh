#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to script directory
cd "$SCRIPT_DIR"

if [ "$1" = "to-ndjson" ]; then
    # Convert pretty JSON to NDJSON
    echo "Converting debug.json to ndjson..."
    if ! jq -c '.objects[]' "$SCRIPT_DIR/roc_eclerc_dashboard.debug.json" > "$SCRIPT_DIR/roc_eclerc_dashboard.ndjson" 2>/dev/null; then
        echo "Warning: No objects found in debug.json or file is empty"
        echo "" > "$SCRIPT_DIR/roc_eclerc_dashboard.ndjson"
    fi
    echo "Done!"
elif [ "$1" = "to-json" ]; then
    # Convert NDJSON to pretty JSON for debugging
    echo "Converting ndjson to debug.json..."
    echo '{
      "objects": [' > "$SCRIPT_DIR/roc_eclerc_dashboard.debug.json"

    # Add each line from NDJSON with proper formatting
    while IFS= read -r line; do
        # Skip empty lines
        [ -z "$line" ] && continue
        # Add the line with proper indentation
        echo "    $line," >> "$SCRIPT_DIR/roc_eclerc_dashboard.debug.json"
    done < "$SCRIPT_DIR/roc_eclerc_dashboard.ndjson"

    # Remove the last comma and close the JSON
    sed -i '$ s/,$//' "$SCRIPT_DIR/roc_eclerc_dashboard.debug.json"
    echo '  ]
}' >> "$SCRIPT_DIR/roc_eclerc_dashboard.debug.json"

    # Pretty print the final JSON
    jq '.' "$SCRIPT_DIR/roc_eclerc_dashboard.debug.json" > "$SCRIPT_DIR/temp" && mv "$SCRIPT_DIR/temp" "$SCRIPT_DIR/roc_eclerc_dashboard.debug.json"
    echo "NDJSON converted to debug.json successfully!"
else
    echo "Usage: $0 [to-ndjson|to-json]"
    echo "  to-ndjson: Convert debug.json to ndjson format"
    echo "  to-json: Convert ndjson to debug.json format"
    exit 1
fi 