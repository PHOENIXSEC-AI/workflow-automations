#!/bin/bash
set -e

echo "Installing Node.js..."
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh | bash

# Source nvm directly instead of sourcing .bashrc
export NVM_DIR="/usr/local/share/nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

# Now nvm command should be available
nvm install --lts

# Install Repomix tool for local dev
echo "Installing dependencies..."
npm install -g repomix

# Install project package
echo "Installing project..."
pip install --upgrade pip
pip install uv

# Create a virtual environment first
echo "Creating virtual environment..."
uv venv

# Activate the virtual environment
source .venv/bin/activate

uv pip install --no-cache -e .

# Setup prefect server ENV vars
echo "Setting up prefect..."
prefect config set PREFECT_API_URL=http://prefect:4200/api
prefect config set PREFECT_RESULTS_PERSIST_BY_DEFAULT=false

# echo "Setting up Git..."
# git config --global user.name 'your-username'
# git config --global user.email 'your-email'

echo "Setup complete!"