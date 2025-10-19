"""Evidence data models."""

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class Observation:
    """
    A single observation from damage analysis.
    
    Attributes:
        label: Type of damage observed (e.g., "water_damage", "mold")
        confidence: Confidence score (0.0 to 1.0)
        bbox: Bounding box in relative coordinates {x, y, w, h}
        location_text: Human-readable location description
        novelty: Whether damage appears new, old, or unclear
        severity: Severity level (minor, moderate, severe)
        evidence_notes: Additional notes about the observation
    """
    label: str
    confidence: float
    bbox: Dict[str, float]
    location_text: str
    novelty: str  # "new" | "old" | "unclear"
    severity: str  # "minor" | "moderate" | "severe"
    evidence_notes: List[str] = field(default_factory=list)


@dataclass
class ImageEvidence:
    """
    Evidence extracted from a single image.
    
    Attributes:
        image_name: Filename of the analyzed image
        observations: List of damage observations detected
        global_assessment: Overall assessment of the image
        chronology: Temporal information about the damage
    """
    image_name: str
    observations: List[Observation]
    global_assessment: Dict[str, Any] = field(default_factory=dict)
    chronology: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExpenseData:
    """
    Expense data extracted from invoices.
    
    Attributes:
        vendor: Vendor/contractor name
        invoice_number: Invoice identifier
        invoice_date: Date of invoice
        currency: Currency code (e.g., "USD")
        subtotal: Subtotal amount before tax
        tax: Tax amount
        total: Total amount including tax
        line_items: List of individual line items with descriptions and amounts
    """
    vendor: str
    invoice_number: str
    invoice_date: str
    currency: str
    subtotal: float
    tax: float
    total: float
    line_items: List[Dict[str, Any]] = field(default_factory=list)
