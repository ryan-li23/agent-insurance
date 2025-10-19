# Implementation Plan

## Current Status Summary
- **Task 1**: ✅ Complete - ImageAnalyzerPlugin already provides Nova Pro vision capabilities
- **Task 2**: ✅ Complete - ResponseFormatter utility class implemented
- **Task 3**: ✅ Complete - Evidence Curator fully refactored to use plugins explicitly
- **Task 7**: ✅ Mostly Complete - Agent names already standardized, minor orchestrator updates needed
- **Tasks 4-6, 8**: 🔄 Ready for implementation - Core infrastructure in place
- **Tasks 9-12**: 📋 Optional testing tasks

- [x] 1. Use ImageAnalyzerPlugin for multimodal analysis (NovaVisionPlugin functionality)
  - ✅ ImageAnalyzerPlugin already implements Nova Pro vision capabilities
  - ✅ Has `analyze_damage_image()` method that accepts image bytes and returns structured observations
  - ✅ Has `extract_pdf_form_fields()` method that accepts PDF bytes and returns form field data
  - ✅ InvoiceParserPlugin provides `parse_invoice()` method for invoice line item extraction
  - ✅ Includes confidence scores in all plugin responses
  - ✅ Handles errors gracefully and returns structured error information
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 2.5, 7.1, 7.2, 7.3_

- [x] 2. Create ResponseFormatter utility class
  - Implement `format_json_response()` static method that wraps JSON with delimiters
  - Implement `extract_json_from_response()` static method that extracts JSON from various formats
  - Handle delimited responses, raw JSON, and JSON embedded in text
  - Add validation to ensure extracted JSON is valid
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 3. Refactor Evidence Curator to use plugins explicitly
  - ✅ Modified `__init__()` to initialize ImageAnalyzerPlugin, PDFExtractorPlugin, EXIFReaderPlugin, and InvoiceParserPlugin
  - ✅ Completely refactored `invoke()` method to explicitly call plugins for each file type
  - ✅ Added logic to process uploaded files as bytes from ClaimInput tuples
  - ✅ Implemented FNOL processing: uses Nova Pro vision for forms via `extract_pdf_form_fields()`, PDFExtractor for narrative text
  - ✅ Implemented photo processing: extracts EXIF data first, then analyzes with Nova Pro vision via `analyze_image()`
  - ✅ Implemented invoice processing: uses Nova Pro vision for line item extraction via InvoiceParserPlugin `parse_invoice()`
  - ✅ Uses ResponseFormatter to format the final evidence JSON
  - ✅ Added comprehensive error handling for individual plugin failures without crashing entire process
  - ✅ Includes plugin errors in metadata field with detailed error information
  - ✅ Added lazy initialization of plugins to avoid import-time issues
  - ✅ Added helper methods: `_process_fnol_files()`, `_process_photos()`, `_process_invoices()`
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 5.1, 5.2, 5.3, 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 4. Enhance SupervisorOrchestrator JSON parsing logic





  - Refactor `_extract_evidence_data()` in SupervisorOrchestrator to use ResponseFormatter first
  - Add fallback to manual JSON extraction with brace counting
  - Add detailed error logging with content previews when parsing fails
  - Ensure fallback structures are returned to prevent workflow crashes
  - Apply same enhancements to `_extract_decision_data()` and `_extract_review_data()`
  - _Requirements: 3.5, 4.1, 4.2, 4.3, 4.4, 4.5_



- [x] 5. Update Policy Interpreter response formatting



  - Modify `invoke()` to use ResponseFormatter for JSON output
  - Ensure all required fields are present in response
  - Verify policy_retriever plugin is explicitly invoked


  - _Requirements: 3.2, 3.4, 3.5, 5.4_

- [x] 6. Update Compliance Reviewer response formatting



  - Modify `invoke()` to use ResponseFormatter for JSON output
  - Ensure all required fields are present in response
  - Verify compliance_checker plugin is explicitly invoked
  - _Requirements: 3.3, 3.4, 3.5, 5.5_

- [x] 7. Standardize agent names across the system



  - ✅ Evidence Curator already uses "evidence-curator" consistently
  - ✅ Policy Interpreter already uses "policy-interpreter" consistently  



  - ✅ Compliance Reviewer already uses "compliance-reviewer" consistently
  - Update SupervisorOrchestrator to handle both kebab-case and title-case for backward compatibility
  - Update ConversationHistory role mapping to handle both formats
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 8. Add comprehensive logging for debugging



  - Add debug logs in ImageAnalyzerPlugin and InvoiceParserPlugin for each API call
  - Add debug logs in EvidenceCuratorAgent for each plugin invocation
  - Add debug logs in SupervisorOrchestrator for JSON extraction attempts
  - Include content previews (first 200 chars) in error logs
  - Log plugin execution times for performance monitoring
  - _Requirements: 4.4, 6.1_

- [ ]* 9. Create unit tests for ImageAnalyzerPlugin and InvoiceParserPlugin
  - Write tests for `analyze_image()` with mock Bedrock responses
  - Write tests for `extract_pdf_form_fields()` with mock responses
  - Write tests for `parse_invoice()` with mock responses
  - Write tests for error handling when Bedrock API fails
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 6.1_

- [ ]* 10. Create unit tests for ResponseFormatter
  - Write tests for `format_json_response()` with various data structures
  - Write tests for `extract_json_from_response()` with well-formed responses
  - Write tests for `extract_json_from_response()` with malformed responses
  - Write tests for handling responses with no JSON
  - _Requirements: 3.4, 3.5_

- [ ]* 11. Create integration tests for EvidenceCuratorAgent
  - Write test that uploads sample FNOL PDF and verifies plugin invocation via `_process_fnol_files()`
  - Write test that uploads sample damage photos and verifies Nova Pro analysis via `_process_photos()`
  - Write test that uploads sample invoice and verifies line item extraction via `_process_invoices()`
  - Write test that verifies error handling when plugin fails
  - Write test that verifies response is properly formatted JSON using ResponseFormatter
  - _Requirements: 1.5, 3.1, 5.1, 5.2, 5.3, 6.2, 6.3, 6.4_

- [ ]* 12. Create integration tests for SupervisorOrchestrator parsing
  - Write test that verifies `_extract_evidence_data()` from well-formed curator response
  - Write test that verifies `_extract_evidence_data()` from malformed curator response
  - Write test that verifies fallback mechanisms work correctly
  - Write test that verifies `_extract_decision_data()` and `_extract_review_data()` methods
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_
