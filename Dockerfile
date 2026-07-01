# Use the official Python 3.13 slim image for a lightweight footprint
FROM python:3.13-slim

# Set working directory inside the container
WORKDIR /app

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies if required (e.g., for compiling packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first to leverage Docker layer caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Create the data mount directory explicitly to avoid permission issues
RUN mkdir -p /app/data

# Expose the data directory as a volume to persist state and logs across daily runs
VOLUME ["/app/data"]

# Define the default execution command (runs once and exits)
CMD ["python", "main.py"]