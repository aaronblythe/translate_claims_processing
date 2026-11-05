/**
 * Healthcare Claims Intake, Translation & AI Adjudication Workbench
 * Frontend Controller (ES Module)
 */

const state = {
  projectId: "GCP Project",
  bucketName: "claims-docs-bucket",
  samples: [],
  claimsHistory: [],
  activeClaim: null,
  selectedFile: null,
};

const el = {
  headerProjectId: document.getElementById("header-project-id"),
  heroBucketUri: document.getElementById("hero-bucket-uri"),
  stepperProjectId: document.getElementById("stepper-project-id"),
  modalProjectId: document.getElementById("modal-project-id"),
  sampleList: document.getElementById("sample-list"),
  historyList: document.getElementById("claims-history-list"),
  historyCountBadge: document.getElementById("history-count-badge"),
  uploadForm: document.getElementById("upload-form"),
  fileInput: document.getElementById("pdf-file-input"),
  dropArea: document.getElementById("drop-area"),
  dropTitle: document.getElementById("drop-title"),
  btnUploadSubmit: document.getElementById("btn-upload-submit"),
  btnProcessAll: document.getElementById("btn-process-all"),
  btnHealthModal: document.getElementById("btn-health-modal"),
  healthDialog: document.getElementById("health-dialog"),
  healthDialogBody: document.getElementById("health-dialog-body"),
  btnCloseDialog: document.getElementById("btn-close-dialog"),
  processingBanner: document.getElementById("processing-banner"),
  processingTitle: document.getElementById("processing-title"),
  processingSubtitle: document.getElementById("processing-subtitle"),
  emptyWorkbench: document.getElementById("empty-workbench"),
  activeClaimView: document.getElementById("active-claim-view"),
  activeClaimId: document.getElementById("active-claim-id"),
  activeClaimFilename: document.getElementById("active-claim-filename"),
  activeLangBadge: document.getElementById("active-lang-badge"),
  activeTranslationBadge: document.getElementById("active-translation-badge"),
  activePatientHeader: document.getElementById("active-patient-header"),
  readinessScoreCircle: document.getElementById("readiness-score-circle"),
  readinessStatusText: document.getElementById("readiness-status-text"),
  pipelineStepsGrid: document.getElementById("pipeline-steps-grid"),
  tabBtnComparison: document.getElementById("tab-btn-comparison"),
  docTypeBadges: document.getElementById("doc-type-badges"),
  execSummaryText: document.getElementById("exec-summary-text"),
  dlPatient: document.getElementById("dl-patient"),
  dlProvider: document.getElementById("dl-provider"),
  dlInsurance: document.getElementById("dl-insurance"),
  dlFinancials: document.getElementById("dl-financials"),
  dlClinical: document.getElementById("dl-clinical"),
  tbodyDiagnoses: document.getElementById("tbody-diagnoses"),
  tbodyLineItems: document.getElementById("tbody-line-items"),
  tbodyChecklist: document.getElementById("tbody-checklist"),
  ulNextActions: document.getElementById("ul-next-actions"),
  comparisonHeading: document.getElementById("comparison-heading"),
  comparisonSubheading: document.getElementById("comparison-subheading"),
  pdfComparisonGrid: document.getElementById("pdf-comparison-grid"),
  segmentComparisonCard: document.getElementById("segment-comparison-card"),
  origPdfLangTag: document.getElementById("orig-pdf-lang-tag"),
  origPdfTitle: document.getElementById("orig-pdf-title"),
  transPdfTitle: document.getElementById("trans-pdf-title"),
  linkOpenOrigPdf: document.getElementById("link-open-orig-pdf"),
  linkOpenTransPdf: document.getElementById("link-open-trans-pdf"),
  iframeOrigPdf: document.getElementById("iframe-orig-pdf"),
  iframeTransPdf: document.getElementById("iframe-trans-pdf"),
  thOrigLang: document.getElementById("th-orig-lang"),
  tbodySegments: document.getElementById("tbody-segments"),
  segmentSearchInput: document.getElementById("segment-search-input"),
  btnModeBoth: document.getElementById("btn-mode-both"),
  btnModePdfs: document.getElementById("btn-mode-pdfs"),
  btnModeSegments: document.getElementById("btn-mode-segments"),
  dlCloudUris: document.getElementById("dl-cloud-uris"),
  rawJsonPre: document.getElementById("raw-json-pre"),
  btnDownloadJson: document.getElementById("btn-download-json"),
};

