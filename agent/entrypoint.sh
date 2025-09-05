#!/bin/bash
set -e

CONFIG_PATH="/config.json"

# Required env vars
if [ -z "$DOMAIN" ]; then
  echo "ERROR: DOMAIN environment variable is required" >&2
  exit 1
fi

if [ -z "$AUTH_TOKEN" ]; then
  echo "ERROR: AUTH_TOKEN environment variable is required" >&2
  exit 1
fi

# Validate IS_HTTPS
if [ -z "$IS_HTTPS" ]; then
  IS_HTTPS_VAL=false
else
  if [ "$IS_HTTPS" != "true" ] && [ "$IS_HTTPS" != "false" ]; then
    echo "ERROR: IS_HTTPS must be 'true' or 'false', got '$IS_HTTPS'" >&2
    exit 1
  fi
  IS_HTTPS_VAL=$IS_HTTPS
fi

# Validate LETS_ENCRYPT_EMAIL
if [ "$IS_HTTPS_VAL" = "true" ] && [ -z "$LETS_ENCRYPT_EMAIL" ]; then
  echo "ERROR: LETS_ENCRYPT_EMAIL environment variable is required for HTTPS" >&2
  exit 1
fi

# By default set to test@example.com
if  [ "$IS_HTTPS_VAL" = "true" ] && [ -z "$LETS_ENCRYPT_EMAIL" ]; then
  LETS_ENCRYPT_EMAIL="test@example.com"
fi

cat > "$CONFIG_PATH" <<EOF
{
  "headless": true,
  "domain": "${DOMAIN}",
  "is_https": ${IS_HTTPS_VAL},
  "auth_token": "${AUTH_TOKEN}",
  "base_data_directory": "/data",
  "lets_encrypt_email": "${LETS_ENCRYPT_EMAIL}"
}
EOF

echo "Generated config:"
cat "$CONFIG_PATH"

exec /drift-agent run --config "$CONFIG_PATH"
