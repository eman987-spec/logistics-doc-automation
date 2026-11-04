# Logistics, Trucking & Shipping — Document Automation PoC
### Technical Architecture & Implementation Plan (Build Spec)

> Prepared for: AI coding agent build (Antigravity)
> Source: Technical & Sales Demonstration Planning doc

---

## 1. Executive Summary

Build a **white-label document-automation prototype** for the Logistics, Trucking, and Shipping industry.

**Core flow:**
```
Document Ingestion → OCR/Document AI → AI Extraction → Validation → Human Review
→ Data Transformation → Third-Party System → Database → Dashboard/Reporting
```

**Recommended stack:**
- Frontend: Next.js / React (white-label)
- Backend/API: Node.js
- Workflow orchestration: n8n
- Database: PostgreSQL
- File storage: S3-compatible object storage
- OCR/Document AI: Azure Document Intelligence / Google Document AI / AWS Textract
- LLM: OpenAI / Claude / Gemini (document understanding & structuring)

---

## 2. Business Objective

Demonstrate that paperwork-heavy logistics processes done manually today can be automated end-to-end. The system must:
- Receive documents
- Extract information
- Validate it
- Identify exceptions
- Route low-confidence cases to a human reviewer
- Submit approved data to a destination system
- Maintain a full audit trail
- Provide a professional dashboard

---

## 3. Initial Scope

Logistics, Trucking, and Shipping only (Phase 1). Candidate document types:
- Bills of Lading (BOL)
- Rate confirmations
- Proof of Delivery (POD)
- Packing lists
- Freight/carrier invoices
- Shipping manifests
- Customs paperwork
- Delivery receipts
- Fillable PDFs, scanned documents, mobile photos, email attachments

> Final document types must be confirmed from the sample batch (see Open Questions §20).

---

## 4. Architecture

**Hybrid architecture** — n8n is the automation engine, not the whole app.

| Layer | Responsibility |
|---|---|
| Next.js / React | White-label UI, dashboard, upload, review queue |
| Node.js | Application/API layer, auth, file handling |
| n8n | Workflow orchestration, AI/OCR calls, validation routing, integrations |
| PostgreSQL | Structured data, workflow state, review state, audit metadata |
| Object Storage | Original PDFs, images, processed files |
| Document AI/OCR | Text, tables, layout extraction |
| LLM | Document understanding, structuring, normalization, reasoning |
| Validation Code | Deterministic business rules and data checks |
| Destination API | Final system-of-record submission |

**Why hybrid instead of n8n-only:** n8n handles triggers, API calls, branching, retries, integrations well, but a polished white-label app needs a custom dashboard, document viewer, human-review queue, branding, user management, and reporting — which n8n alone can't provide.

---

## 5. End-to-End Workflow

1. **Ingestion** — Frontend Upload → Node.js → Storage → n8n (also support email, cloud storage, SFTP, API long-term)
2. **Storage** — Save original file in object storage; create DB record with unique document ID
3. **Preprocessing** — Detect file type, page count, scan quality, orientation; flag if image cleanup needed
4. **Classification** — Identify document type (BOL, POD, invoice, packing list, rate confirmation, etc.)
5. **OCR/Document AI** — Extract text, tables, key-value pairs, layout
6. **AI Extraction** — Convert document into strict canonical logistics JSON schema
7. **Validation** — Required-field, data-type, mathematical, cross-field, and business-rule validation
8. **Confidence Routing** — High-confidence → auto-process; low-confidence/failed → human review
9. **Human Review** — Reviewer views original doc + extracted fields, corrects errors, resubmits for re-validation
10. **Transformation** — Map canonical data → destination-system schema
11. **Population** — Send approved data via REST API where possible; RPA/manual-assisted only as fallback
12. **Audit & Reporting** — Persist original doc, extracted data, review actions, integration status, audit trail; expose metrics on dashboard

---

## 6. AI Responsibilities (Guardrails)

**AI should:**
- Classify documents
- Extract fields
- Normalize data
- Flag suspicious values
- Reason over inconsistent layouts

**AI should NOT:**
- Control system-of-record writes
- Handle authentication
- Handle audit logging
- Enforce deterministic business rules

**Principle:** AI for understanding; deterministic code for control.

---

## 7. Canonical Data Model

Use an intermediate canonical schema instead of sending AI output directly to a destination system (ERP/CRM). This lets one extraction engine support multiple customers/destinations via configurable mappings.

**Core fields:**
```
shipment_number, document_number, document_type, shipper, consignee, carrier,
origin, destination, pickup_date, delivery_date, tracking_number, purchase_order,
weight, quantity, freight_cost, tax, total, currency, line_items
```

---

## 8. Validation & Human-in-the-Loop

Validation types: required fields, data types, mathematical checks (e.g. `subtotal + tax == total`), business rules, cross-field checks, confidence scores.

**Review UI must show:**
- Original PDF/image alongside extracted fields
- Confidence indicators
- Validation warnings
- Editable fields
- Approve / Reject actions

Corrected records are **re-validated** before submission.

---

## 9. Destination Integrations

- Preferred: API-based via n8n HTTP Request or native nodes.
- Candidates: Salesforce, HubSpot, Microsoft Dynamics, SAP, Sage, QuickBooks, Odoo, generic ERP/CRM.
- **PoC #1: pick exactly one destination system.**
- If no usable API exists: Playwright/RPA as fallback, or manual-assisted submission for early demos.

---

## 10. n8n Workflow Structure