function escapeHtml(value) {
  if (value === null || value === undefined) return "—";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function setLoading(isLoading, title = "", subtitle = "") {
  if (isLoading) {
    el.processingTitle.textContent =
      title || "Running Healthcare Claims Pipeline on Google Cloud...";
    if (subtitle) {
      el.processingSubtitle.textContent = subtitle;
    }
    el.processingBanner.classList.remove("hidden");
    el.btnProcessAll.disabled = true;
  } else {
    el.processingBanner.classList.add("hidden");
    el.btnProcessAll.disabled = false;
  }
}

function renderKeyValueList(dlElement, pairs) {
  dlElement.innerHTML = pairs
    .map(
      ([label, val]) =>
        `<dt>${escapeHtml(label)}</dt><dd>${
          val ? escapeHtml(val) : '<span style="color:#94a3b8;">Not specified</span>'
        }</dd>`
    )
    .join("");
}

async function fetchSamples() {
  const res = await fetch("/api/samples");
  const data = await res.json();
  state.samples = data.samples || [];
  renderSamples();
}

function renderSamples() {
  el.sampleList.innerHTML = state.samples
    .map(
      (s) => `
      <div class="sample-item">
        <div class="sample-item-top">
          <span class="sample-title">${escapeHtml(s.flag)} ${escapeHtml(s.title)}</span>
          <span class="badge ${s.language_code === "en" ? "badge-green" : "badge-amber"}">
            ${escapeHtml(s.language_code.toUpperCase())}
          </span>
        </div>
        <div class="sample-sub">${escapeHtml(s.subtitle)}</div>
        <div class="sample-wf">${escapeHtml(s.expected_workflow)}</div>
        <div class="sample-actions">
          <button
            type="button"
            class="btn btn-primary btn-sm"
            data-process-sample="${escapeHtml(s.id)}"
          >
            ▶ Process (${escapeHtml(s.language_name)})
          </button>
          <a
            href="${escapeHtml(s.preview_url)}"
            target="_blank"
            rel="noopener"
            class="btn-link"
          >
            ↗ Raw PDF
          </a>
        </div>
      </div>
    `
    )
    .join("");

  el.sampleList.querySelectorAll("[data-process-sample]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const sampleId = btn.getAttribute("data-process-sample");
      processSampleClaim(sampleId);
    });
  });
}

async function fetchClaimsHistory() {
  const res = await fetch("/api/claims");
  const data = await res.json();
  state.claimsHistory = data.claims || [];
  renderClaimsHistory();
  if (!state.activeClaim && state.claimsHistory.length > 0) {
    selectActiveClaim(state.claimsHistory[0]);
  }
}

