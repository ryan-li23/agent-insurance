"""Error handling utilities for claims processing system."""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum


class ErrorType(Enum):
    """Enumeration of error types in the claims processing system."""
    
    # Bedrock API Errors
    BEDROCK_RATE_LIMIT = "BEDROCK_RATE_LIMIT"
    BEDROCK_TIMEOUT = "BEDROCK_TIMEOUT"
    BEDROCK_AUTH_ERROR = "BEDROCK_AUTH_ERROR"
    BEDROCK_MODEL_ERROR = "BEDROCK_MODEL_ERROR"
    BEDROCK_INVALID_REQUEST = "BEDROCK_INVALID_REQUEST"
    BEDROCK_SERVICE_ERROR = "BEDROCK_SERVICE_ERROR"
    
    # Document Processing Errors
    PDF_EXTRACTION_FAILED = "PDF_EXTRACTION_FAILED"
    IMAGE_ANALYSIS_FAILED = "IMAGE_ANALYSIS_FAILED"
    INVOICE_PARSING_FAILED = "INVOICE_PARSING_FAILED"
    EXIF_EXTRACTION_FAILED = "EXIF_EXTRACTION_FAILED"
    
    # Vector Store Errors
    FAISS_INDEX_NOT_FOUND = "FAISS_INDEX_NOT_FOUND"
    FAISS_INDEX_CORRUPTED = "FAISS_INDEX_CORRUPTED"
    FAISS_SEARCH_FAILED = "FAISS_SEARCH_FAILED"
    EMBEDDING_GENERATION_FAILED = "EMBEDDING_GENERATION_FAILED"
    
    # Agent Errors
    AGENT_PLUGIN_FAILED = "AGENT_PLUGIN_FAILED"
    AGENT_MAX_ROUNDS_EXCEEDED = "AGENT_MAX_ROUNDS_EXCEEDED"
    AGENT_CONSENSUS_FAILED = "AGENT_CONSENSUS_FAILED"
    
    # Configuration Errors
    CONFIG_MISSING = "CONFIG_MISSING"
    CONFIG_INVALID = "CONFIG_INVALID"
    
    # System Errors
    INITIALIZATION_FAILED = "INITIALIZATION_FAILED"
    
    # General Errors
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


@dataclass
class ErrorContext:
    """
    Context information for errors in the claims processing system.
    
    Attributes:
        error_type: Type of error from ErrorType enum
        message: Human-readable error message
        recoverable: Whether the error can be recovered from
        fallback_action: Optional description of fallback action taken
        details: Optional additional error details
        original_exception: Optional original exception that caused this error
    """
    
    error_type: ErrorType
    message: str
    recoverable: bool
    fallback_action: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    original_exception: Optional[Exception] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert error context to dictionary for logging/serialization.
        
        Returns:
            Dictionary representation of error context
        """
        return {
            "error_type": self.error_type.value,
            "message": self.message,
            "recoverable": self.recoverable,
            "fallback_action": self.fallback_action,
            "details": self.details or {},
            "original_exception": str(self.original_exception) if self.original_exception else None
        }


class ClaimsProcessingError(Exception):
    """
    Base exception for all claims processing errors.
    
    This exception wraps errors with additional context to enable
    graceful degradation and better error reporting.
    
    Attributes:
        context: ErrorContext with detailed error information
    """
    
    def __init__(self, context: ErrorContext):
        """
        Initialize claims processing error.
        
        Args:
            context: ErrorContext with error details
        """
        self.context = context
        super().__init__(context.message)
    
    def __str__(self) -> str:
        """String representation of the error."""
        base = f"{self.context.error_type.value}: {self.context.message}"
        if self.context.fallback_action:
            base += f" (Fallback: {self.context.fallback_action})"
        return base
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert error to dictionary for logging/serialization.
        
        Returns:
            Dictionary representation of error
        """
        return self.context.to_dict()


