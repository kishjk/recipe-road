#!/bin/bash

# Check if OPENAI_API_KEY is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "Error: OPENAI_API_KEY environment variable is not set"
    echo "Please set it with: export OPENAI_API_KEY='your-api-key'"
    exit 1
fi

# Install dependencies if needed
if [ ! -d ".venv" ]; then
    echo "Setting up virtual environment..."
    uv venv
fi

echo "Installing dependencies..."
uv pip install -e .

echo "Starting Recipe Road API..."
uv run uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload