# Google Cloud Architecture — Healthcare Claims Document Processing & Translation Platform

**Configuration:** Loaded from `.env.gcp` (template: [`.env.gcp.example`](.env.gcp.example), protected by [`.gitignore`](.gitignore))  
**Primary Region:** `us-central1` (Document AI Multi-Region: `us`, Translation Location: `global`)  

---

## 1. Google Cloud Services Architecture Diagram

The diagram below illustrates how all Google Cloud Platform (GCP) and Firebase services in the configured project (`$GCP_PROJECT_ID`) work together to ingest, inspect, translate, compare, extract, and persist healthcare claims documents.

```mermaid
flowchart TB
    User["Claims Adjuster / Browser Client"]

    subgraph GCP["Google Cloud Project: $GCP_PROJECT_ID ($GCP_PROJECT_NUMBER)"]
        
        subgraph Compute["Serverless Compute & Web Tier (us-central1)"]
            CloudRun["Google Cloud Run\nService: claims-processor-app\n(FastAPI Backend + Web Workbench UI)"]
        end

        subgraph StorageTier["Cloud Storage Tier (us-central1)"]
            GCS_Orig[("Google Cloud Storage\ngs://$GCS_BUCKET_NAME\nPrefix: originals/{claim_id}/")]
            GCS_Trans[("Google Cloud Storage\ngs://$GCS_BUCKET_NAME\nPrefix: translated/{claim_id}/")]
        end

        subgraph DocIntel["Document AI & Cloud Translation Tier"]
            DocAI["Google Cloud Document AI\nProcessor: claims-ocr-processor ($DOCAI_PROCESSOR_ID)\nLocation: us (OCR, Layout & Table Extraction)"]
            
            subgraph TransAPI["Google Cloud Translation API v3 Advanced (global)"]
                DetectLang["detect_language\nImmediate Language Verification"]
                LangRouter{"Language == English (en)?"}
                TransDoc["translate_document\nNative PDF Layout-Preserved Translation\n(application/pdf -> English PDF)"]
                TransText["translate_text\nNMT Block & Table Cell Translation\n(Aligned UI Comparison Segments)"]
            end
        end

        subgraph GenAITier["Generative AI & Medical Coding Tier"]
            Gemini["Gemini API (gemini-3.8-flash)\ngoogle-genai Interactions API\nStructured Claims JSON + ICD-10 / CPT Extraction"]
        end

        subgraph DatabaseTier["Persistence & State Tier (us-central1)"]
            Firestore[("Firebase / Cloud Firestore\nDatabase: (default) Native Mode\nCollection: claims_documents")]
        end

        subgraph DevOpsIAM["Build, Registry & Identity Services"]
            CloudBuild["Google Cloud Build\nContainer Image Builder"]
            ArtifactReg["Google Cloud Artifact Registry\nDocker Container Repository"]
            IAM["Cloud IAM & ADC\nService Account & Quota Governance"]
        end
    end

    %% User & Compute Interactions
    User -->|"1. Upload PDF (EN, ES, FR, KO) or View Workbench"| CloudRun
    CloudRun -->|"2. Store Raw Uploaded PDF"| GCS_Orig
    CloudRun -->|"3. ProcessDocument (application/pdf)"| DocAI
    DocAI -->|"Extracted Text, Layout Blocks & Tables"| CloudRun
    CloudRun -->|"4. Immediate Language Check"| DetectLang
    DetectLang --> LangRouter

    %% Conditional Language Routing
    LangRouter -->|"Yes (English) — Bypass Translation"| Gemini
    LangRouter -->|"No (Spanish, French, Korean, etc.)"| TransDoc
    LangRouter -->|"No (Spanish, French, Korean, etc.)"| TransText

    %% Non-English Translation Path
    TransDoc -->|"5a. Save Layout-Preserved Clean English PDF"| GCS_Trans
    TransDoc -->|"5b. Pass Translated English PDF"| Gemini
    TransText -->|"Aligned Source vs. English Segments"| CloudRun

    %% Gemini & Persistence
    Gemini -->|"6. Validated ClaimExtractionResult\n(ICD-10, CPT/HCPCS, CMS-1500 Readiness)"| CloudRun
    CloudRun -->|"7. Persist Claim Record & Audit Trail"| Firestore

    %% UI Comparison & Retrieval
    GCS_Orig -.->|"Stream Original PDF"| CloudRun
    GCS_Trans -.->|"Stream Translated English PDF"| CloudRun
    Firestore -.->|"Load Claims History & Telemetry"| CloudRun

    %% Deployment & Security Relationships
    CloudBuild -->|"Push Image"| ArtifactReg
    ArtifactReg -->|"Deploy Revision"| CloudRun
    IAM -.->|"Authenticate SDK Calls"| CloudRun
```