function renderClaimsHistory() {
  el.historyCountBadge.textContent = String(state.claimsHistory.length);
  if (state.claimsHistory.length === 0) {
    el.historyList.innerHTML =
      '<div class="empty-hint">No claims processed yet. Click any test document above to run the pipeline.</div>';
    return;
  }

  el.historyList.innerHTML = state.claimsHistory
    .map((c) => {
      const isSelected = state.activeClaim && state.activeClaim.claim_id === c.claim_id;
      const langCode = c.language_detection.language_code.toUpperCase();
      return `
        <div class="history-item ${isSelected ? "active" : ""}" data-claim-id="${escapeHtml(c.claim_id)}">
          <div class="history-top">
            <span class="mono-id">${escapeHtml(c.claim_id)}</span>
            <span class="badge ${c.was_translated ? "badge-amber" : "badge-green"}">
              ${c.was_translated ? `${escapeHtml(langCode)} → EN` : "EN Direct"}
            </span>
          </div>
          <div class="history-name">
            ${escapeHtml(c.extraction.patient.full_name || c.original_filename)}
          </div>
          <div class="history-meta">
            ${escapeHtml(c.extraction.document_classification.document_type)} &bull;
            ${escapeHtml(c.extraction.financials.total_billed_original)}
          </div>
        </div>
      `;
    })
    .join("");

  el.historyList.querySelectorAll("[data-claim-id]").forEach((item) => {
    item.addEventListener("click", () => {
      const id = item.getAttribute("data-claim-id");
      const found = state.claimsHistory.find((x) => x.claim_id === id);
      if (found) selectActiveClaim(found);
    });
  });
}

async function processSampleClaim(sampleId) {
  const sampleMeta = state.samples.find((s) => s.id === sampleId);
  const label = sampleMeta ? sampleMeta.title : sampleId;
  setLoading(
    true,
    `Processing ${label}...`,
    `Uploading to gs://${state.bucketName} → Document AI OCR → Language Check → Conditional Cloud Translation & Clean English PDF → Gemini 3.8 Flash Extraction → Firestore`
  );
  try {
    const res = await fetch(`/api/claims/process-sample/${encodeURIComponent(sampleId)}`, {
      method: "POST",
    });
    if (!res.ok) {
      const errText = await res.text();
      throw new Error(errText || `HTTP ${res.status}`);
    }
    const record = await res.json();
    await fetchClaimsHistory();
    selectActiveClaim(record);
  } catch (err) {
    alert(`Error processing sample claim: ${err.message}`);
  } finally {
    setLoading(false);
  }
}

async function processAllSamples() {
  setLoading(
    true,
    "Processing All 4 Realistic Multi-Language Claims (English, Spanish, French, Korean)...",
    "Executing Cloud Storage + Document AI + Cloud Translation API v3 + Clean English PDF Generation + Gemini 3.8 Flash + Firebase Firestore across all 4 test documents"
  );
  try {
    const res = await fetch("/api/claims/process-all-samples", { method: "POST" });
    if (!res.ok) {
      throw new Error(await res.text());
    }
    const data = await res.json();
    await fetchClaimsHistory();
    if (data.claims && data.claims.length > 0) {
      // Select the Spanish or Korean translated claim first so user immediately sees translation & extraction
      const nonEn = data.claims.find((c) => c.was_translated) || data.claims[0];
      selectActiveClaim(nonEn);
    }
  } catch (err) {
    alert(`Batch processing error: ${err.message}`);
  } finally {
    setLoading(false);
  }
}

