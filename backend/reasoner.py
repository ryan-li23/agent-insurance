"""
Main reasoner entry point for claims processing.

This module provides the run_reasoner function that orchestrates the multi-agent
collaboration workflow using AWS Bedrock (no Semantic Kernel runtime dependency).
"""

from __future__ import annotations
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dotenv import load_dotenv

from .models.claim import ClaimInput
from .orchestration.supervisor import SupervisorOrchestrator
from .storage.vector_store import PolicyVectorStore
from .utils.config import Config
from .utils.bedrock_client import BedrockClient
from .utils.errors import ClaimsProcessingError, ErrorContext, ErrorType

# Load environment variables from .env file
load_dotenv()

# Initialize module-level logger
logger = logging.getLogger(__name__)

# Global instances (initialized on first use)
_config: Optional[Config] = None
_bedrock_client: Optional[BedrockClient] = None
_vector_store: Optional[PolicyVectorStore] = None
_supervisor: Optional[SupervisorOrchestrator] = None


def _initialize_system() -> None:
    """
    Initialize the system components (config, kernel, vector store, supervisor).
    
    This is called lazily on the first run_reasoner invocation to avoid
    initialization overhead when the module is imported.
    """
    global _config, _bedrock_client, _vector_store, _supervisor
    
    if _config is not None:
        # Already initialized
        return
    
    try:
        logger.info("Initializing claims reasoner system")
        
        # Load configuration
        _config = Config.load()
        logger.info(f"Configuration loaded: region={_config.aws_region}, model={_config.bedrock.model_id}")
        
        # Initialize Bedrock client (shared/main)
        _bedrock_client = BedrockClient(region=_config.aws_region)
        logger.info("Bedrock client initialized")
        
        # Initialize FAISS vector store
        _vector_store = PolicyVectorStore(
            index_path=_config.vector_store.index_path,
            metadata_path=_config.vector_store.metadata_path
        )
        
        # Load existing index or log warning if not found
        try:
            _vector_store.load_index()
            logger.info("FAISS index loaded successfully")
        except FileNotFoundError:
            logger.warning(
                "FAISS index not found. Policy retrieval will not work. "
                "Run 'python -m backend.storage.build_index' to create the index."
            )
        
        # Initialize Supervisor orchestrator
        _supervisor = SupervisorOrchestrator(max_rounds=_config.max_agent_rounds)
        logger.info("Supervisor orchestrator initialized")
        
        logger.info("System initialization complete")
        
    except Exception as e:
        logger.error(f"System initialization failed: {str(e)}", exc_info=True)
        raise ClaimsProcessingError(
            ErrorContext(
                error_type=ErrorType.INITIALIZATION_FAILED,
                message=f"Failed to initialize claims reasoner: {str(e)}",
                recoverable=False
            )
        )


