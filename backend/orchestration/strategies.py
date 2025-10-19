"""Custom selection and termination strategies for agent debate workflow."""

import logging
from typing import List

logger = logging.getLogger(__name__)


class DebateSelectionStrategy:
    """
    Custom selection strategy that enforces debate turn order.
    
    Turn Order:
    - Round 1: Curator -> Interpreter -> Reviewer
    - Round 2+: Reviewer -> Curator -> Interpreter
    """

    turn_count: int = 0
    round_number: int = 1
    turns_in_round: int = 0

    def __init__(self):
        logger.info("Initialized DebateSelectionStrategy")

    def next(self) -> str:
        """Return the next agent role to speak."""
        if self.round_number == 1:
            if self.turns_in_round == 0:
                next_role = "curator"
                logger.info("Round 1, Turn 1: Evidence Curator presents evidence")
            elif self.turns_in_round == 1:
                next_role = "interpreter"
                logger.info("Round 1, Turn 2: Policy Interpreter provides coverage decision")
            elif self.turns_in_round == 2:
                next_role = "reviewer"
                logger.info("Round 1, Turn 3: Compliance Reviewer evaluates decision")
            else:
                # Move to next round starting with reviewer
                self.round_number = 2
                self.turns_in_round = 0
                next_role = "reviewer"
                logger.info("Round 2, Turn 1: Compliance Reviewer continues review")
        else:
            # Round 2+: Curator -> Interpreter -> Reviewer
            # Reviewer objections from prior round drive clarification and revision
            if self.turns_in_round == 0:
                next_role = "curator"
                logger.info(f"Round {self.round_number}, Turn 1: Evidence Curator clarifies")
            elif self.turns_in_round == 1:
                next_role = "interpreter"
                logger.info(f"Round {self.round_number}, Turn 2: Policy Interpreter revises")
            elif self.turns_in_round == 2:
                next_role = "reviewer"
                logger.info(f"Round {self.round_number}, Turn 3: Compliance Reviewer re-evaluates")
            else:
                self.round_number += 1
                self.turns_in_round = 0
                next_role = "curator"
                logger.info(f"Round {self.round_number}, Turn 1: Evidence Curator clarifies")

        self.turn_count += 1
        self.turns_in_round += 1
        return next_role

    def reset(self):
        self.turn_count = 0
        self.round_number = 1
        self.turns_in_round = 0
        logger.info("DebateSelectionStrategy reset")

    def get_current_round(self) -> int:
        return self.round_number

    def get_turn_count(self) -> int:
        return self.turn_count


class ConsensusTerminationStrategy:
    """
    Termination strategy based on consensus (reviewer approval) or max rounds.
    """

    def __init__(self, max_rounds: int = 3):
        self.max_rounds = max_rounds
        self.current_round = 1
        logger.info(f"Initialized ConsensusTerminationStrategy with max_rounds={max_rounds}")

    def should_terminate(self, last_speaker_role: str, history_texts: List[str]) -> bool:
        """
        Decide whether to terminate based on reviewer approval, errors, or max rounds.
        - last_speaker_role: role string of the last speaker (curator/interpreter/reviewer)
        - history_texts: list of message contents (strings), ordered
        """
        # Max rounds check (increment on reviewer turn)
        if last_speaker_role == "reviewer":
            self.current_round += 1
        if self.current_round > self.max_rounds:
            logger.info(f"Terminating: Maximum rounds ({self.max_rounds}) reached")
            return True

        # Reviewer approval check
        if last_speaker_role == "reviewer" and history_texts:
            content = history_texts[-1].lower()
            approval_indicators = [
                '"approval": true',
                "approval is granted",
                "i approve",
                "decision is approved",
                "no blocking objections",
            ]
            if any(ind in content for ind in approval_indicators):
                logger.info("Terminating: Compliance Reviewer approved decision (consensus)")
                return True

        # Critical error indicators
        error_indicators = [
            "critical error",
            "unable to process",
            "processing failed",
            "fatal error",
            "cannot continue",
        ]
        recent = history_texts[-3:] if len(history_texts) >= 3 else history_texts
        for text in recent:
            if any(e in text.lower() for e in error_indicators):
                logger.warning("Terminating: Critical error detected in conversation")
                return True

        return False

    def reset(self):
        self.current_round = 1
        logger.info("ConsensusTerminationStrategy reset")

    def get_current_round(self) -> int:
        return self.current_round
