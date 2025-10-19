# Requirements Document

## Introduction

This specification defines the requirements for migrating the Claims Coverage Reasoner from AWS-centric services to a more portable architecture using Microsoft Semantic Kernel for agent orchestration and FAISS for local vector storage. The solution will maintain the multi-agent collaboration model while reducing cloud service dependencies, keeping only AWS Bedrock Nova Pro for LLM inference.

## Requirements

### Requirement 1: Agent Framework Migration

**User Story:** As a developer, I want to use Microsoft Semantic Kernel for agent orchestration, so that I can have a modular, cloud-agnostic multi-agent system.

#### Acceptance Criteria

1. WHEN the system initializes THEN it SHALL use Semantic Kernel's agent framework for all agent definitions
2. WHEN agents collaborate THEN the system SHALL use Semantic Kernel's native orchestration patterns
3. IF an agent needs to invoke a tool THEN Semantic Kernel's plugin system SHALL be used
4. WHEN the supervisor coordinates agents THEN it SHALL use Semantic Kernel's multi-agent collaboration features
5. WHEN agents communicate THEN the system SHALL maintain conversation history using Semantic Kernel's memory abstractions

### Requirement 2: Vector Storage with FAISS

**User Story:** As a developer, I want to use FAISS for local vector storage, so that I can perform policy document retrieval without requiring AWS Knowledge Bases.

#### Acceptance Criteria

1. WHEN policy documents are ingested THEN the system SHALL create FAISS vector indices locally
2. WHEN a policy lookup is requested THEN the system SHALL query FAISS with semantic similarity search
3. WHEN vector embeddings are needed THEN the system SHALL use AWS Bedrock embeddings API or a local embedding model
4. IF the FAISS index doesn't exist THEN the system SHALL create and persist it to disk
5. WHEN the system starts THEN it SHALL load existing FAISS indices from local storage
6. WHEN search results are returned THEN they SHALL include policy text with section and page citations

### Requirement 3: Document Processing Without AWS Services

**User Story:** As a developer, I want to process documents (PDFs, images) using local or minimal cloud dependencies, so that the solution can run without S3, Textract, or Rekognition.

#### Acceptance Criteria

1. WHEN a PDF is uploaded THEN the system SHALL extract text using PyPDF2 or pdfplumber
2. WHEN an image is uploaded THEN the system SHALL use local CV libraries (OpenCV, PIL) for basic analysis
3. WHEN invoice data extraction is needed THEN the system SHALL use AWS Bedrock Nova Pro with vision capabilities
4. WHEN EXIF data is needed THEN the system SHALL use PIL or exifread libraries
5. IF document processing fails THEN the system SHALL provide clear error messages and fallback options

### Requirement 4: Modular Architecture

**User Story:** As a developer, I want a modular codebase with clear separation of concerns, so that components can be easily tested, replaced, or extended.

#### Acceptance Criteria

1. WHEN the system is structured THEN it SHALL have separate modules for agents, tools, storage, and orchestration
2. WHEN a new agent is added THEN it SHALL follow a consistent interface pattern
3. WHEN a new tool is created THEN it SHALL be implemented as a Semantic Kernel plugin
4. IF storage backends need to change THEN the system SHALL use abstraction layers
5. WHEN configuration is needed THEN it SHALL be externalized to config files or environment variables

### Requirement 5: Evidence Curator Agent

**User Story:** As a claims processor, I want the Evidence Curator agent to extract and structure claim data from uploads, so that all evidence is normalized for policy interpretation.

#### Acceptance Criteria

1. WHEN documents are uploaded THEN the Evidence Curator SHALL extract structured data
2. WHEN photos are analyzed THEN the agent SHALL identify damage types, locations, and severity
3. WHEN invoices are processed THEN the agent SHALL extract line items, totals, and vendor information
4. WHEN evidence is collected THEN it SHALL be stored with confidence scores
5. IF additional evidence is requested THEN the agent SHALL respond with specific requirements

### Requirement 6: Policy Interpreter Agent

**User Story:** As a claims processor, I want the Policy Interpreter agent to map claim facts to policy clauses, so that coverage decisions are grounded in specific policy language.

#### Acceptance Criteria

