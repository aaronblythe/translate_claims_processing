"""Pydantic data models for Healthcare Claims Extraction, Translation, and Firestore Persistence."""

from typing import Optional
from pydantic import BaseModel, Field


class DocumentClassification(BaseModel):
    document_type: str = Field(
        description=(
            "Primary category of the healthcare claim document. One of: "
            "ITEMIZED_MEDICAL_BILL_CODED, ITEMIZED_MEDICAL_BILL_UNCODED, "
            "INSURANCE_CARD, POLICY_DETAILS, PROOF_OF_PAYMENT, MEDICAL_RECORD, "
            "REFERRAL, PRIOR_AUTHORIZATION, OTHER_CLAIM_DOCUMENT"
        )
    )
    secondary_types: list[str] = Field(
        default_factory=list,
        description="Additional document types included in the packet (e.g. PROOF_OF_PAYMENT, MEDICAL_RECORD).",
    )
    confidence: float = Field(description="Classification confidence score between 0.0 and 1.0")
    executive_summary: str = Field(
        description="Concise English summary of the document for the healthcare claims adjuster."
    )


class PatientInformation(BaseModel):
    full_name: Optional[str] = Field(default=None, description="Patient full legal name")
    date_of_birth: Optional[str] = Field(default=None, description="Patient DOB in YYYY-MM-DD format if available")
    gender: Optional[str] = Field(default=None, description="Patient gender/sex")
    member_id: Optional[str] = Field(default=None, description="Insurance Member / Subscriber ID")
    group_number: Optional[str] = Field(default=None, description="Insurance Group Number")
    address: Optional[str] = Field(default=None, description="Patient residential address")
    phone: Optional[str] = Field(default=None, description="Patient contact phone number")
    relationship_to_subscriber: Optional[str] = Field(
        default="Self", description="Relationship to primary policy subscriber (Self, Spouse, Child, Other)"
    )


class ProviderInformation(BaseModel):
    facility_name: Optional[str] = Field(default=None, description="Hospital, clinic, or medical facility name")
    attending_physician: Optional[str] = Field(default=None, description="Treating or attending doctor name")
    referring_physician: Optional[str] = Field(default=None, description="Referring physician name if applicable")
    specialty: Optional[str] = Field(default=None, description="Medical specialty or department")
    npi_or_registration_id: Optional[str] = Field(
        default=None, description="US NPI number or international medical facility/provider registration ID"
    )
    tax_id_or_business_id: Optional[str] = Field(
        default=None, description="Tax ID (EIN, RFC, SIRET, Korean Business Registration Number, etc.)"
    )
    address: Optional[str] = Field(default=None, description="Facility physical address")
    country: Optional[str] = Field(default=None, description="Country where medical service was rendered")
    phone: Optional[str] = Field(default=None, description="Provider contact telephone")


class InsurancePolicyInformation(BaseModel):
    payer_name: Optional[str] = Field(default=None, description="Insurance carrier / payer name")
    plan_name: Optional[str] = Field(default=None, description="Specific insurance plan or network name")
    policy_or_member_id: Optional[str] = Field(default=None, description="Policy or Member ID number")
    group_number: Optional[str] = Field(default=None, description="Group ID number")
    prior_authorization_number: Optional[str] = Field(
        default=None, description="Prior authorization or pre-certification reference number"
    )
    authorization_valid_dates: Optional[str] = Field(
        default=None, description="Validity date range for prior authorization or referral"
    )
    claim_or_invoice_number: Optional[str] = Field(
        default=None, description="Hospital invoice, folio, or claim reference number"
    )
    benefit_notes: Optional[str] = Field(
        default=None, description="Copay, deductible, coinsurance, or coverage notes"
    )


class DiagnosisItem(BaseModel):
    code: str = Field(description="ICD-10-CM diagnosis code (either extracted from document or AI-suggested)")
    code_system: str = Field(default="ICD-10-CM", description="Coding system, e.g. ICD-10-CM, CIM-10, KCD-8")
    code_source: str = Field(
        description="EXTRACTED if explicitly printed in the source document, or AI_SUGGESTED if inferred by Gemini from clinical descriptions"
    )
    description_english: str = Field(description="Standard English clinical description of the diagnosis")
    is_primary: bool = Field(default=False, description="True if this is the primary/principal diagnosis")


class ProcedureLineItem(BaseModel):
    line_number: int = Field(description="Sequential line item number (1-indexed)")
    service_date: Optional[str] = Field(default=None, description="Date of service (YYYY-MM-DD)")
    procedure_code: str = Field(
        description="Standardized CPT or HCPCS code (either extracted or AI-suggested for uncoded bills)"
    )
    original_local_code: Optional[str] = Field(
        default=None, description="Original local/internal hospital code if different from CPT/HCPCS"
    )
    code_system: str = Field(default="CPT", description="CPT, HCPCS, Revenue, or Local")
    code_source: str = Field(
        description="EXTRACTED if standard CPT/HCPCS was printed on the document, or AI_SUGGESTED if mapped by AI for claims readiness"
    )
    description_english: str = Field(description="Clean English description of the medical service, procedure, or supply")
    quantity: float = Field(default=1.0, description="Number of units or quantity billed")
    unit_price_original: str = Field(description="Formatted unit price in original currency")
    total_charge_original: str = Field(description="Formatted line total in original currency")
    estimated_usd_amount: Optional[float] = Field(
        default=None, description="Estimated line total in USD for claims adjudication"
    )


