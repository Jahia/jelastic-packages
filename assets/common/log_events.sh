#!/usr/bin/env bash

source /etc/profile

host_name=$(awk '/^hostname:/ {print $2}' /etc/datadog-agent/datadog.yaml)

curl -s -X POST "https://api.${DD_SITE}/api/v1/events?api_key=${DATADOGAPIKEY}" \
-H "Content-Type: application/json" \
-d @- << EOF
{
  "alert_type": "info",
  "host": "$host_name",
  "priority": "normal",
  "tags": [
    "environment:$envName"
  ],
  "text": "$2",
  "title": "$1"
}
EOF
