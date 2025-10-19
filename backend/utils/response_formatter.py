"""Response formatting utilities for JSON handling and extraction."""

import json
import logging
import re
from typing import Dict, Any, Optional, Union

logger = logging.getLogger(__name__)


class ResponseFormatter:
    """
    Utility class for formatting and extracting JSON responses.
    
    Provides methods for:
    - Wrapping JSON data with delimiters for reliable extraction
    - Extracting JSON from various response formats
    - Handling malformed responses gracefully
    """
    
    # Delimiters for wrapping JSON responses
    JSON_START_DELIMITER = "<<<JSON_START>>>"
    JSON_END_DELIMITER = "<<<JSON_END>>>"
    
    @staticmethod
    def format_json_response(data: Union[Dict[str, Any], str]) -> str:
        """
        Format JSON data with delimiters for reliable extraction.
        
        Args:
            data: Dictionary to format as JSON, or JSON string
            
        Returns:
            Formatted string with JSON wrapped in delimiters
            
        Raises:
            ValueError: If data cannot be serialized to JSON
        """
        try:
            if isinstance(data, str):
                # Validate that it's valid JSON
                json.loads(data)
                json_str = data
            else:
                json_str = json.dumps(data, indent=2, ensure_ascii=False)
            
            formatted = (
                f"{ResponseFormatter.JSON_START_DELIMITER}\n"
                f"{json_str}\n"
                f"{ResponseFormatter.JSON_END_DELIMITER}"
            )
            
            logger.debug(f"Formatted JSON response with delimiters")
            return formatted
            
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to format JSON response: {str(e)}")
            raise ValueError(f"Cannot format data as JSON: {str(e)}") from e
    
    @staticmethod
    def extract_json_from_response(response_text: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from various response formats.
        
        Tries multiple extraction methods in order:
        1. Delimited JSON (between JSON_START_DELIMITER and JSON_END_DELIMITER)
        2. Markdown code blocks (```json ... ```)
        3. Raw JSON (entire response)
        4. JSON embedded in text (find first complete JSON object)
        
        Args:
            response_text: Raw response text that may contain JSON
            
        Returns:
            Parsed JSON dictionary, or None if no valid JSON found
        """
        if not response_text or not response_text.strip():
            logger.warning("Empty response text provided")
            return None
        
        text = response_text.strip()
        
        # Method 1: Try delimited JSON first
        json_data = ResponseFormatter._extract_delimited_json(text)
        if json_data is not None:
            logger.debug("Successfully extracted delimited JSON")
            return json_data
        
        # Method 2: Try markdown code blocks
        json_data = ResponseFormatter._extract_markdown_json(text)
        if json_data is not None:
            logger.debug("Successfully extracted JSON from markdown code block")
            return json_data
        
        # Method 3: Try raw JSON (entire response)
        json_data = ResponseFormatter._extract_raw_json(text)
        if json_data is not None:
            logger.debug("Successfully extracted raw JSON")
            return json_data
        
        # Method 4: Try to find JSON embedded in text
        json_data = ResponseFormatter._extract_embedded_json(text)
        if json_data is not None:
            logger.debug("Successfully extracted embedded JSON")
            return json_data
        
        logger.warning(f"Failed to extract JSON from response: {text[:200]}...")
        return None
    
    @staticmethod
    def _extract_delimited_json(text: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON between delimiters.
        
        Args:
            text: Response text
            
        Returns:
            Parsed JSON dict or None
        """
        try:
            start_idx = text.find(ResponseFormatter.JSON_START_DELIMITER)
            end_idx = text.find(ResponseFormatter.JSON_END_DELIMITER)
            
            if start_idx == -1 or end_idx == -1:
                return None
            
            start_idx += len(ResponseFormatter.JSON_START_DELIMITER)
            json_text = text[start_idx:end_idx].strip()
            
            return json.loads(json_text)
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.debug(f"Failed to parse delimited JSON: {str(e)}")
            return None
    
    @staticmethod
    def _extract_markdown_json(text: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from markdown code blocks.
        
        Args:
            text: Response text
            
        Returns:
            Parsed JSON dict or None
        """
        try:
            # Look for ```json ... ``` or ``` ... ```
            patterns = [
                r'```json\s*\n(.*?)\n```',
                r'```\s*\n(.*?)\n```'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.DOTALL)
                if match:
                    json_text = match.group(1).strip()
                    try:
                        return json.loads(json_text)
                    except json.JSONDecodeError:
                        continue
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to parse markdown JSON: {str(e)}")
            return None
    
    @staticmethod
    def _extract_raw_json(text: str) -> Optional[Dict[str, Any]]:
        """
        Try to parse entire response as JSON.
        
        Args:
            text: Response text
            
        Returns:
            Parsed JSON dict or None
        """
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
    
    @staticmethod
    def _extract_embedded_json(text: str) -> Optional[Dict[str, Any]]:
        """
        Find and extract JSON object embedded in text using brace counting.
        
        Args:
            text: Response text
            
        Returns:
            Parsed JSON dict or None
        """
        try:
            # Find the first opening brace
            start_idx = text.find('{')
            if start_idx == -1:
                return None
            
            # Count braces to find the matching closing brace
            brace_count = 0
            in_string = False
            escape_next = False
            
            for i, char in enumerate(text[start_idx:], start_idx):
                if escape_next:
                    escape_next = False
                    continue
                
                if char == '\\':
                    escape_next = True
                    continue
                
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                
                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        
                        if brace_count == 0:
                            # Found complete JSON object
                            json_text = text[start_idx:i + 1]
                            try:
                                return json.loads(json_text)
                            except json.JSONDecodeError:
                                # Try to find next JSON object
                                remaining_text = text[i + 1:]
                                return ResponseFormatter._extract_embedded_json(remaining_text)
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to parse embedded JSON: {str(e)}")
            return None
    
    @staticmethod
    def validate_json_structure(
        data: Dict[str, Any],
        required_fields: Optional[list] = None
    ) -> bool:
        """
        Validate that JSON data has required structure.
        
        Args:
            data: JSON data to validate
            required_fields: List of required field names
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(data, dict):
            logger.warning("JSON data is not a dictionary")
            return False
        
        if required_fields:
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                logger.warning(f"Missing required fields: {missing_fields}")
                return False
        
        return True
    
    @staticmethod
    def sanitize_json_response(response_text: str) -> str:
        """
        Clean up response text before JSON extraction.
        
        Args:
            response_text: Raw response text
            
        Returns:
            Cleaned response text
        """
        if not response_text:
            return ""
        
        # Remove common prefixes/suffixes that interfere with JSON parsing
        text = response_text.strip()
        
        # Remove "Here's the JSON:" type prefixes
        prefixes_to_remove = [
            "here's the json:",
            "here is the json:",
            "the json response is:",
            "json response:",
            "response:",
            "result:"
        ]
        
        text_lower = text.lower()
        for prefix in prefixes_to_remove:
            if text_lower.startswith(prefix):
                text = text[len(prefix):].strip()
                break
        
        # Remove trailing explanatory text after JSON
        # Look for patterns like "This JSON contains..." after a closing brace
        lines = text.split('\n')
        json_end_found = False
        cleaned_lines = []
        
        for line in lines:
            if not json_end_found:
                cleaned_lines.append(line)
                if '}' in line and line.strip().endswith('}'):
                    # Check if this might be the end of JSON
                    try:
                        test_json = '\n'.join(cleaned_lines)
                        json.loads(test_json)
                        json_end_found = True
                    except json.JSONDecodeError:
                        continue
            else:
                # After JSON ends, only include lines that look like they're part of JSON
                if line.strip() and not line.strip().startswith(('This', 'The', 'Note:')):
                    cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)