"""Conversation history management for agent collaboration."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional

from ..models.decision import AgentTurn

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Lightweight chat message used for Bedrock conversations."""
    role: str  # "user" | "assistant"
    content: str
    name: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


class ConversationHistory:
    """
    Manages conversation history for multi-agent collaboration.
    
    Tracks all agent turns with role, content, timestamp, and metadata.
    Also maintains a raw message list suitable for Bedrock Converse API.
    
    Attributes:
        turns: List of AgentTurn objects representing the conversation
        case_id: Optional case identifier for logging
    """
    
    def __init__(self, case_id: Optional[str] = None):
        """
        Initialize conversation history.
        
        Args:
            case_id: Optional case identifier for tracking
        """
        self.turns: List[AgentTurn] = []
        self.case_id = case_id
        self._message_history: List[Message] = []
        
        logger.info(f"Initialized ConversationHistory for case: {case_id or 'unknown'}")
    
    def add_turn(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentTurn:
        """
        Add a new turn to the conversation history.
        
        Args:
            role: Agent role (curator, interpreter, reviewer, supervisor)
            content: Message content
            metadata: Optional metadata about the turn
            
        Returns:
            The created AgentTurn object
        """
        turn = AgentTurn(
            role=role,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        self.turns.append(turn)
        
        logger.debug(
            f"Added turn {len(self.turns)} from {role}: "
            f"{content[:100] if content else 'empty'}..."
        )
        
        return turn
    
    def add_message(self, role: str, content: str, name: Optional[str] = None):
        """
        Add a message to the internal message history and create a corresponding AgentTurn.
        
        Args:
            role: One of "user" or "assistant" (Bedrock roles)
            content: Message content
            name: Optional agent name for assistant messages (e.g., "evidence-curator")
        """
        # Record raw message for Bedrock
        msg = Message(role=role, content=content, name=name, timestamp=datetime.now())
        self._message_history.append(msg)
        
        # Map to our standardized roles for AgentTurn tracking
        mapped_role = self._map_agent_name_to_role(name) if role == "assistant" else "supervisor"
        self.add_turn(
            role=mapped_role,
            content=content,
            metadata={
                "author_role": role,
                "agent_name": name or "Supervisor",
                "mapped_role": mapped_role,
            }
        )
    
    def get_message_history(self) -> List[Dict[str, Any]]:
        """
        Get the raw message history formatted for Bedrock Converse API.
        
        Returns:
            List of message dicts with 'role' and 'content'
        """
        formatted: List[Dict[str, Any]] = []
        for m in self._message_history:
            formatted.append({
                "role": m.role,
                "content": [{"text": m.content}],
            })
        return formatted
    
    def get_turns(self) -> List[AgentTurn]:
        """
        Get all conversation turns.
        
        Returns:
            List of AgentTurn objects
        """
        return self.turns.copy()
    
    def get_turns_by_role(self, role: str) -> List[AgentTurn]:
        """
        Get all turns from a specific agent role.
        
        Args:
            role: Agent role to filter by
            
        Returns:
            List of AgentTurn objects from that role
        """
        return [turn for turn in self.turns if turn.role == role]
    
    def get_latest_turn(self, role: Optional[str] = None) -> Optional[AgentTurn]:
        """
        Get the most recent turn, optionally filtered by role.
        
        Args:
            role: Optional agent role to filter by
            
        Returns:
            Most recent AgentTurn, or None if no turns exist
        """
        if not self.turns:
            return None
        
        if role:
            role_turns = self.get_turns_by_role(role)
            return role_turns[-1] if role_turns else None
        
        return self.turns[-1]
    
    def get_turn_count(self) -> int:
        """
        Get the total number of turns in the conversation.
        
        Returns:
            Number of turns
        """
        return len(self.turns)
    
    def get_turn_count_by_role(self, role: str) -> int:
        """
        Get the number of turns from a specific agent role.
        
        Args:
            role: Agent role to count
            
        Returns:
            Number of turns from that role
        """
        return len(self.get_turns_by_role(role))
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the conversation.
        
        Returns:
            Dictionary with conversation statistics
        """
        return {
            "case_id": self.case_id,
            "total_turns": self.get_turn_count(),
            "curator_turns": self.get_turn_count_by_role("curator"),
            "interpreter_turns": self.get_turn_count_by_role("interpreter"),
            "reviewer_turns": self.get_turn_count_by_role("reviewer"),
            "supervisor_turns": self.get_turn_count_by_role("supervisor"),
            "start_time": self.turns[0].timestamp if self.turns else None,
            "end_time": self.turns[-1].timestamp if self.turns else None,
            "duration_seconds": (
                (self.turns[-1].timestamp - self.turns[0].timestamp).total_seconds()
                if len(self.turns) >= 2 else 0
            )
        }
    
    def format_for_display(self) -> List[Dict[str, Any]]:
        """
        Format conversation history for UI display.
        
        Returns:
            List of dictionaries with formatted turn information
        """
        formatted_turns = []
        
        for i, turn in enumerate(self.turns, 1):
            formatted_turns.append({
                "turn_number": i,
                "role": turn.role,
                "agent_name": self._map_role_to_display_name(turn.role),
                "content": turn.content,
                "timestamp": turn.timestamp.isoformat(),
                "metadata": turn.metadata
            })
        
        return formatted_turns
    
    def export_to_dict(self) -> Dict[str, Any]:
        """
        Export the entire conversation history to a dictionary.
        
        Returns:
            Dictionary representation of the conversation
        """
        return {
            "case_id": self.case_id,
            "summary": self.get_conversation_summary(),
            "turns": [
                {
                    "role": turn.role,
                    "content": turn.content,
                    "timestamp": turn.timestamp.isoformat(),
                    "metadata": turn.metadata
                }
                for turn in self.turns
            ],
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "name": m.name,
                    "timestamp": m.timestamp.isoformat(),
                }
                for m in self._message_history
            ],
        }

    @staticmethod
    def from_export(data: Dict[str, Any]) -> "ConversationHistory":
        """Rehydrate a ConversationHistory from export_to_dict output."""
        case_id = data.get("case_id")
        hist = ConversationHistory(case_id=case_id)
        # restore messages first
        from datetime import datetime as _dt
        for md in data.get("messages", []):
            try:
                ts = md.get("timestamp")
                ts_dt = _dt.fromisoformat(ts) if ts else _dt.now()
            except Exception:
                ts_dt = _dt.now()
            msg = Message(
                role=md.get("role", "assistant"),
                content=md.get("content", ""),
                name=md.get("name"),
                timestamp=ts_dt,
            )
            hist._message_history.append(msg)
        # restore turns
        for td in data.get("turns", []):
            try:
                ts = td.get("timestamp")
                ts_dt = _dt.fromisoformat(ts) if ts else _dt.now()
            except Exception:
                ts_dt = _dt.now()
            hist.turns.append(
                AgentTurn(
                    role=td.get("role", "unknown"),
                    content=td.get("content", ""),
                    timestamp=ts_dt,
                    metadata=td.get("metadata", {}),
                )
            )
        return hist
    
    def clear(self):
        """Clear all conversation history."""
        self.turns.clear()
        self._message_history.clear()
        logger.info(f"Cleared conversation history for case: {self.case_id or 'unknown'}")
    
    def _map_agent_name_to_role(self, agent_name: Optional[str]) -> str:
        """
        Map agent name to role identifier, handling both kebab-case and title-case formats.
        
        Args:
            agent_name: Agent name from ChatMessageContent (e.g., "Evidence Curator" or "evidence-curator")
            
        Returns:
            Role identifier string
        """
        if not agent_name:
            return "unknown"
        
        name_lower = agent_name.lower().replace("-", " ").replace("_", " ")
        
        # Handle both "Evidence Curator" and "evidence-curator" formats
        if "curator" in name_lower or "evidence" in name_lower:
            return "curator"
        elif "interpreter" in name_lower or "policy" in name_lower:
            return "interpreter"
        elif "reviewer" in name_lower or "compliance" in name_lower:
            return "reviewer"
        elif "supervisor" in name_lower:
            return "supervisor"
        else:
            return "unknown"
    
    def _map_role_to_display_name(self, role: str) -> str:
        """
        Map role identifier to display name.
        
        Args:
            role: Role identifier
            
        Returns:
            Display name for the role
        """
        role_map = {
            "curator": "Evidence Curator",
            "interpreter": "Policy Interpreter",
            "reviewer": "Compliance Reviewer",
            "supervisor": "Supervisor",
            "unknown": "Unknown Agent"
        }
        
        return role_map.get(role, role)
    
    def __len__(self) -> int:
        """Return the number of turns in the conversation."""
        return len(self.turns)
    
    def __str__(self) -> str:
        """String representation of the conversation history."""
        return (
            f"ConversationHistory(case_id={self.case_id}, "
            f"turns={len(self.turns)})"
        )
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        summary = self.get_conversation_summary()
        return (
            f"ConversationHistory("
            f"case_id={self.case_id}, "
            f"total_turns={summary['total_turns']}, "
            f"curator={summary['curator_turns']}, "
            f"interpreter={summary['interpreter_turns']}, "
            f"reviewer={summary['reviewer_turns']})"
        )
