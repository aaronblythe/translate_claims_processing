"""
FastAPI Backend Application & Claims Processing Pipeline Orchestrator
"""

from datetime import datetime, timezone
import logging
from pathlib import Path
import time
from typing import Optional
import uuid

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from backend.config import (
    BASE_DIR,
    GCP_PROJECT_ID,
    GCS_BUCKET_NAME,
    DOCAI_LOCATION,
    FIRESTORE_COLLECTION,
    GEMINI_MODEL,
    SAMPLE_DOCS_DIR,
    SAMPLE_DOCUMENTS_METADATA,
)
from backend.models import (
    PipelineStepStatus,
    ProcessedClaimRecord,
    TranslationSegment,
)
from backend.services.storage_service import CloudStorageService
from backend.services.document_ai_service import DocumentAIService
from backend.services.translation_service import CloudTranslationService
from backend.services.gemini_service import GeminiClaimsService
from backend.services.firestore_service import FirestoreClaimsService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Google Cloud Healthcare Claims Processing & Translation Platform",
    description=(
        "End-to-end Healthcare Claims PDF ingestion, Document AI OCR, immediate language detection, "
        "Google Cloud Translation API v3 translation & Clean English PDF generation, side-by-side comparison, "
        f"Gemini 3.8 Flash structured claims extraction, and Firebase/Firestore storage (project: {GCP_PROJECT_ID})."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

storage_service = CloudStorageService()
docai_service = DocumentAIService()
translation_service = CloudTranslationService()
gemini_service = GeminiClaimsService()
firestore_service = FirestoreClaimsService()

FRONTEND_DIR = BASE_DIR / "frontend"


def execute_claims_pipeline(
    pdf_bytes: bytes,
    filename: str,
    sample_id: Optional[str] = None,
) -> ProcessedClaimRecord:
    """
    Executes the end-to-end Healthcare Claims Processing & Translation Pipeline:
      Step 1: Store initial PDF document in Google Cloud Storage bucket.
      Step 2: Run Google Cloud Document AI to extract text, layout, and tables.
      Step 3: Immediately check the document for the language used.
      Step 4:
        - If English ('en'): skip translation and process normally.
        - If non-English ('es', 'fr', 'ko', etc.): translate to English using
          Google Cloud Translation API, create a clean representation of the document
          in English (PDF + structured text), upload to GCS, and process the new document.
      Step 5: Extract structured healthcare claims data via Gemini (`gemini-3.8-flash`).
      Step 6: Persist complete claim record in Firebase / Cloud Firestore.
    """
    claim_id = f"CLM-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    created_at = datetime.now(timezone.utc).isoformat()
    pipeline_steps: list[PipelineStepStatus] = []

    # -------------------------------------------------------------------------
    # STEP 1: Store Initial Document in Google Cloud Storage
    # -------------------------------------------------------------------------
    t0 = time.perf_counter()
    gcs_original_uri, gcs_ok, gcs_detail = storage_service.store_pdf(
        claim_id=claim_id,
        filename=filename,
        pdf_bytes=pdf_bytes,
        folder="originals",
    )
    t1 = time.perf_counter()
    pipeline_steps.append(
        PipelineStepStatus(
            step_number=1,
            step_name="Store Initial Document in Cloud Storage",
            service_used=f"Google Cloud Storage (gs://{GCS_BUCKET_NAME})",
            status="COMPLETED" if gcs_ok else "FALLBACK",
            duration_ms=max(1, int((t1 - t0) * 1000)),
            details=gcs_detail,
        )
    )

    # -------------------------------------------------------------------------
    # STEP 2: Document AI OCR & Layout Extraction
    # -------------------------------------------------------------------------
    t0 = time.perf_counter()
    docai_data = docai_service.extract_document(pdf_bytes)
    original_text = docai_data["full_text"]
    paragraphs = docai_data["paragraphs"]
    t1 = time.perf_counter()
    pipeline_steps.append(
        PipelineStepStatus(
            step_number=2,
            step_name="Document OCR & Structural Layout Extraction",
            service_used=docai_data["engine"],
            status="COMPLETED",
            duration_ms=max(1, int((t1 - t0) * 1000)),
            details=(
                f"Extracted {len(original_text):,} chars across {docai_data['page_count']} page(s) "
                f"and {len(paragraphs)} structural blocks."
            ),
        )
    )

    # -------------------------------------------------------------------------
    # STEP 3: Immediate Language Check
    # -------------------------------------------------------------------------
    t0 = time.perf_counter()
    lang_info = translation_service.detect_document_language(
        text=original_text,
        docai_languages=docai_data.get("detected_languages"),
    )
    t1 = time.perf_counter()
    pipeline_steps.append(
        PipelineStepStatus(
            step_number=3,
            step_name="Immediate Language Detection Check",
            service_used=lang_info.detection_service,
            status="COMPLETED",
            duration_ms=max(1, int((t1 - t0) * 1000)),
            details=(
                f"Detected language: {lang_info.language_name} ({lang_info.language_code}) "
                f"with {lang_info.confidence * 100:.1f}% confidence. "
                + (
                    "Document is in English -> proceeding directly to claims processing."
                    if lang_info.is_english
                    else f"Non-English document detected ({lang_info.language_code}) -> routing to Google Cloud Translation API."
                )
            ),
        )
    )

    # -------------------------------------------------------------------------
    # STEP 4: Conditional Translation & Clean English Document Representation
    # -------------------------------------------------------------------------
    t0 = time.perf_counter()
    if lang_info.is_english:
        was_translated = False
        english_clean_text = original_text
        english_pdf_to_process = pdf_bytes
        gcs_translated_uri = None
        # Build identity segments so the UI comparator also works for English docs if inspected
        raw_segs = translation_service._segment_text(original_text, paragraphs)
        translation_segments = [
            TranslationSegment(
                segment_id=idx,
                section_type=translation_service._classify_segment_type(seg, idx),
                original_text=seg,
                translated_text=seg,
            )
            for idx, seg in enumerate(raw_segs, start=1)
        ]
        t1 = time.perf_counter()
        pipeline_steps.append(
            PipelineStepStatus(
                step_number=4,
                step_name="Cloud Translation & Clean English Representation",
                service_used="Google Cloud Translation API v3 (Bypassed for English)",
                status="SKIPPED",
                duration_ms=max(1, int((t1 - t0) * 1000)),
                details="Language is English ('en'). Skipped translation and processed original document directly.",
            )
        )
    else:
        was_translated = True
        (
            english_clean_text,
            translation_segments,
            clean_english_pdf_bytes,
            trans_service_detail,
        ) = translation_service.translate_document_to_english(
            full_text=original_text,
            paragraphs=paragraphs,
            source_language_code=lang_info.language_code,
            source_language_name=lang_info.language_name,
            original_filename=filename,
            pdf_bytes=pdf_bytes,
        )
        clean_filename = f"clean_english_{Path(filename).name}"
        gcs_translated_uri, _, trans_gcs_detail = storage_service.store_pdf(
            claim_id=claim_id,
            filename=clean_filename,
            pdf_bytes=clean_english_pdf_bytes,
            folder="translated",
            language_code="en",
        )
        english_pdf_to_process = clean_english_pdf_bytes
        t1 = time.perf_counter()
        pipeline_steps.append(
            PipelineStepStatus(
                step_number=4,
                step_name="Cloud Document Translation & Format-Preserved English PDF",
                service_used=trans_service_detail,
                status="COMPLETED",
                duration_ms=max(1, int((t1 - t0) * 1000)),
                details=(
                    f"Translated PDF via Cloud Translation translate_document API preserving original layout/tables "
                    f"({len(clean_english_pdf_bytes):,} bytes) + {len(translation_segments)} aligned segments from "
                    f"{lang_info.language_name} to English at {gcs_translated_uri}."
                ),
            )
        )

    # -------------------------------------------------------------------------
    # STEP 5: Gemini 3.8 Flash Healthcare Claims Extraction (on English Doc)
    # -------------------------------------------------------------------------
    t0 = time.perf_counter()
    extraction_result, gemini_engine = gemini_service.extract_claim_information(
        english_pdf_bytes=english_pdf_to_process,
        english_text=english_clean_text,
        original_language_code=lang_info.language_code,
        was_translated=was_translated,
        original_filename=filename,
    )
    t1 = time.perf_counter()
    pipeline_steps.append(
        PipelineStepStatus(
            step_number=5,
            step_name="Structured Claims & Medical Coding Extraction",
            service_used=gemini_engine,
            status="COMPLETED",
            duration_ms=max(1, int((t1 - t0) * 1000)),
            details=(
                f"Processed {'Clean English Representation' if was_translated else 'Original English Document'}: "
                f"Classified as {extraction_result.document_classification.document_type}, "
                f"extracted {len(extraction_result.diagnoses)} ICD-10 diagnosis code(s), "
                f"{len(extraction_result.line_items)} CPT/HCPCS line item(s), "
                f"Readiness Score: {extraction_result.claims_readiness.readiness_score}/100."
            ),
        )
    )

    # -------------------------------------------------------------------------
    # STEP 6: Store Processed Claim Record in Firebase / Cloud Firestore
    # -------------------------------------------------------------------------
    t0 = time.perf_counter()
    firestore_doc_path = (
        f"projects/{GCP_PROJECT_ID}/databases/(default)/documents/{FIRESTORE_COLLECTION}/{claim_id}"
    )
    record = ProcessedClaimRecord(
        claim_id=claim_id,
        created_at=created_at,
        original_filename=filename,
        sample_id=sample_id,
        gcs_original_uri=gcs_original_uri,
        gcs_translated_uri=gcs_translated_uri,
        language_detection=lang_info,
        was_translated=was_translated,
        original_extracted_text=original_text,
        english_clean_text=english_clean_text,
        translation_segments=translation_segments,
        extraction=extraction_result,
        pipeline_steps=pipeline_steps,
        firestore_doc_path=firestore_doc_path,
    )
    _, fs_ok, fs_detail = firestore_service.save_claim(record)
    t1 = time.perf_counter()
    record.pipeline_steps.append(
        PipelineStepStatus(
            step_number=6,
            step_name="Persist Claim Record to Firebase / Firestore",
            service_used=f"Firebase Cloud Firestore ({FIRESTORE_COLLECTION})",
            status="COMPLETED" if fs_ok else "FALLBACK",
            duration_ms=max(1, int((t1 - t0) * 1000)),
            details=fs_detail,
        )
    )
    # Update saved record with final 6th step telemetry
    firestore_service.save_claim(record)
    return record


@app.get("/api/health")
def get_health():
    """Returns live status of all configured Google Cloud services."""
    return {
        "status": "ok",
        "project_id": GCP_PROJECT_ID,
        "bucket_name": GCS_BUCKET_NAME,
        "services": {
            "cloud_storage": storage_service.check_bucket_status(),
            "document_ai": docai_service.check_status(),
            "cloud_translation": translation_service.check_status(),
            "gemini_llm": gemini_service.check_status(),
            "firebase_firestore": firestore_service.check_status(),
        },
    }


@app.get("/api/samples")
def list_sample_documents():
    """Returns metadata for the 4 built-in realistic test PDFs (English, Spanish, French, Korean)."""
    samples = []
    for key, meta in SAMPLE_DOCUMENTS_METADATA.items():
        pdf_path = SAMPLE_DOCS_DIR / meta["filename"]
        samples.append(
            {
                **meta,
                "exists": pdf_path.exists(),
                "size_bytes": pdf_path.stat().st_size if pdf_path.exists() else 0,
                "preview_url": f"/api/samples/{key}/pdf",
            }
        )
    return {"samples": samples}


@app.get("/api/samples/{sample_id}/pdf")
def get_sample_pdf(sample_id: str):
    """Streams one of the 4 raw test PDFs directly."""
    meta = SAMPLE_DOCUMENTS_METADATA.get(sample_id.lower())
    if not meta:
        raise HTTPException(status_code=404, detail=f"Unknown sample_id '{sample_id}'")
    pdf_path = SAMPLE_DOCS_DIR / meta["filename"]
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail=f"Sample PDF '{meta['filename']}' not found on disk")
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{meta["filename"]}"'},
    )


