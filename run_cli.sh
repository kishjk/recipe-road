#!/bin/bash

# Check if OPENAI_API_KEY is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "Error: OPENAI_API_KEY environment variable is not set"
    echo "Please set it with: export OPENAI_API_KEY='your-api-key'"
    exit 1
fi

# Check if API is running
if ! curl -s http://localhost:8001 > /dev/null 2>&1; then
    echo "Error: Recipe Road API is not running"
    echo "Please start the API first with: ./run.sh"
    exit 1
fi

echo "Starting Recipe Road CLI..."
uv run python -m src.cli