---

## 2. End-to-End Google Cloud Service Call Sequence

This sequence diagram details the runtime API interactions across Google Cloud services for every uploaded document, showing both the **Direct English Path** and the **Non-English Document Translation Path**.

```mermaid
sequenceDiagram
    autonumber
    actor User as Claims Adjuster
    participant Run as Google Cloud Run (FastAPI + UI)
    participant GCS as Google Cloud Storage ($GCS_BUCKET_NAME)
    participant DocAI as Google Cloud Document AI (OCR)
    participant Trans as Cloud Translation API v3 (Advanced)
    participant Gemini as Gemini API (gemini-3.8-flash)
    participant FS as Firebase / Cloud Firestore

    User->>Run: POST /api/claims/upload (PDF Document)
    Run->>GCS: Upload raw PDF to originals/{claim_id}/{filename}
    GCS-->>Run: gs://$GCS_BUCKET_NAME/originals/...

    Run->>DocAI: process_document(raw_document=application/pdf)
    DocAI-->>Run: OCR text, layout paragraphs, tables, page language signals

    Run->>Trans: detect_language(content=extracted_text)
    Trans-->>Run: Detected language code (en, es, fr, ko) + confidence score

    alt Detected Language is English (en)
        Note over Run,Gemini: Direct English Processing Path (No Translation Needed)
        Run->>Gemini: interactions.create(model="gemini-3.8-flash", original_english_pdf + text)
    else Detected Language is Non-English (es, fr, ko, etc.)
        Note over Run,Trans: Advanced Document Translation & Layout Preservation Path
        Run->>Trans: translate_document(DocumentInputConfig=application/pdf, target="en")
        Trans-->>Run: byte_stream_outputs[0] (Layout-Preserved English PDF bytes)
        Run->>GCS: Upload Clean English PDF to translated/{claim_id}/clean_english_{filename}
        GCS-->>Run: gs://$GCS_BUCKET_NAME/translated/...
        Run->>Trans: translate_text(contents=layout_segments, target="en")
        Trans-->>Run: Translated English segments for side-by-side text diff
        Run->>Gemini: interactions.create(model="gemini-3.8-flash", clean_english_pdf + translated_text)
    end

    Gemini-->>Run: Structured JSON (ClaimExtractionResult: Patient, Provider, ICD-10, CPT, Readiness)
    Run->>FS: collection("claims_documents").document(claim_id).set(record)
    FS-->>Run: Write confirmed

    Run-->>User: ProcessedClaimRecord JSON + Side-by-Side Original vs. English PDF Viewer
```

---

## 3. Data & Storage Flow Across Google Cloud Services

```mermaid
flowchart LR
    subgraph Inputs["Incoming Claims PDFs (4 Distinct Formats)"]
        EN["English (en)\nUS CMS-1500 / UB-04 Bill"]
        ES["Spanish (es)\nMexican CFDI 4.0 Invoice"]
        FR["French (fr)\nEuropean Referral & Prior Auth"]
        KO["Korean (ko)\nKorean Boxed Hospital Receipt"]
    end

    subgraph GCSBucket["Google Cloud Storage: gs://$GCS_BUCKET_NAME"]
        OrigFolder["/originals/{claim_id}/\nImmutable Source PDFs"]
        TransFolder["/translated/{claim_id}/\nLayout-Preserved English PDFs"]
    end

    subgraph CloudServices["Google Cloud AI & Data Services"]
        DocAI_Node["Document AI\nOCR & Table Parser"]
        Trans_Node["Cloud Translation v3\ndetect_language & translate_document"]
        Gemini_Node["Gemini 3.8 Flash\nMedical Coding & Claim Extraction"]
        Firestore_Node[("Cloud Firestore\nclaims_documents")]
    end

    EN & ES & FR & KO --> OrigFolder
    OrigFolder --> DocAI_Node
    OrigFolder --> Trans_Node
    DocAI_Node --> Trans_Node
    Trans_Node -->|"es, fr, ko -> en PDF"| TransFolder
    OrigFolder -->|"en PDF"| Gemini_Node
    TransFolder -->|"Translated en PDF"| Gemini_Node
    Gemini_Node --> Firestore_Node
```

