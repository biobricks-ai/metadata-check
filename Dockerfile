FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies using uv
RUN uv sync

# Copy validation script
COPY validate_metadata.py .

# Set the entrypoint
ENTRYPOINT ["uv", "run", "python", "/app/validate_metadata.py"]