def run_reasoner(
    fnol_text: str,
    date_of_loss_iso: str,
    photo_blobs: List[Tuple[str, bytes]],
    invoice_blobs: List[Tuple[str, bytes]],
    fnol_blobs: Optional[List[Tuple[str, bytes]]] = None,
    scenario_hint: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Process a claim using multi-agent collaboration.
    
    This is the main entry point called by the Streamlit UI. It orchestrates
    the Evidence Curator, Policy Interpreter, and Compliance Reviewer agents
    to analyze the claim and produce a coverage decision.
    
    Args:
        fnol_text: First Notice of Loss narrative text
        date_of_loss_iso: Date of loss in ISO format (YYYY-MM-DDTHH:MM:SS)
        photo_blobs: List of (filename, bytes) tuples for damage photos
        invoice_blobs: List of (filename, bytes) tuples for expense invoices
        fnol_blobs: Optional list of (filename, bytes) tuples for FNOL PDF files
        invoice_blobs: List of (filename, bytes) tuples for expense invoices
        scenario_hint: Optional hint for demo purposes (e.g., "case_a", "case_b", "case_c")
        
    Returns:
        Dictionary with keys:
            - turns: List of agent conversation turns (list of dicts with 'role' and 'content')
            - evidence: Extracted evidence data (list of dicts)
            - expense: Expense information (dict)
            - decision: Final coverage decision (dict with 'outcome' and 'rationale')
            - objections: List of objections raised (list of dicts)
            - citations: Policy citations (list of dicts)
            
    Raises:
        ClaimsProcessingError: If processing fails unrecoverably
    """
    try:
        # Initialize system on first use
        _initialize_system()
        
        # Generate case ID
        import uuid
        case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"
        
        logger.info(f"Processing claim {case_id}")
        
        # Parse date of loss
        try:
            date_of_loss = datetime.fromisoformat(date_of_loss_iso)
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid date format: {date_of_loss_iso}, using current time")
            date_of_loss = datetime.now()
        
        # Build ClaimInput
        claim_data = ClaimInput(
            case_id=case_id,
            date_of_loss=date_of_loss,
            fnol_text=fnol_text or "",
            fnol_files=fnol_blobs or [],
            photos=photo_blobs,
            invoices=invoice_blobs,
            scenario_hint=scenario_hint
        )
        
        # Run the supervisor orchestration
        logger.info("Starting supervisor orchestration")
        result = asyncio.run(_supervisor.run_collaboration(claim_data))
        
        logger.info(
            f"Claim {case_id} processed: outcome={result['decision']['outcome']}, "
            f"rounds={result['metadata']['rounds_completed']}"
        )
        
        # Transform result to match expected UI format
        return _format_for_ui(result)
        
    except ClaimsProcessingError:
        # Re-raise our custom errors
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error in run_reasoner: {str(e)}", exc_info=True)
        
        # Return partial results with error information
        return _error_response(str(e))


def _format_for_ui(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform supervisor result to match Streamlit UI expectations.
    
    The UI expects a specific format with keys: turns, evidence, expense,
    decision, objections, citations. This function ensures backward compatibility.
    
    Args:
        result: Result dictionary from supervisor
        
    Returns:
        Dictionary formatted for UI consumption
    """
    # Extract turns and format them for UI
    turns = []
    for turn in result.get("turns", []):
        turns.append({
            "role": turn.get("role", "unknown"),
            "content": turn.get("content", "")
        })
    
    # Extract decision
    decision_data = result.get("decision", {})
    decision = {
        "outcome": decision_data.get("outcome", "Deny"),
        "rationale": decision_data.get("rationale", "Unable to determine coverage"),
        "interpreter_recommendation": decision_data.get("interpreter_recommendation"),
        "interpreter_rationale": decision_data.get("interpreter_rationale"),
        "sensitivity": decision_data.get("sensitivity", "")
    }
    
    # Extract citations
    citations = []
    for citation in result.get("citations", []):
        citations.append({
            "policy": citation.get("policy", "Unknown"),
            "section": citation.get("section", "Unknown"),
            "page": citation.get("page", 0),
            "text_excerpt": citation.get("text_excerpt", "")
        })
    
    # Extract objections
    objections = []
    for objection in result.get("objections", []):
        objections.append({
            "type": objection.get("type", "Unknown"),
            "status": objection.get("status", "Unresolved"),
            "message": objection.get("message", "")
        })
    
    # Extract evidence and expense
    evidence = result.get("evidence", [])
    expense = result.get("expense", {})
    
    return {
        "turns": turns,
        "evidence": evidence,
        "expense": expense,
        "decision": decision,
        "objections": objections,
        "citations": citations,
        "metadata": result.get("metadata", {}),
        "resume_state": result.get("resume_state"),
    }


def continue_reasoner(
    resume_state: Dict[str, Any],
    fnol_text: str,
    date_of_loss_iso: str,
    support_photo_blobs: List[Tuple[str, bytes]],
    support_invoice_blobs: List[Tuple[str, bytes]],
    support_fnol_blobs: Optional[List[Tuple[str, bytes]]] = None,
) -> Dict[str, Any]:
    """Resume claims processing using prior state and optional supplemental files."""
    try:
        _initialize_system()

        # Use same case id if present
        import uuid
        case_id = resume_state.get("case_id") or f"CASE-{uuid.uuid4().hex[:8].upper()}"

        # Parse date
        try:
            date_of_loss = datetime.fromisoformat(date_of_loss_iso)
        except Exception:
            date_of_loss = datetime.now()

        # Build claim data for resume
        claim_data = ClaimInput(
            case_id=case_id,
            date_of_loss=date_of_loss,
            fnol_text=fnol_text or resume_state.get("claim", {}).get("fnol_text", ""),
            fnol_files=support_fnol_blobs or [],
            photos=support_photo_blobs or [],
            invoices=support_invoice_blobs or [],
            scenario_hint=resume_state.get("claim", {}).get("scenario_hint"),
        )

        # Run resume path
        result = asyncio.run(
            _supervisor.resume_collaboration(
                prev_state=resume_state,
                claim_data=claim_data,
                support_photos=support_photo_blobs or [],
                support_invoices=support_invoice_blobs or [],
                support_fnol=support_fnol_blobs or [],
            )
        )

        return _format_for_ui(result)

    except ClaimsProcessingError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in continue_reasoner: {str(e)}", exc_info=True)
        return _error_response(str(e))


def _error_response(error_message: str) -> Dict[str, Any]:
    """
    Create an error response in the format expected by the UI.
    
    Args:
        error_message: Description of the error
        
    Returns:
        Error response dictionary
    """
    return {
        "turns": [
            {
                "role": "supervisor",
                "content": f"Error: {error_message}"
            }
        ],
        "evidence": [],
        "expense": {},
        "decision": {
            "outcome": "Deny",
            "rationale": f"Processing error: {error_message}"
        },
        "objections": [
            {
                "type": "Processing Error",
                "status": "Blocking",
                "message": error_message
            }
        ],
        "citations": []
    }
