"""Script to build FAISS index from policy documents."""

import os
import sys
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.storage.vector_store import PolicyVectorStore
from backend.storage.file_storage import FileStorage
from backend.utils.config import Config
from backend.utils.bedrock_client import BedrockClient
from backend.utils.logging import setup_logging

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    Extract text from PDF file.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Extracted text
    """
    try:
        import PyPDF2
        
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text_parts = []
            
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            
            full_text = '\n'.join(text_parts)
            logger.info(f"Extracted {len(full_text)} characters from {pdf_path.name}")
            return full_text
            
    except Exception as e:
        logger.error(f"Failed to extract text from {pdf_path}: {str(e)}")
        raise


def infer_policy_type(filename: str) -> str:
    """
    Infer policy type from filename.
    
    Args:
        filename: PDF filename
        
    Returns:
        Policy type (e.g., "HO-3", "PAP", "Unknown")
    """
    filename_lower = filename.lower()
    
    if 'ho3' in filename_lower or 'ho-3' in filename_lower or 'homeowner' in filename_lower:
        return "HO-3"
    elif 'pap' in filename_lower or 'auto' in filename_lower or 'personal auto' in filename_lower:
        return "PAP"
    else:
        return "Unknown"


async def build_index_async(config_path: str = "config.yaml"):
    """
    Build FAISS index from policy documents.
    
    Args:
        config_path: Path to configuration file
    """
    # Load configuration
    logger.info("Loading configuration...")
    config = Config.load(config_path)
    
    # Initialize components
    logger.info("Initializing components...")
    file_storage = FileStorage(
        policy_dir=config.storage.policy_dir,
        sample_cases_dir=config.storage.sample_cases_dir,
        uploads_dir=config.storage.uploads_dir
    )
    
    bedrock_client = BedrockClient(
        region=config.aws_region,
        model_id=config.bedrock.model_id,
        embedding_model_id=config.bedrock.embedding_model_id,
        timeout=config.bedrock.timeout,
        max_retries=config.bedrock.max_retries
    )
    
    vector_store = PolicyVectorStore(
        index_path=config.vector_store.index_path,
        metadata_path=config.vector_store.metadata_path,
        dimension=config.vector_store.dimension,
        chunk_size=config.vector_store.chunk_size,
        chunk_overlap=config.vector_store.chunk_overlap
    )
    
    # List policy documents
    logger.info("Scanning for policy documents...")
    policy_files = file_storage.list_policy_documents()
    
    if not policy_files:
        logger.error(f"No policy documents found in {config.storage.policy_dir}")
        logger.info("Please add policy PDF files to the policies directory")
        return
    
    logger.info(f"Found {len(policy_files)} policy documents")
    
    # Extract text from all policy documents
    logger.info("Extracting text from policy documents...")
    policy_documents = []
    
    for pdf_path in policy_files:
        try:
            text = extract_text_from_pdf(pdf_path)
            policy_type = infer_policy_type(pdf_path.name)
            
            policy_documents.append({
                'policy_type': policy_type,
                'document_name': pdf_path.name,
                'text': text,
                'metadata': {
                    'file_path': str(pdf_path),
                    'file_size': pdf_path.stat().st_size
                }
            })
            
            logger.info(f"Processed {pdf_path.name} as {policy_type}")
            
        except Exception as e:
            logger.error(f"Failed to process {pdf_path.name}: {str(e)}")
            continue
    
    if not policy_documents:
        logger.error("No policy documents could be processed")
        return
    
    # Create embedding generator function
    async def generate_embedding(text: str):
        """Generate embedding for text."""
        return await bedrock_client.generate_embedding(text)
    
    # Build index
    logger.info("Building FAISS index...")
    logger.info("This may take several minutes depending on document size...")
    
    try:
        await vector_store.build_index(policy_documents, generate_embedding)
        logger.info("✓ FAISS index built successfully!")
        
        # Print statistics
        stats = vector_store.get_stats()
        logger.info(f"Index statistics:")
        logger.info(f"  - Total vectors: {stats['total_vectors']}")
        logger.info(f"  - Dimension: {stats['dimension']}")
        logger.info(f"  - Policy types: {stats['policy_types']}")
        logger.info(f"  - Index saved to: {stats['index_path']}")
        logger.info(f"  - Metadata saved to: {stats['metadata_path']}")
        
    except Exception as e:
        logger.error(f"Failed to build index: {str(e)}")
        raise


def main():
    """Main entry point."""
    # Setup logging
    setup_logging(level="INFO")
    
    logger.info("=" * 60)
    logger.info("FAISS Index Builder for Policy Documents")
    logger.info("=" * 60)
    
    # Check if config file exists
    if not os.path.exists("config.yaml"):
        logger.error("config.yaml not found in current directory")
        logger.info("Please run this script from the project root directory")
        sys.exit(1)
    
    # Verify AWS credentials are available
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("AWS_REGION")
    
    if not aws_access_key or not aws_secret_key:
        logger.error("AWS credentials not found!")
        logger.info("Please set AWS credentials in one of the following ways:")
        logger.info("  1. Create a .env file with AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        logger.info("  2. Set environment variables: export AWS_ACCESS_KEY_ID=xxx AWS_SECRET_ACCESS_KEY=xxx")
        logger.info("  3. Configure AWS CLI: aws configure")
        sys.exit(1)
    
    logger.info(f"AWS credentials loaded successfully")
    logger.info(f"AWS Region: {aws_region or 'us-east-1 (default)'}")
    logger.info(f"AWS Access Key: {aws_access_key[:8]}..." if aws_access_key else "Not set")
    
    # Check if using temporary credentials (session token)
    aws_session_token = os.getenv("AWS_SESSION_TOKEN")
    if aws_access_key and aws_access_key.startswith("ASIA"):
        if not aws_session_token:
            logger.warning("⚠ You appear to be using temporary AWS credentials (ASIA...)")
            logger.warning("⚠ You may need to set AWS_SESSION_TOKEN in your .env file")
            logger.warning("⚠ If you get authentication errors, add AWS_SESSION_TOKEN to .env")
        else:
            logger.info("AWS Session Token: Found (temporary credentials)")
    
    logger.info("")
    
    # Run async build
    try:
        asyncio.run(build_index_async())
        logger.info("=" * 60)
        logger.info("Index building completed successfully!")
        logger.info("=" * 60)
        
    except KeyboardInterrupt:
        logger.info("\nIndex building interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"Index building failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
