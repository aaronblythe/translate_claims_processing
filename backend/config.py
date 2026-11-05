"""Configuration management for the Healthcare Claims Processing Platform."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env.gcp"

if ENV_FILE.exists():
    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())

GCP_PROJECT_ID: str = os.environ.get("GCP_PROJECT_ID", "unconfigured-gcp-project")
GCP_PROJECT_NUMBER: str = os.environ.get("GCP_PROJECT_NUMBER", "")
GCP_REGION: str = os.environ.get("GCP_REGION", "us-central1")
GCS_BUCKET_NAME: str = os.environ.get("GCS_BUCKET_NAME", f"{GCP_PROJECT_ID}-claims-docs")
DOCAI_LOCATION: str = os.environ.get("DOCAI_LOCATION", "us")
DOCAI_PROCESSOR_ID: str = os.environ.get("DOCAI_PROCESSOR_ID", "")
FIRESTORE_COLLECTION: str = os.environ.get("FIRESTORE_COLLECTION", "claims_documents")
GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")

SAMPLE_DOCS_DIR: Path = BASE_DIR / "sample_documents"
DATA_DIR: Path = BASE_DIR / "data"
LOCAL_GCS_MIRROR_DIR: Path = DATA_DIR / "gcs_mirror"
LOCAL_FIRESTORE_CACHE: Path = DATA_DIR / "firestore_cache.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOCAL_GCS_MIRROR_DIR.mkdir(parents=True, exist_ok=True)

SAMPLE_DOCUMENTS_METADATA = {
    "english": {
        "id": "english",
        "filename": "english_itemized_medical_bill.pdf",
        "language_name": "English",
        "language_code": "en",
        "flag": "🇺🇸",
        "title": "English — Coded Itemized Hospital Bill & Copay Receipt",
        "subtitle": "Pacific Northwest Medical Center (Seattle, WA) | CPT/HCPCS & ICD-10 Coded",
        "document_category": "Itemized Medical Bill (Coded) + Proof of Payment",
        "expected_workflow": "Direct Processing (Language = English)",
    },
    "spanish": {
        "id": "spanish",
        "filename": "spanish_factura_medica_hospital.pdf",
        "language_name": "Spanish",
        "language_code": "es",
        "flag": "🇪🇸",
        "title": "Spanish — Uncoded Emergency Hospital Invoice & Clinical Summary",
        "subtitle": "Hospital Ángeles Pedregal (Mexico City) | Acute Appendicitis Laparoscopy",
        "document_category": "Itemized Medical Bill (Uncoded) + Medical Record + Receipt",
        "expected_workflow": "Cloud Translation API (ES → EN) → Clean English PDF → Claims Extraction",
    },
    "french": {
        "id": "french",
        "filename": "french_dossier_medical_autorisation.pdf",
        "language_name": "French",
        "language_code": "fr",
        "flag": "🇫🇷",
        "title": "French — Specialist Referral, Prior Authorization & Knee MRI Record",
        "subtitle": "Hôpital Américain de Paris (France) | Left Knee ACL Tear & Orthopedic Statement",
        "document_category": "Referral + Prior Authorization + Medical Record + Fee Statement",
        "expected_workflow": "Cloud Translation API (FR → EN) → Clean English PDF → Claims Extraction",
    },
    "korean": {
        "id": "korean",
        "filename": "korean_hospital_claim_receipt.pdf",
        "language_name": "Korean",
        "language_code": "ko",
        "flag": "🇰🇷",
        "title": "Korean — Hospital Itemized Claim Receipt & Diagnosis Certificate",
        "subtitle": "서울아산병원 / Asan Medical Center (Seoul) | Upper GI Endoscopy & Biopsy",
        "document_category": "Itemized Medical Bill + Diagnosis Certificate + Proof of Payment",
        "expected_workflow": "Cloud Translation API (KO → EN) → Clean English PDF → Claims Extraction",
    },
}
