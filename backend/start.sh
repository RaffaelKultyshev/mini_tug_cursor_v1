#!/bin/bash
# Startup script for Render deployment

# Ensure data directory exists
mkdir -p /app/backend/data

# Start the server
exec uvicorn backend.api:app --host 0.0.0.0 --port ${PORT:-8000}