@app.post("/api/claims/upload", response_model=ProcessedClaimRecord)
async def upload_and_process_claim(file: UploadFile = File(...)):
    """Uploads a PDF document and runs the full Healthcare Claims Processing & Translation pipeline."""
    filename = file.filename or "uploaded_claim.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF documents (.pdf) are supported.")
    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded PDF file is empty.")
    return execute_claims_pipeline(pdf_bytes=pdf_bytes, filename=filename)


@app.post("/api/claims/process-sample/{sample_id}", response_model=ProcessedClaimRecord)
def process_sample_claim(sample_id: str):
    """Runs the full pipeline on one of the 4 realistic test PDFs (english, spanish, french, korean)."""
    meta = SAMPLE_DOCUMENTS_METADATA.get(sample_id.lower())
    if not meta:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown sample_id '{sample_id}'. Valid options: {list(SAMPLE_DOCUMENTS_METADATA.keys())}",
        )
    pdf_path = SAMPLE_DOCS_DIR / meta["filename"]
    if not pdf_path.exists():
        # Auto-generate sample PDFs if not yet generated
        from scripts.generate_test_pdfs import main as generate_pdfs
        generate_pdfs()
    pdf_bytes = pdf_path.read_bytes()
    return execute_claims_pipeline(
        pdf_bytes=pdf_bytes,
        filename=meta["filename"],
        sample_id=sample_id.lower(),
    )


