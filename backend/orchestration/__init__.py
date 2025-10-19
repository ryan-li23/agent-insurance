"""Orchestration layer for multi-agent collaboration."""

from .strategies import DebateSelectionStrategy, ConsensusTerminationStrategy
from .conversation import ConversationHistory
from .supervisor import SupervisorOrchestrator

__all__ = [
    "DebateSelectionStrategy",
    "ConsensusTerminationStrategy",
    "ConversationHistory",
    "SupervisorOrchestrator"
]
