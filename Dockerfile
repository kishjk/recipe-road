FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install portaudio
RUN apt-get update && apt-get install -y portaudio19-dev

# Copy dependency files
COPY pyproject.toml .
COPY README.md .

# Install uv package manager
RUN pip install uv

# Install dependencies
RUN uv pip install --system -e .

# Copy application code
COPY src ./src

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]