---

## 4. Google Cloud Services Inventory & Implementation Mapping

| Google Cloud Service | Enabled API | Provisioned Resource / Configuration (via `.env.gcp`) | Role in Architecture | Backend Implementation |
| :--- | :--- | :--- | :--- | :--- |
| **Google Cloud Run** | `run.googleapis.com` | Service `$CLOUD_RUN_SERVICE` (`claims-processor-app`) in `$GCP_REGION` (`us-central1`) | Hosts the containerized FastAPI backend orchestrator and serves the interactive Claims Workbench & Side-by-Side PDF Comparator UI. | [`backend/main.py`](backend/main.py), [`Dockerfile`](Dockerfile) |
| **Google Cloud Storage** | `storage.googleapis.com` | Bucket `gs://${GCS_BUCKET_NAME}` (`us-central1`, `STANDARD`, UBLA, PAP Enforced, 7d Soft Delete, 2555d Lifecycle) | Stores immutable original uploaded PDFs (`originals/{claim_id}/`) and layout-preserved translated English PDFs (`translated/{claim_id}/`). | [`backend/services/storage_service.py`](backend/services/storage_service.py) |
| **Google Cloud Document AI** | `documentai.googleapis.com` | Processor `projects/${GCP_PROJECT_NUMBER}/locations/${DOCAI_LOCATION}/processors/${DOCAI_PROCESSOR_ID}` (`claims-ocr-processor`, `OCR_PROCESSOR`) | Extracts text, structural paragraphs, bounding layouts, tables, and page-level language signals from uploaded PDFs. | [`backend/services/document_ai_service.py`](backend/services/document_ai_service.py) |
| **Google Cloud Translation API v3 (Advanced)** | `translate.googleapis.com` | Parent `projects/${GCP_PROJECT_ID}/locations/global` (`detect_language`, `translate_document`, `translate_text`) | 1. Immediately detects document language.<br/>2. Translates non-English PDFs in-place via `translate_document` while preserving visual layout.<br/>3. Translates text blocks for aligned diff comparison. | [`backend/services/translation_service.py`](backend/services/translation_service.py) |
| **Gemini API (`google-genai`)** | `generativelanguage.googleapis.com`, `aiplatform.googleapis.com` | Model `gemini-3.8-flash` via `client.interactions.create` with strict JSON Schema | Performs multimodal extraction of patient/provider/payer fields, extracts or suggests `ICD-10-CM` and `CPT/HCPCS` codes, and computes CMS-1500 adjudication readiness. | [`backend/services/gemini_service.py`](backend/services/gemini_service.py) |
| **Firebase / Cloud Firestore** | `firestore.googleapis.com`, `firebaserules.googleapis.com` | Database `projects/${GCP_PROJECT_ID}/databases/(default)` (`us-central1`), collection `claims_documents` | Persists processed claims records, translation metadata, pipeline telemetry steps, and GCS document references. | [`backend/services/firestore_service.py`](backend/services/firestore_service.py), [`firestore.rules`](firestore.rules) |
| **Cloud Build & Artifact Registry** | `cloudbuild.googleapis.com`, `artifactregistry.googleapis.com` | Regional image build & container registry in `$GCP_REGION` (`us-central1`) | Builds the application container image and deploys immutable revisions to Cloud Run via `./deploy.sh --cloud-run`. | [`deploy.sh`](deploy.sh) |
| **Cloud IAM & Resource Manager** | `iam.googleapis.com`, `cloudresourcemanager.googleapis.com` | Project `$GCP_PROJECT_ID` (`$GCP_PROJECT_NUMBER`) ADC & Service Account bindings | Authenticates service-to-service API requests and enforces project quota attribution. | [`backend/config.py`](backend/config.py) |
