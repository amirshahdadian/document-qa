#!/bin/bash

# ==============================================================================
# Deployment Script for the Document QA Application
# ==============================================================================

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
PROJECT_ID="rag-pdf-demo"
SERVICE_NAME="document-qa"
REGION="europe-west1"
GCR_HOSTNAME="gcr.io"
IMAGE_TAG="$GCR_HOSTNAME/$PROJECT_ID/$SERVICE_NAME"
SERVICE_ACCOUNT="876776881787-compute@developer.gserviceaccount.com"

# --- 1. Pre-Deployment Tests ---
echo "🧪 Running pre-deployment validation tests..."

# Use the main test runner script
if [ -f "run_tests.py" ]; then
    python run_tests.py
    if [ $? -ne 0 ]; then
        echo "❌ Tests failed. Aborting deployment."
        exit 1
    fi
else
    echo "⚠️ 'run_tests.py' not found. Skipping tests."
fi

echo "✅ Pre-deployment tests passed."

# --- 2. Load Environment Variables ---
echo "🔑 Loading environment variables from .env file..."

if [ ! -f .env ]; then
    echo "❌ Error: .env file not found. Please create it with the required variables."
    exit 1
fi

set -a
source .env
set +a

echo "✅ Environment variables loaded."

# --- 3. Build Docker Image ---
echo "🏗️ Building Docker image with Google Cloud Build..."
gcloud builds submit --tag "$IMAGE_TAG" .

echo "✅ Docker image built and pushed successfully: $IMAGE_TAG"

# --- 4. Deploy to Cloud Run ---
echo "☁️ Deploying to Google Cloud Run..."

gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE_TAG" \
  --platform "managed" \
  --region "$REGION" \
  --allow-unauthenticated \
  --memory "2Gi" \
  --timeout "3600" \
  --service-account "$SERVICE_ACCOUNT" \
  --set-env-vars "GOOGLE_API_KEY=$GOOGLE_API_KEY" \
  --set-env-vars "GOOGLE_OAUTH_CLIENT_ID=$GOOGLE_OAUTH_CLIENT_ID" \
  --set-env-vars "GOOGLE_OAUTH_CLIENT_SECRET=$GOOGLE_OAUTH_CLIENT_SECRET" \
  --set-env-vars "FIREBASE_API_KEY=$FIREBASE_API_KEY" \
  --set-env-vars "FIREBASE_AUTH_DOMAIN=$FIREBASE_AUTH_DOMAIN" \
  --set-env-vars "FIREBASE_PROJECT_ID=$FIREBASE_PROJECT_ID" \
  --set-env-vars "FIREBASE_STORAGE_BUCKET=$FIREBASE_STORAGE_BUCKET" \
  --set-env-vars "FIREBASE_MESSAGING_SENDER_ID=$FIREBASE_MESSAGING_SENDER_ID" \
  --set-env-vars "FIREBASE_APP_ID=$FIREBASE_APP_ID" \
  --set-env-vars "FIREBASE_SERVICE_ACCOUNT_KEY=$FIREBASE_SERVICE_ACCOUNT_KEY" \
  --set-env-vars "GCS_BUCKET_NAME=$GCS_BUCKET_NAME" \
  --set-env-vars "LOG_LEVEL=INFO" \
  --set-env-vars "LANGCHAIN_VERBOSE=false"

# --- 5. Success ---
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --platform managed --region "$REGION" --format 'value(status.url)')

echo ""
echo "🎉 Deployment successful!"
echo "🌐 Your application is now available at: $SERVICE_URL"
