# Dockerfile for CINEAI Backend API (Cloud Run)
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories (will be overridden by Cloud Storage mounts)
RUN mkdir -p uploads frames vector_databases analysis_output analysis_status

# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV STORAGE_BACKEND=gcs
ENV GCS_BUCKET=${GCS_BUCKET}

# Expose port
EXPOSE 8080

# Run the application
CMD exec uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1
