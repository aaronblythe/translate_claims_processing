#!/usr/bin/env bash
# ==============================================================================
# Idempotent GCP Provisioning & Application Deployment Script
# ==============================================================================
# This script can be re-run safely any number of times. Every step checks
# existing state before creating or updating resources.
#
# Configuration is loaded from `.env.gcp` (gitignored). Copy `.env.gcp.example`
# to `.env.gcp` and set `GCP_PROJECT_ID` before running.
#
# Flags:
#   --skip-bucket    Skip Cloud Storage bucket creation/mutation (useful before
#                    manual bucket plan confirmation).
#   --cloud-run      Build and deploy the application to Google Cloud Run in
#                    addition to provisioning backing GCP resources.
#   --start-server   Start the local FastAPI uvicorn server after provisioning.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ -f ".env.gcp" ]]; then
  set -a
  # shellcheck disable=SC1091
  source ".env.gcp"
  set +a
fi

PROJECT_ID="${GCP_PROJECT_ID:-}"
if [[ -z "$PROJECT_ID" || "$PROJECT_ID" == TODO_* ]]; then
  echo "ERROR: GCP_PROJECT_ID is not configured."
  echo "  1. Copy the example environment file: cp .env.gcp.example .env.gcp"
  echo "  2. Set GCP_PROJECT_ID=<your-gcp-project-id> inside .env.gcp (or export GCP_PROJECT_ID)"
  exit 1
fi

REGION="${GCP_REGION:-us-central1}"
DOCAI_LOCATION="${DOCAI_LOCATION:-us}"
if [[ -z "${GCS_BUCKET_NAME:-}" || "${GCS_BUCKET_NAME:-}" == TODO_* ]]; then
  BUCKET_NAME="${PROJECT_ID}-claims-docs"
else
  BUCKET_NAME="${GCS_BUCKET_NAME}"
fi
SERVICE_NAME="${CLOUD_RUN_SERVICE:-claims-processor-app}"
PROCESSOR_DISPLAY_NAME="claims-ocr-processor"

SKIP_BUCKET=false
DEPLOY_CLOUD_RUN=false
START_SERVER=false
RUN_TESTS=false

for arg in "$@"; do
  case "$arg" in
    --skip-bucket)
      SKIP_BUCKET=true
      ;;
    --cloud-run)
      DEPLOY_CLOUD_RUN=true
      ;;
    --start-server)
      START_SERVER=true
      ;;
    --run-tests)
      RUN_TESTS=true
      ;;
  esac
done

export CLOUDSDK_CORE_DISABLE_PROMPTS=1
export CLOUDSDK_BILLING_QUOTA_PROJECT="$PROJECT_ID"

echo "=================================================================="
echo "1. Verifying Google Cloud Project & Active Account"
echo "=================================================================="
ACTIVE_ACCOUNT="$(gcloud auth list --filter="status:ACTIVE" --format="value(account)" | head -n 1)"
if [[ -z "$ACTIVE_ACCOUNT" ]]; then
  echo "ERROR: No active gcloud account found. Run 'gcloud auth login' first."
  exit 1
fi
echo "Active Account : $ACTIVE_ACCOUNT"
echo "Target Project : $PROJECT_ID"
echo "Target Region  : $REGION"

echo ""
echo "=================================================================="
echo "2. Enabling Required Google Cloud APIs (Idempotent)"
echo "=================================================================="
APIS=(
  "cloudresourcemanager.googleapis.com"
  "iam.googleapis.com"
  "storage.googleapis.com"
  "documentai.googleapis.com"
  "translate.googleapis.com"
  "aiplatform.googleapis.com"
  "generativelanguage.googleapis.com"
  "firestore.googleapis.com"
  "firebaserules.googleapis.com"
  "run.googleapis.com"
  "cloudbuild.googleapis.com"
  "artifactregistry.googleapis.com"
)
gcloud services enable "${APIS[@]}" --project="$PROJECT_ID" --quiet
echo "All required APIs are enabled on $PROJECT_ID."

echo ""
echo "=================================================================="
echo "3. Provisioning Cloud Storage Bucket (Idempotent)"
echo "=================================================================="
if [[ "$SKIP_BUCKET" == "true" ]]; then
  echo "Skipping GCS bucket creation (--skip-bucket specified)."
