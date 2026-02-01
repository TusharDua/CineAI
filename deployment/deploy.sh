#!/bin/bash

# CINEAI Deployment Script for GCP
# This script deploys the entire application to Google Cloud Platform

set -e

# Configuration
PROJECT_ID=${GCP_PROJECT_ID:-"your-project-id"}
REGION=${GCP_REGION:-"us-central1"}
BUCKET_NAME="${PROJECT_ID}-cineai-storage"
GEMINI_API_KEY=${GEMINI_API_KEY}

echo "🚀 Starting CINEAI deployment to GCP"
echo "   Project: $PROJECT_ID"
echo "   Region: $REGION"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install it first:"
    echo "   https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Set project
echo "📋 Setting GCP project..."
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    cloudtasks.googleapis.com \
    storage.googleapis.com \
    artifactregistry.googleapis.com

# Create Cloud Storage bucket
echo "💾 Creating Cloud Storage bucket..."
if ! gsutil ls gs://$BUCKET_NAME &> /dev/null; then
    gsutil mb -p $PROJECT_ID -l $REGION gs://$BUCKET_NAME
    echo "   ✅ Bucket created: gs://$BUCKET_NAME"
else
    echo "   ℹ️  Bucket already exists: gs://$BUCKET_NAME"
fi

# Make bucket public for serving static files (optional)
gsutil iam ch allUsers:objectViewer gs://$BUCKET_NAME/uploads

# Create service account
echo "👤 Creating service account..."
SERVICE_ACCOUNT="cineai-service@${PROJECT_ID}.iam.gserviceaccount.com"
if ! gcloud iam service-accounts describe $SERVICE_ACCOUNT &> /dev/null; then
    gcloud iam service-accounts create cineai-service \
        --display-name="CINEAI Service Account"
    echo "   ✅ Service account created"
else
    echo "   ℹ️  Service account already exists"
fi

# Grant permissions
echo "🔐 Granting permissions..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/storage.objectAdmin" \
    --condition=None

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/cloudtasks.enqueuer" \
    --condition=None

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/run.invoker" \
    --condition=None

# Create Cloud Tasks queue
echo "📬 Creating Cloud Tasks queue..."
if ! gcloud tasks queues describe video-processing-queue --location=$REGION &> /dev/null; then
    gcloud tasks queues create video-processing-queue \
        --location=$REGION \
        --max-concurrent-dispatches=3 \
        --max-dispatches-per-second=1
    echo "   ✅ Queue created"
else
    echo "   ℹ️  Queue already exists"
fi

# Build and deploy backend API
echo "🏗️  Building backend API..."
cd ../backend
gcloud builds submit --tag gcr.io/$PROJECT_ID/cineai-api

echo "🚀 Deploying backend API to Cloud Run..."
gcloud run deploy cineai-api \
    --image gcr.io/$PROJECT_ID/cineai-api \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --memory 4Gi \
    --cpu 2 \
    --timeout 60s \
    --min-instances 0 \
    --max-instances 10 \
    --service-account $SERVICE_ACCOUNT \
    --set-env-vars "GCS_BUCKET=$BUCKET_NAME,GEMINI_API_KEY=$GEMINI_API_KEY,STORAGE_BACKEND=gcs"

# Get API URL
API_URL=$(gcloud run services describe cineai-api --region $REGION --format 'value(status.url)')
echo "   ✅ API deployed: $API_URL"

# Build and deploy worker
echo "🏗️  Building worker..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/cineai-worker -f Dockerfile.worker

echo "   ✅ Worker image built (will be invoked by Cloud Run Jobs)"

# Build and deploy frontend
echo "🏗️  Building frontend..."
cd ../frontend

# Update API endpoint in frontend
cat > .env.production << EOF
VITE_API_URL=$API_URL
EOF

# Build frontend Docker image
cat > Dockerfile << EOF
FROM node:18-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
EOF

# Create nginx config
cat > nginx.conf << EOF
server {
    listen 8080;
    server_name _;
    
    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files \$uri \$uri/ /index.html;
    }
    
    location /api {
        proxy_pass $API_URL;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }
}
EOF

gcloud builds submit --tag gcr.io/$PROJECT_ID/cineai-frontend

echo "🚀 Deploying frontend to Cloud Run..."
gcloud run deploy cineai-frontend \
    --image gcr.io/$PROJECT_ID/cineai-frontend \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1

FRONTEND_URL=$(gcloud run services describe cineai-frontend --region $REGION --format 'value(status.url)')

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "📱 Frontend URL: $FRONTEND_URL"
echo "🔗 API URL: $API_URL"
echo "💾 Storage Bucket: gs://$BUCKET_NAME"
echo ""
echo "📝 Next steps:"
echo "   1. Visit $FRONTEND_URL to access your application"
echo "   2. Monitor logs: gcloud logging read 'resource.type=cloud_run_revision' --limit 50"
echo "   3. View costs: https://console.cloud.google.com/billing"
echo ""
