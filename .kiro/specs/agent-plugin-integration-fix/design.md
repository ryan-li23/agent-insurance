# Design Document

## Overview

This design addresses two critical architectural issues in the multi-agent insurance claims processing system:

1. **Plugin Integration**: Agents currently don't properly invoke plugins to extract data from uploaded files. The Evidence Curator needs to leverage AWS Bedrock Nova Pro's multimodal vision capabilities for analyzing PDFs and images, rather than generating synthetic data.

2. **Response Format Consistency**: Agent responses are not consistently formatted, causing the Orchestrator's JSON parsing to fail. This leads to empty evidence, missing decisions, and workflow disruptions.

The solution involves:
- Refactoring the Evidence Curator to explicitly invoke Nova Pro for visual analysis
- Creating a standardized response wrapper for all agents
- Enhancing the Orchestrator's parsing logic with better error handling
- Adding a Nova Pro vision plugin to the plugin system

## Architecture

### Component Interaction Flow

```
┌─────────────────┐
│   Supervisor    │
│  Orchestrator   │
└────────┬────────┘
         │
         ├──────────────────────────────────────┐
         │                                      │
         v                                      v
┌────────────────────┐              ┌──────────────────────┐
│ Evidence Curator   │              │ Policy Interpreter   │
│                    │              │                      │
│ Uses:              │              │ Uses:                │
│ - NovaVisionPlugin │              │ - PolicyRetriever    │
│ - PDFExtractor     │              │                      │
│ - EXIFReader       │              │                      │
└────────────────────┘              └──────────────────────┘
         │                                      │
         │                                      │
         v                                      v
┌────────────────────────────────────────────────────────┐
│              Compliance Reviewer                       │
│                                                        │
│              Uses: ComplianceChecker                   │
└────────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **Nova Pro Integration**: Create a dedicated `NovaVisionPlugin` that wraps the Bedrock client's multimodal capabilities, accepting both image bytes and PDF bytes.

2. **Explicit Plugin Invocation**: Agents will explicitly call plugin methods within their `invoke()` implementation, rather than relying on Semantic Kernel's automatic tool calling.

3. **Structured Response Format**: All agents will use a `ResponseFormatter` utility class to ensure consistent JSON output with proper delimiters.

4. **Robust Parsing**: The Orchestrator will use enhanced JSON extraction logic with fallback mechanisms and detailed error logging.

5. **Agent Name Consistency**: Standardize on kebab-case agent names (`evidence-curator`, `policy-interpreter`, `compliance-reviewer`) throughout the system.

## Components and Interfaces

### 1. NovaVisionPlugin

New plugin for multimodal vision analysis using Nova Pro.

```python
class NovaVisionPlugin:
    """Plugin for analyzing images and PDFs using Nova Pro vision capabilities."""
    
    def __init__(self, bedrock_client: BedrockClient):
        self.bedrock_client = bedrock_client
    
    @kernel_function
    async def analyze_damage_image(
        self,
        image_bytes: bytes,
        image_name: str,
        prompt: str = "Analyze this damage photo..."
    ) -> Dict[str, Any]:
        """
        Analyze a damage photo using Nova Pro vision.
        
        Returns:
            {
                "observations": [...],
                "global_assessment": {...},
                "chronology": {...},
                "confidence": 0.95
            }
        """
        pass
    
    @kernel_function
    async def extract_pdf_form_fields(
        self,
        pdf_bytes: bytes,
        pdf_name: str
    ) -> Dict[str, Any]:
        """
        Extract form fields from PDF using Nova Pro vision.
        
        Returns:
            {
                "fields": {...},
                "confidence": 0.90
            }
        """
        pass
    
    @kernel_function
    async def extract_receipt_data(
        self,
        image_bytes: bytes,
        image_name: str
    ) -> Dict[str, Any]:
        """
        Extract line items from receipt/invoice image.
        
        Returns:
            {
                "vendor": "...",
                "invoice_number": "...",
                "line_items": [...],
                "total": 0.0,
                "confidence": 0.92
            }
        """
        pass
