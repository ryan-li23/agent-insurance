"""Evidence Curator agent for extracting and structuring claim evidence."""

import json
import logging
import time
from typing import Any, Dict, List, Optional

from .base import BaseClaimsAgent
from ..plugins.image_analyzer import ImageAnalyzerPlugin
from ..plugins.pdf_extractor import PDFExtractorPlugin
from ..plugins.exif_reader import EXIFReaderPlugin
from ..plugins.invoice_parser import InvoiceParserPlugin
from ..utils.response_formatter import ResponseFormatter
from ..utils.bedrock_client import BedrockClient
from ..utils.config import Config

logger = logging.getLogger(__name__)


class EvidenceCuratorAgent(BaseClaimsAgent):
    """
    Evidence Curator agent for extracting and normalizing claim evidence.
    
    Responsibilities:
    - Extract structured data from uploaded documents (PDFs, images, text)
    - Normalize evidence into consistent JSON schemas
    - Maintain confidence scores for all extracted data
    - Respond to requests for additional evidence clarification
    
    Plugins used:
    - pdf_extractor: Extract text from PDFs
    - image_analyzer: Analyze damage photos
    - invoice_parser: Extract line items from invoices
    - exif_reader: Extract metadata from images
    """
    
    def __init__(self):
        """
        Initialize Evidence Curator agent.
        
        Args:
            kernel: Semantic Kernel instance with registered plugins
        """
        instructions = self._build_instructions()
        
        plugins = [
            "pdf_extractor",
            "image_analyzer",
            "invoice_parser",
            "exif_reader"
        ]
        
        super().__init__(
            name="evidence-curator",
            instructions=instructions,
            plugins=plugins
        )
        
        # Initialize plugins lazily to avoid import issues
        self._nova_vision: Optional[ImageAnalyzerPlugin] = None
        self._pdf_extractor: Optional[PDFExtractorPlugin] = None
        self._exif_reader: Optional[EXIFReaderPlugin] = None
        self._invoice_parser: Optional[InvoiceParserPlugin] = None
        self._plugin_bedrock_client: Optional[BedrockClient] = None
    
    def _get_plugin_bedrock_client(self) -> BedrockClient:
        """
        Lazily construct the Bedrock client used by vision- and NLP-heavy plugins.
        
        Returns:
            Shared BedrockClient instance for plugin usage
        """
        if self._plugin_bedrock_client is None:
            config = Config.load()
            self._plugin_bedrock_client = BedrockClient(
                region=config.aws_region,
                model_id=config.bedrock.model_id,
                embedding_model_id=config.bedrock.embedding_model_id,
                timeout=config.bedrock.timeout,
                max_retries=config.bedrock.max_retries
            )
        return self._plugin_bedrock_client
    
    @property
    def nova_vision(self) -> ImageAnalyzerPlugin:
        """Lazy initialization of Nova Vision plugin."""
        if self._nova_vision is None:
            self._nova_vision = ImageAnalyzerPlugin(self._get_plugin_bedrock_client())
        return self._nova_vision
    
    @property
    def pdf_extractor(self) -> PDFExtractorPlugin:
        """Lazy initialization of PDF extractor plugin."""
        if self._pdf_extractor is None:
            self._pdf_extractor = PDFExtractorPlugin()
        return self._pdf_extractor
    
    @property
    def exif_reader(self) -> EXIFReaderPlugin:
        """Lazy initialization of EXIF reader plugin."""
        if self._exif_reader is None:
            self._exif_reader = EXIFReaderPlugin()
        return self._exif_reader
    
    @property
    def invoice_parser(self) -> InvoiceParserPlugin:
        """Lazy initialization of invoice parser plugin."""
        if self._invoice_parser is None:
            self._invoice_parser = InvoiceParserPlugin(self._get_plugin_bedrock_client())
        return self._invoice_parser
    
    def _build_instructions(self) -> str:
        """
        Build system instructions for the Evidence Curator.
        
        Returns:
            Instruction string
        """
        return """You are the Evidence Curator agent in a claims processing system.

Your role is to extract and structure all claim evidence from uploaded documents.

RESPONSIBILITIES:
1. Extract text from FNOL (First Notice of Loss) documents using pdf_extractor
2. Analyze damage photos using image_analyzer to identify damage types, locations, and severity
3. Parse invoices using invoice_parser to extract vendor information and line items
4. Extract image metadata using exif_reader to verify timestamps and authenticity
5. Normalize all evidence into structured JSON format
6. Provide confidence scores for extracted data
7. Respond to requests for additional evidence or clarification

OUTPUT FORMAT:
Your output should be a JSON object with this structure:
{
    "evidence": [
        {
            "image_name": "actual_filename.jpg",
            "observations": [
                {
                    "label": "damage_type",
                    "confidence": 0.0-1.0,
                    "bbox": {"x": 0.0-1.0, "y": 0.0-1.0, "w": 0.0-1.0, "h": 0.0-1.0},
                    "location_text": "description of location",
                    "novelty": "new|old|unclear",
                    "severity": "minor|moderate|severe",
                    "evidence_notes": ["specific details observed"]
                }
            ],
            "global_assessment": {
                "overall_condition": "description",
                "primary_concerns": ["list of concerns"],
                "patterns": "patterns observed"
            },
            "chronology": {
                "estimated_age": "timeframe",
                "consistency_indicators": ["indicators"],
                "timeline_notes": "notes about timing"
            }
        }
    ],
    "expense": {
        "vendor": "vendor_name",
        "invoice_number": "invoice_id",
        "invoice_date": "YYYY-MM-DD",
        "currency": "USD",
        "subtotal": 0.00,
        "tax": 0.00,
        "total": 0.00,
        "line_items": [
            {
                "description": "item_description",
                "quantity": 0,
                "unit_price": 0.00,
                "amount": 0.00,
                "category": "category"
            }
        ]
    },
    "fnol_summary": "Summary of extracted FNOL content",
    "metadata": {
        "image_timestamps": ["actual_timestamps_from_exif"],
        "processing_notes": ["actual_processing_results"]
    }
}

GUIDELINES:
- Be thorough and extract all available evidence
- Provide confidence scores for uncertain observations
- Flag any inconsistencies or missing information
- Use the available plugins to process different document types
- If evidence is ambiguous, note what additional information would help
- Maintain objectivity - report what you observe without interpretation

When responding to other agents:
- Provide additional evidence details when requested
- Clarify ambiguous observations
- Explain confidence scores and uncertainty
- Do not make coverage decisions - that's the Policy Interpreter's role"""
    
    async def invoke(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process claim uploads and extract structured evidence using plugins explicitly.
        
        Args:
            context: Dictionary containing:
                - claim_data: ClaimInput with uploaded files
                - conversation_history: Optional list of previous messages
                
        Returns:
            Dictionary with:
                - evidence: List of ImageEvidence dicts
                - expense: ExpenseData dict
                - fnol_summary: Summary of FNOL text
                - metadata: Additional processing metadata
        """
        try:
            claim_data = context.get("claim_data")
            
            logger.info(
                f"Evidence Curator processing claim: {claim_data.case_id if claim_data else 'unknown'}"
            )
            
            # Initialize result structure
            evidence_data = {
                "evidence": [],
                "expense": {},
                "fnol_summary": "",
                "metadata": {
                    "processing_notes": [],
                    "plugin_errors": [],
                    "image_timestamps": []
                }
            }
            
            if not claim_data:
                logger.warning("No claim data provided")
                self._add_processing_note(evidence_data, "No claim data provided")
                return self._format_response(evidence_data)
            
            # 1. Process FNOL documents
            await self._process_fnol_files(claim_data.fnol_files, evidence_data)
            
            # 2. Process damage photos
            await self._process_photos(claim_data.photos, evidence_data)
            
            # 3. Process invoices
            await self._process_invoices(claim_data.invoices, evidence_data)
            
            logger.info(
                f"Evidence Curator completed processing: "
                f"{len(evidence_data.get('evidence', []))} images analyzed, "
                f"expense total: {evidence_data.get('expense', {}).get('total', 0)}"
            )
            
            return self._format_response(evidence_data)
            
        except Exception as e:
            logger.error(f"Evidence Curator failed: {str(e)}")
            # Return structured error response
            error_data = self._empty_evidence_structure()
            self._add_processing_note(error_data, f"Processing failed: {str(e)}")
            return self._format_response(error_data)
    
    def _build_initial_message(self, claim_data: Any) -> str:
        """
        Build the initial message for evidence extraction.
        
        Args:
            claim_data: ClaimInput instance
            
        Returns:
            Formatted message string
        """
        if claim_data is None:
            return "Please extract and structure all available claim evidence."
        
        message_parts = [
            f"CLAIM ID: {claim_data.case_id}",
            f"DATE OF LOSS: {claim_data.date_of_loss}",
            "",
            "FNOL NARRATIVE:",
            claim_data.fnol_text,
            "",
            "UPLOADED FILES:",
            f"- FNOL documents: {len(claim_data.fnol_files)}",
            f"- Photos: {len(claim_data.photos)}",
            f"- Invoices: {len(claim_data.invoices)}",
            "",
            "TASK:",
            "Please extract and structure all evidence from the uploaded documents.",
            "Use the available plugins to:",
            "1. Extract text from FNOL PDFs (pdf_extractor)",
            "2. Analyze all damage photos (image_analyzer)",
            "3. Parse all invoices (invoice_parser)",
            "4. Extract image metadata (exif_reader)",
            "",
            "Return a complete JSON object with all extracted evidence."
        ]
        
        return "\n".join(message_parts)
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse the agent's response to extract structured evidence.
        
        Args:
            response_text: Raw response text from agent
            
        Returns:
            Structured evidence dictionary
        """
        try:
            # Try to extract JSON from the response
            # The response might contain explanatory text before/after JSON
            
            # Look for JSON object in the response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}')
            
            if start_idx == -1 or end_idx == -1:
                logger.warning("No JSON found in response, returning empty structure")
                return self._empty_evidence_structure()
            
            json_text = response_text[start_idx:end_idx + 1]
            
            # Parse JSON
            evidence_data = json.loads(json_text)
            
            # Validate structure
            if "evidence" not in evidence_data:
                evidence_data["evidence"] = []
            
            if "expense" not in evidence_data:
                evidence_data["expense"] = self._empty_expense()
            
            return evidence_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from response: {str(e)}")
            logger.debug(f"Response text: {response_text[:500]}...")
            return self._empty_evidence_structure()
        
        except Exception as e:
            logger.error(f"Error parsing response: {str(e)}")
            return self._empty_evidence_structure()
    
    def _empty_evidence_structure(self) -> Dict[str, Any]:
        """
        Return an empty evidence structure.
        
        Returns:
            Empty evidence dictionary
        """
        return {
            "evidence": [],
            "expense": self._empty_expense(),
            "fnol_summary": "",
            "metadata": {
                "processing_notes": ["Failed to extract evidence"]
            }
        }
    
    def _empty_expense(self) -> Dict[str, Any]:
        """
        Return an empty expense structure.
        
        Returns:
            Empty expense dictionary
        """
        return {
            "vendor": "Unknown",
            "invoice_number": "N/A",
            "invoice_date": "",
            "currency": "USD",
            "subtotal": 0.0,
            "tax": 0.0,
            "total": 0.0,
            "line_items": []
        }
    
    @staticmethod
    def _add_processing_note(evidence_data: Dict[str, Any], note: str) -> None:
        """Append a processing note into metadata, guarding for missing keys."""
        metadata = evidence_data.setdefault("metadata", {})
        notes = metadata.setdefault("processing_notes", [])
        notes.append(note)
    
    @staticmethod
    def _record_plugin_error(
        evidence_data: Dict[str, Any],
        plugin: str,
        filename: str,
        error: Exception | str
    ) -> None:
        """Record plugin-level errors in metadata for downstream reporting."""
        metadata = evidence_data.setdefault("metadata", {})
        errors = metadata.setdefault("plugin_errors", [])
        errors.append({
            "plugin": plugin,
            "file": filename,
            "error": str(error)
        })
    
    async def _process_fnol_files(self, fnol_files: List[tuple], evidence_data: Dict[str, Any]) -> None:
        """
        Process FNOL documents using appropriate plugins.
        
        Args:
            fnol_files: List of (filename, bytes) tuples
            evidence_data: Evidence data structure to update
        """
        fnol_text_parts = []
        
        logger.info(f"Starting FNOL processing: {len(fnol_files)} files")
        
        for filename, file_bytes in fnol_files:
            try:
                start_time = time.time()
                logger.info(f"Processing FNOL file: {filename} ({len(file_bytes)} bytes)")
                
                # Check if it's a form PDF that needs vision analysis
                if self._is_form_pdf(filename, file_bytes):
                    logger.debug(f"Processing {filename} as form PDF using Nova Pro vision")
                    
                    # Use Nova Pro vision for form field extraction
                    plugin_start = time.time()
                    form_data = await self.nova_vision.extract_pdf_form_fields(
                        pdf_bytes=file_bytes,
                        pdf_name=filename
                    )
                    plugin_time = time.time() - plugin_start
                    logger.debug(f"Nova Pro form extraction completed in {plugin_time:.3f}s")
                    
                    evidence_data["metadata"]["form_data"] = form_data
                    
                    # Add form fields to FNOL summary
                    if form_data.get("fields"):
                        form_summary = self._format_form_fields(form_data["fields"])
                        fnol_text_parts.append(f"Form fields from {filename}:\n{form_summary}")
                        logger.debug(f"Extracted {len(form_data['fields'])} form fields from {filename}")
                else:
                    logger.debug(f"Processing {filename} as narrative PDF using text extraction")
                    
                    # Use text extraction for narrative PDFs
                    plugin_start = time.time()
                    text = self.pdf_extractor.extract_text(
                        pdf_bytes=file_bytes,
                        include_page_numbers=False
                    )
                    plugin_time = time.time() - plugin_start
                    logger.debug(f"PDF text extraction completed in {plugin_time:.3f}s")
                    
                    if text and text.strip():
                        fnol_text_parts.append(f"Content from {filename}:\n{text}")
                        logger.debug(f"Extracted {len(text)} characters of text from {filename}")
                
                total_time = time.time() - start_time
                logger.info(f"Successfully processed FNOL: {filename} in {total_time:.3f}s")
                self._add_processing_note(
                    evidence_data,
                    f"Successfully processed FNOL: {filename}"
                )
                
            except Exception as e:
                logger.error(f"Failed to process FNOL file {filename}: {str(e)}")
                logger.error(f"File details: size={len(file_bytes)} bytes")
                self._record_plugin_error(
                    evidence_data,
                    plugin="pdf_extractor/nova_vision",
                    filename=filename,
                    error=e
                )
                self._add_processing_note(
                    evidence_data,
                    f"Failed to process FNOL: {filename}"
                )
        
        # Combine all FNOL text
        evidence_data["fnol_summary"] = "\n\n".join(fnol_text_parts)
        logger.info(f"FNOL processing complete: {len(fnol_text_parts)} documents processed")
    
    async def _process_photos(self, photos: List[tuple], evidence_data: Dict[str, Any]) -> None:
        """
        Process damage photos using EXIF reader and Nova Pro vision.
        
        Args:
            photos: List of (filename, bytes) tuples
            evidence_data: Evidence data structure to update
        """
        logger.info(f"Starting photo processing: {len(photos)} images")
        
        for filename, image_bytes in photos:
            try:
                start_time = time.time()
                logger.info(f"Processing photo: {filename} ({len(image_bytes)} bytes)")
                
                # Extract EXIF metadata first
                logger.debug(f"Extracting EXIF metadata from {filename}")
                exif_start = time.time()
                exif_data = self.exif_reader.extract_metadata(image_bytes=image_bytes)
                exif_time = time.time() - exif_start
                logger.debug(f"EXIF extraction completed in {exif_time:.3f}s, has_exif: {exif_data.get('has_exif', False)}")
                
                # Store timestamp only if EXIF data is available
                timestamp = exif_data.get("timestamp")
                if timestamp:
                    evidence_data["metadata"]["image_timestamps"].append({
                        "filename": filename,
                        "timestamp": timestamp,
                        "source": "exif",
                        "has_exif": True
                    })
                    logger.debug(f"Found EXIF timestamp in {filename}: {timestamp}")
                else:
                    # Report missing EXIF without fallback - let reviewer judge significance
                    evidence_data["metadata"]["image_timestamps"].append({
                        "filename": filename,
                        "timestamp": None,
                        "source": "unavailable",
                        "has_exif": exif_data.get("has_exif", False),
                        "note": "No EXIF timestamp available - image may have been processed or edited"
                    })
                    logger.debug(f"No EXIF timestamp in {filename}, marked as unavailable")
                
                # Analyze damage using Nova Pro vision
                logger.debug(f"Analyzing damage in {filename} using Nova Pro vision")
                analysis_start = time.time()
                analysis = await self.nova_vision.analyze_image(
                    image_bytes=image_bytes,
                    image_name=filename
                )
                analysis_time = time.time() - analysis_start
                logger.debug(f"Damage analysis completed in {analysis_time:.3f}s")
                
                # Ensure the analysis uses the actual filename, not a placeholder
                if analysis.get("image_name") != filename:
                    logger.warning(f"Analysis returned wrong image name: {analysis.get('image_name')} vs {filename}")
                    analysis["image_name"] = filename
                
                # Combine analysis with EXIF data
                image_evidence = {
                    "image_name": filename,  # Use actual filename
                    "observations": analysis.get("observations", []),
                    "global_assessment": analysis.get("global_assessment", {}),
                    "chronology": analysis.get("chronology", {}),
                    "exif_data": {
                        "timestamp": exif_data.get("timestamp"),
                        "camera_make": exif_data.get("camera_make"),
                        "camera_model": exif_data.get("camera_model"),
                        "gps_latitude": exif_data.get("gps_latitude"),
                        "gps_longitude": exif_data.get("gps_longitude"),
                        "has_exif": exif_data.get("has_exif", False)
                    }
                }
                
                evidence_data["evidence"].append(image_evidence)
                
                total_time = time.time() - start_time
                observations_count = len(analysis.get("observations", []))
                logger.info(
                    f"Successfully analyzed photo: {filename} - "
                    f"{observations_count} observations in {total_time:.3f}s"
                )
                self._add_processing_note(
                    evidence_data,
                    f"Successfully analyzed photo: {filename}"
                )
                
            except Exception as e:
                logger.error(f"Failed to process photo {filename}: {str(e)}")
                logger.error(f"Photo details: size={len(image_bytes)} bytes")
                self._record_plugin_error(
                    evidence_data,
                    plugin="exif_reader/nova_vision",
                    filename=filename,
                    error=e
                )
                self._add_processing_note(
                    evidence_data,
                    f"Failed to analyze photo: {filename}"
                )
        
        logger.info(f"Photo processing complete: {len(evidence_data['evidence'])} images analyzed")
    
    async def _process_invoices(self, invoices: List[tuple], evidence_data: Dict[str, Any]) -> None:
        """
        Process invoices using Nova Pro vision for line item extraction.
        
        Args:
            invoices: List of (filename, bytes) tuples
            evidence_data: Evidence data structure to update
        """
        all_line_items = []
        total_amount = 0.0
        primary_vendor = None
        primary_invoice = None
        
        logger.info(f"Starting invoice processing: {len(invoices)} documents")
        
        for filename, invoice_bytes in invoices:
            try:
                start_time = time.time()
                logger.info(f"Processing invoice: {filename} ({len(invoice_bytes)} bytes)")
                
                # Use Nova Pro vision for invoice parsing
                logger.debug(f"Parsing invoice {filename} using Nova Pro vision")
                parse_start = time.time()
                expense_data = await self.invoice_parser.parse_invoice(
                    document_bytes=invoice_bytes,
                    document_name=filename
                )
                parse_time = time.time() - parse_start
                logger.debug(f"Invoice parsing completed in {parse_time:.3f}s")
                
                # Set primary invoice data from first successful parse
                if not primary_invoice and expense_data.get("vendor") != "Unknown Vendor":
                    primary_invoice = expense_data
                    primary_vendor = expense_data.get("vendor")
                    logger.debug(f"Set primary vendor: {primary_vendor}")
                
                # Accumulate line items and totals
                line_items = expense_data.get("line_items", [])
                all_line_items.extend(line_items)
                
                invoice_total = expense_data.get("total", 0.0)
                if isinstance(invoice_total, (int, float)):
                    total_amount += invoice_total
                
                total_time = time.time() - start_time
                logger.info(
                    f"Successfully parsed invoice: {filename} - vendor: {expense_data.get('vendor')}, "
                    f"total: {invoice_total}, line_items: {len(line_items)} in {total_time:.3f}s"
                )
                self._add_processing_note(
                    evidence_data,
                    f"Successfully parsed invoice: {filename}"
                )
                
            except Exception as e:
                logger.error(f"Failed to process invoice {filename}: {str(e)}")
                logger.error(f"Invoice details: size={len(invoice_bytes)} bytes")
                self._record_plugin_error(
                    evidence_data,
                    plugin="invoice_parser",
                    filename=filename,
                    error=e
                )
                self._add_processing_note(
                    evidence_data,
                    f"Failed to parse invoice: {filename}"
                )
        
        # Build consolidated expense data
        if primary_invoice:
            evidence_data["expense"] = {
                "vendor": primary_invoice.get("vendor", "Unknown"),
                "invoice_number": primary_invoice.get("invoice_number", "N/A"),
                "invoice_date": primary_invoice.get("invoice_date", ""),
                "currency": primary_invoice.get("currency", "USD"),
                "subtotal": primary_invoice.get("subtotal", 0.0),
                "tax": primary_invoice.get("tax", 0.0),
                "total": total_amount,
                "line_items": all_line_items
            }
            logger.info(f"Consolidated expense data: vendor={primary_vendor}, total={total_amount}, items={len(all_line_items)}")
        else:
            evidence_data["expense"] = self._empty_expense()
            logger.warning("No valid invoices found, using empty expense structure")
        
        logger.info(f"Invoice processing complete: {len(invoices)} documents processed")
    
    def _is_form_pdf(self, filename: str, file_bytes: bytes) -> bool:
        """
        Determine if a PDF is a form that needs vision analysis.
        
        Args:
            filename: Name of the file
            file_bytes: PDF bytes
            
        Returns:
            True if it appears to be a form PDF
        """
        # Simple heuristic: check filename for form-related keywords
        form_keywords = ["form", "application", "claim", "report", "worksheet"]
        filename_lower = filename.lower()
        
        for keyword in form_keywords:
            if keyword in filename_lower:
                return True
        
        # Could add more sophisticated detection here
        # For now, default to text extraction for most PDFs
        return False
    
    def _format_form_fields(self, fields: Dict[str, Any]) -> str:
        """
        Format form fields into readable text.
        
        Args:
            fields: Dictionary of field names to values
            
        Returns:
            Formatted string
        """
        formatted_lines = []
        for field_name, field_value in fields.items():
            if field_value is not None:
                formatted_lines.append(f"  {field_name}: {field_value}")
        
        return "\n".join(formatted_lines) if formatted_lines else "No form fields extracted"
    
    def _format_response(self, evidence_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format the final response using ResponseFormatter.
        
        Args:
            evidence_data: Raw evidence data
            
        Returns:
            Formatted response dictionary
        """
        try:
            # Ensure all required fields are present
            if "evidence" not in evidence_data:
                evidence_data["evidence"] = []
            
            if "expense" not in evidence_data:
                evidence_data["expense"] = self._empty_expense()
            
            if "fnol_summary" not in evidence_data:
                evidence_data["fnol_summary"] = ""
            
            if "metadata" not in evidence_data:
                evidence_data["metadata"] = {
                    "processing_notes": [],
                    "plugin_errors": [],
                    "image_timestamps": []
                }
            
            # Log the evidence data for debugging
            logger.info(f"Evidence Curator returning {len(evidence_data.get('evidence', []))} image analyses")
            for img_evidence in evidence_data.get("evidence", []):
                logger.info(f"  - Image: {img_evidence.get('image_name', 'unknown')}")
                logger.debug(f"    Observations: {len(img_evidence.get('observations', []))}")
                logger.debug(f"    EXIF timestamp: {img_evidence.get('exif_data', {}).get('timestamp', 'none')}")
            
            # Log expense data
            expense = evidence_data.get("expense", {})
            logger.info(f"  - Expense: vendor={expense.get('vendor', 'none')}, total={expense.get('total', 0)}")
            
            # Log metadata
            metadata = evidence_data.get("metadata", {})
            logger.info(f"  - Processing notes: {len(metadata.get('processing_notes', []))}")
            logger.info(f"  - Plugin errors: {len(metadata.get('plugin_errors', []))}")
            logger.info(f"  - Image timestamps: {len(metadata.get('image_timestamps', []))}")
            
            # Use ResponseFormatter to ensure consistent JSON output
            formatted_response = ResponseFormatter.format_json_response(
                data=evidence_data
            )
            
            # Log the formatted response for debugging
            logger.debug(f"Formatted evidence response length: {len(formatted_response)}")
            logger.debug(f"Formatted evidence response preview: {formatted_response[:300]}...")
            
            # For the invoke method, we return the data directly
            # The formatted response would be used if this were a string response
            return evidence_data
            
        except Exception as e:
            logger.error(f"Failed to format response: {str(e)}")
            return evidence_data
    
    async def clarify_evidence(
        self,
        question: str,
        conversation_history: List[Dict[str, Any]]
    ) -> str:
        """
        Respond to a request for evidence clarification.
        
        Args:
            question: Question about the evidence
            conversation_history: Previous conversation messages
            
        Returns:
            Clarification response
        """
        try:
            # Ask Bedrock using conversation history
            response_text = await self.get_response(
                conversation_history=conversation_history,
                user_message=question,
            )
            return response_text
            
        except Exception as e:
            logger.error(f"Failed to clarify evidence: {str(e)}")
            return f"I apologize, but I encountered an error while clarifying the evidence: {str(e)}"
