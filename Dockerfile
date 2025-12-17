# Use official Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies and development tools
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    vim \
    nano \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install additional development tools
RUN pip install --no-cache-dir \
    ipython \
    jupyter \
    black \
    flake8 \
    mypy

# Copy the entire project
COPY . .

# Create necessary directories
RUN mkdir -p logs data/ratings uploads static/card_cache

# Expose Flask port
EXPOSE 5000

# Set environment variables
ENV PYTHONPATH=/app
ENV FLASK_ENV=development
ENV FLASK_DEBUG=1

# Default command (can be overridden by docker-compose)
CMD ["bash"] 