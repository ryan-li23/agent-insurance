"""Structured logging setup for claims reasoner."""

import logging
from typing import Optional, Dict, Any
from pathlib import Path


class ContextFilter(logging.Filter):
    """Add context information to log records."""
    
    def __init__(self):
        super().__init__()
        self.context: Dict[str, Any] = {}
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add context fields to log record."""
        for key, value in self.context.items():
            setattr(record, key, value)
        return True
    
    def set_context(self, **kwargs):
        """Set context fields for logging."""
        self.context.update(kwargs)
    
    def clear_context(self):
        """Clear all context fields."""
        self.context.clear()


# Global context filter instance
_context_filter = ContextFilter()


def setup_logging(
    level: str = "INFO",
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Set up structured logging with optional file output.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format string for log messages
        log_file: Optional path to log file
        
    Returns:
        Configured root logger
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(log_format)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(_context_filter)
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        # Create log directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(_context_filter)
        root_logger.addHandler(file_handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def set_context(**kwargs):
    """
    Set context fields for all subsequent log messages.
    
    Example:
        set_context(case_id="CLAIM-123", component="curator")
        logger.info("Processing claim")  # Will include case_id and component
    
    Args:
        **kwargs: Context key-value pairs
    """
    _context_filter.set_context(**kwargs)


def clear_context():
    """Clear all context fields."""
    _context_filter.clear_context()


def with_context(**context_kwargs):
    """
    Decorator to add context to all log messages within a function.
    
    Example:
        @with_context(component="curator")
        def process_claim(case_id):
            set_context(case_id=case_id)
            logger.info("Processing")  # Includes component and case_id
    
    Args:
        **context_kwargs: Context key-value pairs
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Save current context
            old_context = _context_filter.context.copy()
            
            # Add new context
            set_context(**context_kwargs)
            
            try:
                return func(*args, **kwargs)
            finally:
                # Restore old context
                _context_filter.context = old_context
        
        return wrapper
    return decorator
