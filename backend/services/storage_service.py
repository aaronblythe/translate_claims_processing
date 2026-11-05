"""
Google Cloud Storage Service for storing initial uploaded PDFs and
translated Clean English Representation PDFs in the configured GCS bucket.
"""

import logging
from pathlib import Path
from typing import Optional
from google.api_core.client_options import ClientOptions
from google.api_core.gapic_v1.client_info import ClientInfo
from google.cloud import storage

from backend.config import GCP_PROJECT_ID, GCS_BUCKET_NAME, LOCAL_GCS_MIRROR_DIR

logger = logging.getLogger(__name__)


class CloudStorageService:
    """Manages document storage in Google Cloud Storage with local mirror caching."""

    def __init__(self, project_id: str = GCP_PROJECT_ID, bucket_name: str = GCS_BUCKET_NAME):
        self.project_id = project_id
        self.bucket_name = bucket_name
        self._client: Optional[storage.Client] = None
        self._bucket_available: Optional[bool] = None

    def _get_client(self) -> storage.Client:
        if self._client is None:
            self._client = storage.Client(
                project=self.project_id,
                client_options=ClientOptions(quota_project_id=self.project_id),
                client_info=ClientInfo(user_agent="gcs-skills/1.0 (skill:google-cloud-storage-basics)"),
            )
        return self._client

    def check_bucket_status(self) -> dict:
        """Checks whether the configured GCS bucket exists and is accessible."""
        try:
            client = self._get_client()
            bucket = client.lookup_bucket(self.bucket_name, timeout=5, retry=None)
            if bucket is not None:
                self._bucket_available = True
                return {
                    "available": True,
                    "bucket_name": self.bucket_name,
                    "location": bucket.location,
                    "storage_class": bucket.storage_class,
                }
            self._bucket_available = False
            return {
                "available": False,
                "bucket_name": self.bucket_name,
                "reason": "Bucket not yet created in project",
            }
        except Exception as exc:
            self._bucket_available = False
            return {
                "available": False,
                "bucket_name": self.bucket_name,
                "reason": str(exc),
            }

    def store_pdf(
        self,
        claim_id: str,
        filename: str,
        pdf_bytes: bytes,
        folder: str = "originals",
        language_code: str = "unknown",
    ) -> tuple[str, bool, str]:
        """
        Stores a PDF in GCS (`gs://{bucket}/{folder}/{claim_id}/{filename}`) and
        always saves a local mirror copy for fast streaming in the UI.
        Returns (gcs_uri, uploaded_to_remote_gcs, status_detail).
        """
        safe_name = Path(filename).name
        object_name = f"{folder}/{claim_id}/{safe_name}"
        gcs_uri = f"gs://{self.bucket_name}/{object_name}"

        # Always persist to local mirror for zero-latency UI PDF viewing
        local_path = LOCAL_GCS_MIRROR_DIR / folder / claim_id / safe_name
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(pdf_bytes)

        if self._bucket_available is None:
            self.check_bucket_status()

        if not self._bucket_available:
            return (
                gcs_uri,
                False,
                f"Staged {len(pdf_bytes):,} bytes for {gcs_uri} (local GCS mirror active)",
            )

        try:
            client = self._get_client()
            bucket = client.bucket(self.bucket_name)
            blob = bucket.blob(object_name)
            blob.metadata = {
                "claim_id": claim_id,
                "folder": folder,
                "language_code": language_code,
                "project": self.project_id,
            }
            blob.upload_from_string(pdf_bytes, content_type="application/pdf", timeout=10, retry=None)
            return (
                gcs_uri,
                True,
                f"Uploaded {len(pdf_bytes):,} bytes to {gcs_uri}",
            )
        except Exception as exc:
            self._bucket_available = False
            logger.warning("GCS upload fallback to local mirror for %s: %s", gcs_uri, exc)
            return (
                gcs_uri,
                False,
                f"Staged {len(pdf_bytes):,} bytes for {gcs_uri} (local mirror active: {exc})",
            )

    def get_pdf_bytes(self, claim_id: str, filename: str, folder: str = "originals") -> Optional[bytes]:
        """Retrieves PDF bytes from local mirror first, falling back to GCS bucket."""
        safe_name = Path(filename).name
        local_path = LOCAL_GCS_MIRROR_DIR / folder / claim_id / safe_name
        if local_path.exists():
            return local_path.read_bytes()

        object_name = f"{folder}/{claim_id}/{safe_name}"
        try:
            client = self._get_client()
            bucket = client.bucket(self.bucket_name)
            blob = bucket.blob(object_name)
            if blob.exists():
                data = blob.download_as_bytes(timeout=30)
                local_path.parent.mkdir(parents=True, exist_ok=True)
                local_path.write_bytes(data)
                return data
        except Exception as exc:
            logger.warning("Failed to fetch %s from GCS: %s", object_name, exc)
        return None
