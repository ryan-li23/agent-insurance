"""Claim input data models."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple, Optional


@dataclass
class ClaimInput:
    """
    Input data for a claim submission.
    
    Attributes:
        case_id: Unique identifier for the claim
        date_of_loss: Date when the loss occurred
        fnol_text: First Notice of Loss narrative text
        fnol_files: List of (filename, content) tuples for FNOL documents
        photos: List of (filename, content) tuples for damage photos
        invoices: List of (filename, content) tuples for expense invoices
        scenario_hint: Optional hint for demo purposes (e.g., "burst_pipe", "seepage")
    """
    case_id: str
    date_of_loss: datetime
    fnol_text: str
    fnol_files: List[Tuple[str, bytes]]
    photos: List[Tuple[str, bytes]]
    invoices: List[Tuple[str, bytes]]
    scenario_hint: Optional[str] = None
