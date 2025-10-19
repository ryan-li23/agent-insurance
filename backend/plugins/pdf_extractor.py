"""PDF text extraction plugin for Semantic Kernel."""

import importlib.util
import logging
from typing import Optional, Dict, Any

from semantic_kernel.functions import kernel_function

logger = logging.getLogger(__name__)


class PDFExtractorPlugin:
    """
    Semantic Kernel plugin for extracting text from PDF documents.
    
    Uses PyPDF2 as primary extractor with pdfplumber as fallback
    for better handling of complex layouts.
    """
    
    def __init__(self):
        """Initialize PDF extractor plugin."""
        self._validate_dependencies()
        logger.info("Initialized PDFExtractorPlugin")
    
    def _validate_dependencies(self):
        """Validate that required libraries are available."""
        self.has_pypdf2 = importlib.util.find_spec("PyPDF2") is not None
        if not self.has_pypdf2:
            logger.warning("PyPDF2 not available")

        self.has_pdfplumber = importlib.util.find_spec("pdfplumber") is not None
        if not self.has_pdfplumber:
            logger.warning("pdfplumber not available")

        if not self.has_pypdf2 and not self.has_pdfplumber:
            raise ImportError(
                "Neither PyPDF2 nor pdfplumber is available. "
                "Install at least one: pip install PyPDF2 pdfplumber"
            )
    
    @kernel_function(
        name="extract_pdf_text",
        description="Extract text content from PDF documents. Returns the full text with page numbers."
    )
    def extract_text(
        self,
        pdf_path: str = None,
        pdf_bytes: bytes = None,
        include_page_numbers: bool = True
    ) -> str:
        """
        Extract text from a PDF file.
        
        Args:
            pdf_path: Path to PDF file (optional if pdf_bytes provided)
            pdf_bytes: Raw PDF bytes (optional if pdf_path provided)
            include_page_numbers: Whether to include page number markers
            
        Returns:
            Extracted text content
            
        Raises:
            ValueError: If neither pdf_path nor pdf_bytes provided
            RuntimeError: If text extraction fails
        """
        if pdf_path is None and pdf_bytes is None:
            raise ValueError("Either pdf_path or pdf_bytes must be provided")
        
        # Try PyPDF2 first (faster)
        if self.has_pypdf2:
            try:
                text = self._extract_with_pypdf2(pdf_path, pdf_bytes, include_page_numbers)
                if text and len(text.strip()) > 0:
                    logger.info(
                        f"Extracted {len(text)} characters using PyPDF2 "
                        f"from {pdf_path or 'bytes'}"
                    )
                    return text
                else:
                    logger.warning("PyPDF2 returned empty text, trying pdfplumber")
            except Exception as e:
                logger.warning(f"PyPDF2 extraction failed: {str(e)}, trying pdfplumber")
        
        # Fallback to pdfplumber (better for complex layouts)
        if self.has_pdfplumber:
            try:
                text = self._extract_with_pdfplumber(pdf_path, pdf_bytes, include_page_numbers)
                logger.info(
                    f"Extracted {len(text)} characters using pdfplumber "
                    f"from {pdf_path or 'bytes'}"
                )
                return text
            except Exception as e:
                logger.error(f"pdfplumber extraction failed: {str(e)}")
                raise RuntimeError(f"Failed to extract text from PDF: {str(e)}") from e
        
        raise RuntimeError("No PDF extraction library available")
    
    def _extract_with_pypdf2(
        self,
        pdf_path: Optional[str],
        pdf_bytes: Optional[bytes],
        include_page_numbers: bool
    ) -> str:
        """Extract text using PyPDF2."""
        import PyPDF2
        import io
        
        # Open PDF
        if pdf_bytes:
            pdf_file = io.BytesIO(pdf_bytes)
        else:
            pdf_file = open(pdf_path, 'rb')
        
        try:
            reader = PyPDF2.PdfReader(pdf_file)
            text_parts = []
            
            for page_num, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text()
                
                if page_text:
                    if include_page_numbers:
                        text_parts.append(f"\n--- Page {page_num} ---\n")
                    text_parts.append(page_text)
            
            return ''.join(text_parts)
        
        finally:
            if not pdf_bytes:
                pdf_file.close()
    
    def _extract_with_pdfplumber(
        self,
        pdf_path: Optional[str],
        pdf_bytes: Optional[bytes],
        include_page_numbers: bool
    ) -> str:
        """Extract text using pdfplumber."""
        import pdfplumber
        import io
        
        # Open PDF
        if pdf_bytes:
            pdf_file = io.BytesIO(pdf_bytes)
        else:
            pdf_file = pdf_path
        
        text_parts = []
        
        with pdfplumber.open(pdf_file) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text()
                
                if page_text:
                    if include_page_numbers:
                        text_parts.append(f"\n--- Page {page_num} ---\n")
                    text_parts.append(page_text)
        
        return ''.join(text_parts)
    
    @kernel_function(
        name="extract_pdf_metadata",
        description="Extract metadata from PDF documents (title, author, creation date, etc.)"
    )
    def extract_metadata(
        self,
        pdf_path: str = None,
        pdf_bytes: bytes = None
    ) -> Dict[str, Any]:
        """
        Extract metadata from a PDF file.
        
        Args:
            pdf_path: Path to PDF file (optional if pdf_bytes provided)
            pdf_bytes: Raw PDF bytes (optional if pdf_path provided)
            
        Returns:
            Dictionary with metadata fields
            
        Raises:
            ValueError: If neither pdf_path nor pdf_bytes provided
            RuntimeError: If metadata extraction fails
        """
        if pdf_path is None and pdf_bytes is None:
            raise ValueError("Either pdf_path or pdf_bytes must be provided")
        
        if not self.has_pypdf2:
            raise RuntimeError("PyPDF2 required for metadata extraction")
        
        try:
            import PyPDF2
            import io
            
            # Open PDF
            if pdf_bytes:
                pdf_file = io.BytesIO(pdf_bytes)
            else:
                pdf_file = open(pdf_path, 'rb')
            
            try:
                reader = PyPDF2.PdfReader(pdf_file)
                
                metadata = {
                    'page_count': len(reader.pages),
                    'title': None,
                    'author': None,
                    'subject': None,
                    'creator': None,
                    'producer': None,
                    'creation_date': None,
                    'modification_date': None
                }
                
                # Extract metadata if available
                if reader.metadata:
                    metadata['title'] = reader.metadata.get('/Title')
                    metadata['author'] = reader.metadata.get('/Author')
                    metadata['subject'] = reader.metadata.get('/Subject')
                    metadata['creator'] = reader.metadata.get('/Creator')
                    metadata['producer'] = reader.metadata.get('/Producer')
                    metadata['creation_date'] = reader.metadata.get('/CreationDate')
                    metadata['modification_date'] = reader.metadata.get('/ModDate')
                
                logger.debug(f"Extracted metadata from {pdf_path or 'bytes'}: {metadata}")
                return metadata
            
            finally:
                if not pdf_bytes:
                    pdf_file.close()
        
        except Exception as e:
            logger.error(f"Failed to extract PDF metadata: {str(e)}")
            raise RuntimeError(f"Metadata extraction failed: {str(e)}") from e
    
    @kernel_function(
        name="extract_pdf_page",
        description="Extract text from a specific page of a PDF document"
    )
    def extract_page(
        self,
        page_number: int,
        pdf_path: str = None,
        pdf_bytes: bytes = None
    ) -> str:
        """
        Extract text from a specific page.
        
        Args:
            page_number: Page number to extract (1-indexed)
            pdf_path: Path to PDF file (optional if pdf_bytes provided)
            pdf_bytes: Raw PDF bytes (optional if pdf_path provided)
            
        Returns:
            Text content from the specified page
            
        Raises:
            ValueError: If page_number is invalid or neither pdf_path nor pdf_bytes provided
            RuntimeError: If extraction fails
        """
        if pdf_path is None and pdf_bytes is None:
            raise ValueError("Either pdf_path or pdf_bytes must be provided")
        
        if page_number < 1:
            raise ValueError(f"Page number must be >= 1, got {page_number}")
        
        if not self.has_pypdf2:
            raise RuntimeError("PyPDF2 required for page extraction")
        
        try:
            import PyPDF2
            import io
            
            # Open PDF
            if pdf_bytes:
                pdf_file = io.BytesIO(pdf_bytes)
            else:
                pdf_file = open(pdf_path, 'rb')
            
            try:
                reader = PyPDF2.PdfReader(pdf_file)
                
                if page_number > len(reader.pages):
                    raise ValueError(
                        f"Page {page_number} does not exist "
                        f"(document has {len(reader.pages)} pages)"
                    )
                
                page = reader.pages[page_number - 1]  # Convert to 0-indexed
                text = page.extract_text()
                
                logger.debug(
                    f"Extracted {len(text)} characters from page {page_number} "
                    f"of {pdf_path or 'bytes'}"
                )
                
                return text
            
            finally:
                if not pdf_bytes:
                    pdf_file.close()
        
        except Exception as e:
            logger.error(f"Failed to extract page {page_number}: {str(e)}")
            raise RuntimeError(f"Page extraction failed: {str(e)}") from e
