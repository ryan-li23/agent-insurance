"""FAISS vector store for policy document retrieval."""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import faiss

logger = logging.getLogger(__name__)


class PolicyVectorStore:
    """
    FAISS-based vector store for semantic search over policy documents.
    
    Provides methods for:
    - Building index from policy PDFs
    - Loading existing index from disk
    - Semantic similarity search
    - Index persistence
    """
    
    def __init__(
        self,
        index_path: str,
        metadata_path: str,
        dimension: int = 1024,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ):
        """
        Initialize PolicyVectorStore.
        
        Args:
            index_path: Path to save/load FAISS index file
            metadata_path: Path to save/load metadata JSON file
            dimension: Embedding vector dimension (1024 for Titan)
            chunk_size: Number of tokens per chunk
            chunk_overlap: Number of overlapping tokens between chunks
        """
        self.index_path = index_path
        self.metadata_path = metadata_path
        self.dimension = dimension
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        self.index: Optional[faiss.Index] = None
        self.metadata: List[Dict[str, Any]] = []
        
        logger.info(
            f"Initialized PolicyVectorStore: "
            f"index_path={index_path}, dimension={dimension}"
        )
    
    async def build_index(
        self,
        policy_documents: List[Dict[str, Any]],
        embedding_generator
    ) -> None:
        """
        Build FAISS index from policy documents.
        
        Args:
            policy_documents: List of dicts with keys:
                - 'policy_type': str (e.g., "HO-3", "PAP")
                - 'document_name': str (filename)
                - 'text': str (full document text)
                - 'metadata': dict (optional additional metadata)
            embedding_generator: Async function that takes text and returns embedding
                                 Signature: async def generate(text: str) -> np.ndarray
        
        Raises:
            ValueError: If policy_documents is empty
            RuntimeError: If index building fails
        """
        if not policy_documents:
            raise ValueError("Cannot build index from empty policy documents list")
        
        logger.info(f"Building FAISS index from {len(policy_documents)} policy documents")
        
        try:
            # Step 1: Chunk all documents and extract metadata
            all_chunks = []
            all_metadata = []
            
            for doc in policy_documents:
                chunks_with_meta = self._chunk_document(
                    text=doc['text'],
                    policy_type=doc['policy_type'],
                    document_name=doc['document_name'],
                    additional_metadata=doc.get('metadata', {})
                )
                
                for chunk_text, chunk_meta in chunks_with_meta:
                    all_chunks.append(chunk_text)
                    all_metadata.append(chunk_meta)
            
            logger.info(f"Created {len(all_chunks)} chunks from policy documents")
            
            # Step 2: Generate embeddings for all chunks
            embeddings = []
            for i, chunk_text in enumerate(all_chunks):
                if i % 100 == 0:
                    logger.info(f"Generating embeddings: {i}/{len(all_chunks)}")
                
                # Call the embedding generator (async)
                embedding = await embedding_generator(chunk_text)
                embeddings.append(embedding)
            
            embeddings_array = np.array(embeddings, dtype=np.float32)
            
            logger.info(
                f"Generated embeddings: shape={embeddings_array.shape}, "
                f"dtype={embeddings_array.dtype}"
            )
            
            # Step 3: Create FAISS index (IndexFlatIP for cosine similarity)
            # Normalize vectors for cosine similarity with inner product
            faiss.normalize_L2(embeddings_array)
            
            self.index = faiss.IndexFlatIP(self.dimension)
            self.index.add(embeddings_array)
            self.metadata = all_metadata
            
            logger.info(
                f"Built FAISS index: total_vectors={self.index.ntotal}, "
                f"dimension={self.dimension}"
            )
            
            # Step 4: Persist to disk
            self._save_index()
            
        except Exception as e:
            logger.error(f"Failed to build FAISS index: {str(e)}")
            raise RuntimeError(f"Index building failed: {str(e)}") from e
    
    def load_index(self) -> bool:
        """
        Load existing FAISS index from disk.
        
        Returns:
            True if index loaded successfully, False if files don't exist
            
        Raises:
            RuntimeError: If index files exist but loading fails
        """
        if not os.path.exists(self.index_path):
            logger.warning(f"Index file not found: {self.index_path}")
            return False
        
        if not os.path.exists(self.metadata_path):
            logger.warning(f"Metadata file not found: {self.metadata_path}")
            return False
        
        try:
            logger.info(f"Loading FAISS index from {self.index_path}")
            
            # Load FAISS index
            self.index = faiss.read_index(self.index_path)
            
            # Load metadata
            with open(self.metadata_path, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
            
            logger.info(
                f"Loaded FAISS index: total_vectors={self.index.ntotal}, "
                f"metadata_entries={len(self.metadata)}"
            )
            
            # Validate consistency
            if self.index.ntotal != len(self.metadata):
                raise RuntimeError(
                    f"Index/metadata mismatch: index has {self.index.ntotal} vectors "
                    f"but metadata has {len(self.metadata)} entries"
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load FAISS index: {str(e)}")
            raise RuntimeError(f"Index loading failed: {str(e)}") from e
    
    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        policy_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant policy clauses using semantic similarity.
        
        Args:
            query_embedding: Query embedding vector (must be normalized)
            top_k: Number of top results to return
            policy_type: Optional filter by policy type (e.g., "HO-3", "PAP")
            
        Returns:
            List of dicts with keys:
                - 'policy_type': str
                - 'section': str
                - 'page': int
                - 'text': str (chunk text)
                - 'chunk_id': str
                - 'document_name': str
                - 'score': float (similarity score)
                
        Raises:
            RuntimeError: If index is not loaded
        """
        if self.index is None:
            raise RuntimeError("Index not loaded. Call load_index() or build_index() first.")
        
        if len(query_embedding.shape) == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        # Normalize query vector for cosine similarity
        query_embedding = query_embedding.astype(np.float32)
        faiss.normalize_L2(query_embedding)
        
        # Search FAISS index
        # We search for more results if filtering by policy_type
        search_k = top_k * 3 if policy_type else top_k
        distances, indices = self.index.search(query_embedding, search_k)
        
        # Compile results
        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx < 0 or idx >= len(self.metadata):
                continue
            
            result = self.metadata[idx].copy()
            result['score'] = float(dist)
            
            # Filter by policy type if specified
            if policy_type and result.get('policy_type') != policy_type:
                continue
            
            results.append(result)
            
            # Stop when we have enough results
            if len(results) >= top_k:
                break
        
        logger.debug(
            f"Search completed: query_dim={query_embedding.shape}, "
            f"top_k={top_k}, results={len(results)}"
        )
        
        return results
    
    def _chunk_document(
        self,
        text: str,
        policy_type: str,
        document_name: str,
        additional_metadata: Dict[str, Any]
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Chunk document text with overlap and extract metadata.
        
        Args:
            text: Full document text
            policy_type: Policy type (e.g., "HO-3", "PAP")
            document_name: Document filename
            additional_metadata: Additional metadata to include
            
        Returns:
            List of tuples (chunk_text, chunk_metadata)
        """
        # Simple token-based chunking (approximate with words)
        # In production, use a proper tokenizer
        words = text.split()
        
        chunks = []
        chunk_id = 0
        
        i = 0
        while i < len(words):
            # Extract chunk
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = ' '.join(chunk_words)
            
            # Create metadata for this chunk
            chunk_metadata = {
                'policy_type': policy_type,
                'document_name': document_name,
                'chunk_id': f"{document_name}_{chunk_id}",
                'text': chunk_text,
                'start_word': i,
                'end_word': min(i + self.chunk_size, len(words)),
                **additional_metadata
            }
            
            chunks.append((chunk_text, chunk_metadata))
            
            # Move to next chunk with overlap
            i += self.chunk_size - self.chunk_overlap
            chunk_id += 1
        
        logger.debug(
            f"Chunked document '{document_name}': "
            f"total_words={len(words)}, chunks={len(chunks)}"
        )
        
        return chunks
    
    def _save_index(self) -> None:
        """
        Save FAISS index and metadata to disk.
        
        Raises:
            RuntimeError: If saving fails
        """
        if self.index is None:
            raise RuntimeError("No index to save")
        
        try:
            # Create directories if they don't exist
            os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
            os.makedirs(os.path.dirname(self.metadata_path), exist_ok=True)
            
            # Save FAISS index
            faiss.write_index(self.index, self.index_path)
            logger.info(f"Saved FAISS index to {self.index_path}")
            
            # Save metadata
            with open(self.metadata_path, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved metadata to {self.metadata_path}")
            
        except Exception as e:
            logger.error(f"Failed to save index: {str(e)}")
            raise RuntimeError(f"Index saving failed: {str(e)}") from e
    
    def is_loaded(self) -> bool:
        """
        Check if index is loaded and ready for search.
        
        Returns:
            True if index is loaded, False otherwise
        """
        return self.index is not None and len(self.metadata) > 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the loaded index.
        
        Returns:
            Dict with index statistics
        """
        if not self.is_loaded():
            return {
                'loaded': False,
                'total_vectors': 0,
                'metadata_entries': 0
            }
        
        policy_types = {}
        for meta in self.metadata:
            policy_type = meta.get('policy_type', 'unknown')
            policy_types[policy_type] = policy_types.get(policy_type, 0) + 1
        
        return {
            'loaded': True,
            'total_vectors': self.index.ntotal,
            'metadata_entries': len(self.metadata),
            'dimension': self.dimension,
            'policy_types': policy_types,
            'index_path': self.index_path,
            'metadata_path': self.metadata_path
        }