1. WHEN claim evidence is presented THEN the Interpreter SHALL query the policy knowledge base
2. WHEN policy clauses are retrieved THEN they SHALL include section names, page numbers, and exact text
3. WHEN a coverage decision is made THEN it SHALL cite specific policy provisions
4. WHEN exclusions apply THEN the agent SHALL explicitly reference exclusion clauses
5. IF evidence is ambiguous THEN the agent SHALL state what additional information would clarify coverage

### Requirement 7: Compliance & Fairness Reviewer Agent

**User Story:** As a claims processor, I want the Reviewer agent to adversarially challenge coverage decisions, so that errors, fraud indicators, and unfair practices are caught before finalization.

#### Acceptance Criteria

1. WHEN the Interpreter proposes a decision THEN the Reviewer SHALL evaluate it for logical consistency
2. WHEN evidence conflicts with the narrative THEN the Reviewer SHALL raise objections
3. WHEN invoice scope exceeds claim description THEN the Reviewer SHALL flag scope creep
4. WHEN timestamps are inconsistent THEN the Reviewer SHALL identify potential fraud indicators
5. IF objections are raised THEN they SHALL be documented with specific evidence references

### Requirement 8: Supervisor Orchestration

**User Story:** As a system operator, I want the Supervisor to coordinate multi-agent collaboration with proper stop conditions, so that debates converge to decisions efficiently.

#### Acceptance Criteria

1. WHEN a claim is submitted THEN the Supervisor SHALL initiate the agent collaboration workflow
2. WHEN agents exchange messages THEN the Supervisor SHALL enforce turn-taking rules
3. WHEN consensus is reached THEN the Supervisor SHALL terminate the debate
4. IF the maximum round limit is reached THEN the Supervisor SHALL force a decision
5. WHEN the workflow completes THEN the Supervisor SHALL compile the final decision package

### Requirement 9: AWS Bedrock Integration

**User Story:** As a developer, I want to use AWS Bedrock Nova Pro for LLM inference, so that agents have access to powerful reasoning capabilities.

#### Acceptance Criteria

1. WHEN agents need LLM inference THEN the system SHALL call AWS Bedrock Nova Pro
2. WHEN vision analysis is needed THEN the system SHALL use Nova Pro's multimodal capabilities
3. WHEN embeddings are needed THEN the system SHALL use Bedrock's embedding models
4. IF Bedrock calls fail THEN the system SHALL handle errors gracefully with retries
5. WHEN credentials are needed THEN the system SHALL use standard AWS credential providers

### Requirement 10: Streamlit UI Integration

**User Story:** As a user, I want the existing Streamlit UI to work with the new backend, so that the demo experience remains consistent.

#### Acceptance Criteria

1. WHEN the backend is replaced THEN the Streamlit UI SHALL continue to function without breaking changes
2. WHEN a claim is processed THEN the UI SHALL display agent conversation turns in real-time
3. WHEN a decision is reached THEN the UI SHALL show the decision card with citations and objections
4. WHEN evidence is processed THEN the UI SHALL display structured evidence maps
5. IF the backend API changes THEN the UI integration layer SHALL adapt transparently

### Requirement 11: Local Development & Testing

**User Story:** As a developer, I want to run the entire system locally without cloud dependencies (except Bedrock), so that I can develop and test efficiently.

#### Acceptance Criteria

1. WHEN the system starts THEN it SHALL run entirely on localhost
2. WHEN policy documents are loaded THEN they SHALL be read from local file storage
3. WHEN FAISS indices are created THEN they SHALL be persisted to local disk
4. WHEN sample cases are run THEN they SHALL produce consistent, reproducible results
5. IF AWS credentials are unavailable THEN the system SHALL provide clear setup instructions

### Requirement 12: Configuration Management

**User Story:** As a developer, I want externalized configuration for models, paths, and parameters, so that the system can be easily adapted to different environments.

#### Acceptance Criteria

1. WHEN the system initializes THEN it SHALL load configuration from environment variables or config files
2. WHEN model parameters are needed THEN they SHALL be defined in configuration
3. WHEN file paths are referenced THEN they SHALL use configurable base directories
4. IF configuration is missing THEN the system SHALL use sensible defaults
5. WHEN configuration changes THEN the system SHALL not require code modifications
