#!/bin/bash

# Script to generate a virtual key for the LiteLLM proxy

# Make sure the proxy is running before using this script
echo "Generating a new virtual key for the LiteLLM proxy..."

# Get master key from environment variable or use default if not set
MASTER_KEY=${LITELLM_MASTER_KEY:-"sk-1234"}
PROXY_HOST=${LITELLM_PROXY_HOST:-"http://localhost:4000"}
MODEL=${LITELLM_MODEL:-"deepseek/deepseek-chat"}
USER_METADATA=${LITELLM_USER_METADATA:-"workflow-automation"}

# Generate a key with access to the specified model
RESPONSE=$(curl -s -X POST "$PROXY_HOST/key/generate" \
  -H "Authorization: Bearer $MASTER_KEY" \
  -H 'Content-Type: application/json' \
  -d "{
    \"models\": [\"$MODEL\"],
    \"metadata\": {\"user\": \"$USER_METADATA\"}
  }")

# Extract the key from the response
KEY=$(echo $RESPONSE | grep -o '"key":"[^"]*' | cut -d'"' -f4)

if [ -n "$KEY" ]; then
  echo "Successfully generated new key: $KEY"
  
  # Get environment variables for .env file or use defaults
  OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-"your_openrouter_key_here"}
  LITELLM_PROXY_BASE_URL=${LITELLM_PROXY_BASE_URL:-"http://litellm-proxy:4000"}
  LITELLM_SALT_KEY=${LITELLM_SALT_KEY:-"sk-salt-key-required"}
  DATABASE_URL=${DATABASE_URL:-"postgresql://prefect:prefect@postgres:5432/litellm"}
  
  # Create or update .env file with the new key
  if [ -f .env ]; then
    # Update existing .env file
    sed -i '/LITELLM_PROXY_API_KEY=/d' .env
    echo "LITELLM_PROXY_API_KEY=$KEY" >> .env
    echo "Updated .env file with the new key"
  else
    # Create new .env file
    echo "OPENROUTER_API_KEY=$OPENROUTER_API_KEY" > .env
    echo "LITELLM_PROXY_BASE_URL=$LITELLM_PROXY_BASE_URL" >> .env
    echo "LITELLM_PROXY_API_KEY=$KEY" >> .env
    echo "LITELLM_MASTER_KEY=$MASTER_KEY" >> .env
    echo "LITELLM_SALT_KEY=$LITELLM_SALT_KEY" >> .env
    echo "DATABASE_URL=$DATABASE_URL" >> .env
    echo "Created new .env file with the new key"
  fi
else
  echo "Failed to generate key. Response: $RESPONSE"
  echo "Make sure the LiteLLM proxy is running."