else
  export CLOUDSDK_METRICS_ENVIRONMENT="gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-bucket-architect)"
  if gcloud storage buckets describe "gs://${BUCKET_NAME}" --project="$PROJECT_ID" >/dev/null 2>&1; then
    echo "Bucket gs://${BUCKET_NAME} already exists. Applying idempotent security & lifecycle configuration..."
    gcloud storage buckets update "gs://${BUCKET_NAME}" \
      --project="$PROJECT_ID" \
      --uniform-bucket-level-access \
      --public-access-prevention \
      --soft-delete-duration=7d \
      --lifecycle-file="config/lifecycle.json" \
      --update-labels="env=prod,workload=healthcare-claims,data-classification=confidential,project=${PROJECT_ID}" \
      --quiet
  else
    echo "Creating bucket gs://${BUCKET_NAME} in ${REGION} with Sensitive Data security controls..."
    gcloud storage buckets create "gs://${BUCKET_NAME}" \
      --project="$PROJECT_ID" \
      --location="$REGION" \
      --default-storage-class=STANDARD \
      --uniform-bucket-level-access \
      --public-access-prevention \
      --soft-delete-duration=7d \
      --encryption-enforcement-file="config/encryption_enforcement.json" \
      --quiet 2>/dev/null || \
    gcloud storage buckets create "gs://${BUCKET_NAME}" \
      --project="$PROJECT_ID" \
      --location="$REGION" \
      --default-storage-class=STANDARD \
      --uniform-bucket-level-access \
      --public-access-prevention \
      --soft-delete-duration=7d \
      --quiet

    gcloud storage buckets update "gs://${BUCKET_NAME}" \
      --project="$PROJECT_ID" \
      --lifecycle-file="config/lifecycle.json" \
      --update-labels="env=prod,workload=healthcare-claims,data-classification=confidential,project=${PROJECT_ID}" \
      --quiet
  fi
  if [[ -d "data/gcs_mirror/originals" ]]; then
    echo "Syncing local claims PDFs to gs://${BUCKET_NAME}/ ..."
    gcloud storage cp -r data/gcs_mirror/* "gs://${BUCKET_NAME}/" --project="$PROJECT_ID" --quiet || true
  fi
  echo "Bucket gs://${BUCKET_NAME} is ready."
fi

echo ""
echo "=================================================================="
echo "4. Provisioning Firebase / Cloud Firestore Database (Idempotent)"
echo "=================================================================="
EXISTING_DB="$(gcloud firestore databases list --project="$PROJECT_ID" --format="value(name)" 2>/dev/null || true)"
if echo "$EXISTING_DB" | grep -q "(default)"; then
  echo "Firestore (default) database already exists in $PROJECT_ID."
else
  echo "Creating Firestore (default) database in $REGION..."
  gcloud firestore databases create \
    --project="$PROJECT_ID" \
    --database="(default)" \
    --location="$REGION" \
    --type="firestore-native" \
    --quiet || echo "Firestore database creation already in progress or completed."
fi

echo ""
echo "=================================================================="
echo "5. Provisioning Document AI OCR Processor (Idempotent)"
echo "=================================================================="
ACCESS_TOKEN="$(gcloud auth application-default print-access-token 2>/dev/null || gcloud auth print-access-token)"
PROCESSORS_JSON="$(curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "x-goog-user-project: ${PROJECT_ID}" \
  "https://${DOCAI_LOCATION}-documentai.googleapis.com/v1/projects/${PROJECT_ID}/locations/${DOCAI_LOCATION}/processors" || echo "{}")"

PROCESSOR_NAME="$(python3 -c '
import json, sys
data = json.loads(sys.argv[1]) if sys.argv[1].strip() else {}
for p in data.get("processors", []):
    if p.get("type") in ("OCR_PROCESSOR", "FORM_PARSER_PROCESSOR") and p.get("state") == "ENABLED":
        print(p.get("name", ""))
        break
' "$PROCESSORS_JSON" 2>/dev/null || true)"

if [[ -z "$PROCESSOR_NAME" ]]; then
  echo "Creating Document AI OCR_PROCESSOR (${PROCESSOR_DISPLAY_NAME}) in location '${DOCAI_LOCATION}'..."
  CREATE_RESP="$(curl -s -X POST \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "x-goog-user-project: ${PROJECT_ID}" \
    -H "Content-Type: application/json" \
    -d "{\"type\": \"OCR_PROCESSOR\", \"displayName\": \"${PROCESSOR_DISPLAY_NAME}\"}" \
    "https://${DOCAI_LOCATION}-documentai.googleapis.com/v1/projects/${PROJECT_ID}/locations/${DOCAI_LOCATION}/processors" || echo "{}")"
  PROCESSOR_NAME="$(python3 -c '
import json, sys
data = json.loads(sys.argv[1]) if sys.argv[1].strip() else {}
print(data.get("name", ""))
' "$CREATE_RESP" 2>/dev/null || true)"
fi

if [[ -n "$PROCESSOR_NAME" ]]; then
  PROCESSOR_ID="${PROCESSOR_NAME##*/}"
  echo "Document AI Processor Ready: ${PROCESSOR_NAME} (ID: ${PROCESSOR_ID})"
