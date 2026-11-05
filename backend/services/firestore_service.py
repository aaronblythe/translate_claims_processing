"""
Firebase / Google Cloud Firestore Service for persisting processed healthcare
claims records, translation segments, and pipeline telemetry.
"""

import json
import logging
from typing import Optional
import firebase_admin
from google.api_core.client_options import ClientOptions
from google.cloud import firestore

from backend.config import GCP_PROJECT_ID, FIRESTORE_COLLECTION, LOCAL_FIRESTORE_CACHE
from backend.models import ProcessedClaimRecord

logger = logging.getLogger(__name__)


class FirestoreClaimsService:
    """Persists and queries processed claims in Firebase / Cloud Firestore."""

    def __init__(self, project_id: str = GCP_PROJECT_ID, collection_name: str = FIRESTORE_COLLECTION):
        self.project_id = project_id
        self.collection_name = collection_name
        self._db: Optional[firestore.Client] = None
        self._available: Optional[bool] = None
        self._init_firebase_app()

    def _init_firebase_app(self):
        try:
            if not firebase_admin._apps:
                firebase_admin.initialize_app(options={"projectId": self.project_id})
        except Exception as exc:
            logger.debug("Firebase Admin init note: %s", exc)

    def _get_db(self) -> firestore.Client:
        if self._db is None:
            opts = ClientOptions(quota_project_id=self.project_id)
            self._db = firestore.Client(
                project=self.project_id,
                database="(default)",
                client_options=opts,
            )
        return self._db

    def _read_local_cache(self) -> dict[str, dict]:
        if LOCAL_FIRESTORE_CACHE.exists():
            try:
                return json.loads(LOCAL_FIRESTORE_CACHE.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _write_local_cache(self, cache: dict[str, dict]):
        LOCAL_FIRESTORE_CACHE.parent.mkdir(parents=True, exist_ok=True)
        LOCAL_FIRESTORE_CACHE.write_text(
            json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def check_status(self) -> dict:
        """Checks whether Cloud Firestore `(default)` database is reachable in the configured project."""
        try:
            db = self._get_db()
            list(db.collection(self.collection_name).limit(1).stream(timeout=4, retry=None))
            self._available = True
            return {
                "available": True,
                "project_id": self.project_id,
                "database": "(default)",
                "collection": self.collection_name,
            }
        except Exception as exc:
            self._available = False
            return {
                "available": False,
                "project_id": self.project_id,
                "database": "(default)",
                "collection": self.collection_name,
                "reason": str(exc),
            }

    def save_claim(self, record: ProcessedClaimRecord) -> tuple[str, bool, str]:
        """
        Saves a `ProcessedClaimRecord` to Cloud Firestore and mirrors to local cache.
        Returns `(doc_path, saved_to_remote_firestore, status_message)`.
        """
        doc_path = f"projects/{self.project_id}/databases/(default)/documents/{self.collection_name}/{record.claim_id}"
        payload = record.model_dump()

        # Always update local cache mirror
        cache = self._read_local_cache()
        cache[record.claim_id] = payload
        self._write_local_cache(cache)

        if self._available is False:
            return (
                doc_path,
                False,
                f"Persisted claim {record.claim_id} to local Firestore mirror",
            )

        try:
            db = self._get_db()
            doc_ref = db.collection(self.collection_name).document(record.claim_id)
            doc_ref.set(payload, timeout=6, retry=None)
            self._available = True
            return (
                doc_path,
                True,
                f"Persisted claim {record.claim_id} to Firebase Firestore ({self.collection_name}/{record.claim_id})",
            )
        except Exception as exc:
            self._available = False
            logger.warning("Firestore write fallback to local cache for %s: %s", record.claim_id, exc)
            return (
                doc_path,
                False,
                f"Persisted claim {record.claim_id} to local Firestore mirror ({exc})",
            )

    def get_claim(self, claim_id: str) -> Optional[ProcessedClaimRecord]:
        """Retrieves a single `ProcessedClaimRecord` by ID from local mirror or Firestore."""
        cache = self._read_local_cache()
        if claim_id in cache:
            try:
                return ProcessedClaimRecord.model_validate(cache[claim_id])
            except Exception:
                pass

        if self._available is False:
            return None

        try:
            db = self._get_db()
            snap = db.collection(self.collection_name).document(claim_id).get(timeout=4, retry=None)
            if snap.exists:
                data = snap.to_dict()
                if data:
                    cache[claim_id] = data
                    self._write_local_cache(cache)
                    return ProcessedClaimRecord.model_validate(data)
        except Exception as exc:
            self._available = False
            logger.warning("Firestore get_claim fallback: %s", exc)
        return None

    def list_claims(self, limit: int = 50) -> list[ProcessedClaimRecord]:
        """Lists processed claims ordered by `created_at` descending."""
        cache = self._read_local_cache()
        if self._available is not False and not cache:
            try:
                db = self._get_db()
                docs = (
                    db.collection(self.collection_name)
                    .order_by("created_at", direction=firestore.Query.DESCENDING)
                    .limit(limit)
                    .stream(timeout=4, retry=None)
                )
                for d in docs:
                    data = d.to_dict()
                    if data and "claim_id" in data:
                        cache[data["claim_id"]] = data
                self._write_local_cache(cache)
                self._available = True
            except Exception as exc:
                self._available = False
                logger.debug("Listing claims from local mirror cache (%s)", exc)

        records: list[ProcessedClaimRecord] = []
        for item in cache.values():
            try:
                records.append(ProcessedClaimRecord.model_validate(item))
            except Exception:
                pass
        records.sort(key=lambda r: r.created_at, reverse=True)
        return records[:limit]
