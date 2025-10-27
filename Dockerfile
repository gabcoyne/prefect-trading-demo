# Dockerfile for Trading Partition Demo
# Built automatically via: prefect deploy --all
# Version: 1.1.0 - Fixed timestamp index issue
FROM python:3.11-slim

# Cache busting arg
ARG CACHEBUST=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY README.md .
COPY flows/ flows/
COPY scripts/ scripts/
COPY input/ input/

# Install uv
RUN pip install --no-cache-dir uv

# Install dependencies using uv
RUN uv pip install --system -e .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PREFECT_API_URL=${PREFECT_API_URL}
ENV PREFECT_API_KEY=${PREFECT_API_KEY}

# Default command (can be overridden)
CMD ["python", "-m", "prefect.engine"]

