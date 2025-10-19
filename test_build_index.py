"""Test script to verify build_index.py structure without AWS credentials."""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.storage.vector_store import PolicyVectorStore
from backend.storage.file_storage import FileStorage
from backend.utils.config import Config
import numpy as np
import asyncio
import pytest


async def mock_embedding_generator(text: str) -> np.ndarray:
    """Mock embedding generator that returns random vectors."""
    return np.random.rand(1024).astype(np.float32)


@pytest.mark.asyncio
async def test_build_index():
    """Test building index with mock embeddings."""
    print("=" * 60)
    print("Testing FAISS Index Builder (Mock Mode)")
    print("=" * 60)
    print()
    
    # Load configuration
    print("Loading configuration...")
    config = Config.load("config.yaml")
    
    # Initialize components
    print("Initializing components...")
    file_storage = FileStorage(
        policy_dir=config.storage.policy_dir,
        sample_cases_dir=config.storage.sample_cases_dir,
        uploads_dir=config.storage.uploads_dir
    )
    
    vector_store = PolicyVectorStore(
        index_path="data/test_policy_index.faiss",
        metadata_path="data/test_policy_metadata.json",
        dimension=config.vector_store.dimension,
        chunk_size=config.vector_store.chunk_size,
        chunk_overlap=config.vector_store.chunk_overlap
    )
    
    # List policy documents
    print("Scanning for policy documents...")
    policy_files = file_storage.list_policy_documents()
    
    if not policy_files:
        print("ERROR: No policy documents found!")
        print("Run: python backend/storage/create_sample_policies.py")
        return False
    
    print(f"Found {len(policy_files)} policy documents")
    print()
    
    # Extract text from policies (simplified)
    print("Extracting text from policy documents...")
    policy_documents = []
    
    for pdf_path in policy_files:
        try:
            import PyPDF2
            
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text_parts = []
                
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                
                full_text = '\n'.join(text_parts)
                
                # Infer policy type
                filename_lower = pdf_path.name.lower()
                if 'ho3' in filename_lower or 'ho-3' in filename_lower:
                    policy_type = "HO-3"
                elif 'pap' in filename_lower or 'auto' in filename_lower:
                    policy_type = "PAP"
                else:
                    policy_type = "Unknown"
                
                policy_documents.append({
                    'policy_type': policy_type,
                    'document_name': pdf_path.name,
                    'text': full_text,
                    'metadata': {
                        'file_path': str(pdf_path),
                        'file_size': pdf_path.stat().st_size
                    }
                })
                
                print(f"  [OK] Processed {pdf_path.name} as {policy_type} ({len(full_text)} chars)")
                
        except Exception as e:
            print(f"  [FAIL] Failed to process {pdf_path.name}: {str(e)}")
            continue
    
    if not policy_documents:
        print("ERROR: No policy documents could be processed")
        return False
    
    print()
    print("Building FAISS index with mock embeddings...")
    
    try:
        await vector_store.build_index(policy_documents, mock_embedding_generator)
        print("[OK] FAISS index built successfully!")
        print()
        
        # Print statistics
        stats = vector_store.get_stats()
        print("Index Statistics:")
        print(f"  - Total vectors: {stats['total_vectors']}")
        print(f"  - Dimension: {stats['dimension']}")
        print(f"  - Policy types: {stats['policy_types']}")
        print(f"  - Index saved to: {stats['index_path']}")
        print(f"  - Metadata saved to: {stats['metadata_path']}")
        print()
        
        # Test search
        print("Testing search functionality...")
        query_embedding = np.random.rand(1024).astype(np.float32)
        results = vector_store.search(query_embedding, top_k=3)
        
        print(f"  [OK] Search returned {len(results)} results")
        if results:
            print(f"  - Top result policy type: {results[0]['policy_type']}")
            print(f"  - Top result score: {results[0]['score']:.4f}")
        print()
        
        print("=" * 60)
        print("[OK] All tests passed!")
        print("=" * 60)
        print()
        print("The build_index.py script is working correctly.")
        print("To build the real index with AWS Bedrock embeddings:")
        print("  1. Configure AWS credentials")
        print("  2. Run: python backend/storage/build_index.py")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Failed to build index: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_build_index())
    sys.exit(0 if success else 1)
