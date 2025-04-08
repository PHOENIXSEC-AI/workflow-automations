#!/bin/bash

# Start LiteLLM Proxy Server
# This script starts the LiteLLM proxy server with our configuration

# Check if the config file exists
if [ ! -f "litellm_config.yaml" ]; then
    echo "Error: litellm_config.yaml not found!"
    exit 1
fi

# Check if litellm is installed
if ! command -v litellm &> /dev/null; then
    echo "Installing litellm..."
    pip install 'litellm[proxy]'
fi

# Set environment variables for API keys (if not already set)
# Uncomment and set these if not using .env file
# export OPENROUTER_API_KEY="your_openrouter_api_key"
# export OPENAI_API_KEY="your_openai_api_key"
# export FIREWORKS_API_KEY="your_fireworks_api_key"

# Start the LiteLLM proxy server
echo "Starting LiteLLM proxy server..."
litellm --config litellm_config.yaml --port 4000 --host 0.0.0.0 --detailed_debug

# Note: To run this in the background, use:
# nohup litellm --config litellm_config.yaml --port 4000 --host 0.0.0.0 --detailed_debug > litellm.log 2>&1 & 