#!/bin/bash
# ===================================================================
# Workflow Automation - Docker Debug Build Script
# ===================================================================
# This script builds the Docker image with debugging enabled

set -e

echo "Building Docker image with debugging..."
docker build --no-cache --progress=plain . 2>&1 | tee docker-build.log

echo ""
echo "Build complete. Check docker-build.log for detailed output."
echo "If the build failed, you can find the error messages in the log." 