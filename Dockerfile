FROM python:3.13-slim


# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
ADD ["pyproject.toml", "uv.lock", "validate_metadata.py", "./"]

# Install Python dependencies using uv
RUN uv sync --directory "./" --frozen

ENTRYPOINT [ "uv", "run", "python", "./validate_metadata.py" ]