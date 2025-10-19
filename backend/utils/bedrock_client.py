"""AWS Bedrock client wrapper with retry logic and error handling."""

import json
import time
import logging
import os
import base64
from typing import Dict, List, Optional, Any
import numpy as np
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv

from .errors import BedrockAPIError, ErrorType, ErrorContext

# Ensure environment variables are loaded
load_dotenv()

logger = logging.getLogger(__name__)

_API_KEY_SECRET_CACHE: Dict[str, str] = {}


class BedrockClient:
    """
    Wrapper for AWS Bedrock Runtime client with retry logic.
    
    Provides methods for:
    - Invoking Nova Pro via Converse API
    - Generating embeddings with Titan
    - Automatic retry with exponential backoff
    """
    
    def __init__(
        self,
        region: str = "us-east-1",
        model_id: str = "amazon.nova-pro-v1:0",
        embedding_model_id: str = "amazon.titan-embed-text-v2:0",
        timeout: int = 3600,
        max_retries: int = 3
    ):
        """
        Initialize Bedrock client.
        
        Args:
            region: AWS region for Bedrock service
            model_id: Model ID for Nova Pro
            embedding_model_id: Model ID for Titan embeddings
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.region = region
        self.model_id = model_id
        self.embedding_model_id = embedding_model_id
        self.max_retries = max_retries
        
        # Determine authentication mode (IAM vs API key / secret manager)
        self._bearer_token = self._resolve_bearer_token(region)
        self._using_bearer_token = bool(self._bearer_token)
        if self._using_bearer_token and not os.getenv("AWS_BEARER_TOKEN_BEDROCK"):
            os.environ["AWS_BEARER_TOKEN_BEDROCK"] = self._bearer_token
        
        if self._using_bearer_token:
            logger.info("BedrockClient configured to use Amazon Bedrock API key authentication")
        else:
            logger.info("BedrockClient configured to use AWS IAM credentials (SigV4)")
        
        # Configure boto3 client with timeouts and retries
        config_kwargs: Dict[str, Any] = {
            "region_name": region,
            "connect_timeout": timeout,
            "read_timeout": timeout,
            "retries": {"max_attempts": 0},  # We handle retries manually
        }
        
        # When an API key is present, instruct botocore to use bearer-token auth.
        # Recent versions of botocore automatically honour AWS_BEARER_TOKEN_BEDROCK,
        # but we set signature_version explicitly for clarity/future compatibility.
        if self._using_bearer_token:
            config_kwargs["signature_version"] = "bearer"
        
        config = Config(**config_kwargs)
        
        self.runtime = boto3.client("bedrock-runtime", config=config)
        # Optional: Agents for Amazon Bedrock runtime (only used if configured)
        try:
            self.agents_runtime = boto3.client("bedrock-agent-runtime", config=config)
        except Exception:
            self.agents_runtime = None
        
        logger.info(
            f"Initialized BedrockClient: region={region}, "
            f"model={model_id}, max_retries={max_retries}"
        )

    def _resolve_bearer_token(self, region: str) -> Optional[str]:
        """
        Resolve the bearer token for Bedrock authentication.

        Order of precedence:
        1. AWS_BEARER_TOKEN_BEDROCK / BEDROCK_API_KEY environment variables.
        2. Secret fetched from AWS Secrets Manager when BEDROCK_API_KEY_SECRET_NAME (or ARN) is provided.

        Args:
            region: Default region to use for Secrets Manager fallback.

        Returns:
            Bearer token string if available, otherwise None.
        """
        direct_token = os.getenv("AWS_BEARER_TOKEN_BEDROCK") or os.getenv("BEDROCK_API_KEY")
        if direct_token:
            return direct_token.strip()

        secret_name = os.getenv("BEDROCK_API_KEY_SECRET_NAME") or os.getenv("BEDROCK_API_KEY_SECRET_ARN")
        if not secret_name:
            return None

        if secret_name in _API_KEY_SECRET_CACHE:
            return _API_KEY_SECRET_CACHE[secret_name]

        secrets_region = os.getenv("AWS_SECRETS_MANAGER_REGION", region)

        try:
            profile_name = (
                os.getenv("BEDROCK_API_KEY_SECRET_PROFILE")
                or os.getenv("AWS_SECRETS_MANAGER_PROFILE")
                or None
            )

            session = (
                boto3.session.Session(profile_name=profile_name)
                if profile_name
                else boto3.session.Session()
            )

            client = session.client("secretsmanager", region_name=secrets_region)
            response = client.get_secret_value(SecretId=secret_name)

            secret_value = self._extract_secret_value(response)
            if secret_value:
                _API_KEY_SECRET_CACHE[secret_name] = secret_value
                logger.info("Loaded Bedrock API key from AWS Secrets Manager secret '%s'", secret_name)
                return secret_value

            logger.warning(
                "Secrets Manager secret '%s' did not contain a usable Bedrock API key",
                secret_name,
            )
        except NoCredentialsError:
            logger.error(
                "Unable to locate AWS credentials while retrieving Bedrock API key secret '%s'. "
                "Configure credentials (e.g., via AWS_PROFILE, aws configure, or role assumption) "
                "to allow access to AWS Secrets Manager.",
                secret_name,
            )
        except ClientError as exc:
            logger.error(
                "Failed to retrieve Bedrock API key from secret '%s': %s",
                secret_name,
                exc,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "Unexpected error retrieving Bedrock API key from secret '%s': %s",
                secret_name,
                exc,
            )

        return None

    @staticmethod
    def _extract_secret_value(response: Dict[str, Any]) -> Optional[str]:
        """
        Extract the API key string from a Secrets Manager response.
        Supports plain string secrets, JSON objects, and binary secrets.
        """
        secret_string = response.get("SecretString")
        if secret_string:
            # First, try parsing as JSON in case the secret stores multiple keys.
            try:
                data = json.loads(secret_string)
                if isinstance(data, dict):
                    for candidate_key in (
                        "bedrock_api_key",
                        "api_key",
                        "AWS_BEARER_TOKEN_BEDROCK",
                        "bearer_token",
                    ):
                        value = data.get(candidate_key)
                        if isinstance(value, str) and value.strip():
                            return value.strip()
            except json.JSONDecodeError:
                pass  # Not JSON, treat as raw string

            if secret_string.strip():
                return secret_string.strip()

        secret_binary = response.get("SecretBinary")
        if secret_binary:
            try:
                decoded = base64.b64decode(secret_binary).decode("utf-8").strip()
                if decoded:
                    return decoded
            except Exception:  # pragma: no cover - defensive
                logger.warning("Failed to decode binary Secrets Manager payload for Bedrock API key")

        return None
    
    async def invoke_nova_pro(
        self,
        messages: List[Dict[str, Any]],
        tool_config: Optional[Dict[str, Any]] = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        system_prompts: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Invoke Nova Pro model via Converse API with retry logic.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            tool_config: Optional tool configuration for function calling
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens: Maximum tokens to generate
            system_prompts: Optional system prompts
            
        Returns:
            Dict containing response with 'content', 'stop_reason', etc.
            
        Raises:
            ClientError: If all retry attempts fail
        """
        params = {
            "modelId": self.model_id,
            "messages": messages,
            "inferenceConfig": {
                "temperature": temperature,
                "maxTokens": max_tokens
            }
        }
        
        if tool_config:
            params["toolConfig"] = tool_config
        
        if system_prompts:
            params["system"] = system_prompts
        
        # Retry with exponential backoff
        for attempt in range(self.max_retries):
            try:
                logger.debug(
                    f"Invoking Nova Pro (attempt {attempt + 1}/{self.max_retries})"
                )
                
                response = self.runtime.converse(**params)
                
                logger.info(
                    f"Nova Pro invocation successful: "
                    f"stop_reason={response.get('stopReason')}, "
                    f"usage={response.get('usage')}"
                )
                
                return self._parse_converse_response(response)
                
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                error_message = e.response.get("Error", {}).get("Message", str(e))
                
                logger.warning(
                    f"Bedrock API error (attempt {attempt + 1}/{self.max_retries}): "
                    f"code={error_code}, message={error_message}"
                )
                
                # Check if error is retryable
                if self._is_retryable_error(error_code):
                    if attempt < self.max_retries - 1:
                        # Exponential backoff: 1s, 2s, 4s, ...
                        wait_time = 2 ** attempt
                        logger.info(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue
                
                # Non-retryable error or max retries reached
                logger.error(
                    f"Bedrock API call failed after {attempt + 1} attempts: "
                    f"{error_code} - {error_message}"
                )
                
                # Wrap in BedrockAPIError with context
                raise BedrockAPIError.from_client_error(
                    error=e,
                    operation="invoke_nova_pro",
                    recoverable=False,
                    fallback_action=None
                )
            
            except Exception as e:
                logger.error(f"Unexpected error invoking Nova Pro: {str(e)}")
                
                # Wrap unexpected errors in BedrockAPIError
                context = ErrorContext(
                    error_type=ErrorType.BEDROCK_SERVICE_ERROR,
                    message=f"Unexpected error invoking Nova Pro: {str(e)}",
                    recoverable=False,
                    fallback_action=None,
                    original_exception=e
                )
                raise BedrockAPIError(context)
        
        # Should not reach here, but just in case
        context = ErrorContext(
            error_type=ErrorType.BEDROCK_SERVICE_ERROR,
            message=f"Failed to invoke Nova Pro after {self.max_retries} attempts",
            recoverable=False,
            fallback_action=None
        )
        raise BedrockAPIError(context)
    
    async def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding vector using Titan embedding model.
        
        Args:
            text: Input text to embed
            
        Returns:
            NumPy array of embedding vector
            
        Raises:
            ClientError: If all retry attempts fail
        """
        body = json.dumps({"inputText": text})
        
        # Retry with exponential backoff
        for attempt in range(self.max_retries):
            try:
                logger.debug(
                    f"Generating embedding (attempt {attempt + 1}/{self.max_retries})"
                )
                
                response = self.runtime.invoke_model(
                    modelId=self.embedding_model_id,
                    body=body,
                    contentType="application/json",
                    accept="application/json"
                )
                
                result = json.loads(response["body"].read())
                embedding = np.array(result["embedding"], dtype=np.float32)
                
                logger.debug(f"Generated embedding: dimension={len(embedding)}")
                
                return embedding
                
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                error_message = e.response.get("Error", {}).get("Message", str(e))
                
                logger.warning(
                    f"Bedrock embedding error (attempt {attempt + 1}/{self.max_retries}): "
                    f"code={error_code}, message={error_message}"
                )
                
                # Check if error is retryable
                if self._is_retryable_error(error_code):
                    if attempt < self.max_retries - 1:
                        # Exponential backoff: 1s, 2s, 4s, ...
                        wait_time = 2 ** attempt
                        logger.info(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue
                
                # Non-retryable error or max retries reached
                logger.error(
                    f"Embedding generation failed after {attempt + 1} attempts: "
                    f"{error_code} - {error_message}"
                )
                
                # Wrap in BedrockAPIError with context
                raise BedrockAPIError.from_client_error(
                    error=e,
                    operation="generate_embedding",
                    recoverable=False,
                    fallback_action=None
                )
            
            except Exception as e:
                logger.error(f"Unexpected error generating embedding: {str(e)}")
                
                # Wrap unexpected errors in BedrockAPIError
                context = ErrorContext(
                    error_type=ErrorType.EMBEDDING_GENERATION_FAILED,
                    message=f"Unexpected error generating embedding: {str(e)}",
                    recoverable=False,
                    fallback_action=None,
                    original_exception=e
                )
                raise BedrockAPIError(context)
        
        # Should not reach here, but just in case
        context = ErrorContext(
            error_type=ErrorType.EMBEDDING_GENERATION_FAILED,
            message=f"Failed to generate embedding after {self.max_retries} attempts",
            recoverable=False,
            fallback_action=None
        )
        raise BedrockAPIError(context)

    async def invoke_managed_agent(
        self,
        agent_id: str,
        agent_alias_id: str,
        input_text: str,
        session_id: Optional[str] = None,
    ) -> str:
        """
        Invoke an Agent for Amazon Bedrock and return aggregated plain text.
        Requires that the agent is pre-configured in your AWS account.
        """
        if not self.agents_runtime:
            raise BedrockAPIError(
                ErrorContext(
                    error_type=ErrorType.BEDROCK_SERVICE_ERROR,
                    message="bedrock-agent-runtime client is not initialized",
                    recoverable=False,
                )
            )

        try:
            response = self.agents_runtime.invoke_agent(
                agentId=agent_id,
                agentAliasId=agent_alias_id,
                sessionId=session_id or "default",
                inputText=input_text,
            )

            # Read streaming completion
            chunks: List[str] = []
            for event in response.get("completion", []):
                # Event has keys like {'chunk': {'bytes': b'...'}}
                try:
                    if "chunk" in event and "bytes" in event["chunk"]:
                        chunks.append(event["chunk"]["bytes"].decode("utf-8"))
                except Exception:
                    continue
            return "".join(chunks)

        except ClientError as e:
            raise BedrockAPIError.from_client_error(
                error=e,
                operation="invoke_managed_agent",
                recoverable=False,
                fallback_action=None,
            )
    
    def _parse_converse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Converse API response into a simplified format.
        
        Args:
            response: Raw response from Converse API
            
        Returns:
            Parsed response dict with 'content', 'stop_reason', 'usage', etc.
        """
        output = response.get("output", {})
        message = output.get("message", {})
        
        parsed = {
            "content": message.get("content", []),
            "role": message.get("role", "assistant"),
            "stop_reason": response.get("stopReason", "unknown"),
            "usage": response.get("usage", {}),
            "metrics": response.get("metrics", {})
        }
        
        # Extract text content if available
        if parsed["content"]:
            text_parts = []
            for content_block in parsed["content"]:
                if "text" in content_block:
                    text_parts.append(content_block["text"])
            parsed["text"] = "\n".join(text_parts) if text_parts else ""
        else:
            parsed["text"] = ""
        
        return parsed
    
    def _is_retryable_error(self, error_code: str) -> bool:
        """
        Determine if an error code is retryable.
        
        Args:
            error_code: AWS error code
            
        Returns:
            True if error is retryable, False otherwise
        """
        retryable_errors = {
            "ThrottlingException",
            "TooManyRequestsException",
            "ServiceUnavailableException",
            "InternalServerException",
            "RequestTimeout",
            "RequestTimeoutException"
        }
        
        return error_code in retryable_errors
