"""
End-to-End Integration Test Suite for the Healthcare Claims Processing & Translation Platform.
Verifies:
1. Generation of all 4 realistic claims PDFs (English, Spanish, French, Korean).
2. Immediate language detection and conditional routing:
   - English ('en') -> skips translation, processes directly.
   - Spanish ('es'), French ('fr'), Korean ('ko') -> translates to English via Google Cloud Translation API,
     generates Clean English Representation PDF, and processes the new English document.
3. Structured claims extraction (patient, provider, policy, ICD-10, CPT/HCPCS, financials, readiness).
4. Side-by-side PDF comparison endpoints and Firebase / Cloud Firestore persistence.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

from backend.main import app
from scripts.generate_test_pdfs import main as generate_all_test_pdfs

client = TestClient(app)


def setup_module():
    """Ensure all 4 test PDFs exist before running tests."""
    generate_all_test_pdfs()


def test_sample_documents_catalog():
    resp = client.get("/api/samples")
    assert resp.status_code == 200
    samples = resp.json()["samples"]
    assert len(samples) == 4
    by_id = {s["id"]: s for s in samples}
    for lang_id in ("english", "spanish", "french", "korean"):
        assert lang_id in by_id
        assert by_id[lang_id]["exists"] is True
        assert by_id[lang_id]["size_bytes"] > 1000


def test_english_claim_processes_directly_without_translation():
    resp = client.post("/api/claims/process-sample/english")
    assert resp.status_code == 200
    data = resp.json()

    assert data["language_detection"]["language_code"] == "en"
    assert data["language_detection"]["is_english"] is True
    assert data["was_translated"] is False
    assert data["gcs_translated_uri"] is None

    # Step 4 must be SKIPPED for English
    step4 = [s for s in data["pipeline_steps"] if s["step_number"] == 4][0]
    assert step4["status"] == "SKIPPED"

    ext = data["extraction"]
    assert ext["document_classification"]["document_type"] == "ITEMIZED_MEDICAL_BILL_CODED"
    assert "Eleanor" in ext["patient"]["full_name"]
    assert any(d["code"] == "J18.9" for d in ext["diagnoses"])
    assert any(li["procedure_code"] == "99284" for li in ext["line_items"])


def test_spanish_claim_translates_and_creates_clean_english_pdf():
    resp = client.post("/api/claims/process-sample/spanish")
    assert resp.status_code == 200
    data = resp.json()

    assert data["language_detection"]["language_code"] == "es"
    assert data["language_detection"]["is_english"] is False
    assert data["was_translated"] is True
    assert data["gcs_translated_uri"] is not None
    assert len(data["translation_segments"]) >= 5

    # Verify Clean English Representation PDF endpoint streams valid PDF bytes
    claim_id = data["claim_id"]
    orig_pdf = client.get(f"/api/claims/{claim_id}/pdf/original")
    trans_pdf = client.get(f"/api/claims/{claim_id}/pdf/translated")
    assert orig_pdf.status_code == 200
    assert trans_pdf.status_code == 200
    assert orig_pdf.content.startswith(b"%PDF-")
    assert trans_pdf.content.startswith(b"%PDF-")
    assert orig_pdf.content != trans_pdf.content

    ext = data["extraction"]
    assert "Mateo" in ext["patient"]["full_name"]
    assert ext["financials"]["original_currency"] == "MXN"
    assert any(li["procedure_code"] == "44970" for li in ext["line_items"])


def test_french_claim_translates_referral_and_prior_auth():
    resp = client.post("/api/claims/process-sample/french")
    assert resp.status_code == 200
    data = resp.json()

    assert data["language_detection"]["language_code"] == "fr"
    assert data["language_detection"]["is_english"] is False
    assert data["was_translated"] is True
    assert data["gcs_translated_uri"] is not None

    ext = data["extraction"]
    assert "Claire" in ext["patient"]["full_name"]
    assert ext["insurance_policy"]["prior_authorization_number"] == "PA-FR-2026-90412"
    assert any(d["code"] == "S83.512A" for d in ext["diagnoses"])


def test_korean_claim_translates_hangul_and_extracts_claim():
    resp = client.post("/api/claims/process-sample/korean")
    assert resp.status_code == 200
    data = resp.json()

    assert data["language_detection"]["language_code"] == "ko"
    assert data["language_detection"]["is_english"] is False
    assert data["was_translated"] is True
    assert data["gcs_translated_uri"] is not None
    assert len(data["translation_segments"]) >= 5

    ext = data["extraction"]
    assert "Ji-Hoon" in ext["patient"]["full_name"] or "김지훈" in ext["patient"]["full_name"]
    assert ext["financials"]["original_currency"] == "KRW"
    assert any(d["code"] == "K25.3" for d in ext["diagnoses"])
    assert any(li["procedure_code"] == "43239" for li in ext["line_items"])


def test_firestore_claims_listing():
    resp = client.get("/api/claims")
    assert resp.status_code == 200
    claims = resp.json()["claims"]
    assert len(claims) >= 4
