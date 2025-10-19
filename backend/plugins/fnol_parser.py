"""FNOL (First Notice of Loss) parsing plugin for Semantic Kernel using AWS Bedrock Nova Pro."""

import base64
import json
import logging
from typing import Dict, Any, Optional, List

from semantic_kernel.functions import kernel_function

from ..utils.bedrock_client import BedrockClient
from ..utils.errors import DocumentProcessingError, ErrorType, ErrorContext

logger = logging.getLogger(__name__)


class FNOLParserPlugin:
    """
    Semantic Kernel plugin for parsing FNOL (First Notice of Loss) forms.
    
    Extracts structured claim data from FNOL documents including policy information,
    loss details, claimant information, and damage descriptions.
    Handles both PDF and image formats.
    """
    
    def __init__(self, bedrock_client: BedrockClient):
        """
        Initialize FNOL parser plugin.
        
        Args:
            bedrock_client: Configured BedrockClient instance
        """
        self.bedrock = bedrock_client
        logger.info("Initialized FNOLParserPlugin")
    
    @kernel_function(
        name="parse_fnol_form",
        description=(
            "Extract structured data from FNOL (First Notice of Loss) forms. "
            "Returns policy information, loss details, claimant data, and damage descriptions. "
            "Handles both PDF and image formats."
        )
    )
    async def parse_fnol_form(
        self,
        document_bytes: bytes,
        document_name: str = "fnol",
        document_format: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Parse an FNOL form using Nova Pro document analysis.
        
        Args:
            document_bytes: Raw document bytes (PDF, JPEG, PNG, etc.)
            document_name: Name/identifier for the document
            document_format: Optional format hint ("pdf", "jpeg", "png")
            
        Returns:
            Dictionary containing:
                - policy_number: Policy number
                - policy_type: Type of policy (e.g., "HO-3", "PAP")
                - insured_name: Name of insured
                - insured_contact: Contact information
                - loss_date: Date of loss
                - loss_time: Time of loss (if available)
                - loss_location: Location where loss occurred
                - loss_description: Description of what happened
                - damage_description: Description of damage
                - estimated_loss_amount: Estimated loss amount
                - cause_of_loss: Cause/peril (e.g., "fire", "water", "theft")
                - witnesses: List of witnesses (if any)
                - police_report: Police report information (if applicable)
                - additional_info: Any additional notes or information
            
        Raises:
            DocumentProcessingError: If FNOL parsing fails
        """
        try:
            logger.info(f"Parsing FNOL form: {document_name}")
            
            # Detect document format if not provided
            if document_format is None:
                document_format = self._detect_document_format(document_bytes)
            
            # Encode document to base64
            document_base64 = base64.b64encode(document_bytes).decode('utf-8')
            
            # Build prompt for FNOL parsing
            prompt = self._build_parsing_prompt()
            
            # Construct message with document content block
            messages = self._build_messages(
                document_base64,
                document_format,
                prompt
            )
            
            # Call Nova Pro with document analysis
            response = await self.bedrock.invoke_nova_pro(
                messages=messages,
                temperature=0.0,
                max_tokens=4096
            )
            
            # Parse response text as JSON
            response_text = response.get("text", "")
            
            if not response_text:
                logger.warning(f"Empty response from Nova Pro for FNOL: {document_name}")
                return self._empty_fnol_result()
            
            # Extract JSON from response
            fnol_data = self._parse_fnol_response(response_text)
            
            # Validate and structure the result
            structured_result = self._structure_fnol_result(
                fnol_data,
                document_name
            )
            
            logger.info(
                f"FNOL parsing complete for {document_name}: "
                f"policy={structured_result.get('policy_number')}, "
                f"loss_date={structured_result.get('loss_date')}"
            )
            
            return structured_result
            
        except Exception as e:
            logger.error(f"Failed to parse FNOL form {document_name}: {str(e)}")
            
            # Wrap in DocumentProcessingError
            context = ErrorContext(
                error_type=ErrorType.PDF_EXTRACTION_FAILED,  # Using PDF as generic doc error
                message=f"Failed to parse FNOL form {document_name}: {str(e)}",
                recoverable=True,
                fallback_action="Request manual FNOL review",
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
        prompt = """Analyze this First Notice of Loss (FNOL) form and extract all relevant information in a structured format.

Extract the following information:

**Policy Information:**
1. policy_number: The policy number
2. policy_type: Type of policy (e.g., "HO-3", "HO-5", "PAP", "Commercial")
3. insured_name: Name of the insured/policyholder
4. insured_contact: Contact information (phone, email, address)

**Loss Information:**
5. loss_date: Date when the loss occurred (format as YYYY-MM-DD if possible)
6. loss_time: Time when the loss occurred (if available)
7. loss_location: Address or location where the loss occurred
8. loss_description: Detailed description of what happened
9. damage_description: Description of the damage sustained
10. cause_of_loss: Primary cause/peril (e.g., "fire", "water damage", "theft", "wind", "collision")
11. estimated_loss_amount: Estimated dollar amount of loss (as a number)

**Additional Information:**
12. witnesses: List of witnesses with names and contact info (if any)
13. police_report: Police report number and department (if applicable)
14. emergency_services: Whether emergency services responded (fire dept, police, etc.)
15. injuries: Whether there were any injuries
16. additional_info: Any other relevant notes or information

Return your analysis as a JSON object with this structure:
{
    "policy_number": "POL-123456",
    "policy_type": "HO-3",
    "insured_name": "John Doe",
    "insured_contact": {
        "phone": "555-1234",
        "email": "john@example.com",
        "address": "123 Main St, City, ST 12345"
    },
    "loss_date": "2024-01-15",
    "loss_time": "14:30",
    "loss_location": "123 Main St, City, ST 12345",
    "loss_description": "Pipe burst in basement causing water damage",
    "damage_description": "Water damage to basement floor, walls, and personal property",
    "cause_of_loss": "water damage",
    "estimated_loss_amount": 15000.00,
    "witnesses": [
        {
            "name": "Jane Smith",
            "contact": "555-5678"
        }
    ],
    "police_report": {
        "report_number": "2024-12345",
        "department": "City Police Department"
    },
    "emergency_services": true,
    "injuries": false,
    "additional_info": "Homeowner was present when pipe burst"
}

Important:
- Extract all amounts as numbers (not strings with currency symbols)
- If a field is not found, use null for strings/objects or 0.0 for numbers
- For dates, use YYYY-MM-DD format when possible
- For cause_of_loss, use standard insurance perils terminology
- If the document is not an FNOL form or cannot be parsed, return a minimal structure with available information

Return ONLY the JSON object, no additional text."""
        
        return prompt
    
    def _build_messages(
        self,
        document_base64: str,
        document_format: str,
        prompt: str
    ) -> List[Dict[str, Any]]:
        """
        Build messages for Nova Pro API call.
        
        Args:
            document_base64: Base64-encoded document
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
                                "name": "fnol",
                                "source": {
                                    "bytes": document_base64
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
                                    "bytes": document_base64
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
    
    def _parse_fnol_response(self, response_text: str) -> Dict[str, Any]:
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
    
    def _structure_fnol_result(
        self,
        fnol_data: Dict[str, Any],
        document_name: str
    ) -> Dict[str, Any]:
        """
        Structure and validate the FNOL result.
        
        Args:
            fnol_data: Raw FNOL data from Nova Pro
            document_name: Name of the parsed document
            
        Returns:
            Structured result dict
        """
        # Extract and validate core fields
        result = {
            'policy_number': fnol_data.get('policy_number') or 'Unknown',
            'policy_type': fnol_data.get('policy_type') or 'Unknown',
            'insured_name': fnol_data.get('insured_name') or 'Unknown',
            'insured_contact': fnol_data.get('insured_contact') or {},
            'loss_date': fnol_data.get('loss_date') or '',
            'loss_time': fnol_data.get('loss_time'),
            'loss_location': fnol_data.get('loss_location') or '',
            'loss_description': fnol_data.get('loss_description') or '',
            'damage_description': fnol_data.get('damage_description') or '',
            'cause_of_loss': fnol_data.get('cause_of_loss') or 'unknown',
            'document_name': document_name
        }
        
        # Parse estimated loss amount
        try:
            result['estimated_loss_amount'] = float(fnol_data.get('estimated_loss_amount', 0.0))
        except (ValueError, TypeError):
            result['estimated_loss_amount'] = 0.0
        
        # Add optional fields if present
        if 'witnesses' in fnol_data:
            result['witnesses'] = fnol_data['witnesses']
        
        if 'police_report' in fnol_data:
            result['police_report'] = fnol_data['police_report']
        
        if 'emergency_services' in fnol_data:
            result['emergency_services'] = fnol_data['emergency_services']
        
        if 'injuries' in fnol_data:
            result['injuries'] = fnol_data['injuries']
        
        if 'additional_info' in fnol_data:
            result['additional_info'] = fnol_data['additional_info']
        
        return result
    
    def _empty_fnol_result(self) -> Dict[str, Any]:
        """
        Return an empty FNOL result structure.
        
        Returns:
            Empty result dict
        """
        return {
            'policy_number': 'Unknown',
            'policy_type': 'Unknown',
            'insured_name': 'Unknown',
            'insured_contact': {},
            'loss_date': '',
            'loss_time': None,
            'loss_location': '',
            'loss_description': '',
            'damage_description': '',
            'cause_of_loss': 'unknown',
            'estimated_loss_amount': 0.0,
            'document_name': 'unknown'
        }
    
    @kernel_function(
        name="extract_loss_date",
        description=(
            "Extract just the loss date from an FNOL form. "
            "Returns ISO format date string or None if not available."
        )
    )
    async def extract_loss_date(
        self,
        document_bytes: bytes,
        document_format: Optional[str] = None
    ) -> Optional[str]:
        """
        Extract only the loss date from FNOL form.
        
        Args:
            document_bytes: Raw document bytes
            document_format: Optional format hint
            
        Returns:
            ISO format date string or None
        """
        try:
            fnol_data = await self.parse_fnol_form(
                document_bytes=document_bytes,
                document_format=document_format
            )
            return fnol_data.get('loss_date')
        except Exception as e:
            logger.warning(f"Failed to extract loss date: {str(e)}")
            return None
    
    @kernel_function(
        name="extract_policy_number",
        description=(
            "Extract just the policy number from an FNOL form. "
            "Returns policy number string or 'Unknown' if not available."
        )
    )
    async def extract_policy_number(
        self,
        document_bytes: bytes,
        document_format: Optional[str] = None
    ) -> str:
        """
        Extract only the policy number from FNOL form.
        
        Args:
            document_bytes: Raw document bytes
            document_format: Optional format hint
            
        Returns:
            Policy number string
        """
        try:
            fnol_data = await self.parse_fnol_form(
                document_bytes=document_bytes,
                document_format=document_format
            )
            return fnol_data.get('policy_number', 'Unknown')
        except Exception as e:
            logger.warning(f"Failed to extract policy number: {str(e)}")
            return 'Unknown'