class BedrockAPIError(ClaimsProcessingError):
    """Exception for AWS Bedrock API errors."""
    
    @classmethod
    def from_client_error(
        cls,
        error: Exception,
        operation: str,
        recoverable: bool = False,
        fallback_action: Optional[str] = None
    ) -> "BedrockAPIError":
        """
        Create BedrockAPIError from boto3 ClientError.
        
        Args:
            error: Original boto3 ClientError
            operation: Description of operation that failed
            recoverable: Whether error is recoverable
            fallback_action: Optional fallback action description
            
        Returns:
            BedrockAPIError instance
        """
        # Extract error details from boto3 ClientError
        error_code = "Unknown"
        error_message = str(error)
        
        if hasattr(error, 'response'):
            error_info = error.response.get("Error", {})
            error_code = error_info.get("Code", "Unknown")
            error_message = error_info.get("Message", str(error))
        
        # Map error codes to error types
        error_type_map = {
            "ThrottlingException": ErrorType.BEDROCK_RATE_LIMIT,
            "TooManyRequestsException": ErrorType.BEDROCK_RATE_LIMIT,
            "RequestTimeout": ErrorType.BEDROCK_TIMEOUT,
            "RequestTimeoutException": ErrorType.BEDROCK_TIMEOUT,
            "UnauthorizedException": ErrorType.BEDROCK_AUTH_ERROR,
            "AccessDeniedException": ErrorType.BEDROCK_AUTH_ERROR,
            "ValidationException": ErrorType.BEDROCK_INVALID_REQUEST,
            "ModelNotReadyException": ErrorType.BEDROCK_MODEL_ERROR,
            "ModelTimeoutException": ErrorType.BEDROCK_TIMEOUT,
            "ServiceUnavailableException": ErrorType.BEDROCK_SERVICE_ERROR,
            "InternalServerException": ErrorType.BEDROCK_SERVICE_ERROR,
        }
        
        error_type = error_type_map.get(error_code, ErrorType.BEDROCK_SERVICE_ERROR)
        
        context = ErrorContext(
            error_type=error_type,
            message=f"Bedrock API error during {operation}: {error_message}",
            recoverable=recoverable,
            fallback_action=fallback_action,
            details={
                "error_code": error_code,
                "operation": operation
            },
            original_exception=error
        )
        
        return cls(context)


class DocumentProcessingError(ClaimsProcessingError):
    """Exception for document processing errors."""
    
    @classmethod
    def pdf_extraction_failed(
        cls,
        filename: str,
        error: Exception,
        fallback_action: Optional[str] = None
    ) -> "DocumentProcessingError":
        """
        Create error for PDF extraction failure.
        
        Args:
            filename: Name of PDF file
            error: Original exception
            fallback_action: Optional fallback action
            
        Returns:
            DocumentProcessingError instance
        """
        context = ErrorContext(
            error_type=ErrorType.PDF_EXTRACTION_FAILED,
            message=f"Failed to extract text from PDF '{filename}': {str(error)}",
            recoverable=True,
            fallback_action=fallback_action or "Continue with available evidence",
            details={"filename": filename},
            original_exception=error
        )
        return cls(context)
    
    @classmethod
    def image_analysis_failed(
        cls,
        filename: str,
        error: Exception,
        fallback_action: Optional[str] = None
    ) -> "DocumentProcessingError":
        """
        Create error for image analysis failure.
        
        Args:
            filename: Name of image file
            error: Original exception
            fallback_action: Optional fallback action
            
        Returns:
            DocumentProcessingError instance
        """
        context = ErrorContext(
            error_type=ErrorType.IMAGE_ANALYSIS_FAILED,
            message=f"Failed to analyze image '{filename}': {str(error)}",
            recoverable=True,
            fallback_action=fallback_action or "Continue with available evidence",
            details={"filename": filename},
            original_exception=error
        )
        return cls(context)
    
    @classmethod
    def invoice_parsing_failed(
        cls,
        filename: str,
        error: Exception,
        fallback_action: Optional[str] = None
    ) -> "DocumentProcessingError":
        """
        Create error for invoice parsing failure.
        
        Args:
            filename: Name of invoice file
            error: Original exception
            fallback_action: Optional fallback action
            
        Returns:
            DocumentProcessingError instance
        """
        context = ErrorContext(
            error_type=ErrorType.INVOICE_PARSING_FAILED,
            message=f"Failed to parse invoice '{filename}': {str(error)}",
            recoverable=True,
            fallback_action=fallback_action or "Request manual review",
            details={"filename": filename},
            original_exception=error
        )
        return cls(context)


class VectorStoreError(ClaimsProcessingError):
    """Exception for FAISS vector store errors."""
    
    @classmethod
    def index_not_found(
        cls,
        index_path: str,
        fallback_action: Optional[str] = None
    ) -> "VectorStoreError":
        """
        Create error for missing FAISS index.
        
        Args:
            index_path: Path to missing index file
            fallback_action: Optional fallback action
            
        Returns:
            VectorStoreError instance
        """
        context = ErrorContext(
            error_type=ErrorType.FAISS_INDEX_NOT_FOUND,
            message=f"FAISS index not found at '{index_path}'",
            recoverable=True,
            fallback_action=fallback_action or "Rebuild index from policy documents",
            details={"index_path": index_path}
        )
        return cls(context)
    
    @classmethod
    def search_failed(
        cls,
        query: str,
        error: Exception,
        fallback_action: Optional[str] = None
    ) -> "VectorStoreError":
        """
        Create error for FAISS search failure.
        
        Args:
            query: Search query that failed
            error: Original exception
            fallback_action: Optional fallback action
            
        Returns:
            VectorStoreError instance
        """
        context = ErrorContext(
            error_type=ErrorType.FAISS_SEARCH_FAILED,
            message=f"FAISS search failed for query '{query[:50]}...': {str(error)}",
            recoverable=True,
            fallback_action=fallback_action or "Return empty results",
            details={"query": query},
            original_exception=error
        )
        return cls(context)


