"""Decision and agent communication data models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class Objection:
    """
    An objection raised by the Compliance Reviewer.
    
    Attributes:
        type: Type of objection (e.g., "Inconsistent Narrative", "Invoice Scope Mismatch")
        status: Whether the objection is blocking or has been resolved
        message: Detailed explanation of the objection
        evidence_reference: Reference to specific evidence that triggered the objection
    """
    type: str
    status: str  # "Blocking" | "Resolved"
    message: str
    evidence_reference: Optional[str] = None


@dataclass
class Citation:
    """
    A citation to a specific policy clause.
    
    Attributes:
        policy: Policy type (e.g., "HO-3", "PAP")
        section: Section name or number
        page: Page number in the policy document
        text_excerpt: Relevant excerpt from the policy text
    """
    policy: str
    section: str
    page: int
    text_excerpt: str


@dataclass
class Decision:
    """
    Final coverage decision.
    
    Attributes:
        outcome: Coverage decision (Pay, Partial, Deny)
        rationale: Explanation of the decision
        citations: List of policy citations supporting the decision
        objections: List of objections raised during review
        sensitivity: Description of what evidence would change the decision
    """
    outcome: str  # "Pay" | "Partial" | "Deny"
    rationale: str
    citations: List[Citation] = field(default_factory=list)
    objections: List[Objection] = field(default_factory=list)
    sensitivity: str = ""


@dataclass
class AgentTurn:
    """
    A single turn in the agent conversation.
    
    Attributes:
        role: Agent role (curator, interpreter, reviewer, supervisor)
        content: Message content
        timestamp: When the turn occurred
        metadata: Additional metadata about the turn
    """
    role: str  # "curator" | "interpreter" | "reviewer" | "supervisor"
    content: str
    timestamp: datetime
    metadata: dict = field(default_factory=dict)
