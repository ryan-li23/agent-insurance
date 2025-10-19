# Implementation Plan

- [x] 1. Set up project infrastructure and configuration





- [x] 1.1 Create modular directory structure (backend/agents, backend/plugins, backend/storage, backend/orchestration, backend/models, backend/utils)


  - Create all necessary __init__.py files
  - Set up proper Python package structure
  - _Requirements: 4.1, 4.2_

- [x] 1.2 Create configuration management system


  - Implement config.yaml with AWS, FAISS, agent, and storage settings
  - Create backend/utils/config.py to load configuration from file and environment variables
  - Add support for environment variable overrides
  - _Requirements: 12.1, 12.2, 12.3, 12.4_

- [x] 1.3 Set up logging infrastructure


  - Create backend/utils/logging.py with structured logging
  - Configure log levels, formats, and file output
  - Add context-aware logging (case_id, component, etc.)
  - _Requirements: 11.1, 11.2_

- [x] 1.4 Create requirements.txt with all dependencies


  - Add semantic-kernel, streamlit, boto3, faiss-cpu, PyPDF2, pdfplumber, Pillow, pytest
  - Pin versions for reproducibility
  - _Requirements: 11.1, 11.5_

- [x] 1.5 Create data models


  - Implement backend/models/claim.py (ClaimInput dataclass)
  - Implement backend/models/evidence.py (Observation, ImageEvidence, ExpenseData dataclasses)
  - Implement backend/models/decision.py (Objection, Citation, Decision, AgentTurn dataclasses)
  - _Requirements: 4.1, 4.2, 4.3_

- [ ] 2. Implement AWS Bedrock integration layer
- [x] 2.1 Create Bedrock client wrapper




  - Implement backend/utils/bedrock_client.py with BedrockClient class
  - Add invoke_nova_pro method for Converse API calls
  - Add generate_embedding method for Titan embeddings
  - Implement retry logic with exponential backoff
  - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [x] 2.2 Add error handling for Bedrock API






  - Create backend/utils/errors.py with ErrorContext and ClaimsProcessingError classes
  - Handle rate limiting, timeouts, and authentication errors
  - Implement graceful degradation patterns
  - _Requirements: 3.4, 9.4_


- [x] 3. Implement FAISS vector store for policy retrieval



- [x] 3.1 Create PolicyVectorStore class


  - Implement backend/storage/vector_store.py with FAISS index management
  - Add build_index method to create index from policy PDFs
  - Add load_index method to load existing index from disk
  - Add search method for semantic similarity search
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 3.2 Implement policy document chunking

  - Create chunking logic (500 tokens with 50 token overlap)
  - Extract metadata (policy type, section, page number)
  - Generate embeddings using Bedrock Titan
  - _Requirements: 2.1, 2.6_

- [x] 3.3 Add index persistence and loading

  - Save FAISS index to data/policy_index.faiss
  - Save metadata to data/policy_metadata.json
  - Implement lazy loading on first access
  - _Requirements: 2.4, 2.5_

- [x] 3.4 Create file storage utilities


  - Implement backend/storage/file_storage.py for local file management
  - Add methods to save/load uploads by case_id
  - Create directory structure for policies, sample_cases, uploads
  - _Requirements: 11.2, 11.3_

- [x] 4. Implement Semantic Kernel plugins (tools)



- [x] 4.1 Create PDF text extractor plugin



  - Implement backend/plugins/pdf_extractor.py using PyPDF2 or pdfplumber
  - Add @kernel_function decorator for extract_pdf_text
  - Handle extraction errors gracefully
  - _Requirements: 3.1, 3.5, 5.1_

- [x] 4.2 Create image analyzer plugin





  - Implement backend/plugins/image_analyzer.py using Nova Pro vision
  - Add @kernel_function decorator for analyze_damage_image
  - Call Bedrock Converse API with image content block
  - Return structured observations with bboxes, severity, novelty
  - _Requirements: 3.2, 5.2, 9.2_