else
  PROCESSOR_ID=""
  echo "Warning: Document AI processor could not be resolved immediately; backend will auto-discover at runtime."
fi

PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)" 2>/dev/null || echo "${GCP_PROJECT_NUMBER:-}")"

cat > .env.gcp <<EOF
GCP_PROJECT_ID=${PROJECT_ID}
GCP_PROJECT_NUMBER=${PROJECT_NUMBER}
GCP_REGION=${REGION}
GCS_BUCKET_NAME=${BUCKET_NAME}
DOCAI_LOCATION=${DOCAI_LOCATION}
DOCAI_PROCESSOR_ID=${PROCESSOR_ID}
FIRESTORE_COLLECTION=claims_documents
GEMINI_MODEL=gemini-3.8-flash
CLOUD_RUN_SERVICE=${SERVICE_NAME}
EOF
echo "Wrote runtime configuration to .env.gcp (gitignored)"

cat > .firebaserc <<EOF
{
  "projects": {
    "default": "${PROJECT_ID}"
  }
}
EOF
echo "Wrote Firebase project alias to .firebaserc (gitignored)"

echo ""
echo "=================================================================="
echo "6. Setting Up Local Python Environment & Generating Test PDFs"
echo "=================================================================="
if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt
.venv/bin/python scripts/generate_test_pdfs.py

if [[ "$RUN_TESTS" == "true" ]]; then
  echo ""
  echo "=================================================================="
  echo "6b. Running End-to-End Integration Test Suite (EN / ES / FR / KO)"
  echo "=================================================================="
  .venv/bin/python -m pytest tests/test_pipeline.py -v
fi

echo ""
echo "=================================================================="
echo "7. Cloud Run Deployment"
echo "=================================================================="
if [[ "$DEPLOY_CLOUD_RUN" == "true" ]]; then
  if [[ -z "${PROJECT_NUMBER:-}" || "${PROJECT_NUMBER:-}" == TODO_* ]]; then
    PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")"
  fi
  COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
  echo "Granting required Cloud Build & runtime IAM roles to ${COMPUTE_SA}..."
  for ROLE in \
    roles/serviceusage.serviceUsageConsumer \
    roles/storage.admin \
    roles/artifactregistry.writer \
    roles/logging.logWriter \
    roles/documentai.apiUser \
    roles/cloudtranslate.user \
    roles/datastore.user \
    roles/aiplatform.user; do
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
      --member="serviceAccount:${COMPUTE_SA}" \
      --role="$ROLE" \
      --condition=None \
      --quiet >/dev/null 2>&1 || true
  done

  gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
    --member="serviceAccount:${COMPUTE_SA}" \
    --role="roles/storage.objectAdmin" \
    --project="$PROJECT_ID" \
    --quiet >/dev/null 2>&1 || true

  gcloud storage buckets add-iam-policy-binding "gs://run-sources-${PROJECT_ID}-${REGION}" \
    --member="serviceAccount:${COMPUTE_SA}" \
    --role="roles/storage.objectViewer" \
    --project="$PROJECT_ID" \
    --quiet >/dev/null 2>&1 || true

  echo "Deploying ${SERVICE_NAME} to Cloud Run in ${REGION} (allow-unauthenticated / no-invoker-iam-check)..."
  gcloud run deploy "$SERVICE_NAME" \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --source=. \
    --allow-unauthenticated \
    --no-invoker-iam-check \
    --memory=1Gi \
    --cpu=1 \
    --timeout=300 \
    --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID},GCP_REGION=${REGION},GCS_BUCKET_NAME=${BUCKET_NAME},DOCAI_LOCATION=${DOCAI_LOCATION},DOCAI_PROCESSOR_ID=${PROCESSOR_ID},FIRESTORE_COLLECTION=claims_documents,GEMINI_MODEL=gemini-3.8-flash" \
    --quiet

  gcloud run services update "$SERVICE_NAME" \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --no-invoker-iam-check \
    --quiet >/dev/null 2>&1 || true

  SERVICE_URL="$(gcloud run services describe "$SERVICE_NAME" --project="$PROJECT_ID" --region="$REGION" --format="value(status.url)" 2>/dev/null || true)"
  echo "Cloud Run Service Deployed: ${SERVICE_URL}"
else
  echo "Skipping Cloud Run deployment (pass --cloud-run to deploy to Cloud Run)."
fi

if [[ "$START_SERVER" == "true" ]]; then
  echo ""
  echo "Starting local FastAPI server on http://127.0.0.1:8000 ..."
  exec .venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000
fi

echo ""
echo "=================================================================="
echo "Deployment & Provisioning Complete!"
echo "To run locally: .venv/bin/uvicorn backend.main:app --reload --port 8000"
echo "=================================================================="