**Workflow 1 — Ingestion**
`Webhook/Email Trigger → Validate File → Store File → Create DB Record → Trigger Processing`

**Workflow 2 — Document Processing**
`Get Document → Preprocess → OCR/Document AI → LLM Extraction → Save Extraction`

**Workflow 3 — Validation**
`Get Extraction → Schema Validation → Business Rules → Confidence Check → Pass/Review Routing`

**Workflow 4 — Human Review**
`Create Review Task → Frontend Review → Correction Webhook → Re-validation`

**Workflow 5 — Destination**
`Approved → Transform Data → Destination API → Check Response → Update Database`

**Workflow 6 — Errors**
`Error → Retry → Log → Notify Admin (on persistent failure)`

---

## 11. Technology Stack

| Layer | Choice |
|---|---|
| Frontend | Next.js / React + Tailwind CSS |
| Backend | Node.js |
| Automation | n8n |
| Database | PostgreSQL |
| Auth | Supabase Auth (or equivalent) |
| Storage | S3-compatible object storage |
| OCR/Document AI | Azure Document Intelligence / Google Document AI / AWS Textract |
| LLM | OpenAI / Claude / Gemini |
| API comms | REST |
| Optional RPA | Playwright |
| Deployment | Docker + VM + Nginx |

---

## 12. Database Design

Recommended tables:
```
customers, users, documents, extractions, validation_results,
review_tasks, integrations, workflow_runs, audit_logs
```
PostgreSQL = structured state. Object storage = original files & large artifacts.

---

## 13. Frontend Screens

- Login
- Dashboard
- Documents
- Review Queue
- Document Details
- Integration Status
- Customer branding/configuration

**Dashboard metrics:** total documents, processed, approved, review-required, failed, average processing time, automation rate, destination submission status.

---

## 14. White-Label Capability

Customer-specific config: logo, colors, company name, domain, document types, business rules, destination system, field mappings. Core app stays reusable; config drives per-customer experience.

---

## 15. Security & Deployment

HTTPS, authentication, role-based access control, secure API credentials, environment variables, encrypted secrets, DB access controls, file permissions, audit logs, input validation.

Deploy: Docker + Nginx on a VM. Keep frontend, backend, n8n, database, and storage logically separated.

---

## 16. Accuracy Strategy

Treat 98–99% as a **target for straight-through processing** on supported document types, not a guarantee. Improve via: OCR quality, document classification, document-specific schemas, structured outputs, business rules, confidence thresholds, human review, and testing against real samples.

---

## 17. PoC Demo Script

Process a representative batch → auto-classify & extract → route exceptions to review queue → reviewer corrects a field → re-validate → submit approved data to destination → dashboard metrics update. Report actual performance from real testing, not assumptions.

---

## 18. Implementation Phases

| Phase | Deliverable |
|---|---|
| 1 | Requirements & process mapping — manual process, sample docs, fields, rules, destination, expected volume |
| 2 | Architecture & data model — schemas, DB, APIs, n8n workflow structure |
| 3 | Document processing — ingestion, storage, OCR, classification, AI extraction |
| 4 | Validation — schema validation, business rules, confidence scoring, exceptions |
| 5 | Human review — review queue, document viewer, corrections, re-validation |
| 6 | Destination integration — selected API + field mappings |
| 7 | Dashboard & white-label UI |
| 8 | Testing — clean PDFs, scans, phone photos, missing fields, poor quality, duplicates, API/AI failures |
| 9 | VM deployment, HTTPS, monitoring, demo data, sales-demo readiness |

---

## 19. Open Questions to Confirm Before Build

1. Which exact document types are included in PoC #1?
2. How many sample documents are available?
3. What percentage are scanned or photographed?
4. What is the expected document volume?
5. Which destination system will be demonstrated?
6. Does it have an API?
7. What fields are currently extracted manually?
8. What business validation rules exist?
9. Which cases require human review?
10. Which OCR/LLM combination performs best on the sample batch?
11. What VM/database/storage environment is available?
12. What budget ceiling applies?

---

## 20. Final Recommendation

Proceed with hybrid architecture:
`Next.js + Node.js + n8n + PostgreSQL + S3-compatible storage + Document AI/OCR + LLM + destination API`

Reusable core: `Ingestion → Document Intelligence → AI Extraction → Validation → Human Review → Audit`

Customer-specific config: document types, business rules, field mappings, destination integration, branding.

**Build one complete logistics workflow first** — not every document type/ERP at once. Extend later to additional customers, documents, systems, and verticals (medical billing, healthcare, finance, accounting).

---

## 21. Immediate Next Steps

**From stakeholder:** Provide sample end-to-end manual process, representative document batch, current destination system/process, manually extracted fields, existing validation rules, expected document volume.

**Dev team:** Analyze samples → define schemas → benchmark OCR/LLM options → select destination integration → finalize DB and n8n architecture → estimate effort/cost → build PoC → test → deploy to VM.

---

## Appendix: Architecture Responsibility Matrix

| Component | Primary Responsibility |
|---|---|
| Next.js / React | White-label UI, dashboard, upload, review queue |
| Node.js | Application/API layer, authentication, file handling |
| n8n | Workflow orchestration, AI/OCR calls, validation routing, integrations |
| PostgreSQL | Structured data, workflow state, review state, audit metadata |
| Object Storage | Original PDFs, images, processed files |
| Document AI/OCR | Text, tables, layout and OCR extraction |
| LLM | Document understanding, structuring, normalization, reasoning |
| Validation Code | Deterministic business rules and data checks |
| Destination API | Final system-of-record submission |
