#!/bin/bash

# This script initializes the LiteLLM database in the existing Postgres instance

# Wait for Postgres to be ready
echo "Waiting for Postgres to be ready..."
until docker exec $(docker ps -q -f name=postgres) pg_isready -U prefect -d prefect
do
  echo "Postgres is unavailable - sleeping"
  sleep 2
done

echo "Postgres is ready! Creating LiteLLM database..."

# Create the LiteLLM database if it doesn't exist
docker exec $(docker ps -q -f name=postgres) psql -U prefect -d prefect -c "
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'litellm') THEN
        CREATE DATABASE litellm;
    END IF;
END
\$\$;
"

echo "Database setup complete. You can now start the LiteLLM proxy with:"
echo "docker-compose up -d litellm-proxy" 