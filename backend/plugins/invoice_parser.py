"""Invoice parsing plugin for Semantic Kernel using AWS Bedrock Nova Pro."""

import json
import logging
import time
from typing import Dict, Any, Optional, List

from semantic_kernel.functions import kernel_function

from ..utils.bedrock_client import BedrockClient
from ..utils.errors import DocumentProcessingError, ErrorType, ErrorContext

logger = logging.getLogger(__name__)


class InvoiceParserPlugin:
    """
    Semantic Kernel plugin for parsing invoice documents using Nova Pro.
    
    Extracts structured expense data including vendor information, line items,
    totals, and other invoice details from PDF or image documents.
    """
    
    def __init__(self, bedrock_client: BedrockClient):
        """
        Initialize invoice parser plugin.
        
        Args:
            bedrock_client: Configured BedrockClient instance
        """
        self.bedrock = bedrock_client
        logger.info("Initialized InvoiceParserPlugin")
    
    @kernel_function(
        name="parse_invoice",
        description=(
            "Extract structured data from invoice PDFs or images. "
            "Returns vendor information, line items, totals, and other invoice details. "
            "Handles various invoice formats and layouts."
        )
    )
    async def parse_invoice(
        self,
        document_bytes: bytes,
        document_name: str = "invoice",
        document_format: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Parse an invoice document using Nova Pro document analysis.
        
        Args:
            document_bytes: Raw document bytes (PDF, JPEG, PNG, etc.)
            document_name: Name/identifier for the document
            document_format: Optional format hint ("pdf", "jpeg", "png")
            
        Returns:
            Dictionary containing:
                - vendor: Vendor/contractor name
                - invoice_number: Invoice identifier
                - invoice_date: Date of invoice
                - currency: Currency code
                - subtotal: Subtotal amount
                - tax: Tax amount
                - total: Total amount
                - line_items: List of line item dicts
            
        Raises:
            DocumentProcessingError: If invoice parsing fails
        """
        try:
            start_time = time.time()
            logger.info(f"Starting invoice parsing: {document_name}")
            logger.debug(f"Document size: {len(document_bytes)} bytes, format hint: {document_format}")
            
            # Detect document format if not provided
            if document_format is None:
                document_format = self._detect_document_format(document_bytes)
            
            logger.debug(f"Detected/using document format: {document_format}")
            
            # Build prompt for invoice parsing
            prompt = self._build_parsing_prompt()
            logger.debug(f"Parsing prompt length: {len(prompt)} characters")
            
            # Construct message with document content block
            # Note: boto3's converse API expects raw bytes, not base64-encoded strings
            messages = self._build_messages(
                document_bytes,  # Pass raw bytes instead of base64
                document_format,
                prompt
            )
            logger.debug(f"Constructed message with {len(messages)} parts")
            
            logger.debug(f"Calling Nova Pro API for invoice parsing: {document_name}")
            
            # Call Nova Pro with document analysis
            api_start = time.time()
            response = await self.bedrock.invoke_nova_pro(
                messages=messages,
                temperature=0.0,
                max_tokens=4096
            )
            api_time = time.time() - api_start
            logger.debug(f"Nova Pro API call completed in {api_time:.3f}s")
            
            # Parse response text as JSON
            response_text = response.get("text", "")
            
            if not response_text:
                logger.warning(f"Empty response from Nova Pro for invoice: {document_name}")
                return self._empty_invoice_result()
            
            logger.debug(f"Nova Pro response length: {len(response_text)} characters")
            logger.debug(f"Response preview: {response_text[:200]}...")
            
            # Extract JSON from response
            parse_start = time.time()
            invoice_data = self._parse_invoice_response(response_text)
            parse_time = time.time() - parse_start
            logger.debug(f"JSON parsing completed in {parse_time:.3f}s")
            
            # Validate and structure the result
            structure_start = time.time()
            structured_result = self._structure_invoice_result(
                invoice_data,
                document_name
            )
            structure_time = time.time() - structure_start
            logger.debug(f"Result structuring completed in {structure_time:.3f}s")
            
            total_time = time.time() - start_time
            logger.info(
                f"Invoice parsing complete for {document_name}: "
                f"vendor={structured_result.get('vendor')}, "
                f"total={structured_result.get('total')}, "
                f"line_items={len(structured_result.get('line_items', []))} "
                f"in {total_time:.3f}s (API: {api_time:.3f}s)"
            )
            
            return structured_result
            
        except Exception as e:
            logger.error(f"Failed to parse invoice {document_name}: {str(e)}")
            
            # Wrap in DocumentProcessingError
            context = ErrorContext(
                error_type=ErrorType.INVOICE_PARSING_FAILED,
                message=f"Failed to parse invoice {document_name}: {str(e)}",
                recoverable=True,
                fallback_action="Request manual invoice review",
                original_exception=e
            )
            raise DocumentProcessingError(context)
    
    def _detect_document_format(self, document_bytes: bytes) -> str:
        """
        Detect document format from bytes.
        
        Args:
            document_bytes: Raw document bytes
            
        Returns:
            Format string ("pdf", "jpeg", "png", "gif", "webp")
        """
        # Check magic bytes for PDF
        if document_bytes.startswith(b'%PDF'):
            return "pdf"
        # Check for image formats
        elif document_bytes.startswith(b'\xff\xd8\xff'):
            return "jpeg"
        elif document_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
            return "png"
        elif document_bytes.startswith(b'GIF87a') or document_bytes.startswith(b'GIF89a'):
            return "gif"
        elif document_bytes.startswith(b'RIFF') and b'WEBP' in document_bytes[:12]:
            return "webp"
        else:
            # Default to PDF for unknown formats
            logger.warning("Unknown document format, defaulting to PDF")
            return "pdf"
    
    def _build_parsing_prompt(self) -> str:
        """
        Build the parsing prompt for Nova Pro.
        
        Returns:
            Formatted prompt string
        """
        prompt = """Analyze this invoice document and extract all relevant information in a structured format.

Extract the following information:
1. vendor: The vendor/contractor/company name
2. invoice_number: The invoice number or identifier
3. invoice_date: The date of the invoice (format as YYYY-MM-DD if possible)
4. currency: The currency code (e.g., "USD", "EUR", "CAD")
5. subtotal: The subtotal amount before tax (as a number)
6. tax: The tax amount (as a number)
7. total: The total amount including tax (as a number)
8. line_items: A list of individual line items, each containing:
   - description: Description of the item/service
   - quantity: Quantity (if applicable)
   - unit_price: Price per unit (if applicable)
   - amount: Total amount for this line item
   - category: Category of the item (e.g., "labor", "materials", "equipment")

Additional fields to extract if available:
- payment_terms: Payment terms or due date
- purchase_order: Purchase order number if referenced
- notes: Any special notes or comments on the invoice

Return your analysis as a JSON object with this structure:
{
    "vendor": "Company Name",
    "invoice_number": "INV-12345",
    "invoice_date": "2024-01-15",
    "currency": "USD",
    "subtotal": 1000.00,
    "tax": 80.00,
    "total": 1080.00,
    "line_items": [
        {
            "description": "Item description",
            "quantity": 1,
            "unit_price": 100.00,
            "amount": 100.00,
            "category": "materials"
        }
    ],
    "payment_terms": "Net 30",
    "purchase_order": "PO-123",
    "notes": "Any additional notes"
}

Important:
- Extract all amounts as numbers (not strings with currency symbols)
- If a field is not found, use null for strings or 0.0 for numbers
- Ensure line_items is always a list (empty list if no items found)
- For dates, use YYYY-MM-DD format when possible
- If the document is not an invoice or cannot be parsed, return a minimal structure with available information

Return ONLY the JSON object, no additional text."""
        
        return prompt
    
    def _build_messages(
        self,
        document_bytes: bytes,
        document_format: str,
        prompt: str
    ) -> List[Dict[str, Any]]:
        """
        Build messages for Nova Pro API call.
        
        Args:
            document_bytes: Raw document bytes (boto3 handles encoding)
            document_format: Document format
            prompt: Parsing prompt
            
        Returns:
            List of message dicts
        """
        # For PDF documents, use document content block
        if document_format == "pdf":
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "document": {
                                "format": "pdf",
                                "name": "invoice",
                                "source": {
                                    "bytes": document_bytes  # Pass raw bytes
                                }
                            }
                        },
                        {
                            "text": prompt
                        }
                    ]
                }
            ]
        else:
            # For images, use image content block
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "image": {
                                "format": document_format,
                                "source": {
                                    "bytes": document_bytes  # Pass raw bytes
                                }
                            }
                        },
                        {
                            "text": prompt
                        }
                    ]
                }
            ]
        
        return messages
    
    def _parse_invoice_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse the JSON response from Nova Pro.
        
        Args:
            response_text: Raw response text
            
        Returns:
            Parsed JSON dict
            
        Raises:
            ValueError: If response cannot be parsed as JSON
        """
        # Try to extract JSON from response
        # Sometimes the model includes markdown code blocks
        text = response_text.strip()
        
        # Remove markdown code blocks if present
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        
        if text.endswith("```"):
            text = text[:-3]
        
        text = text.strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {text[:200]}...")
            raise ValueError(f"Invalid JSON response from Nova Pro: {str(e)}")
    
    def _structure_invoice_result(
        self,
        invoice_data: Dict[str, Any],
        document_name: str
    ) -> Dict[str, Any]:
        """
        Structure and validate the invoice result.
        
        Args:
            invoice_data: Raw invoice data from Nova Pro
            document_name: Name of the parsed document
            
        Returns:
            Structured result dict matching ExpenseData schema
        """
        # Extract and validate core fields
        vendor = invoice_data.get("vendor") or "Unknown Vendor"
        invoice_number = invoice_data.get("invoice_number") or "N/A"
        invoice_date = invoice_data.get("invoice_date") or ""
        currency = invoice_data.get("currency") or "USD"
        
        # Parse numeric fields with fallbacks
        try:
            subtotal = float(invoice_data.get("subtotal", 0.0))
        except (ValueError, TypeError):
            subtotal = 0.0
        
        try:
            tax = float(invoice_data.get("tax", 0.0))
        except (ValueError, TypeError):
            tax = 0.0
        
        try:
            total = float(invoice_data.get("total", 0.0))
        except (ValueError, TypeError):
            total = 0.0
        
        # Process line items
        line_items = []
        for item_data in invoice_data.get("line_items", []):
            try:
                line_item = {
                    "description": item_data.get("description", ""),
                    "quantity": item_data.get("quantity"),
                    "unit_price": self._safe_float(item_data.get("unit_price")),
                    "amount": self._safe_float(item_data.get("amount", 0.0)),
                    "category": item_data.get("category", "other")
                }
                line_items.append(line_item)
            except Exception as e:
                logger.warning(f"Failed to process line item: {str(e)}")
                continue
        
        # Build structured result
        result = {
            "vendor": vendor,
            "invoice_number": invoice_number,
            "invoice_date": invoice_date,
            "currency": currency,
            "subtotal": subtotal,
            "tax": tax,
            "total": total,
            "line_items": line_items,
            "document_name": document_name
        }
        
        # Add optional fields if present
        if "payment_terms" in invoice_data:
            result["payment_terms"] = invoice_data["payment_terms"]
        
        if "purchase_order" in invoice_data:
            result["purchase_order"] = invoice_data["purchase_order"]
        
        if "notes" in invoice_data:
            result["notes"] = invoice_data["notes"]
        
        return result
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """
        Safely convert a value to float.
        
        Args:
            value: Value to convert
            
        Returns:
            Float value or None if conversion fails
        """
        if value is None:
            return None
        
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _empty_invoice_result(self) -> Dict[str, Any]:
        """
        Return an empty invoice result structure.
        
        Returns:
            Empty result dict
        """
        return {
            "vendor": "Unknown Vendor",
            "invoice_number": "N/A",
            "invoice_date": "",
            "currency": "USD",
            "subtotal": 0.0,
            "tax": 0.0,
            "total": 0.0,
            "line_items": [],
            "document_name": "unknown"
        }
    
    @kernel_function(
        name="batch_parse_invoices",
        description="Parse multiple invoice documents in sequence. Returns a list of parsed invoice results."
    )
    async def batch_parse(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Parse multiple invoice documents in sequence.
        
        Args:
            documents: List of dicts with 'bytes', 'name', and optional 'format' keys
            
        Returns:
            List of parsed invoice results, one per document
        """
        results = []
        
        for doc_data in documents:
            try:
                result = await self.parse_invoice(
                    document_bytes=doc_data["bytes"],
                    document_name=doc_data.get("name", "unknown"),
                    document_format=doc_data.get("format")
                )
                results.append(result)
            except Exception as e:
                logger.error(
                    f"Failed to parse invoice {doc_data.get('name', 'unknown')}: {str(e)}"
                )
                # Add empty result for failed document
                results.append(self._empty_invoice_result())
        
        logger.info(f"Batch invoice parsing complete: {len(results)} documents processed")
        return results
