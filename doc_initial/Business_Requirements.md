# Claims Coverage Reasoner - Business Requirements Document

## Executive Summary

The Claims Coverage Reasoner is an AI-powered proof-of-concept application that automates insurance claims analysis through multi-agent collaboration. The system ingests claim documentation (forms, photos, invoices), interprets policy coverage, and produces defensible coverage decisions with full citation trails and adversarial review.

**Target Audience**: AWS AI Agent Hackathon judges and insurance industry stakeholders  
**Deployment**: Local development with future AWS cloud deployment capability  
**Core Innovation**: Multi-agent debate system that mimics real-world claims adjudication workflows

---

## Business Problem

Insurance claims processing today involves:
- Manual review of multiple document types (FNOL forms, photos, invoices, policy documents)
- Time-consuming policy interpretation requiring specialized knowledge
- Risk of inconsistent decisions across similar claims
- Limited transparency in decision rationale
- Potential for overlooked fraud indicators or compliance issues

**The Opportunity**: Automate the evidence gathering, policy interpretation, and adversarial review process while maintaining transparency and fairness.

---

## Solution Overview

A multi-agent AI system that collaborates to analyze insurance claims:

### Agent Roles

**Evidence Curator**
- Ingests and normalizes all claim artifacts (forms, photos, invoices, notes)
- Extracts structured data from unstructured sources
- Maintains evidence confidence scores
- Responds to requests for additional documentation

**Policy Interpreter**
- Maps claim facts to specific policy clauses
- Provides coverage recommendations with citations
- Explains what additional evidence would change the decision
- Handles both homeowners (HO-3) and auto (PAP) policies

**Compliance & Fairness Reviewer**
- Adversarially challenges the Interpreter's reasoning
- Identifies missing evidence or misapplied clauses
- Flags potential fraud indicators (timestamp mismatches, scope creep)
- Ensures fair language and proper disclosures

**Supervisor**
- Orchestrates agent collaboration
- Manages conversation rounds and turn-taking
- Enforces stop conditions (consensus reached or max rounds exceeded)

### Collaboration Model

Unlike traditional pipeline architectures, agents engage in **iterative debate**:
1. Curator presents evidence
2. Interpreter proposes coverage decision
3. Reviewer challenges with objections
4. Loop continues until consensus or round limit
5. System produces final decision with full audit trail

**Key Innovation**: The system can reach quick consensus on clear-cut cases (1 round) or engage in multi-round debate for complex scenarios.

---

## Use Cases & Scenarios

### Scenario A: Burst Pipe (Clear Coverage)
**Claim Type**: Homeowners property damage  
**Artifacts**: FNOL form, fresh water damage photos, contractor estimate  
**Expected Outcome**: Quick approval (1 round) - sudden & accidental discharge covered under HO-3  
**Business Value**: Demonstrates efficiency on straightforward claims

### Scenario B: Seepage vs. Burst (Requires Debate)
**Claim Type**: Homeowners property damage with ambiguity  
**Artifacts**: FNOL form, photos showing old staining, estimate with unrelated work  
**Expected Outcome**: Multi-round debate, partial approval with documented rationale  
**Business Value**: Shows nuanced reasoning and proper exclusion application

### Scenario C: Auto Collision with Scope Dispute
**Claim Type**: Vehicle collision claim  
**Artifacts**: FNOL form, rear-end damage photos, invoice including unrelated repairs  
**Expected Outcome**: Approval of collision damage, denial of pre-existing work, appraisal clause reference  
**Business Value**: Demonstrates fraud detection and scope management

---

## User Experience

### Primary Workflow

1. **Case Initiation**
   - User uploads claim documents (FNOL/Proof of Loss, photos, invoices)
   - System accepts PDFs, images, and text inputs

2. **Agent Processing**
   - Real-time visualization of agent collaboration
   - Transparent display of challenges and resolutions
   - Progress indicators for each processing stage

3. **Decision Delivery**
   - Coverage decision (Approve / Partial / Deny)
   - Policy citations with page/section references
   - Objection log showing all challenges and resolutions
   - Evidence map linking decision to source documents
   - Downloadable decision memo

### Demo Mode
- Pre-loaded sample scenarios (A, B, C) for instant demonstration
- One-click case loading for consistent judge evaluation
- Reproducible outcomes for validation

---

## Key Deliverables

### For Each Claim
1. **Decision Memo**: Coverage determination with full rationale
2. **Policy Citations**: Specific clauses, pages, and sections referenced
3. **Objection Log**: Complete record of challenges and resolutions
4. **Evidence Bundle**: Links to all source documents used in decision
5. **Decision Sensitivity**: Explicit statement of what evidence would change the outcome

### System Outputs
- Structured JSON transcripts of agent conversations
- Confidence scores for evidence quality
- Fraud risk indicators
- Compliance check results

---

## Success Criteria

