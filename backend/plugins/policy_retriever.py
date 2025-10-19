"""Policy retrieval plugin for Semantic Kernel using FAISS vector store."""

import logging
from typing import List, Dict, Any, Optional

from semantic_kernel.functions import kernel_function

from ..storage.vector_store import PolicyVectorStore
from ..utils.bedrock_client import BedrockClient
from ..utils.errors import VectorStoreError

logger = logging.getLogger(__name__)


class PolicyRetrieverPlugin:
    """
    Semantic Kernel plugin for retrieving relevant policy clauses.
    
    Uses FAISS vector store for semantic similarity search over policy documents.
    Returns policy text with citations including section names and page numbers.
    """
    
    def __init__(
        self,
        vector_store: PolicyVectorStore,
        bedrock_client: BedrockClient
    ):
        """
        Initialize policy retriever plugin.
        
        Args:
            vector_store: Configured PolicyVectorStore instance
            bedrock_client: BedrockClient for generating query embeddings
        """
        self.vector_store = vector_store
        self.bedrock = bedrock_client
        logger.info("Initialized PolicyRetrieverPlugin")
    
    @kernel_function(
        name="retrieve_policy_clauses",
        description=(
            "Search policy documents for relevant clauses based on a query. "
            "Returns policy text with citations including section names, page numbers, "
            "and similarity scores. Use this to find coverage provisions, exclusions, "
            "and conditions related to claim evidence."
        )
    )
    async def retrieve_policy_clauses(
        self,
        query: str,
        top_k: int = 5,
        policy_type: Optional[str] = None,
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant policy clauses using semantic search.
        
        Args:
            query: Natural language query describing what to search for
            top_k: Number of top results to return (default: 5)
            policy_type: Optional filter by policy type (e.g., "HO-3", "PAP")
            min_score: Minimum similarity score threshold (0.0 to 1.0)
            
        Returns:
            List of policy clause dicts with keys:
                - policy_type: Policy type identifier
                - section: Section name or identifier
                - page: Page number in original document
                - text: Policy clause text
                - document_name: Source document filename
                - score: Similarity score (0.0 to 1.0)
                - citation: Formatted citation string
            
        Raises:
            VectorStoreError: If search fails
        """
        try:
            logger.info(
                f"Retrieving policy clauses: query='{query[:50]}...', "
                f"top_k={top_k}, policy_type={policy_type}"
            )
            
            # Generate query embedding
            query_embedding = await self.bedrock.generate_embedding(query)
            
            # Search vector store
            results = self.vector_store.search(
                query_embedding=query_embedding,
                top_k=top_k,
                policy_type=policy_type
            )
            
            # Filter by minimum score and format results
            formatted_results = []
            for result in results:
                score = result.get('score', 0.0)
                
                # Skip results below threshold
                if score < min_score:
                    continue
                
                # Format citation
                citation = self._format_citation(result)
                
                formatted_result = {
                    'policy_type': result.get('policy_type', 'Unknown'),
                    'section': result.get('section', 'Unknown Section'),
                    'page': result.get('page', 0),
                    'text': result.get('text', ''),
                    'document_name': result.get('document_name', 'Unknown'),
                    'score': score,
                    'citation': citation,
                    'chunk_id': result.get('chunk_id', '')
                }
                
                formatted_results.append(formatted_result)
            
            logger.info(
                f"Retrieved {len(formatted_results)} policy clauses "
                f"(filtered from {len(results)} results)"
            )
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to retrieve policy clauses: {str(e)}")
            
            # Wrap in VectorStoreError
            raise VectorStoreError.search_failed(
                query=query,
                error=e,
                fallback_action="Return empty results"
            )
    
    @kernel_function(
        name="retrieve_policy_by_section",
        description=(
            "Retrieve specific policy sections by name. "
            "Use this when you need to look up a specific section like 'Coverage A', "
            "'Exclusions', or 'Conditions'."
        )
    )
    async def retrieve_by_section(
        self,
        section_name: str,
        policy_type: Optional[str] = None,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Retrieve policy clauses from a specific section.
        
        Args:
            section_name: Name of the section to retrieve (e.g., "Coverage A", "Exclusions")
            policy_type: Optional filter by policy type
            top_k: Number of results to return
            
        Returns:
            List of policy clause dicts
        """
        # Use section name as query
        query = f"policy section {section_name}"
        
        return await self.retrieve_policy_clauses(
            query=query,
            top_k=top_k,
            policy_type=policy_type
        )
    
    @kernel_function(
        name="retrieve_exclusions",
        description=(
            "Retrieve policy exclusions relevant to a claim scenario. "
            "Use this to check if any exclusions apply to the claim."
        )
    )
    async def retrieve_exclusions(
        self,
        claim_description: str,
        policy_type: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant policy exclusions.
        
        Args:
            claim_description: Description of the claim or damage
            policy_type: Optional filter by policy type
            top_k: Number of results to return
            
        Returns:
            List of exclusion clause dicts
        """
        # Enhance query to focus on exclusions
        query = f"exclusions that apply to: {claim_description}"
        
        return await self.retrieve_policy_clauses(
            query=query,
            top_k=top_k,
            policy_type=policy_type
        )
    
    @kernel_function(
        name="retrieve_coverage_provisions",
        description=(
            "Retrieve coverage provisions relevant to a claim scenario. "
            "Use this to find what is covered under the policy."
        )
    )
    async def retrieve_coverage_provisions(
        self,
        claim_description: str,
        policy_type: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant coverage provisions.
        
        Args:
            claim_description: Description of the claim or damage
            policy_type: Optional filter by policy type
            top_k: Number of results to return
            
        Returns:
            List of coverage provision dicts
        """
        # Enhance query to focus on coverage
        query = f"coverage provisions for: {claim_description}"
        
        return await self.retrieve_policy_clauses(
            query=query,
            top_k=top_k,
            policy_type=policy_type
        )
    
    def _format_citation(self, result: Dict[str, Any]) -> str:
        """
        Format a citation string from search result.
        
        Args:
            result: Search result dict
            
        Returns:
            Formatted citation string
        """
        policy_type = result.get('policy_type', 'Unknown')
        section = result.get('section', 'Unknown Section')
        page = result.get('page', 0)
        document_name = result.get('document_name', 'Unknown')
        
        # Format: "HO-3 Policy, Section: Coverage A, Page 5 (policy_ho3.pdf)"
        citation = f"{policy_type} Policy, Section: {section}"
        
        if page > 0:
            citation += f", Page {page}"
        
        if document_name and document_name != 'Unknown':
            citation += f" ({document_name})"
        
        return citation
    
    @kernel_function(
        name="get_policy_context",
        description=(
            "Get comprehensive policy context for a claim by retrieving multiple "
            "relevant sections including coverage, exclusions, and conditions."
        )
    )
    async def get_policy_context(
        self,
        claim_description: str,
        policy_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive policy context for a claim.
        
        Args:
            claim_description: Description of the claim
            policy_type: Optional filter by policy type
            
        Returns:
            Dict with keys:
                - coverage_provisions: List of relevant coverage clauses
                - exclusions: List of relevant exclusion clauses
                - general_context: List of other relevant clauses
        """
        logger.info(f"Getting policy context for claim: {claim_description[:50]}...")
        
        try:
            # Retrieve coverage provisions
            coverage = await self.retrieve_coverage_provisions(
                claim_description=claim_description,
                policy_type=policy_type,
                top_k=3
            )
            
            # Retrieve exclusions
            exclusions = await self.retrieve_exclusions(
                claim_description=claim_description,
                policy_type=policy_type,
                top_k=3
            )
            
            # Retrieve general context
            general = await self.retrieve_policy_clauses(
                query=claim_description,
                policy_type=policy_type,
                top_k=3
            )
            
            context = {
                'coverage_provisions': coverage,
                'exclusions': exclusions,
                'general_context': general,
                'policy_type': policy_type or 'All Policies'
            }
            
            logger.info(
                f"Policy context retrieved: "
                f"coverage={len(coverage)}, exclusions={len(exclusions)}, "
                f"general={len(general)}"
            )
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to get policy context: {str(e)}")
            
            # Return empty context on error
            return {
                'coverage_provisions': [],
                'exclusions': [],
                'general_context': [],
                'policy_type': policy_type or 'All Policies',
                'error': str(e)
            }