```

### 2. ResponseFormatter Utility

Utility class for standardizing agent responses.

```python
class ResponseFormatter:
    """Utility for formatting agent responses consistently."""
    
    @staticmethod
    def format_json_response(data: Dict[str, Any], agent_name: str) -> str:
        """
        Format a dictionary as a JSON response with clear delimiters.
        
        Returns:
            String with format:
            [AGENT_NAME_RESPONSE_START]
            {json_data}
            [AGENT_NAME_RESPONSE_END]
        """
        pass
    
    @staticmethod
    def extract_json_from_response(response: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from a formatted response.
        
        Handles:
        - Delimited responses
        - Raw JSON
        - JSON embedded in text
        """
        pass
```

### 3. Enhanced Evidence Curator

Refactored to explicitly invoke plugins.

```python
class EvidenceCuratorAgent(BaseClaimsAgent):
    
    async def invoke(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process claim uploads using plugins explicitly.
        """
        claim_data = context.get("claim_data")
        
        # Initialize result structure
        evidence_data = {
            "evidence": [],
            "expense": {},
            "fnol_summary": "",
            "metadata": {"processing_notes": []}
        }
        
        # 1. Extract FNOL text using PDFExtractor
        for fnol_file in claim_data.fnol_files:
            fnol_bytes = self._read_file_bytes(fnol_file)
            
            # Check if it's a form that needs vision analysis
            if self._is_form_pdf(fnol_file):
                # Use Nova Pro vision for form field extraction
                form_data = await self.nova_vision.extract_pdf_form_fields(
                    pdf_bytes=fnol_bytes,
                    pdf_name=fnol_file.filename
                )
                evidence_data["metadata"]["form_data"] = form_data
            else:
                # Use text extraction for narrative PDFs
                text = await self.pdf_extractor.extract_text(
                    pdf_bytes=fnol_bytes
                )
                evidence_data["fnol_summary"] += text
        
        # 2. Analyze damage photos using Nova Pro vision
        for photo in claim_data.photos:
            photo_bytes = self._read_file_bytes(photo)
            
            # Extract EXIF metadata
            exif_data = await self.exif_reader.extract_metadata(
                image_bytes=photo_bytes
            )
            
            # Analyze damage using Nova Pro vision
            analysis = await self.nova_vision.analyze_damage_image(
                image_bytes=photo_bytes,
                image_name=photo.filename,
                prompt=self._build_damage_analysis_prompt()
            )
            
            # Combine analysis with EXIF data
            image_evidence = {
                "image_name": photo.filename,
                "observations": analysis["observations"],
                "global_assessment": analysis["global_assessment"],
                "chronology": analysis["chronology"],
                "exif_data": exif_data
            }
            
            evidence_data["evidence"].append(image_evidence)
        
        # 3. Extract invoice data using Nova Pro vision
        for invoice in claim_data.invoices:
            invoice_bytes = self._read_file_bytes(invoice)
            
            expense_data = await self.nova_vision.extract_receipt_data(
                image_bytes=invoice_bytes,
                image_name=invoice.filename
            )
            
            # Merge with existing expense data or set as primary
            if not evidence_data["expense"]:
                evidence_data["expense"] = expense_data
            else:
                # Merge line items if multiple invoices
                evidence_data["expense"]["line_items"].extend(
                    expense_data["line_items"]
                )
        
        # 4. Format response consistently
        response_text = ResponseFormatter.format_json_response(
            data=evidence_data,
            agent_name=self.name
        )
        
        return evidence_data
```

### 4. Enhanced Orchestrator Parsing

Improved JSON extraction with fallback mechanisms.

```python
class SupervisorOrchestrator:
    
    def _extract_evidence_data(self) -> Dict[str, Any]:
        """
        Extract evidence data with enhanced parsing.
        """
        curator_turns = self.conversation.get_turns_by_role("evidence-curator")
        
        if not curator_turns:
            logger.warning("No curator turns found")
            return {"evidence": [], "expense": {}}
        
        # Try each turn in reverse order (most recent first)
        for turn in reversed(curator_turns):
            try:
                # Try ResponseFormatter extraction first
                evidence_data = ResponseFormatter.extract_json_from_response(
                    turn.content
                )
                
                if evidence_data and ("evidence" in evidence_data or "expense" in evidence_data):
                    logger.info("Successfully extracted evidence using ResponseFormatter")
                    return evidence_data
                
                # Fallback to manual JSON extraction
                evidence_data = self._manual_json_extraction(turn.content)
                
                if evidence_data and ("evidence" in evidence_data or "expense" in evidence_data):
                    logger.info("Successfully extracted evidence using manual extraction")
                    return evidence_data
            
            except Exception as e:
                logger.error(
                    f"Failed to parse evidence from turn: {str(e)}\n"
                    f"Content preview: {turn.content[:200]}"
                )
                continue
        
        logger.error("Could not extract evidence from any curator turn")
        return {"evidence": [], "expense": {}}
    
    def _manual_json_extraction(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Manual JSON extraction with brace counting.
        """
        start_idx = content.find('{')
        if start_idx == -1:
            return None
        
        brace_count = 0
        end_idx = -1
        
        for i in range(start_idx, len(content)):
            if content[i] == '{':
                brace_count += 1
            elif content[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i
                    break
        
        if end_idx != -1:
            json_text = content[start_idx:end_idx + 1]
            return json.loads(json_text)
        
        return None
```

## Data Models

### NovaVisionAnalysisResult

```python
@dataclass
class NovaVisionAnalysisResult:
    """Result from Nova Pro vision analysis."""
    observations: List[Dict[str, Any]]
    global_assessment: Dict[str, Any]
    chronology: Dict[str, Any]
    confidence: float
    raw_response: str
```

### PluginInvocationResult

```python
@dataclass
class PluginInvocationResult:
    """Result from a plugin invocation."""
    success: bool
    data: Optional[Dict[str, Any]]
    error: Optional[str]
    plugin_name: str
    execution_time_ms: float
```

## Error Handling

### Plugin Invocation Errors

1. **Network Errors**: Retry with exponential backoff (handled by BedrockClient)
2. **Vision Analysis Failures**: Log error, continue with other files, include error in metadata
3. **JSON Parsing Errors**: Use fallback structure, log detailed error with content preview

### Response Parsing Errors

1. **No JSON Found**: Log warning with content preview, use empty structure
2. **Invalid JSON**: Try alternative extraction methods, use fallback structure
3. **Missing Required Fields**: Add default values, log warning

### Error Propagation

- Plugin errors should NOT crash the agent
- Agent errors should NOT crash the orchestrator
- All errors should be logged with context
- Partial results should be returned when possible

## Testing Strategy

### Unit Tests

1. **NovaVisionPlugin Tests**
   - Test image analysis with mock Bedrock responses
   - Test PDF form extraction with mock responses
   - Test receipt extraction with mock responses
   - Test error handling for API failures

2. **ResponseFormatter Tests**
   - Test JSON formatting with delimiters
   - Test JSON extraction from various formats
   - Test handling of malformed responses

3. **Evidence Curator Tests**
   - Test plugin invocation for each file type
   - Test error handling when plugins fail
   - Test response formatting

4. **Orchestrator Parsing Tests**
   - Test extraction from well-formed responses
   - Test extraction from malformed responses
   - Test fallback mechanisms

### Integration Tests

1. **End-to-End Plugin Flow**
   - Upload sample files (PDFs, images, invoices)
   - Verify Evidence Curator invokes correct plugins
   - Verify extracted data matches expected structure

2. **Multi-Agent Collaboration**
   - Run full workflow with sample claim
   - Verify all agents return parseable responses
   - Verify Orchestrator correctly compiles final decision

### Manual Testing

1. **Nova Pro Vision Quality**
   - Test with real damage photos
   - Test with real FNOL forms
   - Test with real receipts
   - Verify accuracy and confidence scores

2. **Response Format Consistency**
   - Review agent outputs in logs
   - Verify JSON is properly formatted
   - Verify Orchestrator successfully parses all responses

## Performance Considerations

1. **Parallel Plugin Invocation**: Process multiple files concurrently using asyncio.gather()
2. **Caching**: Cache EXIF data and PDF metadata to avoid redundant processing
3. **Streaming**: For large PDFs, consider streaming to Nova Pro rather than loading entirely in memory
4. **Timeout Handling**: Set appropriate timeouts for Nova Pro calls (30-60 seconds per image)

## Security Considerations

1. **File Validation**: Validate file types and sizes before processing
2. **Byte Handling**: Ensure uploaded file bytes are not persisted unnecessarily
3. **PII Redaction**: Consider redacting PII from logs when logging response content
4. **API Key Management**: Ensure Bedrock credentials are properly secured (already handled by boto3)

## Migration Path

1. **Phase 1**: Implement NovaVisionPlugin and ResponseFormatter
2. **Phase 2**: Refactor Evidence Curator to use plugins explicitly
3. **Phase 3**: Enhance Orchestrator parsing logic
4. **Phase 4**: Update Policy Interpreter and Compliance Reviewer response formatting
5. **Phase 5**: Add comprehensive logging and monitoring
6. **Phase 6**: Test with real claim data and iterate

## Open Questions

1. Should we support batch processing of images to Nova Pro for better performance?
2. What confidence threshold should trigger manual review?
3. Should we implement a plugin result cache to avoid redundant API calls during retries?
4. How should we handle very large PDFs (>10MB) that may exceed Nova Pro limits?
