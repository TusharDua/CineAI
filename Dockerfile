# Stage 1: Build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
ENV VITE_API_URL=/
RUN npm run build

# Stage 2: Backend + serve frontend dist
FROM python:3.11-slim
RUN apt-get update && apt-get install -y \
    ffmpeg libgl1 libglib2.0-0 \
    gcc portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend-build /app/frontend/dist ./dist
RUN mkdir -p uploads frames vector_databases analysis_output analysis_status
ENV PORT=8080 PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