function selectActiveClaim(record) {
  state.activeClaim = record;
  renderClaimsHistory();

  el.emptyWorkbench.classList.add("hidden");
  el.activeClaimView.classList.remove("hidden");

  const lang = record.language_detection;
  const ext = record.extraction;

  el.activeClaimId.textContent = record.claim_id;
  el.activeClaimFilename.textContent = record.original_filename;
  el.activeLangBadge.textContent = `Detected: ${lang.language_name} (${lang.language_code.toUpperCase()})`;

  if (record.was_translated) {
    el.activeTranslationBadge.className = "badge badge-amber";
    el.activeTranslationBadge.textContent = `Translated ${lang.language_code.toUpperCase()} → EN (Clean English PDF Created)`;
    el.tabBtnComparison.innerHTML = `🔍 Side-by-Side Comparison (${escapeHtml(lang.language_code.toUpperCase())} vs. Clean EN) ✨`;
  } else {
    el.activeTranslationBadge.className = "badge badge-green";
    el.activeTranslationBadge.textContent = "English Document — Processed Directly";
    el.tabBtnComparison.innerHTML = `🔍 Document Inspector (Original English)`;
  }

  el.activePatientHeader.textContent = `${ext.patient.full_name || "Unknown Patient"} — ${
    ext.provider.facility_name || "Healthcare Facility"
  }`;

  el.readinessScoreCircle.textContent = `${ext.claims_readiness.readiness_score}`;
  el.readinessStatusText.textContent = ext.claims_readiness.readiness_status;

  // Render 6-step pipeline trace
  el.pipelineStepsGrid.innerHTML = (record.pipeline_steps || [])
    .map(
      (step) => `
      <div class="step-card status-${escapeHtml(step.status)}">
        <div class="step-card-top">
          <span class="step-num">Step ${escapeHtml(step.step_number)}</span>
          <span class="step-time">${escapeHtml(step.duration_ms)} ms</span>
        </div>
        <div class="step-name">${escapeHtml(step.step_name)}</div>
        <div class="step-service">${escapeHtml(step.service_used)}</div>
        <div class="step-details">${escapeHtml(step.details)}</div>
      </div>
    `
    )
    .join("");

  // Render Document Classification & Summary
  const allTypes = [
    ext.document_classification.document_type,
    ...(ext.document_classification.secondary_types || []),
  ];
  el.docTypeBadges.innerHTML = allTypes
    .map(
      (t, i) =>
        `<span class="badge ${i === 0 ? "badge-teal" : "badge-neutral"}">${escapeHtml(t)}</span>`
    )
    .join("");
  el.execSummaryText.textContent = ext.document_classification.executive_summary;

  // Render 4 entity cards
  renderKeyValueList(el.dlPatient, [
    ["Full Name", ext.patient.full_name],
    ["Date of Birth", ext.patient.date_of_birth],
    ["Gender", ext.patient.gender],
    ["Member / Policy ID", ext.patient.member_id],
    ["Group Number", ext.patient.group_number],
    ["Relationship", ext.patient.relationship_to_subscriber],
    ["Address", ext.patient.address],
    ["Phone", ext.patient.phone],
  ]);

  renderKeyValueList(el.dlProvider, [
    ["Facility Name", ext.provider.facility_name],
    ["Attending Physician", ext.provider.attending_physician],
    ["Referring Physician", ext.provider.referring_physician],
    ["Specialty / Dept", ext.provider.specialty],
    ["NPI / Facility ID", ext.provider.npi_or_registration_id],
    ["Tax / Business ID", ext.provider.tax_id_or_business_id],
    ["Country", ext.provider.country],
    ["Address", ext.provider.address],
  ]);

  renderKeyValueList(el.dlInsurance, [
    ["Payer / Carrier", ext.insurance_policy.payer_name],
    ["Plan / Network", ext.insurance_policy.plan_name],
    ["Policy / Member ID", ext.insurance_policy.policy_or_member_id],
    ["Group Number", ext.insurance_policy.group_number],
    ["Prior Auth #", ext.insurance_policy.prior_authorization_number],
    ["Auth Valid Dates", ext.insurance_policy.authorization_valid_dates],
    ["Claim / Invoice #", ext.insurance_policy.claim_or_invoice_number],
    ["Benefit Notes", ext.insurance_policy.benefit_notes],
  ]);

  renderKeyValueList(el.dlFinancials, [
    [
      "Service Dates",
      `${ext.financials.service_date_start || "—"} to ${ext.financials.service_date_end || "—"}`,
    ],
    ["Original Currency", ext.financials.original_currency],
    ["Total Billed (Orig)", ext.financials.total_billed_original],
    [
      "Estimated USD Total",
      `$${Number(ext.financials.total_billed_usd_estimate || 0).toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })} USD`,
    ],
    ["Paid by Patient", ext.financials.amount_paid_by_patient],
    ["Plan Adjustments", ext.financials.plan_adjustments_or_discounts],
    ["Balance / Claim Due", ext.financials.balance_or_reimbursement_due],
    ["Payment Proof", ext.financials.payment_method_and_receipt],
  ]);

  renderKeyValueList(el.dlClinical, [
    ["Chief Complaint", ext.clinical_details.chief_complaint],
    ["Clinical Findings", ext.clinical_details.clinical_findings_summary],
    ["Procedures Performed", ext.clinical_details.procedures_and_treatment],
    [
      "Medications",
      (ext.clinical_details.medications_prescribed || []).join(", ") || "None listed",
    ],
  ]);

  // Diagnoses Table
  el.tbodyDiagnoses.innerHTML = (ext.diagnoses || [])
    .map(
      (d) => `
      <tr>
        <td>
          <span class="badge ${d.is_primary ? "badge-teal" : "badge-neutral"}">
            ${d.is_primary ? "Primary" : "Secondary"}
          </span>
        </td>
        <td><code><strong>${escapeHtml(d.code)}</strong></code> <small>(${escapeHtml(d.code_system)})</small></td>
        <td>
          <span class="badge ${d.code_source === "EXTRACTED" ? "badge-green" : "badge-purple"}">
            ${escapeHtml(d.code_source)}
          </span>
        </td>
        <td>${escapeHtml(d.description_english)}</td>
      </tr>
    `
    )
    .join("");

  // Line Items Table
  el.tbodyLineItems.innerHTML = (ext.line_items || [])
    .map(
      (item) => `
      <tr>
        <td>${escapeHtml(item.line_number)}</td>
        <td>${escapeHtml(item.service_date || "—")}</td>
        <td><code><strong>${escapeHtml(item.procedure_code)}</strong></code> <small>(${escapeHtml(item.code_system)})</small></td>
        <td><code>${escapeHtml(item.original_local_code || "—")}</code></td>
        <td>
          <span class="badge ${item.code_source === "EXTRACTED" ? "badge-green" : "badge-purple"}">
            ${escapeHtml(item.code_source)}
          </span>
        </td>
        <td>${escapeHtml(item.description_english)}</td>
        <td class="num-col">${escapeHtml(item.quantity)}</td>
        <td class="num-col">${escapeHtml(item.unit_price_original)}</td>
        <td class="num-col"><strong>${escapeHtml(item.total_charge_original)}</strong></td>
        <td class="num-col">
          ${
            item.estimated_usd_amount !== null && item.estimated_usd_amount !== undefined
              ? `$${Number(item.estimated_usd_amount).toFixed(2)}`
              : "—"
          }
        </td>
      </tr>
    `
    )
    .join("");

  // Readiness Checklist Table
  el.tbodyChecklist.innerHTML = (ext.claims_readiness.checklist || [])
    .map(
      (c) => `
      <tr>
        <td><code>${escapeHtml(c.cms_1500_box)}</code></td>
        <td><strong>${escapeHtml(c.requirement)}</strong></td>
        <td>
          <span class="badge ${c.status === "COMPLETE" ? "badge-green" : "badge-purple"}">
            ${escapeHtml(c.status)}
          </span>
        </td>
        <td>${escapeHtml(c.value_summary)}</td>
      </tr>
    `
    )
    .join("");

  // Next Actions
  el.ulNextActions.innerHTML = (ext.claims_readiness.recommended_next_actions || [])
    .map((act) => `<li>${escapeHtml(act)}</li>`)
    .join("");

  // Side-by-Side Comparison Tab
  const origPdfUrl = `/api/claims/${encodeURIComponent(record.claim_id)}/pdf/original`;
  const transPdfUrl = `/api/claims/${encodeURIComponent(record.claim_id)}/pdf/translated`;

  el.origPdfLangTag.textContent = `Original (${lang.language_code.toUpperCase()})`;
  el.origPdfTitle.textContent = `${record.original_filename} (${lang.language_name})`;
  el.transPdfTitle.textContent = record.was_translated
    ? `clean_english_${record.original_filename} (Translated to English)`
    : `${record.original_filename} (Already in English)`;

  el.linkOpenOrigPdf.href = origPdfUrl;
  el.linkOpenTransPdf.href = transPdfUrl;
  el.iframeOrigPdf.src = origPdfUrl;
  el.iframeTransPdf.src = transPdfUrl;

  el.thOrigLang.textContent = `Original Document Segment (${lang.language_name} / ${lang.language_code})`;
  el.segmentSearchInput.value = "";
  renderSegmentsTable(record.translation_segments || [], "");

  // Cloud URIs & Raw JSON Tab
  renderKeyValueList(el.dlCloudUris, [
    ["Google Cloud Project", state.projectId],
    ["Original PDF GCS URI", record.gcs_original_uri],
    [
      "Clean English PDF GCS URI",
      record.gcs_translated_uri || "N/A (Source document is already in English)",
    ],
    ["Firestore Document Path", record.firestore_doc_path],
    ["Language Detection Service", record.language_detection.detection_service],
    ["Gemini Model", "gemini-3.8-flash (Interactions API)"],
  ]);
  el.rawJsonPre.textContent = JSON.stringify(record, null, 2);
}

