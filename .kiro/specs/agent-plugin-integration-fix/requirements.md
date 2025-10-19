# Requirements Document

## Introduction

This specification addresses critical architectural issues in the multi-agent insurance claims processing system. The current implementation has two major problems: (1) agents are not properly utilizing plugins to extract data from input files, particularly failing to leverage AWS Bedrock Nova Pro's vision capabilities for PDF and image analysis, and (2) agent response formats are inconsistent with orchestration requirements, causing parsing failures and workflow disruptions.

## Glossary

- **Agent**: An AI component responsible for a specific role in claims processing (Evidence Curator, Policy Interpreter, Compliance Reviewer)
- **Plugin**: A tool that agents can invoke to perform specific tasks (PDF extraction, image analysis, policy retrieval, compliance checking)
- **Nova Pro**: AWS Bedrock's multimodal LLM with vision capabilities for analyzing images and PDFs
- **Orchestrator**: The Supervisor component that coordinates agent collaboration and manages conversation flow
- **FNOL**: First Notice of Loss - the initial claim report document
- **Response Format**: The structured JSON output that agents must return for orchestration parsing

## Requirements

### Requirement 1

**User Story:** As a claims processing system, I want agents to use appropriate plugins for data extraction, so that evidence is accurately extracted from uploaded documents.

#### Acceptance Criteria

1. WHEN the Evidence Curator receives uploaded files, THE Evidence Curator SHALL invoke the pdf_extractor plugin with byte input for FNOL documents
2. WHEN the Evidence Curator receives image files, THE Evidence Curator SHALL invoke Nova Pro vision capability for damage analysis
3. WHEN the Evidence Curator receives receipt images, THE Evidence Curator SHALL invoke Nova Pro vision capability for key-value pair extraction
4. WHEN the Evidence Curator receives PDF loss forms, THE Evidence Curator SHALL invoke Nova Pro vision capability with byte input for form field extraction
5. WHERE plugins are available, THE Evidence Curator SHALL use plugin outputs as the primary data source rather than generating synthetic data

### Requirement 2

**User Story:** As a claims processing system, I want the Evidence Curator to leverage Nova Pro's multimodal capabilities, so that visual content is accurately analyzed without relying on text-only extraction.

#### Acceptance Criteria

1. WHEN processing damage photos, THE Evidence Curator SHALL send image bytes to Nova Pro for visual damage assessment
2. WHEN processing PDF documents with forms, THE Evidence Curator SHALL send PDF bytes to Nova Pro for form field extraction
3. WHEN processing receipts or invoices, THE Evidence Curator SHALL send image bytes to Nova Pro for line item extraction
4. THE Evidence Curator SHALL include confidence scores from Nova Pro in the extracted evidence
5. THE Evidence Curator SHALL handle both image formats (JPEG, PNG) and PDF formats using Nova Pro's multimodal input

### Requirement 3

**User Story:** As an orchestrator, I want agents to return responses in a consistent, parseable format, so that I can reliably extract decisions and evidence from agent outputs.

#### Acceptance Criteria

1. THE Evidence Curator SHALL return a JSON object containing evidence, expense, fnol_summary, and metadata fields
2. THE Policy Interpreter SHALL return a JSON object containing coverage_position, rationale, citations, sensitivity, and coverage_details fields
3. THE Compliance Reviewer SHALL return a JSON object containing objections, approval, summary, and recommendations fields
4. WHEN agents return JSON responses, THE agents SHALL ensure the JSON is valid and properly formatted
5. THE agents SHALL wrap JSON responses with clear delimiters or return pure JSON without extraneous text

### Requirement 4

**User Story:** As an orchestrator, I want to reliably parse agent responses, so that the workflow can proceed without parsing failures.

#### Acceptance Criteria

1. THE Orchestrator SHALL successfully extract evidence data from Evidence Curator responses
2. THE Orchestrator SHALL successfully extract decision data from Policy Interpreter responses
3. THE Orchestrator SHALL successfully extract review data from Compliance Reviewer responses
4. WHEN JSON parsing fails, THE Orchestrator SHALL log detailed error information including the unparseable content
5. THE Orchestrator SHALL provide fallback structures when parsing fails to prevent workflow crashes

### Requirement 5

**User Story:** As a developer, I want clear plugin invocation patterns in agent code, so that I can verify plugins are being called correctly.

#### Acceptance Criteria

1. THE Evidence Curator SHALL explicitly invoke pdf_extractor plugin for each FNOL document
2. THE Evidence Curator SHALL explicitly invoke Nova Pro for each image file
3. THE Evidence Curator SHALL explicitly invoke Nova Pro for each PDF form
4. THE Policy Interpreter SHALL explicitly invoke policy_retriever plugin for policy clause lookup
5. THE Compliance Reviewer SHALL explicitly invoke compliance_checker plugin for fraud detection

### Requirement 6

**User Story:** As a claims processing system, I want agents to handle plugin errors gracefully, so that processing continues even when individual plugin calls fail.

#### Acceptance Criteria

1. WHEN a plugin invocation fails, THE agent SHALL log the error with details
2. WHEN a plugin invocation fails, THE agent SHALL continue processing other files
3. WHEN a plugin invocation fails, THE agent SHALL include error information in the metadata field
4. THE agent SHALL return partial results when some plugin calls succeed and others fail
5. THE agent SHALL not crash or return empty responses due to single plugin failures

### Requirement 7

**User Story:** As an Evidence Curator, I want to use Nova Pro's byte input capability, so that I can analyze PDFs and images without intermediate file conversion.

#### Acceptance Criteria

1. THE Evidence Curator SHALL read uploaded files as bytes
2. THE Evidence Curator SHALL pass byte data directly to Nova Pro for analysis
3. THE Evidence Curator SHALL handle both PDF bytes and image bytes in the same workflow
4. THE Evidence Curator SHALL preserve original file metadata (filename, upload timestamp)
5. THE Evidence Curator SHALL not require temporary file storage for Nova Pro processing

### Requirement 8

**User Story:** As an orchestrator, I want agent names to be consistent across the system, so that conversation history tracking works reliably.

#### Acceptance Criteria

1. THE Evidence Curator SHALL use a consistent agent name in all responses
2. THE Policy Interpreter SHALL use a consistent agent name in all responses
3. THE Compliance Reviewer SHALL use a consistent agent name in all responses
4. THE Orchestrator SHALL correctly identify agent turns by agent name
5. THE Orchestrator SHALL handle both kebab-case and title-case agent names for backward compatibility