class AgentError(ClaimsProcessingError):
    """Exception for agent-related errors."""
    
    @classmethod
    def max_rounds_exceeded(
        cls,
        max_rounds: int,
        fallback_action: Optional[str] = None
    ) -> "AgentError":
        """
        Create error for exceeding maximum debate rounds.
        
        Args:
            max_rounds: Maximum number of rounds allowed
            fallback_action: Optional fallback action
            
        Returns:
            AgentError instance
        """
        context = ErrorContext(
            error_type=ErrorType.AGENT_MAX_ROUNDS_EXCEEDED,
            message=f"Agent debate exceeded maximum rounds ({max_rounds})",
            recoverable=True,
            fallback_action=fallback_action or "Force decision with disclaimer",
            details={"max_rounds": max_rounds}
        )
        return cls(context)
    
    @classmethod
    def plugin_failed(
        cls,
        plugin_name: str,
        error: Exception,
        fallback_action: Optional[str] = None
    ) -> "AgentError":
        """
        Create error for agent plugin failure.
        
        Args:
            plugin_name: Name of plugin that failed
            error: Original exception
            fallback_action: Optional fallback action
            
        Returns:
            AgentError instance
        """
        context = ErrorContext(
            error_type=ErrorType.AGENT_PLUGIN_FAILED,
            message=f"Agent plugin '{plugin_name}' failed: {str(error)}",
            recoverable=True,
            fallback_action=fallback_action or "Skip tool and continue with available data",
            details={"plugin_name": plugin_name},
            original_exception=error
        )
        return cls(context)


def handle_bedrock_error(
    error: Exception,
    operation: str,
    logger,
    fallback_action: Optional[str] = None
) -> None:
    """
    Handle Bedrock API errors with logging and graceful degradation.
    
    This function logs the error appropriately and raises a ClaimsProcessingError
    with context for upstream handling.
    
    Args:
        error: Original exception from Bedrock API
        operation: Description of operation that failed
        logger: Logger instance for error logging
        fallback_action: Optional fallback action description
        
    Raises:
        BedrockAPIError: Wrapped error with context
    """
    bedrock_error = BedrockAPIError.from_client_error(
        error=error,
        operation=operation,
        recoverable=True,
        fallback_action=fallback_action
    )
    
    # Log with appropriate level based on recoverability
    if bedrock_error.context.recoverable:
        logger.warning(f"Recoverable Bedrock error: {bedrock_error}")
    else:
        logger.error(f"Non-recoverable Bedrock error: {bedrock_error}")
    
    raise bedrock_error


def handle_document_processing_error(
    error: Exception,
    filename: str,
    doc_type: str,
    logger,
    fallback_action: Optional[str] = None
) -> None:
    """
    Handle document processing errors with logging and graceful degradation.
    
    Args:
        error: Original exception from document processing
        filename: Name of file being processed
        doc_type: Type of document ('pdf', 'image', 'invoice')
        logger: Logger instance for error logging
        fallback_action: Optional fallback action description
        
    Raises:
        DocumentProcessingError: Wrapped error with context
    """
    if doc_type == 'pdf':
        doc_error = DocumentProcessingError.pdf_extraction_failed(
            filename=filename,
            error=error,
            fallback_action=fallback_action
        )
    elif doc_type == 'image':
        doc_error = DocumentProcessingError.image_analysis_failed(
            filename=filename,
            error=error,
            fallback_action=fallback_action
        )
    elif doc_type == 'invoice':
        doc_error = DocumentProcessingError.invoice_parsing_failed(
            filename=filename,
            error=error,
            fallback_action=fallback_action
        )
    else:
        # Generic document processing error
        context = ErrorContext(
            error_type=ErrorType.UNKNOWN_ERROR,
            message=f"Failed to process document '{filename}': {str(error)}",
            recoverable=True,
            fallback_action=fallback_action or "Continue with available evidence",
            details={"filename": filename, "doc_type": doc_type},
            original_exception=error
        )
        doc_error = DocumentProcessingError(context)
    
    logger.warning(f"Document processing error: {doc_error}")
    raise doc_error
