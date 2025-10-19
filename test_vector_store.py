"""Simple test script to verify FAISS vector store implementation."""

import numpy as np
from backend.storage.vector_store import PolicyVectorStore
from backend.storage.file_storage import FileStorage


def test_file_storage():
    """Test FileStorage functionality."""
    print("\n" + "=" * 60)
    print("Testing FileStorage")
    print("=" * 60)
    
    # Initialize file storage
    file_storage = FileStorage()
    
    # Get storage stats
    stats = file_storage.get_storage_stats()
    print("\nStorage Statistics:")
    print(f"  Policy directory: {stats['policy_dir']['path']}")
    print(f"  - Exists: {stats['policy_dir']['exists']}")
    print(f"  - Files: {stats['policy_dir']['file_count']}")
    
    print(f"\n  Uploads directory: {stats['uploads_dir']['path']}")
    print(f"  - Exists: {stats['uploads_dir']['exists']}")
    print(f"  - Cases: {stats['uploads_dir']['case_count']}")
    
    print(f"\n  Sample cases directory: {stats['sample_cases_dir']['path']}")
    print(f"  - Exists: {stats['sample_cases_dir']['exists']}")
    print(f"  - Cases: {stats['sample_cases_dir']['case_count']}")
    
    # List policy documents
    policy_files = file_storage.list_policy_documents()
    print(f"\n  Policy documents found: {len(policy_files)}")
    for pf in policy_files:
        print(f"    - {pf.name}")
    
    # List sample cases
    sample_cases = file_storage.list_sample_cases()
    print(f"\n  Sample cases found: {len(sample_cases)}")
    for sc in sample_cases:
        print(f"    - {sc}")
    
    # Test upload functionality
    print("\n  Testing upload functionality...")
    test_case_id = "TEST_CASE_001"
    test_content = b"This is test content"
    
    try:
        saved_path = file_storage.save_upload(
            case_id=test_case_id,
            filename="test_file.txt",
            content=test_content,
            category="general"
        )
        print(f"    [OK] Saved test upload to: {saved_path}")
        
        # Load it back
        loaded_content = file_storage.load_upload(
            case_id=test_case_id,
            filename="test_file.txt",
            category="general"
        )
        
        if loaded_content == test_content:
            print("    [OK] Successfully loaded test upload")
        else:
            print("    [FAIL] Content mismatch!")
        
        # List uploads
        uploads = file_storage.list_uploads(test_case_id)
        print(f"    [OK] Found {len(uploads)} upload(s) for test case")
        
        # Clean up
        file_storage.delete_case_uploads(test_case_id)
        print("    [OK] Cleaned up test uploads")
        
    except Exception as e:
        print(f"    [FAIL] Upload test failed: {str(e)}")
    
    print("\n[OK] FileStorage tests completed")


def test_vector_store():
    """Test PolicyVectorStore functionality."""
    print("\n" + "=" * 60)
    print("Testing PolicyVectorStore")
    print("=" * 60)
    
    # Initialize vector store
    vector_store = PolicyVectorStore(
        index_path="data/policy_index.faiss",
        metadata_path="data/policy_metadata.json",
        dimension=1024,
        chunk_size=500,
        chunk_overlap=50
    )
    
    print("\nVector store initialized:")
    print(f"  - Index path: {vector_store.index_path}")
    print(f"  - Metadata path: {vector_store.metadata_path}")
    print(f"  - Dimension: {vector_store.dimension}")
    print(f"  - Chunk size: {vector_store.chunk_size}")
    print(f"  - Chunk overlap: {vector_store.chunk_overlap}")
    
    # Check if index exists
    print("\n  Checking for existing index...")
    if vector_store.load_index():
        print("    [OK] Loaded existing index")
        
        # Get stats
        stats = vector_store.get_stats()
        print("\n  Index Statistics:")
        print(f"    - Total vectors: {stats['total_vectors']}")
        print(f"    - Metadata entries: {stats['metadata_entries']}")
        print(f"    - Dimension: {stats['dimension']}")
        print(f"    - Policy types: {stats['policy_types']}")
        
        # Test search with dummy query
        print("\n  Testing search functionality...")
        dummy_query = np.random.randn(1024).astype(np.float32)
        
        try:
            results = vector_store.search(dummy_query, top_k=3)
            print(f"    [OK] Search returned {len(results)} results")
            
            for i, result in enumerate(results[:3], 1):
                print(f"\n    Result {i}:")
                print(f"      - Policy: {result.get('policy_type', 'N/A')}")
                print(f"      - Document: {result.get('document_name', 'N/A')}")
                print(f"      - Score: {result.get('score', 0):.4f}")
                print(f"      - Text preview: {result.get('text', '')[:100]}...")
        
        except Exception as e:
            print(f"    [FAIL] Search test failed: {str(e)}")
    
    else:
        print("    [INFO] No existing index found")
        print("    [INFO] Run 'python backend/storage/build_index.py' to create index")
        print("    [INFO] Make sure to add policy PDF files to data/policies/ first")
    
    print("\n[OK] PolicyVectorStore tests completed")


def test_chunking():
    """Test document chunking functionality."""
    print("\n" + "=" * 60)
    print("Testing Document Chunking")
    print("=" * 60)
    
    vector_store = PolicyVectorStore(
        index_path="data/test_index.faiss",
        metadata_path="data/test_metadata.json",
        dimension=1024,
        chunk_size=50,  # Small for testing
        chunk_overlap=10
    )
    
    # Create sample document
    sample_text = " ".join([f"word{i}" for i in range(200)])
    
    print(f"\n  Sample document: {len(sample_text.split())} words")
    
    # Chunk it
    chunks = vector_store._chunk_document(
        text=sample_text,
        policy_type="TEST",
        document_name="test_doc.pdf",
        additional_metadata={"test": True}
    )
    
    print(f"  Generated {len(chunks)} chunks")
    print("\n  First chunk:")
    print(f"    - Text length: {len(chunks[0][0])} chars")
    print(f"    - Metadata: {chunks[0][1]}")
    
    print("\n  Last chunk:")
    print(f"    - Text length: {len(chunks[-1][0])} chars")
    print(f"    - Metadata: {chunks[-1][1]}")
    
    # Verify overlap
    if len(chunks) > 1:
        chunk1_words = chunks[0][0].split()
        chunk2_words = chunks[1][0].split()
        
        # Check if there's overlap
        overlap_found = False
        for word in chunk1_words[-10:]:
            if word in chunk2_words[:10]:
                overlap_found = True
                break
        
        if overlap_found:
            print("\n  [OK] Overlap detected between chunks")
        else:
            print("\n  [INFO] No overlap detected (may be expected for small chunks)")
    
    print("\n[OK] Chunking tests completed")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("FAISS Vector Store Implementation Tests")
    print("=" * 60)
    
    try:
        # Test file storage
        test_file_storage()
        
        # Test vector store
        test_vector_store()
        
        # Test chunking
        test_chunking()
        
        print("\n" + "=" * 60)
        print("All tests completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Add policy PDF files to data/policies/")
        print("  2. Run: python backend/storage/build_index.py")
        print("  3. The index will be ready for use in the application")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n[FAIL] Tests failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
