#!/bin/bash

# This script builds and deploys the LocalVortex AI application to Google Cloud Run.
#
# Prerequisites:
# 1. Google Cloud SDK (gcloud) installed and authenticated.
# 2. A Google Cloud Project with billing enabled.
# 3. The Cloud Build and Cloud Run APIs enabled in your project.
# 4. You are in the root directory of the project.

# --- Configuration ---
# Replace with your Google Cloud Project ID
PROJECT_ID="your-gcp-project-id"

# Replace with your desired Cloud Run service name
SERVICE_NAME="localvortex-ai"

# Replace with your desired GCP region
REGION="us-central1"

# --- Script ---
set -e # Exit immediately if a command exits with a non-zero status.

echo "--- Configuring gcloud to use project $PROJECT_ID ---"
gcloud config set project $PROJECT_ID

echo "--- Building the Docker image with Cloud Build ---"
# This command builds the Docker image using the Dockerfile and pushes it to Google Container Registry.
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

echo "--- Deploying to Cloud Run ---"
# This command deploys the container image to Cloud Run.
# It uses a .env.gcp file to securely manage environment variables.
#
# IMPORTANT: Create a .env.gcp file in the root of your project with the following content:
#
# SECRET_KEY=your-production-secret-key
# DATABASE_URL=your-production-database-url (e.g., from a Cloud SQL instance)
# GOOGLE_OAUTH_CLIENT_ID=your-production-google-client-id
# GOOGLE_OAUTH_CLIENT_SECRET=your-production-google-client-secret
# GOOGLE_API_KEY=your-production-google-api-key
# GEMINI_API_KEY=your-production-gemini-api-key
# STRIPE_PUBLIC_KEY=your-production-stripe-public-key
# STRIPE_SECRET_KEY=your-production-stripe-secret-key
# STRIPE_PRICE_ID=your-production-stripe-price-id
# STRIPE_WEBHOOK_SECRET=your-production-stripe-webhook-secret
#
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --env-vars-from-file .env.gcp \
  --allow-unauthenticated

echo "--- Deployment successful! ---"
echo "Service URL: $(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)')"