- [x] 4.3 Create invoice parser plugin





  - Implement backend/plugins/invoice_parser.py using Nova Pro document analysis
  - Add @kernel_function decorator for parse_invoice
  - Call Bedrock Converse API with document content block
  - Return normalized expense JSON with line items
  - _Requirements: 3.2, 5.2, 9.2_

- [x] 4.4 Create policy retriever plugin


  - Implement backend/plugins/policy_retriever.py using FAISS vector store
  - Add @kernel_function decorator for retrieve_policy_clauses
  - Generate query embeddings and search FAISS index
  - Return policy text with citations (section, page)
  - _Requirements: 2.2, 2.6, 6.1, 6.2_

- [x] 4.5 Create EXIF reader plugin


  - Implement backend/plugins/exif_reader.py using PIL or exifread
  - Add @kernel_function decorator for extract_image_metadata
  - Extract timestamp, camera info, GPS data if available
  - _Requirements: 3.4, 5.4_




- [x] 4.6 Create compliance checker plugin

  - Implement backend/plugins/compliance_checker.py for fraud detection
  - Add @kernel_function decorator for check_compliance
  - Implement timestamp mismatch detection


  - Implement scope creep detection (invoice vs. claim narrative)
  - _Requirements: 7.2, 7.3, 7.4_

- [x] 4.7 Create FNOL parser plugin


  - Implement backend/plugins/fnol_parser.py using Nova Pro document analysis
  - Add @kernel_function decorator for parse_fnol_form
  - Call Bedrock Converse API with document/image content block
  - Return structured FNOL data (policy number, dates, loss description, etc.)
  - Handle both PDF and image formats
  - _Requirements: 7.2, 7.3, 7.4_

- [-] 5. Implement agent classes



- [x] 5.1 Create base agent class

  - Implement backend/agents/base.py with BaseClaimsAgent
  - Extend Semantic Kernel Agent class
  - Add common initialization (kernel, name, instructions, plugins)
  - _Requirements: 1.1, 1.2, 4.2_

- [x] 5.2 Implement Evidence Curator agent


  - Create backend/agents/curator.py extending BaseClaimsAgent
  - Wire plugins: pdf_extractor, image_analyzer, invoice_parser, exif_reader
  - Implement invoke method to process uploads and extract evidence
  - Return structured evidence JSON (observations, expense data)
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 5.3 Implement Policy Interpreter agent


  - Create backend/agents/interpreter.py extending BaseClaimsAgent
  - Wire plugins: policy_retriever, citation_formatter, coverage_analyzer
  - Implement invoke method to map evidence to policy clauses
  - Return coverage position with citations and rationale
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 5.4 Implement Compliance Reviewer agent



  - Create backend/agents/reviewer.py extending BaseClaimsAgent
  - Wire plugins: objection_generator, fraud_detector, fairness_checker
  - Implement invoke method to challenge Interpreter's decision
  - Return objections list with blocking/resolved status
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 6. Implement orchestration layer




- [x] 6.1 Create custom selection strategy


  - Implement backend/orchestration/strategies.py with DebateSelectionStrategy
  - Enforce turn order: Round 1 (Curator → Interpreter → Reviewer), Round 2+ (Reviewer → Curator → Interpreter)
  - Prevent infinite loops with turn tracking
  - _Requirements: 8.1, 8.2_

- [x] 6.2 Create custom termination strategy

  - Implement ConsensusTerminationStrategy in backend/orchestration/strategies.py
  - Terminate on Reviewer approval (no blocking objections)
  - Terminate on max rounds reached (3 rounds)
  - _Requirements: 8.3, 8.4_

- [x] 6.3 Implement conversation history management


  - Create backend/orchestration/conversation.py to track agent turns
  - Store role, content, timestamp for each turn
  - Provide methods to retrieve full conversation history
  - _Requirements: 1.5, 8.5_

- [x] 6.4 Create Supervisor orchestrator


  - Implement backend/orchestration/supervisor.py with SupervisorOrchestrator class
  - Initialize Semantic Kernel and all three agents
  - Create AgentGroupChat with custom strategies
  - Implement run_collaboration method to execute debate workflow
  - Compile final decision from conversation history
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 7. Update main reasoner entry point