### Functional Requirements
- ✓ Process all three claim types (property burst, property seepage, auto collision)
- ✓ Extract structured data from PDFs and images
- ✓ Retrieve and cite relevant policy clauses
- ✓ Complete multi-round agent debates with proper stop conditions
- ✓ Generate downloadable decision memos

### Quality Requirements
- **Accuracy**: Correct policy clause application in test scenarios
- **Transparency**: Every decision traceable to source evidence and policy text
- **Efficiency**: Clear-cut cases resolve in 1 round
- **Fairness**: Adversarial review catches scope creep and fraud indicators

### Technical Requirements
- Run locally for development and testing
- Deploy to AWS for judge evaluation (future)
- Use AWS services where appropriate (Bedrock, Textract, Rekognition, S3, AgentCore SDK)
- No database required (file-based storage acceptable for POC)

---

## Scope & Constraints

### In Scope
- Homeowners (HO-3) and Personal Auto Policy (PAP) specimen forms
- Three demonstration scenarios with sample data
- Multi-agent collaboration with debate capability
- Evidence extraction from common document types
- Basic fraud detection (timestamp/EXIF checks, scope mismatches)

### Out of Scope
- Production-grade database integration
- Real-time policy updates or endorsement management
- Integration with existing claims management systems
- Advanced fraud detection (network analysis, behavioral patterns)
- Multi-language support
- Mobile application

### Constraints
- POC-level quality (not production-ready)
- Public specimen policies only (no proprietary forms)
- Sample data from publicly available sources

---

## Data Requirements

### Input Documents
- **FNOL/Proof of Loss**: ACORD forms, sworn statements, consumer letters
- **Photos**: Vehicle damage, property damage, water/flood damage
- **Invoices/Estimates**: Auto repair estimates, contractor bids, line-item breakdowns
- **Policy Documents**: HO-3 specimen, PAP PP 00 01 specimen

### Data Sources (Public)
- ACORD specimen forms
- ISO policy templates
- Vehicle damage image datasets
- Property damage photo collections
- Sample invoice templates

### Data Handling
- All uploads stored in S3 with encryption
- Sample data bundled with application for offline demo

---

## Technical Architecture (High-Level)

### Frontend
- Streamlit web application
- Three-panel layout: Upload | Agent Conversation | Decision Card
- Real-time agent activity visualization

### Backend
- AWS AgentCore Multi-Agent Collaboration
- Amazon Textract for document extraction
- Amazon Rekognition for image analysis
- Knowledge Bases for Amazon Bedrock for policy RAG
- S3 for artifact storage
- DynamoDB for case metadata (optional)
- OpenSearch Serverless for vector search
- AWS Nova Pro LLM for reasoning

### Agent Tools
- PDF form parser
- Image analyzer with EXIF reader
- Invoice OCR and line-item extraction
- Policy retrieval with citation anchors
- Compliance rule checker

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Agent debate loops indefinitely | High | Hard limit of 3 rounds; supervisor enforces stop conditions |
| Policy RAG returns irrelevant clauses | Medium | Curate specimen policies; tune retrieval parameters |
| Image analysis misses fraud indicators | Medium | Combine CV with EXIF checks; flag for human review |
| Demo fails without AWS credentials | High | Bundle sample data; implement offline demo mode |
| Complex claims exceed POC capabilities | Low | Clearly scope to three scenarios; document limitations |

---

## Success Metrics (Demo Evaluation)

### For Judges
1. **Innovation**: Multi-agent debate vs. traditional pipeline
2. **AWS Integration**: Effective use of Bedrock, Textract, Rekognition, Knowledge Bases
3. **Transparency**: Clear audit trail from evidence to decision
4. **Practical Value**: Addresses real insurance industry pain points
5. **Technical Execution**: Clean code, working demo, reproducible results

### For Business Stakeholders
1. **Time Savings**: Automated evidence gathering and policy lookup
2. **Consistency**: Reproducible decisions on similar claims
3. **Risk Reduction**: Adversarial review catches errors and fraud
4. **Auditability**: Complete documentation for regulatory compliance
5. **Scalability**: Agent architecture supports additional claim types

---

## Future Enhancements (Post-POC)

- Additional policy types (commercial, specialty lines)
- Integration with claims management systems
- Advanced fraud detection with network analysis
- Real-time policy endorsement handling
- Multi-language support for international operations
- Mobile-first interface for field adjusters
- Machine learning for evidence confidence scoring
- Automated reserve recommendations
- Subrogation opportunity identification

---

## Appendix: Sample Data Sources

- ACORD Property Loss Notice specimens
- Sworn Proof of Loss templates
- HO-3 specimen policies (ISO-style)
- Personal Auto Policy PP 00 01 09 18 specimen
- Vehicle damage datasets (labeled photos)
- Water/flood damage image collections
- Auto repair invoice templates
- Contractor estimate samples
- Adjuster note documentation standards
