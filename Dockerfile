FROM python:3.13-slim


# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
ADD ["pyproject.toml", "uv.lock", "validate_metadata.py", "/github/workspace/"]

# Install Python dependencies using uv
# --frozen ensures we use the exact versions from uv.lock
# --no-dev skips development dependencies
RUN uv sync --directory "/github/workspace/" --frozen --no-dev

RUN ls /github/workspace/

# Set the entrypoint to run within the uv environment
ENTRYPOINT ["uv", "run", "python", "/github/workspace/validate_metadata.py"]
# ENTRYPOINT ["tail", "-f", "/dev/null"]