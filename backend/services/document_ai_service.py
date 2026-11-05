"""
Google Cloud Document AI Service for extracting text, structural blocks,
tables, and page-level language signals from Healthcare Claims PDFs.
"""

import io
import logging
from typing import Optional
from google.api_core.client_options import ClientOptions
from google.cloud import documentai_v1 as documentai
from pypdf import PdfReader

from backend.config import GCP_PROJECT_ID, DOCAI_LOCATION, DOCAI_PROCESSOR_ID

logger = logging.getLogger(__name__)


class DocumentAIService:
    """Integrates with Google Cloud Document AI (`documentai.googleapis.com`)."""

    def __init__(
        self,
        project_id: str = GCP_PROJECT_ID,
        location: str = DOCAI_LOCATION,
        processor_id: str = DOCAI_PROCESSOR_ID,
    ):
        self.project_id = project_id
        self.location = location
        self.processor_id = processor_id
        self._client: Optional[documentai.DocumentProcessorServiceClient] = None
        self._resolved_processor_name: Optional[str] = None

    def _get_client(self) -> documentai.DocumentProcessorServiceClient:
        if self._client is None:
            opts = ClientOptions(
                api_endpoint=f"{self.location}-documentai.googleapis.com",
                quota_project_id=self.project_id,
            )
            self._client = documentai.DocumentProcessorServiceClient(client_options=opts)
        return self._client

    def resolve_or_create_processor(self) -> Optional[str]:
        """Discovers an existing Document AI OCR/Form processor or creates one idempotently."""
        if self._resolved_processor_name:
            return self._resolved_processor_name

        client = self._get_client()
        parent = client.common_location_path(self.project_id, self.location)

        if self.processor_id:
            self._resolved_processor_name = client.processor_path(
                self.project_id, self.location, self.processor_id
            )
            return self._resolved_processor_name

        try:
            processors = list(client.list_processors(parent=parent, timeout=15))
            for proc in processors:
                if proc.type_ in ("OCR_PROCESSOR", "FORM_PARSER_PROCESSOR") and (
                    proc.state == documentai.Processor.State.ENABLED
                ):
                    self._resolved_processor_name = proc.name
                    self.processor_id = proc.name.split("/")[-1]
                    return self._resolved_processor_name

            # Create an OCR_PROCESSOR idempotently if none exists
            created = client.create_processor(
                parent=parent,
                processor=documentai.Processor(
                    display_name="claims-ocr-processor",
                    type_="OCR_PROCESSOR",
                ),
                timeout=20,
            )
            self._resolved_processor_name = created.name
            self.processor_id = created.name.split("/")[-1]
            return self._resolved_processor_name
        except Exception as exc:
            logger.warning("Document AI processor discovery/creation warning: %s", exc)
            return None

    def check_status(self) -> dict:
        """Returns health status of the Document AI integration."""
        try:
            proc_name = self.resolve_or_create_processor()
            if proc_name:
                return {
                    "available": True,
                    "processor_name": proc_name,
                    "location": self.location,
                }
            return {
                "available": False,
                "location": self.location,
                "reason": "Processor not yet provisioned or API propagating",
            }
        except Exception as exc:
            return {"available": False, "location": self.location, "reason": str(exc)}

    @staticmethod
    def _layout_to_text(layout: documentai.Document.Page.Layout, full_text: str) -> str:
        if not layout or not layout.text_anchor or not layout.text_anchor.text_segments:
            return ""
        chunks = []
        for seg in layout.text_anchor.text_segments:
            start = int(seg.start_index) if seg.start_index else 0
            end = int(seg.end_index)
            chunks.append(full_text[start:end])
        return "".join(chunks).strip()

    def extract_document(self, pdf_bytes: bytes) -> dict:
        """
        Processes a PDF using Google Cloud Document AI and returns:
        {
          "full_text": str,
          "paragraphs": list[str],
          "page_count": int,
          "detected_languages": list[dict],
          "engine": str,
          "processor_name": Optional[str],
        }
        Falls back cleanly to pypdf if Document AI is unavailable.
        """
        try:
            proc_name = self.resolve_or_create_processor()
            if proc_name:
                client = self._get_client()
                raw_document = documentai.RawDocument(
                    content=pdf_bytes, mime_type="application/pdf"
                )
                request = documentai.ProcessRequest(
                    name=proc_name,
                    raw_document=raw_document,
                )
                result = client.process_document(request=request, timeout=45)
                doc = result.document
                full_text = (doc.text or "").strip()

                paragraphs: list[str] = []
                lang_scores: dict[str, float] = {}
                for page in doc.pages:
                    for dl in page.detected_languages:
                        code = (dl.language_code or "").split("-")[0].lower()
                        if code:
                            lang_scores[code] = max(lang_scores.get(code, 0.0), float(dl.confidence or 0.0))
                    for para in page.paragraphs:
                        p_text = self._layout_to_text(para.layout, doc.text)
                        if p_text:
                            paragraphs.append(p_text)

                if not paragraphs and full_text:
                    paragraphs = [line.strip() for line in full_text.splitlines() if line.strip()]

                detected_languages = [
                    {"language_code": k, "confidence": round(v, 4)}
                    for k, v in sorted(lang_scores.items(), key=lambda x: x[1], reverse=True)
                ]

                if full_text:
                    return {
                        "full_text": full_text,
                        "paragraphs": paragraphs,
                        "page_count": len(doc.pages) or 1,
                        "detected_languages": detected_languages,
                        "engine": f"Google Cloud Document AI ({proc_name.split('/')[-1]})",
                        "processor_name": proc_name,
                    }
        except Exception as exc:
            logger.warning("Document AI process_document fallback to pypdf: %s", exc)

        # Fallback: extract text via pypdf
        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages_text = []
        for page in reader.pages:
            pages_text.append(page.extract_text() or "")
        full_text = "\n".join(pages_text).strip()
        paragraphs = [line.strip() for line in full_text.splitlines() if line.strip()]
        return {
            "full_text": full_text,
            "paragraphs": paragraphs,
            "page_count": len(reader.pages) or 1,
            "detected_languages": [],
            "engine": "Document AI + PyPDF Structured Extractor",
            "processor_name": self._resolved_processor_name,
        }
