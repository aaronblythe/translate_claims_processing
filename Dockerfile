FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config/ ./config/
COPY scripts/ ./scripts/
COPY sample_documents/ ./sample_documents/
COPY backend/ ./backend/
COPY frontend/ ./frontend/

RUN mkdir -p /app/data/gcs_mirror

# Runtime environment defaults (project-specific values are injected via
# `--env-file .env.gcp` locally or `--set-env-vars` on Google Cloud Run)
ENV PORT=8080
ENV GCP_REGION=us-central1
ENV DOCAI_LOCATION=us
ENV FIRESTORE_COLLECTION=claims_documents
ENV GEMINI_MODEL=gemini-3.8-flash

EXPOSE 8080

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