function renderSegmentsTable(segments, filterQuery) {
  const q = (filterQuery || "").trim().toLowerCase();
  const filtered = q
    ? segments.filter(
        (s) =>
          s.original_text.toLowerCase().includes(q) ||
          s.translated_text.toLowerCase().includes(q) ||
          s.section_type.toLowerCase().includes(q)
      )
    : segments;

  el.tbodySegments.innerHTML = filtered
    .map(
      (s) => `
      <tr>
        <td class="num-col"><code>#${escapeHtml(s.segment_id)}</code></td>
        <td><span class="badge badge-neutral">${escapeHtml(s.section_type)}</span></td>
        <td class="seg-orig-cell">${escapeHtml(s.original_text)}</td>
        <td class="seg-trans-cell">${escapeHtml(s.translated_text)}</td>
      </tr>
    `
    )
    .join("");
}

// Tab switching
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const targetId = btn.getAttribute("data-tab");
    document.querySelectorAll(".tab-btn").forEach((b) => {
      b.classList.toggle("active", b === btn);
      b.setAttribute("aria-selected", b === btn ? "true" : "false");
    });
    document.querySelectorAll(".tab-pane").forEach((pane) => {
      pane.classList.toggle("active", pane.id === targetId);
    });
  });
});

// Comparison Sub-Mode Switching
function setComparisonMode(mode) {
  el.btnModeBoth.classList.toggle("active", mode === "both");
  el.btnModePdfs.classList.toggle("active", mode === "pdfs");
  el.btnModeSegments.classList.toggle("active", mode === "segments");

  el.pdfComparisonGrid.classList.toggle("hidden", mode === "segments");
  el.segmentComparisonCard.classList.toggle("hidden", mode === "pdfs");
}