@app.post("/api/claims/process-all-samples")
def process_all_samples():
    """Processes all 4 test documents (English, Spanish, French, Korean) sequentially."""
    results = []
    for sample_id in ("english", "spanish", "french", "korean"):
        rec = process_sample_claim(sample_id)
        results.append(rec)
    return {"processed_count": len(results), "claims": results}


@app.get("/api/claims")
def list_processed_claims():
    """Returns all processed claims stored in Firebase / Cloud Firestore."""
    records = firestore_service.list_claims(limit=50)
    return {"claims": records}


@app.get("/api/claims/{claim_id}", response_model=ProcessedClaimRecord)
def get_processed_claim(claim_id: str):
    """Retrieves a specific processed claim by ID."""
    record = firestore_service.get_claim(claim_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Claim '{claim_id}' not found.")
    return record


@app.get("/api/claims/{claim_id}/pdf/original")
def get_original_claim_pdf(claim_id: str):
    """Streams the original uploaded PDF for the UI viewer."""
    record = firestore_service.get_claim(claim_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Claim '{claim_id}' not found.")
    pdf_bytes = storage_service.get_pdf_bytes(
        claim_id=claim_id,
        filename=record.original_filename,
        folder="originals",
    )
    if not pdf_bytes:
        raise HTTPException(status_code=404, detail="Original PDF binary not found.")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{record.original_filename}"'},
    )


@app.get("/api/claims/{claim_id}/pdf/translated")
def get_translated_claim_pdf(claim_id: str):
    """Streams the Clean English Representation PDF (or original if already English) for side-by-side comparison."""
    record = firestore_service.get_claim(claim_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Claim '{claim_id}' not found.")

    if not record.was_translated:
        return get_original_claim_pdf(claim_id)

    clean_filename = f"clean_english_{Path(record.original_filename).name}"
    pdf_bytes = storage_service.get_pdf_bytes(
        claim_id=claim_id,
        filename=clean_filename,
        folder="translated",
    )
    if not pdf_bytes:
        raise HTTPException(status_code=404, detail="Clean English PDF binary not found.")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{clean_filename}"'},
    )


# Serve static frontend assets
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
def serve_frontend():
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        return {"message": "Backend running. Frontend index.html not found."}
    return FileResponse(str(index_path))
