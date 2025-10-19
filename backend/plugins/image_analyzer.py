"""Image analysis plugin for Semantic Kernel using AWS Bedrock Nova Pro vision."""

import json
import logging
import time
from typing import List, Dict, Any, Optional

from semantic_kernel.functions import kernel_function

from ..utils.bedrock_client import BedrockClient
from ..utils.errors import DocumentProcessingError, ErrorType, ErrorContext

logger = logging.getLogger(__name__)


class ImageAnalyzerPlugin:
    """
    Semantic Kernel plugin for analyzing damage images using Nova Pro vision.
    
    Provides multi-label damage detection with bounding boxes, severity assessment,
    and novelty detection (new vs. old damage).
    """
    
    def __init__(self, bedrock_client: BedrockClient):
        """
        Initialize image analyzer plugin.
        
        Args:
            bedrock_client: Configured BedrockClient instance
        """
        self.bedrock = bedrock_client
        logger.info("Initialized ImageAnalyzerPlugin")
    
    @kernel_function(
        name="analyze_damage_image",
        description=(
            "Analyze damage photos for multi-label detection with bounding boxes. "
            "Identifies damage types, locations, severity, and whether damage appears new or old. "
            "Returns structured observations with confidence scores."
        )
    )
    async def analyze_image(
        self,
        image_bytes: bytes,
        image_name: str = "image",
        allowed_labels: Optional[List[str]] = None,
        include_bboxes: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze a damage image using Nova Pro vision capabilities.
        
        Args:
            image_bytes: Raw image bytes (JPEG, PNG, etc.)
            image_name: Name/identifier for the image
            allowed_labels: Optional list of damage types to detect
            include_bboxes: Whether to request bounding box coordinates
            
        Returns:
            Dictionary containing:
                - observations: List of Observation dicts with damage details
                - global_assessment: Overall image assessment
                - chronology: Temporal information about damage
            
        Raises:
            DocumentProcessingError: If image analysis fails
        """
        try:
            start_time = time.time()
            logger.info(f"Starting image analysis: {image_name}")
            logger.debug(f"Image size: {len(image_bytes)} bytes, include_bboxes: {include_bboxes}")
            
            # Default damage labels if not provided
            if allowed_labels is None:
                allowed_labels = [
                    "water_damage",
                    "fire_damage",
                    "mold",
                    "structural_damage",
                    "roof_damage",
                    "ceiling_damage",
                    "wall_damage",
                    "floor_damage",
                    "smoke_damage",
                    "impact_damage",
                    "broken_glass",
                    "dent",
                    "scratch",
                    "collision_damage"
                ]
            
            logger.debug(f"Using {len(allowed_labels)} damage labels for analysis")
            
            # Determine image format from bytes
            image_format = self._detect_image_format(image_bytes)
            logger.debug(f"Detected image format: {image_format}")
            
            # Build prompt for damage analysis
            prompt = self._build_analysis_prompt(allowed_labels, include_bboxes)
            logger.debug(f"Analysis prompt length: {len(prompt)} characters")
            
            # Construct message with image content block
            # Note: boto3's converse API expects raw bytes, not base64-encoded strings
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "image": {
                                "format": image_format,
                                "source": {
                                    "bytes": image_bytes  # Pass raw bytes, boto3 handles encoding
                                }
                            }
                        },
                        {
                            "text": prompt
                        }
                    ]
                }
            ]
            
            logger.debug(f"Calling Nova Pro API for image analysis: {image_name}")
            
            # Call Nova Pro with vision
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
                logger.warning(f"Empty response from Nova Pro for image: {image_name}")
                return self._empty_analysis_result()
            
            logger.debug(f"Nova Pro response length: {len(response_text)} characters")
            logger.debug(f"Response preview: {response_text[:200]}...")
            
            # Extract JSON from response
            parse_start = time.time()
            analysis_result = self._parse_analysis_response(response_text)
            parse_time = time.time() - parse_start
            logger.debug(f"JSON parsing completed in {parse_time:.3f}s")
            
            # Validate and structure the result
            structure_start = time.time()
            structured_result = self._structure_analysis_result(
                analysis_result,
                image_name
            )
            structure_time = time.time() - structure_start
            logger.debug(f"Result structuring completed in {structure_time:.3f}s")
            
            total_time = time.time() - start_time
            logger.info(
                f"Image analysis complete for {image_name}: "
                f"{len(structured_result['observations'])} observations detected "
                f"in {total_time:.3f}s (API: {api_time:.3f}s)"
            )
            
            # Debug log the structured result
            logger.debug(f"Analysis result for {image_name}:")
            logger.debug(f"  - Image name in result: {structured_result.get('image_name')}")
            logger.debug(f"  - Observations count: {len(structured_result.get('observations', []))}")
            for i, obs in enumerate(structured_result.get('observations', [])[:3]):  # Log first 3
                confidence = obs.get('confidence', 0)
                try:
                    confidence = float(confidence) if confidence is not None else 0.0
                except (ValueError, TypeError):
                    confidence = 0.0
                logger.debug(f"    {i+1}. {obs.get('label')} ({confidence:.2f}) at {obs.get('location_text', 'unknown')}")
            
            return structured_result
            
        except Exception as e:
            logger.error(f"Failed to analyze image {image_name}: {str(e)}")
            
            # Wrap in DocumentProcessingError
            context = ErrorContext(
                error_type=ErrorType.IMAGE_ANALYSIS_FAILED,
                message=f"Failed to analyze image {image_name}: {str(e)}",
                recoverable=True,
                fallback_action="Continue with available evidence",
                original_exception=e
            )
            raise DocumentProcessingError(context)
    
    def _detect_image_format(self, image_bytes: bytes) -> str:
        """
        Detect image format from bytes.
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            Format string ("jpeg", "png", "gif", "webp")
        """
        # Check magic bytes
        if image_bytes.startswith(b'\xff\xd8\xff'):
            return "jpeg"
        elif image_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
            return "png"
        elif image_bytes.startswith(b'GIF87a') or image_bytes.startswith(b'GIF89a'):
            return "gif"
        elif image_bytes.startswith(b'RIFF') and b'WEBP' in image_bytes[:12]:
            return "webp"
        else:
            # Default to JPEG
            logger.warning("Unknown image format, defaulting to JPEG")
            return "jpeg"
    
    def _build_analysis_prompt(
        self,
        allowed_labels: List[str],
        include_bboxes: bool
    ) -> str:
        """
        Build the analysis prompt for Nova Pro.
        
        Args:
            allowed_labels: List of damage types to detect
            include_bboxes: Whether to request bounding boxes
            
        Returns:
            Formatted prompt string
        """
        labels_str = ", ".join(allowed_labels)
        
        bbox_instruction = ""
        if include_bboxes:
            bbox_instruction = (
                "For each observation, provide a bounding box in relative coordinates "
                "(x, y, w, h where all values are between 0.0 and 1.0, with origin at top-left). "
            )
        
        prompt = f"""Analyze this image for damage and provide a structured assessment.

Identify any of the following damage types present: {labels_str}

For each damage observation, provide:
1. label: The damage type from the allowed list
2. confidence: Confidence score (0.0 to 1.0)
3. bbox: Bounding box coordinates {{x, y, w, h}} in relative coordinates (0.0 to 1.0)
4. location_text: Human-readable description of where the damage is located
5. novelty: Whether the damage appears "new", "old", or "unclear"
6. severity: Severity level - "minor", "moderate", or "severe"
7. evidence_notes: List of specific details about this observation

{bbox_instruction}

Also provide:
- global_assessment: Overall assessment of the image including general condition, primary concerns, and any patterns
- chronology: Temporal information such as estimated_age, consistency_indicators, and timeline_notes

Return your analysis as a JSON object with this structure:
{{
    "observations": [
        {{
            "label": "damage_type",
            "confidence": 0.95,
            "bbox": {{"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.4}},
            "location_text": "upper left corner of ceiling",
            "novelty": "new",
            "severity": "moderate",
            "evidence_notes": ["visible water staining", "paint bubbling"]
        }}
    ],
    "global_assessment": {{
        "overall_condition": "description",
        "primary_concerns": ["concern1", "concern2"],
        "patterns": "any patterns observed"
    }},
    "chronology": {{
        "estimated_age": "recent/weeks/months/years",
        "consistency_indicators": ["indicator1", "indicator2"],
        "timeline_notes": "notes about damage timeline"
    }}
}}

Return ONLY the JSON object, no additional text."""
        
        return prompt
    
    def _parse_analysis_response(self, response_text: str) -> Dict[str, Any]:
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
    
    def _structure_analysis_result(
        self,
        analysis_result: Dict[str, Any],
        image_name: str
    ) -> Dict[str, Any]:
        """
        Structure and validate the analysis result.
        
        Args:
            analysis_result: Raw analysis result from Nova Pro
            image_name: Name of the analyzed image
            
        Returns:
            Structured result dict
        """
        observations = []
        
        # Process observations
        for obs_data in analysis_result.get("observations", []):
            try:
                # Validate required fields
                observation = {
                    "label": obs_data.get("label", "unknown"),
                    "confidence": float(obs_data.get("confidence", 0.0)),
                    "bbox": obs_data.get("bbox", {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}),
                    "location_text": obs_data.get("location_text", ""),
                    "novelty": obs_data.get("novelty", "unclear"),
                    "severity": obs_data.get("severity", "moderate"),
                    "evidence_notes": obs_data.get("evidence_notes", [])
                }
                
                # Validate novelty and severity values
                if observation["novelty"] not in ["new", "old", "unclear"]:
                    observation["novelty"] = "unclear"
                
                if observation["severity"] not in ["minor", "moderate", "severe"]:
                    observation["severity"] = "moderate"
                
                observations.append(observation)
                
            except Exception as e:
                logger.warning(f"Failed to process observation: {str(e)}")
                continue
        
        # Structure the complete result
        result = {
            "image_name": image_name,
            "observations": observations,
            "global_assessment": analysis_result.get("global_assessment", {}),
            "chronology": analysis_result.get("chronology", {})
        }
        
        return result
    
    def _empty_analysis_result(self) -> Dict[str, Any]:
        """
        Return an empty analysis result structure.
        
        Returns:
            Empty result dict
        """
        return {
            "image_name": "unknown",
            "observations": [],
            "global_assessment": {
                "overall_condition": "Unable to analyze",
                "primary_concerns": [],
                "patterns": ""
            },
            "chronology": {
                "estimated_age": "unknown",
                "consistency_indicators": [],
                "timeline_notes": ""
            }
        }
    
    @kernel_function(
        name="batch_analyze_images",
        description="Analyze multiple damage images in sequence. Returns a list of analysis results."
    )
    async def batch_analyze(
        self,
        images: List[Dict[str, Any]],
        allowed_labels: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Analyze multiple images in sequence.
        
        Args:
            images: List of dicts with 'bytes' and 'name' keys
            allowed_labels: Optional list of damage types to detect
            
        Returns:
            List of analysis results, one per image
        """
        results = []
        
        for image_data in images:
            try:
                result = await self.analyze_image(
                    image_bytes=image_data["bytes"],
                    image_name=image_data.get("name", "unknown"),
                    allowed_labels=allowed_labels
                )
                results.append(result)
            except Exception as e:
                logger.error(
                    f"Failed to analyze image {image_data.get('name', 'unknown')}: {str(e)}"
                )
                # Add empty result for failed image
                results.append(self._empty_analysis_result())
        
        logger.info(f"Batch analysis complete: {len(results)} images processed")
        return results
    
    @kernel_function(
        name="extract_pdf_form_fields",
        description=(
            "Extract form fields from PDF documents using Nova Pro vision. "
            "Returns structured form data with field names and values."
        )
    )
    async def extract_pdf_form_fields(
        self,
        pdf_bytes: bytes,
        pdf_name: str = "document.pdf"
    ) -> Dict[str, Any]:
        """
        Extract form fields from a PDF using Nova Pro vision.
        
        Args:
            pdf_bytes: Raw PDF bytes
            pdf_name: Name/identifier for the PDF
            
        Returns:
            Dictionary containing:
                - fields: Dict of field names to values
                - confidence: Overall confidence score (0.0 to 1.0)
            
        Raises:
            DocumentProcessingError: If PDF form extraction fails
        """
        try:
            logger.info(f"Extracting form fields from PDF: {pdf_name}")
            
            # Build prompt for form extraction
            prompt = """Extract all form fields from this PDF document.

For each form field, identify:
- The field label or name
- The field value (if filled in)
- The field type (text, checkbox, date, etc.)

Return the extracted data as a JSON object with this structure:
{
    "fields": {
        "field_name_1": "field_value_1",
        "field_name_2": "field_value_2",
        ...
    },
    "confidence": 0.90
}

Include all visible form fields, even if they are empty (use null for empty fields).
The confidence score should reflect your overall confidence in the extraction accuracy.

Return ONLY the JSON object, no additional text."""
            
            # Construct message with PDF content block
            # Note: boto3's converse API expects raw bytes, not base64-encoded strings
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "document": {
                                "format": "pdf",
                                "name": pdf_name,
                                "source": {
                                    "bytes": pdf_bytes  # Pass raw bytes, boto3 handles encoding
                                }
                            }
                        },
                        {
                            "text": prompt
                        }
                    ]
                }
            ]
            
            # Call Nova Pro with vision
            response = await self.bedrock.invoke_nova_pro(
                messages=messages,
                temperature=0.0,
                max_tokens=4096
            )
            
            # Parse response
            response_text = response.get("text", "")
            
            if not response_text:
                logger.warning(f"Empty response from Nova Pro for PDF: {pdf_name}")
                return {"fields": {}, "confidence": 0.0}
            
            # Extract and validate JSON
            result = self._parse_analysis_response(response_text)
            
            # Ensure required fields are present
            if "fields" not in result:
                result["fields"] = {}
            
            if "confidence" not in result:
                result["confidence"] = 0.8 if result["fields"] else 0.0
            
            # Safely format confidence for logging
            confidence = result.get('confidence', 0)
            try:
                confidence = float(confidence) if confidence is not None else 0.0
            except (ValueError, TypeError):
                confidence = 0.0
                
            logger.info(
                f"Form extraction complete for {pdf_name}: "
                f"{len(result['fields'])} fields extracted, "
                f"confidence={confidence:.2f}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to extract form fields from {pdf_name}: {str(e)}")
            
            # Return structured error information
            context = ErrorContext(
                error_type=ErrorType.DOCUMENT_PROCESSING_FAILED,
                message=f"Failed to extract form fields from {pdf_name}: {str(e)}",
                recoverable=True,
                fallback_action="Continue with available evidence",
                original_exception=e
            )
            
            return {
                "fields": {},
                "confidence": 0.0,
                "error": {
                    "type": "PDF_FORM_EXTRACTION_FAILED",
                    "message": str(e),
                    "recoverable": True
                }
            }