el.btnModeBoth.addEventListener("click", () => setComparisonMode("both"));
el.btnModePdfs.addEventListener("click", () => setComparisonMode("pdfs"));
el.btnModeSegments.addEventListener("click", () => setComparisonMode("segments"));

el.segmentSearchInput.addEventListener("input", (e) => {
  if (!state.activeClaim) return;
  renderSegmentsTable(state.activeClaim.translation_segments || [], e.target.value);
});

// File Upload & Drag-and-Drop
el.dropArea.addEventListener("click", () => el.fileInput.click());
el.dropArea.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    el.fileInput.click();
  }
});

el.dropArea.addEventListener("dragover", (e) => {
  e.preventDefault();
  el.dropArea.classList.add("drag-over");
});

el.dropArea.addEventListener("dragleave", () => {
  el.dropArea.classList.remove("drag-over");
});

el.dropArea.addEventListener("drop", (e) => {
  e.preventDefault();
  el.dropArea.classList.remove("drag-over");
  const file = e.dataTransfer?.files?.[0];
  if (file) setSelectedUploadFile(file);
});

el.fileInput.addEventListener("change", (e) => {
  const file = e.target.files?.[0];
  if (file) setSelectedUploadFile(file);
});

function setSelectedUploadFile(file) {
  state.selectedFile = file;
  el.dropTitle.textContent = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
  el.btnUploadSubmit.disabled = false;
}