class FinancialSummary(BaseModel):
    service_date_start: Optional[str] = Field(default=None, description="First date of service (YYYY-MM-DD)")
    service_date_end: Optional[str] = Field(default=None, description="Last date of service (YYYY-MM-DD)")
    original_currency: str = Field(default="USD", description="ISO currency code (USD, MXN, EUR, KRW, etc.)")
    total_billed_original: str = Field(description="Total gross charges in original currency")
    total_billed_usd_estimate: float = Field(description="Total gross charges converted/estimated in USD")
    amount_paid_by_patient: Optional[str] = Field(
        default=None, description="Amount already paid by patient in original currency"
    )
    plan_adjustments_or_discounts: Optional[str] = Field(
        default=None, description="Contracted network adjustments or tax notes"
    )
    balance_or_reimbursement_due: Optional[str] = Field(
        default=None, description="Remaining balance or patient reimbursement claim amount"
    )
    payment_status: str = Field(
        default="PAID_BY_PATIENT_REIMBURSEMENT_PENDING",
        description="Payment status, e.g. PAID_IN_FULL, PARTIAL_COPAY_PAID, UNPAID_PROVIDER_CLAIM",
    )
    payment_method_and_receipt: Optional[str] = Field(
        default=None, description="Card type, transaction approval number, receipt ID, or fiscal UUID"
    )


class ClinicalAndAuthDetails(BaseModel):
    chief_complaint: Optional[str] = Field(default=None, description="Primary reason for visit or referral")
    clinical_findings_summary: Optional[str] = Field(
        default=None, description="Key examination, laboratory, imaging (X-ray, MRI, ultrasound, endoscopy) findings"
    )
    procedures_and_treatment: Optional[str] = Field(
        default=None, description="Surgical procedures, infusions, or therapies performed"
    )
    medications_prescribed: list[str] = Field(
        default_factory=list, description="List of medications administered or prescribed"
    )


class ReadinessChecklistItem(BaseModel):
    requirement: str = Field(description="CMS-1500 / Claims Adjudication requirement name")
    cms_1500_box: str = Field(description="Corresponding CMS-1500 Form Box number (e.g. Box 1a, Box 21, Box 24)")
    status: str = Field(description="COMPLETE, AI_ENRICHED, or REVIEW_NEEDED")
    value_summary: str = Field(description="Extracted or enriched value satisfying this requirement")


class ClaimsReadinessAssessment(BaseModel):
    readiness_status: str = Field(
        description="READY_FOR_ADJUDICATION, READY_WITH_AI_CODING_ASSIST, or NEEDS_MANUAL_REVIEW"
    )
    readiness_score: int = Field(description="Readiness score from 0 to 100")
    requires_medical_coder_signoff: bool = Field(
        description="True if any CPT or ICD-10 codes were AI-suggested for an uncoded or foreign bill"
    )
    checklist: list[ReadinessChecklistItem] = Field(
        default_factory=list, description="Itemized CMS-1500 claims readiness verification checklist"
    )
    recommended_next_actions: list[str] = Field(
        default_factory=list, description="Recommended workflow steps for the claims processor"
    )


class ClaimExtractionResult(BaseModel):
    """Top-level structured schema extracted by Gemini 3.8 Flash from the English document."""

    document_classification: DocumentClassification
    patient: PatientInformation
    provider: ProviderInformation
    insurance_policy: InsurancePolicyInformation
    diagnoses: list[DiagnosisItem] = Field(default_factory=list)
    line_items: list[ProcedureLineItem] = Field(default_factory=list)
    financials: FinancialSummary
    clinical_details: ClinicalAndAuthDetails
    claims_readiness: ClaimsReadinessAssessment


class TranslationSegment(BaseModel):
    segment_id: int
    section_type: str = Field(description="HEADER, SECTION_TITLE, TABLE_ROW, or PARAGRAPH")
    original_text: str
    translated_text: str


class LanguageDetectionInfo(BaseModel):
    language_code: str = Field(description="BCP-47 / ISO-639-1 code such as en, es, fr, ko")
    language_name: str = Field(description="Human-readable language name")
    confidence: float = Field(default=0.99)
    is_english: bool
    detection_service: str = Field(default="Google Cloud Translation API v3 + Document AI")


class PipelineStepStatus(BaseModel):
    step_number: int
    step_name: str
    service_used: str
    status: str = Field(description="COMPLETED, SKIPPED, or FALLBACK")
    duration_ms: int
    details: str


class ProcessedClaimRecord(BaseModel):
    claim_id: str
    created_at: str
    original_filename: str
    sample_id: Optional[str] = None
    gcs_original_uri: str
    gcs_translated_uri: Optional[str] = None
    language_detection: LanguageDetectionInfo
    was_translated: bool
    original_extracted_text: str
    english_clean_text: str
    translation_segments: list[TranslationSegment] = Field(default_factory=list)
    extraction: ClaimExtractionResult
    pipeline_steps: list[PipelineStepStatus] = Field(default_factory=list)
    firestore_doc_path: str
