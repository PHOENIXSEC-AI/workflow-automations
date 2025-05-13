FROM python:3.11-slim

# Metadata labels
LABEL org.opencontainers.image.authors="phoenixsec" \
      org.opencontainers.image.title="Workflow Automation" \
      org.opencontainers.image.description="A modular and scalable workflow automation system built with Prefect" \
      org.opencontainers.image.licenses="MIT" \
      com.phoenixsec.component="workflow-agent" \
      com.phoenixsec.environment="development"

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    NVM_DIR="/usr/local/share/nvm" \
    NODE_PATH="/usr/local/lib/node_modules" \
    PREFECT_API_URL=http://prefect:4200/api \
    PREFECT_RESULTS_PERSIST_BY_DEFAULT=false

WORKDIR /app

# Install system dependencies
RUN apt update && apt install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js using nvm
RUN mkdir -p $NVM_DIR && \
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh | bash && \
    . "$NVM_DIR/nvm.sh" && \
    nvm install --lts && \
    nvm use --lts && \
    ln -sf $(which node) /usr/local/bin/node && \
    ln -sf $(which npm) /usr/local/bin/npm

# Install codebase parser tool - Repomix
RUN . "$NVM_DIR/nvm.sh" && \
    npm install -g repomix && \
    ln -sf $(which repomix) /usr/local/bin/repomix

# Copy Project dependencies
COPY pyproject.toml ./

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy the source code
COPY src/ ./src/
COPY scripts/ ./scripts/

# Install package in development mode
RUN pip install -e .

# Create a non-root user to run the application
RUN useradd -m appuser && \
    chown -R appuser:appuser /app

# Verify installations
RUN node --version && \
    npm --version && \
    repomix --version && \
    python --version

# Set up NVM in bash environment
RUN echo 'export NVM_DIR="/usr/local/share/nvm"' >> /etc/bash.bashrc && \
    echo '[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"' >> /etc/bash.bashrc

# Switch to non-root user
USER appuser

# Exposed ports
EXPOSE 4200

# Data volume for persistent storage
VOLUME ["/app/data"]

# Command to execute when container starts
CMD ["sleep", "infinity"] 