- [x] 7.1 Refactor backend/reasoner.py to use new architecture

  - Replace simulated logic with Supervisor orchestration
  - Initialize configuration, Bedrock client, FAISS index
  - Create Semantic Kernel instance
  - Call Supervisor.run_collaboration with claim data
  - Return decision in format expected by Streamlit UI
  - _Requirements: 10.1, 10.2_


- [x] 7.2 Ensure backward compatibility with Streamlit UI


  - Maintain run_reasoner function signature
  - Return dict with keys: turns, evidence, expense, decision, objections, citations
  - Handle errors gracefully and return partial results
  - _Requirements: 10.1, 10.3, 10.4, 10.5_

- [x] 8. Create initialization script for FAISS index






- [x] 8.1 Create script to build policy index

  - Create backend/storage/build_index.py as standalone script
  - Load policy PDFs from data/policies/
  - Chunk documents and generate embeddings
  - Build and save FAISS index
  - _Requirements: 2.1, 2.3, 11.2_


- [x] 8.2 Add sample policy documents

  - Download HO-3 specimen policy PDF
  - Download PAP specimen policy PDF
  - Save to data/policies/ directory
  - _Requirements: 11.2_

- [-] 9. Add sample test cases
- [x] 9.1 Create sample case data files






  - Create data/sample_cases/case_a/ with FNOL, photos, invoice (burst pipe)
  - Create data/sample_cases/case_b/ with FNOL, photos, invoice (seepage)
  - Create data/sample_cases/case_c/ with FNOL, photos, invoice (auto collision)
  - _Requirements: 11.1, 11.5_

- [x] 9.2 Update Streamlit UI to load sample cases






  - Modify app.py "Load Sample" button to read actual files from data/sample_cases/case_X/
  - Load FNOL PDFs, photos, and invoices into session_state file uploaders
  - Remove hardcoded simulation logic that uses scenario flags
  - Ensure loaded sample files are processed by real backend (not simulated)
  - Sample cases provide quick demo/testing without manual file uploads
  - _Requirements: 10.1, 10.2_

- [ ]* 10. Write unit tests
- [ ]* 10.1 Write tests for plugins
  - Test PDF extractor with sample PDFs
  - Test image analyzer with mock Bedrock responses
  - Test invoice parser with mock Bedrock responses
  - Test policy retriever with test FAISS index
  - _Requirements: 11.1_

- [ ]* 10.2 Write tests for agents
  - Test each agent in isolation with mocked plugins
  - Verify correct plugin invocation patterns
  - Validate output schema compliance
  - _Requirements: 11.1_

- [ ]* 10.3 Write tests for orchestration
  - Test selection strategy turn order
  - Test termination strategy conditions
  - Test conversation history tracking
  - _Requirements: 11.1_

- [ ]* 10.4 Write integration tests
  - Test full debate workflow with sample cases
  - Verify expected outcomes for case A, B, C
  - Check objection handling and resolution
  - _Requirements: 11.1, 11.5_

- [ ] 11. Documentation and deployment
- [ ] 11.1 Create comprehensive README.md
  - Add setup instructions (prerequisites, installation, AWS credentials)
  - Add usage instructions (running locally, sample cases)
  - Add architecture overview and design decisions
  - Add troubleshooting guide
  - _Requirements: 11.1, 11.4_

- [ ] 11.2 Create .env.example file
  - Document all required environment variables
  - Provide example values
  - _Requirements: 12.1, 12.5_

- [ ] 11.3 Add inline code documentation
  - Add docstrings to all classes and methods
  - Add type hints throughout codebase
  - Add comments for complex logic
  - _Requirements: 4.1, 4.2_

- [ ] 11.4 Test end-to-end with all three scenarios
  - Run case A and verify quick approval (1 round)
  - Run case B and verify multi-round debate with partial approval
  - Run case C and verify fraud detection and partial approval
  - Validate all outputs match expected format
  - _Requirements: 11.5_