el.uploadForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!state.selectedFile) return;

  const formData = new FormData();
  formData.append("file", state.selectedFile);

  setLoading(
    true,
    `Uploading & Processing ${state.selectedFile.name}...`,
    "Storing in Google Cloud Storage → Document AI OCR → Language Detection → Conditional Translation → Gemini 3.8 Flash Extraction → Firebase Firestore"
  );
  try {
    const res = await fetch("/api/claims/upload", {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      throw new Error(await res.text());
    }
    const record = await res.json();
    state.selectedFile = null;
    el.fileInput.value = "";
    el.dropTitle.textContent = "Drop PDF here or click to browse";
    el.btnUploadSubmit.disabled = true;
    await fetchClaimsHistory();
    selectActiveClaim(record);
  } catch (err) {
    alert(`Upload failed: ${err.message}`);
  } finally {
    setLoading(false);
  }
});

// Download JSON button
el.btnDownloadJson.addEventListener("click", () => {
  if (!state.activeClaim) return;
  const blob = new Blob([JSON.stringify(state.activeClaim, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${state.activeClaim.claim_id}_processed.json`;
  a.click();
  URL.revokeObjectURL(url);
});

// Process All 4 Test Documents button
el.btnProcessAll.addEventListener("click", () => processAllSamples());

// Health Modal
el.btnHealthModal.addEventListener("click", async () => {
  el.healthDialog.showModal();
  el.healthDialogBody.innerHTML = "Checking Google Cloud service connectivity...";
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    const svcs = data.services || {};
    el.healthDialogBody.innerHTML = Object.entries(svcs)
      .map(
        ([key, info]) => `
        <div class="svc-status-row">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.25rem;">
            <strong>${escapeHtml(key.toUpperCase())}</strong>
            <span class="badge ${info.available ? "badge-green" : "badge-amber"}">
              ${info.available ? "ACTIVE" : "LOCAL MIRROR / PENDING"}
            </span>
          </div>
          <pre style="font-size:0.75rem;color:#334155;white-space:pre-wrap;">${escapeHtml(
            JSON.stringify(info, null, 2)
          )}</pre>
        </div>
      `
      )
      .join("");
  } catch (err) {
    el.healthDialogBody.innerHTML = `<div style="color:#dc2626;">Error checking status: ${escapeHtml(
      err.message
    )}</div>`;
  }
});

el.btnCloseDialog.addEventListener("click", () => el.healthDialog.close());

async function fetchRuntimeConfig() {
  try {
    const res = await fetch("/api/health");
    if (!res.ok) return;
    const data = await res.json();
    if (data.project_id) {
      state.projectId = data.project_id;
      if (el.headerProjectId) el.headerProjectId.textContent = data.project_id;
      if (el.stepperProjectId) el.stepperProjectId.textContent = data.project_id;
      if (el.modalProjectId) el.modalProjectId.textContent = data.project_id;
    }
    const bucket = data.bucket_name || data.services?.cloud_storage?.bucket;
    if (bucket) {
      state.bucketName = bucket;
      if (el.heroBucketUri) el.heroBucketUri.textContent = `gs://${bucket}/originals/`;
    }
  } catch (_) {
    // Keep default labels if offline
  }
}

// Initial bootstrap
(async function init() {
  await fetchRuntimeConfig();
  await fetchSamples();
  await fetchClaimsHistory();
})();
