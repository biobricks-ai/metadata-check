FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml .
COPY uv.lock .

# Copy validation script (needed before sync for project structure)
COPY validate_metadata.py .

# Install Python dependencies using uv
# --frozen ensures we use the exact versions from uv.lock
# --no-dev skips development dependencies
RUN uv sync --frozen --no-dev

# Set the entrypoint to run within the uv environment
ENTRYPOINT ["uv", "run", "validate_metadata.py"]