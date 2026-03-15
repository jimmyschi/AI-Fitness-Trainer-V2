#!/bin/bash

# Deploy the fitness_final project to Google Cloud Run and upload the frontend to Cloud Storage.
# This is adapted from fitness_copy's deploy scripts.

set -e

PROJECT_ID="gleaming-bus-449020-t9"
REGION="us-east1"

echo "════════════════════════════════════════════════════════════"
echo "Deploying fitness_final to Cloud Run + Cloud Storage"
echo "════════════════════════════════════════════════════════════"
echo ""

# Build and deploy Django backend
echo "🔨 Building backend container image..."
cd fitness_backend

docker buildx create --use --name buildx || true
docker buildx inspect --bootstrap

docker buildx build --platform linux/amd64 -t gcr.io/${PROJECT_ID}/fitness-django:cloudrun -f Dockerfile.cloudrun . --push

echo ""

echo "🚀 Deploying backend to Cloud Run..."
gcloud run deploy fitness-app \
  --image gcr.io/${PROJECT_ID}/fitness-django:cloudrun \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 3600 \
  --max-instances 10 \
  --min-instances 0 \
  --set-env-vars "DJANGO_SETTINGS_MODULE=fitness_backend.container_settings" \
  --quiet

echo ""

echo "✅ Backend deployed."

echo ""

echo "Building and uploading frontend to Cloud Storage..."
cd ../fitness-frontend
npm ci
npm run build

gsutil -m rsync -r build/ gs://fitness-frontend-y/
gsutil setmeta -h "Cache-Control:public, max-age=0, no-cache, no-store, must-revalidate" gs://fitness-frontend-y/index.html

echo ""
echo "✅ Frontend uploaded to gs://fitness-frontend-y/"

echo ""
echo "Deployment complete."

echo "Use the following URLs:"
echo "  Frontend: https://fitness-frontend-y.storage.googleapis.com/index.html#/"
echo "  Backend: (see gcloud run services list)"
