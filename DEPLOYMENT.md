# Idempotent Deployment & Operations Guide

**Configuration Source:** `.env.gcp` (created from [`.env.gcp.example`](.env.gcp.example), protected by [`.gitignore`](.gitignore))  
**Default Primary Region:** `us-central1`  
**Default Document AI Multi-Region:** `us`  
**Default Cloud Storage Bucket:** `gs://${GCP_PROJECT_ID}-claims-docs`  
**Default Firestore Collection:** `claims_documents`  

---

## 1. Prerequisites & Environment Configuration (`TODO` Setup)

1. **Copy the environment template to `.env.gcp`:**
   ```bash
   cp .env.gcp.example .env.gcp
   ```
2. **Update `.env.gcp` (`TODO` items):**
   - Set `GCP_PROJECT_ID=<your-gcp-project-id>` (required).
   - Optionally set `GCP_PROJECT_NUMBER`, `GCS_BUCKET_NAME`, and `DOCAI_PROCESSOR_ID`—or leave them for `./deploy.sh` to auto-discover/provision and write back into `.env.gcp`.
3. **Authenticate Google Cloud SDK (`gcloud`)** with an account that has permissions on `$GCP_PROJECT_ID`:
   ```bash
   source .env.gcp
   gcloud auth login
   gcloud auth application-default login
   gcloud config set project "$GCP_PROJECT_ID"
   ```
4. **Python 3.11+** installed locally.

---

## 2. One-Command Idempotent Setup & Provisioning

All infrastructure provisioning, dependency installation, and sample PDF generation steps are encapsulated in [`deploy.sh`](deploy.sh). Every step checks whether the target resource already exists before mutating state, so it can be re-executed safely at any time:

```bash
chmod +x deploy.sh

# Provision all GCP resources (APIs, GCS Bucket, Firestore, Document AI Processor),
# update .env.gcp & .firebaserc, and generate the 4 realistic test PDFs (EN, ES, FR, KO):
./deploy.sh
```

### Supported Flags for `deploy.sh`

| Flag | Description |
| :--- | :--- |
| *(no flags)* | Loads `.env.gcp`, enables GCP APIs, creates/updates the hardened GCS bucket `gs://${GCS_BUCKET_NAME}`, creates the `(default)` Firestore database if missing, creates/discovers the Document AI `OCR_PROCESSOR`, writes `.env.gcp` and `.firebaserc`, sets up `.venv`, and generates the 4 sample PDFs. |
| `--skip-bucket` | Runs all idempotent provisioning steps **except** GCS bucket creation/mutation (used when reviewing the bucket plan prior to creation). |
| `--cloud-run` | Also builds and deploys the containerized application to Google Cloud Run (`claims-processor-app` in `$GCP_REGION`). |
| `--run-tests` | Executes the automated end-to-end test suite (`pytest tests/test_pipeline.py -v`) after provisioning. |
| `--start-server` | Starts the local FastAPI web server (`http://127.0.0.1:8000`) immediately after provisioning. |

---

## 3. Step-by-Step Idempotent Commands Reference

If you prefer to execute each provisioning step individually, load your `.env.gcp` first:
```bash
set -a && source .env.gcp && set +a
```

### Step 3.1: Enable Google Cloud APIs
```bash
gcloud services enable \
  storage.googleapis.com \
  documentai.googleapis.com \
  translate.googleapis.com \
  aiplatform.googleapis.com \
  generativelanguage.googleapis.com \
  firestore.googleapis.com \
  firebaserules.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  --project="$GCP_PROJECT_ID" \
  --quiet
```

### Step 3.2: Create or Update the Hardened Cloud Storage Bucket
Uses [`config/encryption_enforcement.json`](config/encryption_enforcement.json) and [`config/lifecycle.json`](config/lifecycle.json):

```bash
CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-bucket-architect)" \
gcloud storage buckets create "gs://${GCS_BUCKET_NAME}" \
  --project="$GCP_PROJECT_ID" \
  --location="$GCP_REGION" \
  --default-storage-class=STANDARD \
  --uniform-bucket-level-access \
  --public-access-prevention \
  --soft-delete-duration=7d \
  --encryption-enforcement-file=config/encryption_enforcement.json

CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-bucket-architect)" \
gcloud storage buckets update "gs://${GCS_BUCKET_NAME}" \
  --project="$GCP_PROJECT_ID" \
  --lifecycle-file=config/lifecycle.json \
  --update-labels="env=prod,workload=healthcare-claims,data-classification=confidential,project=${GCP_PROJECT_ID}"
```

### Step 3.3: Create the Cloud Firestore `(default)` Database
```bash
gcloud firestore databases describe --database="(default)" --project="$GCP_PROJECT_ID" >/dev/null 2>&1 || \
gcloud firestore databases create \
  --project="$GCP_PROJECT_ID" \
  --database="(default)" \
  --location="$GCP_REGION" \
  --type=firestore-native \
  --quiet
```

### Step 3.4: Generate Realistic Multi-Language Claims Test PDFs
Generates test PDFs in **English**, **Spanish**, **French**, and **Korean** inside `sample_documents/`:
```bash
.venv/bin/python scripts/generate_test_pdfs.py
```

### Step 3.5: Run the Application Locally
```bash
.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8001
```
Open `http://127.0.0.1:8001` in your browser.

### Step 3.6: Run End-to-End Automated Tests
```bash
.venv/bin/pytest tests/test_pipeline.py -v
```

### Step 3.7: Deploy to Google Cloud Run (Idempotent, Unauthenticated)
```bash
./deploy.sh --cloud-run
```

This command idempotently:
1. Resolves `$GCP_PROJECT_NUMBER` and grants the default Compute Engine service account (`${GCP_PROJECT_NUMBER}-compute@developer.gserviceaccount.com`) the required Cloud Build and runtime IAM roles (`roles/serviceusage.serviceUsageConsumer`, `roles/storage.admin`, `roles/artifactregistry.writer`, `roles/logging.logWriter`, `roles/documentai.apiUser`, `roles/cloudtranslate.user`, `roles/datastore.user`, `roles/aiplatform.user`).
2. Builds the container image from [`Dockerfile`](Dockerfile) via Cloud Build and deploys `$CLOUD_RUN_SERVICE` (`claims-processor-app`) to Cloud Run in `$GCP_REGION`, injecting runtime environment variables from `.env.gcp` via `--set-env-vars`.
3. Enables public unauthenticated access using `--allow-unauthenticated` and `--no-invoker-iam-check`.
