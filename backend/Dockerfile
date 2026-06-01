# PortWatch Backend Dockerfile
# Python 3.12 slim image with system dependencies for WeasyPrint PDF generation

FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies required by WeasyPrint, PostGIS client, and general build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    # WeasyPrint dependencies
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    libglib2.0-0 \
    # Font rendering
    fonts-liberation \
    # Build essentials for native extensions
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency specification first to leverage Docker layer caching
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# Copy application source code
COPY app/ ./app/
COPY seed/ ./seed/

# Expose the default Uvicorn port
EXPOSE 8000

# Run the application with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
