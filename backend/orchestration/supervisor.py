"""Supervisor orchestrator for multi-agent collaboration (Bedrock-based)."""

import json
import logging
from typing import Dict, Any, List, Optional

from ..agents.curator import EvidenceCuratorAgent
from ..agents.interpreter import PolicyInterpreterAgent
from ..agents.reviewer import ComplianceReviewerAgent
from ..models.claim import ClaimInput
from ..utils.response_formatter import ResponseFormatter
from .strategies import DebateSelectionStrategy, ConsensusTerminationStrategy
from .conversation import ConversationHistory

logger = logging.getLogger(__name__)


class SupervisorOrchestrator:
    """
    Supervisor orchestrator for coordinating multi-agent collaboration.
    
    Manages the debate workflow between Evidence Curator, Policy Interpreter,
    and Compliance Reviewer agents using custom selection and termination strategies.
    
    Attributes:
        curator: Evidence Curator agent
        interpreter: Policy Interpreter agent
        reviewer: Compliance Reviewer agent
        max_rounds: Maximum number of debate rounds
        conversation: Conversation history tracker
    """
    
    def __init__(self, max_rounds: int = 3):
        """
        Initialize the Supervisor orchestrator.
        
        Args:
            max_rounds: Maximum number of debate rounds (default: 3)
        """
        self.max_rounds = max_rounds
        
        # Initialize agents
        self.curator = EvidenceCuratorAgent()
        self.interpreter = PolicyInterpreterAgent()
        self.reviewer = ComplianceReviewerAgent()
        
        # Initialize conversation history
        self.conversation: Optional[ConversationHistory] = None
        
        logger.info(
            f"Initialized SupervisorOrchestrator with {max_rounds} max rounds"
        )
    
    async def run_collaboration(
        self,
        claim_data: ClaimInput
    ) -> Dict[str, Any]:
        """
        Execute the multi-agent debate workflow.
        
        This method orchestrates the collaboration between agents:
        1. Evidence Curator extracts and structures claim evidence
        2. Policy Interpreter maps evidence to policy clauses
        3. Compliance Reviewer challenges the interpretation
        4. Agents iterate until consensus or max rounds reached
        
        Args:
            claim_data: ClaimInput with uploaded files and claim information
            
        Returns:
            Dictionary containing:
                - decision: Final coverage decision
                - turns: List of agent conversation turns
                - evidence: Extracted evidence data
                - expense: Expense information
                - citations: Policy citations
                - objections: List of objections raised
                - metadata: Additional processing metadata
        """
        try:
            logger.info(f"Starting collaboration for claim: {claim_data.case_id}")
            
            # Initialize conversation history
            self.conversation = ConversationHistory(case_id=claim_data.case_id)
            
            # Build initial message for the curator
            initial_message = self._build_initial_message(claim_data)
            
            # Add initial message to conversation (user)
            self.conversation.add_message(role="user", content=initial_message, name="Supervisor")

            selection_strategy = DebateSelectionStrategy()
            termination_strategy = ConsensusTerminationStrategy(max_rounds=self.max_rounds)

            evidence_result: Optional[Dict[str, Any]] = None
            decision_result: Optional[Dict[str, Any]] = None
            review_result: Optional[Dict[str, Any]] = None

            logger.info("Starting multi-round agent collaboration")

            while True:
                next_role = selection_strategy.next()
                current_round = selection_strategy.get_current_round()

                if next_role == "curator":
                    logger.info("Evidence Curator turn")
                    if current_round == 1:
                        evidence_context = {"claim_data": claim_data}
                        evidence_result = await self.curator.invoke(evidence_context)
                        curator_response = self._format_evidence_response(evidence_result)
                    else:
                        clarification_pack = self._build_clarification_pack(evidence_result or {}, review_result)
                        if clarification_pack:
                            self.conversation.add_message(role="user", content=clarification_pack, name="Supervisor")
                        clarification_prompt = self._build_clarification_prompt(review_result)
                        curator_response = await self.curator.clarify_evidence(
                            question=clarification_prompt,
                            conversation_history=self.conversation.get_message_history(),
                        )
                    self.conversation.add_message(role="assistant", content=curator_response, name="evidence-curator")

                elif next_role == "interpreter":
                    logger.info("Policy Interpreter turn")
                    if current_round == 1:
                        interpreter_context = {
                            "evidence_data": evidence_result or {},
                            "claim_data": claim_data,
                            "conversation_history": self.conversation.get_message_history(),
                        }
                        decision_result = await self.interpreter.invoke(interpreter_context)
                    else:
                        feedback = self._build_revision_feedback(review_result)
                        decision_result = await self.interpreter.revise_decision(
                            feedback=feedback,
                            conversation_history=self.conversation.get_message_history(),
                        )
                    interpreter_response = self._format_decision_response(decision_result)
                    self.conversation.add_message(role="assistant", content=interpreter_response, name="policy-interpreter")

                elif next_role == "reviewer":
                    logger.info("Compliance Reviewer turn")
                    reviewer_context = {
                        "decision_data": decision_result or {},
                        "evidence_data": evidence_result or {},
                        "claim_data": claim_data,
                        "conversation_history": self.conversation.get_message_history(),
                    }
                    review_result = await self.reviewer.invoke(reviewer_context)
                    reviewer_response = self._format_review_response(review_result)
                    self.conversation.add_message(role="assistant", content=reviewer_response, name="compliance-reviewer")

                    approved = bool(review_result.get("approval", False))
                    blocking_count = sum(
                        1 for obj in review_result.get("objections", [])
                        if str(obj.get("status", "")).lower() == "blocking"
                    )

                    if current_round == 1 and blocking_count > 0 and not approved:
                        logger.info("Pausing after Round 1 due to blocking objections; awaiting user supplemental uploads")
                        paused_result = self._compile_decision()
                        paused_result.setdefault("metadata", {})
                        paused_result["metadata"]["paused_for_user"] = True
                        paused_result["metadata"]["recommendations"] = review_result.get("recommendations", [])
                        paused_result["resume_state"] = self._build_resume_state(
                            claim_data=claim_data,
                            evidence=evidence_result or {},
                            decision=decision_result or {},
                            review=review_result or {},
                        )
                        return paused_result

                    if approved or blocking_count == 0:
                        logger.info("Terminating: Reviewer approval achieved or no blocking objections remain")
                        break

                last_role = next_role
                if termination_strategy.should_terminate(
                    last_speaker_role=last_role,
                    history_texts=[t.content for t in self.conversation.turns],
                ):
                    break
            
            logger.info(f"Agent collaboration completed after {self.conversation.get_turn_count()} turns")
            
            # Debug: log conversation state before compiling
            logger.info(f"Total turns in conversation: {len(self.conversation.turns)}")
            logger.info(f"Turn order: {[f'{i+1}:{t.role}' for i, t in enumerate(self.conversation.turns)]}")
            
            # Verify first four expected order when available
            expected_prefix = ["supervisor", "curator", "interpreter", "reviewer"]
            actual_order = [t.role for t in self.conversation.turns][:4]
            if actual_order != expected_prefix[: len(actual_order)]:
                logger.warning(f"Unexpected initial turn order! Expected prefix: {expected_prefix}, Got: {actual_order}")
            
            # Compile final decision from conversation history
            final_decision = self._compile_decision()
            
            return final_decision
            
        except Exception as e:
            logger.error(f"Collaboration failed: {str(e)}", exc_info=True)
            
            # Return error decision
            return self._error_decision(claim_data.case_id, str(e))
    
    def _build_initial_message(self, claim_data: ClaimInput) -> str:
        """
        Build the initial message to start the collaboration.
        
        Args:
            claim_data: ClaimInput instance
            
        Returns:
            Formatted initial message
        """
        message_parts = [
            "=" * 60,
            "NEW CLAIM PROCESSING REQUEST",
            "=" * 60,
            "",
            f"CLAIM ID: {claim_data.case_id}",
            f"DATE OF LOSS: {claim_data.date_of_loss}",
            "",
            "FNOL NARRATIVE:",
            claim_data.fnol_text,
            "",
            "UPLOADED FILES:",
            f"- FNOL documents: {len(claim_data.fnol_files)}",
            f"- Photos: {len(claim_data.photos)}",
            f"- Invoices: {len(claim_data.invoices)}",
            "",
            "=" * 60,
            "WORKFLOW:",
            "=" * 60,
            "",
            "1. Evidence Curator: Extract and structure all claim evidence",
            "2. Policy Interpreter: Map evidence to policy clauses and provide coverage decision",
            "3. Compliance Reviewer: Challenge the decision and identify any issues",
            "4. Iterate until consensus is reached or max rounds completed",
            "",
            "Evidence Curator, please begin by processing the uploaded documents."
        ]
        
        return "\n".join(message_parts)
    
    def _compile_decision(self) -> Dict[str, Any]:
        """
        Compile the final decision from conversation history.
        
        Extracts evidence, coverage decision, citations, and objections
        from the agent conversation.
        
        Returns:
            Dictionary with compiled decision data
        """
        if not self.conversation:
            logger.error("No conversation history available")
            return self._error_decision("unknown", "No conversation history")
        
        logger.info("Compiling final decision from conversation history")
        
        # Extract data from agent turns (with enhanced parsing)
        evidence_data = self._extract_evidence_data()
        decision_data = self._extract_decision_data()
        review_data = self._extract_review_data()
        
        # Determine final outcome based on reviewer approval and blocking objections
        interpreter_outcome = decision_data.get("coverage_position", "Deny")
        reviewer_approval = review_data.get("approval", False)
        objections = review_data.get("objections", [])
        
        # Check if there are any blocking objections
        blocking_objections = [
            obj for obj in objections 
            if obj.get("status", "").lower() == "blocking"
        ]
        
        # Final outcome logic:
        # - If reviewer approves AND no blocking objections: use interpreter's decision
        # - If there are blocking objections: outcome should be "Pending" or "Deny"
        # - If reviewer doesn't approve: outcome should reflect that
        if reviewer_approval and not blocking_objections:
            final_outcome = interpreter_outcome
            final_rationale = decision_data.get("rationale", "Unable to determine coverage")
        elif blocking_objections:
            final_outcome = "Pending Investigation"
            blocking_reasons = [obj.get("message", obj.get("type", "Unknown")) for obj in blocking_objections]
            final_rationale = (
                f"The claim requires further investigation due to {len(blocking_objections)} blocking objection(s): "
                f"{'; '.join(blocking_reasons[:3])}. Original interpreter recommendation was '{interpreter_outcome}', "
                f"but compliance review identified issues that must be resolved before final determination."
            )
        else:
            final_outcome = "Pending Review"
            final_rationale = (
                f"The claim requires additional review. Original interpreter recommendation was '{interpreter_outcome}', "
                f"but compliance reviewer has not provided final approval."
            )
        
        # Build the final decision structure
        final_decision = {
            "case_id": self.conversation.case_id,
            "decision": {
                "outcome": final_outcome,
                "rationale": final_rationale,
                "sensitivity": decision_data.get("sensitivity", ""),
                "interpreter_recommendation": interpreter_outcome,
                "interpreter_rationale": decision_data.get("rationale", "")
            },
            "citations": decision_data.get("citations", []),
            "objections": objections,
            "evidence": evidence_data.get("evidence", []),
            "expense": evidence_data.get("expense", {}),
            "turns": self.conversation.format_for_display(),
            "metadata": {
                "conversation_summary": self.conversation.get_conversation_summary(),
                "approval": reviewer_approval,
                "blocking_objections_count": len(blocking_objections),
                "rounds_completed": self._get_rounds_completed(),
                "recommendations": review_data.get("recommendations", [])
            }
        }
        
        logger.info(
            f"Decision compiled: {final_decision['decision']['outcome']}, "
            f"approval={final_decision['metadata']['approval']}, "
            f"rounds={final_decision['metadata']['rounds_completed']}"
        )
        
        return final_decision

    def _build_resume_state(
        self,
        claim_data: ClaimInput,
        evidence: Dict[str, Any],
        decision: Dict[str, Any],
        review: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a minimal state package needed to resume collaboration later."""
        return {
            "case_id": self.conversation.case_id,
            "conversation": self.conversation.export_to_dict() if self.conversation else {},
            "evidence_result": evidence,
            "decision_result": decision,
            "review_result": review,
            "claim": {
                "date_of_loss": claim_data.date_of_loss.isoformat() if claim_data and claim_data.date_of_loss else None,
                "fnol_text": claim_data.fnol_text if claim_data else "",
                "scenario_hint": getattr(claim_data, "scenario_hint", None),
            },
        }

    def _merge_evidence(self, base: Dict[str, Any], delta: Dict[str, Any]) -> Dict[str, Any]:
        """Merge supplemental evidence into existing evidence dict."""
        if not base:
            return delta or {}
        base = json.loads(json.dumps(base))  # shallow copy via serialization
        delta = delta or {}

        images_map = {entry.get("image_name"): entry for entry in base.get("evidence", [])}
        for entry in delta.get("evidence", []) or []:
            key = entry.get("image_name")
            if not key:
                continue
            if key in images_map:
                existing = images_map[key]
                existing.setdefault("observations", [])
                existing["observations"].extend(entry.get("observations", []) or [])
                for field in ("global_assessment", "chronology"):
                    if entry.get(field):
                        existing[field] = entry[field]
            else:
                base.setdefault("evidence", []).append(entry)
                images_map[key] = entry

        base_expense = base.setdefault("expense", {})
        delta_expense = delta.get("expense") or {}
        if delta_expense:
            if delta_expense.get("total") is not None:
                try:
                    base_total = float(base_expense.get("total", 0) or 0)
                    delta_total = float(delta_expense.get("total", 0) or 0)
                    base_expense["total"] = max(base_total, delta_total)
                except Exception:
                    base_expense["total"] = delta_expense.get("total")
            base_expense.setdefault("line_items", [])
            base_expense["line_items"].extend(delta_expense.get("line_items", []) or [])
            for key in ("vendor", "invoice_number", "invoice_date", "currency", "subtotal", "tax"):
                if key not in base_expense and key in delta_expense:
                    base_expense[key] = delta_expense[key]

        if delta.get("fnol_summary"):
            summary = base.get("fnol_summary", "")
            combined = (summary + "\n\n" + delta.get("fnol_summary")).strip()
            base["fnol_summary"] = combined

        base_meta = base.setdefault("metadata", {})
        delta_meta = delta.get("metadata") or {}
        for key in ("processing_notes", "plugin_errors", "image_timestamps"):
            base_meta.setdefault(key, [])
            base_meta[key].extend(delta_meta.get(key, []) or [])

        return base

    async def resume_collaboration(
        self,
        prev_state: Dict[str, Any],
        claim_data: ClaimInput,
        support_photos: List[Any],
        support_invoices: List[Any],
        support_fnol: List[Any],
    ) -> Dict[str, Any]:
        """Resume collaboration after user supplies supplemental evidence or opts to continue without uploads."""
        logger.info("Resuming collaboration with supplemental inputs")

        try:
            self.conversation = ConversationHistory.from_export(prev_state.get("conversation", {}))
        except Exception:
            self.conversation = ConversationHistory(case_id=prev_state.get("case_id"))

        evidence_result = prev_state.get("evidence_result") or {}
        decision_result = prev_state.get("decision_result") or {}
        review_result = prev_state.get("review_result") or {}

        has_support = bool(support_photos or support_invoices or support_fnol)

        if has_support:
            support_claim = ClaimInput(
                case_id=claim_data.case_id,
                date_of_loss=claim_data.date_of_loss,
                fnol_text=claim_data.fnol_text,
                fnol_files=support_fnol,
                photos=support_photos,
                invoices=support_invoices,
                scenario_hint=claim_data.scenario_hint,
            )
            new_evidence = await self.curator.invoke({"claim_data": support_claim})
            curator_response = self._format_evidence_response(new_evidence)
            self.conversation.add_message(role="assistant", content=curator_response, name="evidence-curator")
            evidence_result = self._merge_evidence(evidence_result, new_evidence)

            interpreter_context = {
                "evidence_data": evidence_result,
                "claim_data": claim_data,
                "conversation_history": self.conversation.get_message_history(),
            }
            decision_result = await self.interpreter.invoke(interpreter_context)
            interpreter_response = self._format_decision_response(decision_result)
            self.conversation.add_message(role="assistant", content=interpreter_response, name="policy-interpreter")
        else:
            clarification_pack = self._build_clarification_pack(evidence_result, review_result)
            if clarification_pack:
                self.conversation.add_message(role="user", content=clarification_pack, name="Supervisor")

            clarification_prompt = self._build_clarification_prompt(review_result)
            curator_response = await self.curator.clarify_evidence(
                question=clarification_prompt,
                conversation_history=self.conversation.get_message_history(),
            )
            self.conversation.add_message(role="assistant", content=curator_response, name="evidence-curator")

            feedback = self._build_revision_feedback(review_result)
            decision_result = await self.interpreter.revise_decision(
                feedback=feedback,
                conversation_history=self.conversation.get_message_history(),
            )
            interpreter_response = self._format_decision_response(decision_result)
            self.conversation.add_message(role="assistant", content=interpreter_response, name="policy-interpreter")

        reviewer_context = {
            "decision_data": decision_result or {},
            "evidence_data": evidence_result or {},
            "claim_data": claim_data,
            "conversation_history": self.conversation.get_message_history(),
        }
        review_result = await self.reviewer.invoke(reviewer_context)
        reviewer_response = self._format_review_response(review_result)
        self.conversation.add_message(role="assistant", content=reviewer_response, name="compliance-reviewer")

        final_decision = self._compile_decision()
        return final_decision

    def _build_clarification_pack(
        self,
        evidence_data: Dict[str, Any],
        review_result: Optional[Dict[str, Any]],
    ) -> str:
        """Create a structured clarification pack summarizing evidence vs. objections."""
        if not evidence_data:
            return ""

        lines: List[str] = [
            "=" * 68,
            "EVIDENCE CLARIFICATION PACK",
            "=" * 68,
        ]

        images = evidence_data.get("evidence", []) or []
        if images:
            lines.append("\n1. Evidence Overview")
            for img in images:
                name = img.get("image_name", "(unnamed)")
                observations = img.get("observations", []) or []
                lines.append(f"  - {name}: {len(observations)} observations recorded")
                for obs in observations[:3]:
                    label = obs.get("label", "unknown")
                    severity = obs.get("severity", "?")
                    novelty = obs.get("novelty", "?")
                    location = obs.get("location_text", "unspecified location")
                    conf = obs.get("confidence", 0)
                    try:
                        conf = float(conf)
                    except Exception:
                        conf = 0.0
                    lines.append(
                        f"     - {label} ({severity}, {novelty}) at {location} — confidence {conf:.2f}"
                    )
                if len(observations) > 3:
                    lines.append(f"     - (+{len(observations) - 3} additional observations)")

        expense = evidence_data.get("expense") or {}
        if expense:
            lines.append("\n2. Invoice Reconciliation")
            vendor = expense.get("vendor", "Unknown vendor")
            total = expense.get("total")
            try:
                total_fmt = f"${float(total):,.2f}" if total is not None else "N/A"
            except Exception:
                total_fmt = str(total)
            lines.append(f"  - Vendor: {vendor}")
            lines.append(f"  - Total: {total_fmt}")
            line_items = expense.get("line_items", []) or []
            for li in line_items[:5]:
                desc = li.get("description", "Item")
                amount = li.get("amount")
                try:
                    amount_fmt = f"${float(amount):,.2f}" if amount is not None else "N/A"
                except Exception:
                    amount_fmt = str(amount)
                lines.append(f"     - {desc} — {amount_fmt}")
            if len(line_items) > 5:
                lines.append(f"     - (+{len(line_items) - 5} additional line items)")

        metadata = evidence_data.get("metadata", {}) or {}
        timestamps = metadata.get("image_timestamps", []) or []
        notes = metadata.get("processing_notes", []) or []
        if timestamps or notes:
            lines.append("\n3. Timeline & Metadata")
            if timestamps:
                lines.append("  - Image timestamps:")
                for ts in timestamps[:5]:
                    lines.append(f"     - {ts}")
                if len(timestamps) > 5:
                    lines.append(f"     - (+{len(timestamps) - 5} more timestamps)")
            if notes:
                lines.append("  - Processing notes:")
                for note in notes[:5]:
                    lines.append(f"     - {note}")
                if len(notes) > 5:
                    lines.append(f"     - (+{len(notes) - 5} additional notes)")

        objections = (review_result or {}).get("objections", []) if review_result else []
        if objections:
            lines.append("\n4. Current Reviewer Objections")
            for obj in objections:
                lines.append(
                    f"  - [{obj.get('status','?').title()}] {obj.get('type','Objection')}: {obj.get('message','')}"
                )

        recs = (review_result or {}).get("recommendations", []) if review_result else []
        if recs:
            lines.append("\n5. Reviewer Recommendations")
            for rec in recs:
                lines.append(f"  - [ ] {rec}")

        return "\n".join(lines).strip()

    def _build_clarification_prompt(self, review_result: Optional[Dict[str, Any]]) -> str:
        """Build a clarification prompt for the curator based on reviewer objections."""
        if not review_result:
            return (
                "Please provide any additional clarifications or details about the evidence "
                "that could help address potential reviewer concerns."
            )
        objections = review_result.get("objections", []) or []
        if not objections:
            return (
                "Reviewer raised no specific objections. Provide brief clarifications to strengthen the evidence, "
                "and call out any confidence caveats."
            )
        lines = ["Reviewer objections to address:"]
        for idx, obj in enumerate(objections, 1):
            status = obj.get("status", "").title()
            lines.append(f"{idx}. [{status}] {obj.get('type','Objection')}: {obj.get('message','')}")
        lines.append(
            "\nFor each item above, clarify the relevant observations, timestamps, and any context that resolves the concern."
        )
        return "\n".join(lines)

    def _build_revision_feedback(self, review_result: Optional[Dict[str, Any]]) -> str:
        """Build feedback text for interpreter to revise decision based on reviewer objections."""
        if not review_result:
            return (
                "Please re-evaluate the policy decision, ensuring citations are precise and rationale is clear. "
                "Return a complete JSON decision."
            )
        objections = review_result.get("objections", []) or []
        approval = review_result.get("approval", False)
        summary = review_result.get("summary", "")
        header = [
            f"Reviewer approval: {approval}",
            f"Reviewer summary: {summary}",
            "Objections to address:",
        ]
        for idx, obj in enumerate(objections, 1):
            status = obj.get("status", "").title()
            header.append(f"{idx}. [{status}] {obj.get('type','Objection')}: {obj.get('message','')}")
        header.append(
            "\nRevise the coverage decision accordingly. If objections are resolved, update the rationale and coverage details. "
            "Return a complete JSON decision."
        )
        return "\n".join(header)
    
    def _extract_evidence_data(self) -> Dict[str, Any]:
        """
        Extract evidence data from curator's turns using ResponseFormatter with fallback.
        
        Returns:
            Dictionary with evidence and expense data
        """
        # Get curator turns using standardized role mapping
        curator_turns = self.conversation.get_turns_by_role("curator")
        
        if not curator_turns:
            logger.warning("No curator turns found")
            print("Could not extract evidence data from any curator turns")
            return {"evidence": [], "expense": {}}
        
        # Get the most recent curator turn with evidence
        for turn in reversed(curator_turns):
            try:
                content = turn.content
                if not content:
                    logger.debug("Empty content in curator turn")
                    continue
                
                logger.debug(f"Curator content preview: {content[:200]}...")
                print(f"DEBUG: Processing curator turn with content length: {len(content)}")
                
                # Method 1: Try ResponseFormatter first
                logger.debug("Attempting JSON extraction using ResponseFormatter")
                evidence_data = ResponseFormatter.extract_json_from_response(content)
                
                if evidence_data and ("evidence" in evidence_data or "expense" in evidence_data or "fnol_summary" in evidence_data):
                    logger.info("Successfully extracted evidence data using ResponseFormatter")
                    logger.debug(f"Extracted keys: {list(evidence_data.keys())}")
                    print(f"DEBUG: Successfully extracted evidence using ResponseFormatter")
                    return evidence_data
                else:
                    logger.debug("ResponseFormatter extraction failed or returned invalid structure")
                    print(f"DEBUG: ResponseFormatter failed, extracted: {evidence_data}")
                
                # Method 2: Fallback to manual JSON extraction with brace counting
                logger.debug("ResponseFormatter failed, trying manual extraction")
                evidence_data = self._manual_json_extraction(content)
                
                if evidence_data and ("evidence" in evidence_data or "expense" in evidence_data or "fnol_summary" in evidence_data):
                    logger.info("Successfully extracted evidence data using manual extraction")
                    logger.debug(f"Extracted keys: {list(evidence_data.keys())}")
                    print(f"DEBUG: Successfully extracted evidence using manual extraction")
                    return evidence_data
                else:
                    logger.debug("Manual extraction failed or returned invalid structure")
                    print(f"DEBUG: Manual extraction failed, extracted: {evidence_data}")
                
                # Method 3: Try to find JSON-like patterns in the response
                logger.debug("Trying pattern-based extraction")
                evidence_data = self._pattern_based_extraction(content, "evidence")
                
                if evidence_data:
                    logger.info("Successfully extracted evidence data using pattern-based extraction")
                    print(f"DEBUG: Successfully extracted evidence using pattern-based extraction")
                    return evidence_data
                
                logger.debug("No valid evidence data found in this turn")
                print(f"DEBUG: No valid evidence data found in turn")
            
            except Exception as e:
                logger.error(f"Failed to parse evidence from turn: {str(e)}")
                logger.error(f"Content preview (first 200 chars): {content[:200] if content else 'EMPTY'}")
                print(f"DEBUG: Exception parsing evidence: {str(e)}")
                continue
        
        logger.warning("Could not extract evidence data from any curator turns")
        print("Could not extract evidence data from any curator turns")
        return {
            "evidence": [],
            "expense": {
                "vendor": "Unknown",
                "invoice_number": "N/A",
                "invoice_date": "",
                "currency": "USD",
                "subtotal": 0.0,
                "tax": 0.0,
                "total": 0.0,
                "line_items": []
            },
            "fnol_summary": "Unable to extract evidence data",
            "metadata": {
                "processing_notes": ["Failed to parse evidence from curator turns"],
                "plugin_errors": []
            }
        }
    
    def _extract_decision_data(self) -> Dict[str, Any]:
        """
        Extract coverage decision from interpreter's turns using ResponseFormatter with fallback.
        
        Returns:
            Dictionary with coverage decision and citations
        """
        # Get interpreter turns using standardized role mapping
        interpreter_turns = self.conversation.get_turns_by_role("interpreter")
        
        if not interpreter_turns:
            logger.warning("No interpreter turns found")
            print("Could not extract decision data from any interpreter turns")
            return {
                "coverage_position": "Deny",
                "rationale": "No policy interpretation available",
                "citations": [],
                "sensitivity": ""
            }
        
        # Get the most recent interpreter turn with a decision
        for turn in reversed(interpreter_turns):
            try:
                content = turn.content
                if not content:
                    logger.debug("Empty content in interpreter turn")
                    continue
                
                logger.debug(f"Interpreter content preview: {content[:200]}...")
                print(f"DEBUG: Processing interpreter turn with content length: {len(content)}")
                
                # Method 1: Try ResponseFormatter first
                logger.debug("Attempting JSON extraction using ResponseFormatter")
                decision_data = ResponseFormatter.extract_json_from_response(content)
                
                if decision_data and "coverage_position" in decision_data:
                    logger.info("Successfully extracted decision data using ResponseFormatter")
                    logger.debug(f"Coverage position: {decision_data.get('coverage_position')}")
                    print(f"DEBUG: Successfully extracted decision using ResponseFormatter")
                    return decision_data
                else:
                    logger.debug("ResponseFormatter extraction failed or returned invalid structure")
                    print(f"DEBUG: ResponseFormatter failed, extracted: {decision_data}")
                
                # Method 2: Fallback to manual JSON extraction with brace counting
                logger.debug("ResponseFormatter failed, trying manual extraction")
                decision_data = self._manual_json_extraction(content)
                
                if decision_data and "coverage_position" in decision_data:
                    logger.info("Successfully extracted decision data using manual extraction")
                    logger.debug(f"Coverage position: {decision_data.get('coverage_position')}")
                    print(f"DEBUG: Successfully extracted decision using manual extraction")
                    return decision_data
                else:
                    logger.debug("Manual extraction failed or returned invalid structure")
                    print(f"DEBUG: Manual extraction failed, extracted: {decision_data}")
                
                # Method 3: Try to find JSON-like patterns in the response
                logger.debug("Trying pattern-based extraction")
                decision_data = self._pattern_based_extraction(content, "decision")
                
                if decision_data:
                    logger.info("Successfully extracted decision data using pattern-based extraction")
                    print(f"DEBUG: Successfully extracted decision using pattern-based extraction")
                    return decision_data
                
                logger.debug("No valid decision data found in this turn")
                print(f"DEBUG: No valid decision data found in turn")
            
            except Exception as e:
                logger.error(f"Failed to parse decision from turn: {str(e)}")
                logger.error(f"Content preview (first 200 chars): {content[:200] if content else 'EMPTY'}")
                print(f"DEBUG: Exception parsing decision: {str(e)}")
                continue
        
        logger.warning("Could not extract decision data from any interpreter turns")
        print("Could not extract decision data from any interpreter turns")
        return {
            "coverage_position": "Deny",
            "rationale": "Unable to parse policy interpretation from agent responses",
            "citations": [],
            "sensitivity": "Additional evidence or clearer agent responses needed",
            "coverage_details": {
                "covered_items": [],
                "excluded_items": [],
                "limitations": []
            }
        }
    
    def _extract_review_data(self) -> Dict[str, Any]:
        """
        Extract review findings from reviewer's turns using ResponseFormatter with fallback.
        
        Returns:
            Dictionary with objections and approval status
        """
        # Get reviewer turns using standardized role mapping
        reviewer_turns = self.conversation.get_turns_by_role("reviewer")
        
        if not reviewer_turns:
            logger.warning("No reviewer turns found")
            return {
                "objections": [],
                "approval": False,
                "summary": "No compliance review available"
            }
        
        # Get the most recent reviewer turn with a review
        for turn in reversed(reviewer_turns):
            try:
                content = turn.content
                if not content:
                    logger.debug("Empty content in reviewer turn")
                    continue
                
                logger.debug(f"Reviewer content preview: {content[:200]}...")
                
                # Method 1: Try ResponseFormatter first
                logger.debug("Attempting JSON extraction using ResponseFormatter")
                review_data = ResponseFormatter.extract_json_from_response(content)
                
                if review_data and ("objections" in review_data or "approval" in review_data):
                    logger.info("Successfully extracted review data using ResponseFormatter")
                    logger.debug(f"Approval: {review_data.get('approval')}, Objections: {len(review_data.get('objections', []))}")
                    return review_data
                else:
                    logger.debug("ResponseFormatter extraction failed or returned invalid structure")
                
                # Method 2: Fallback to manual JSON extraction with brace counting
                logger.debug("ResponseFormatter failed, trying manual extraction")
                review_data = self._manual_json_extraction(content)
                
                if review_data and ("objections" in review_data or "approval" in review_data):
                    logger.info("Successfully extracted review data using manual extraction")
                    logger.debug(f"Approval: {review_data.get('approval')}, Objections: {len(review_data.get('objections', []))}")
                    return review_data
                else:
                    logger.debug("Manual extraction failed or returned invalid structure")
                
                logger.debug("No valid review data found in this turn")
            
            except Exception as e:
                logger.error(f"Failed to parse review from turn: {str(e)}")
                logger.error(f"Content preview (first 200 chars): {content[:200] if content else 'EMPTY'}")
                continue
        
        logger.warning("Could not extract review data from any reviewer turns")
        return {
            "objections": [
                {
                    "type": "Parsing Error",
                    "status": "Blocking",
                    "message": "Unable to parse compliance review from agent responses",
                    "evidence_reference": None
                }
            ],
            "approval": False,
            "summary": "Unable to parse compliance review from agent responses",
            "recommendations": []
        }
    
    def _manual_json_extraction(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Manual JSON extraction using brace counting as fallback.
        
        Args:
            content: Text content to extract JSON from
            
        Returns:
            Parsed JSON dictionary or None if extraction fails
        """
        try:
            # Find JSON block (look for outermost braces)
            start_idx = content.find('{')
            if start_idx == -1:
                logger.debug("No opening brace found in content")
                return None
            
            # Find matching closing brace by counting braces
            brace_count = 0
            end_idx = -1
            in_string = False
            escape_next = False
            
            for i in range(start_idx, len(content)):
                char = content[i]
                
                if escape_next:
                    escape_next = False
                    continue
                
                if char == '\\':
                    escape_next = True
                    continue
                
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                
                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i
                            break
            
            if end_idx != -1:
                json_text = content[start_idx:end_idx + 1]
                logger.debug(f"Manual extraction found JSON of length: {len(json_text)}")
                
                # Try to clean up common JSON issues
                json_text = self._clean_json_text(json_text)
                
                return json.loads(json_text)
            else:
                logger.debug("No matching closing brace found")
                return None
        
        except (json.JSONDecodeError, Exception) as e:
            logger.debug(f"Manual JSON extraction failed: {str(e)}")
            return None
    
    def _clean_json_text(self, json_text: str) -> str:
        """
        Clean up common JSON formatting issues.
        
        Args:
            json_text: Raw JSON text
            
        Returns:
            Cleaned JSON text
        """
        # Remove trailing commas before closing braces/brackets
        import re
        json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
        
        # Fix common quote issues
        json_text = json_text.replace('"', '"').replace('"', '"')
        json_text = json_text.replace(''', "'").replace(''', "'")
        
        return json_text
    
    def _pattern_based_extraction(self, content: str, data_type: str) -> Optional[Dict[str, Any]]:
        """
        Pattern-based extraction for when JSON parsing fails.
        
        Args:
            content: Text content to extract from
            data_type: Type of data to extract ("evidence" or "decision")
            
        Returns:
            Extracted data dictionary or None if extraction fails
        """
        try:
            if data_type == "evidence":
                return self._extract_evidence_patterns(content)
            elif data_type == "decision":
                return self._extract_decision_patterns(content)
            else:
                return None
        except Exception as e:
            logger.debug(f"Pattern-based extraction failed: {str(e)}")
            return None
    
    def _extract_evidence_patterns(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Extract evidence data using text patterns when JSON parsing fails.
        
        Args:
            content: Text content to extract from
            
        Returns:
            Evidence data dictionary or None
        """
        import re
        
        # Look for evidence-related patterns
        evidence_data = {
            "evidence": [],
            "expense": {},
            "fnol_summary": "",
            "metadata": {
                "processing_notes": ["Extracted using pattern matching"],
                "plugin_errors": []
            }
        }
        
        # Try to find image names and observations
        image_pattern = r'(?:image_name|filename|photo).*?["\']([^"\']+\.(jpg|jpeg|png|gif))["\']'
        image_matches = re.findall(image_pattern, content, re.IGNORECASE)
        
        if image_matches:
            for match in image_matches:
                image_name = match[0]
                evidence_data["evidence"].append({
                    "image_name": image_name,
                    "observations": [],
                    "global_assessment": {},
                    "chronology": {}
                })
        
        # Try to find expense information
        vendor_pattern = r'(?:vendor|company).*?["\']([^"\']+)["\']'
        vendor_match = re.search(vendor_pattern, content, re.IGNORECASE)
        if vendor_match:
            evidence_data["expense"]["vendor"] = vendor_match.group(1)
        
        total_pattern = r'(?:total|amount).*?(\d+\.?\d*)'
        total_match = re.search(total_pattern, content, re.IGNORECASE)
        if total_match:
            evidence_data["expense"]["total"] = float(total_match.group(1))
        
        return evidence_data if evidence_data["evidence"] or evidence_data["expense"] else None
    
    def _extract_decision_patterns(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Extract decision data using text patterns when JSON parsing fails.
        
        Args:
            content: Text content to extract from
            
        Returns:
            Decision data dictionary or None
        """
        import re
        
        # Look for coverage position
        coverage_pattern = r'(?:coverage_position|decision|outcome).*?["\']?(Pay|Partial|Deny)["\']?'
        coverage_match = re.search(coverage_pattern, content, re.IGNORECASE)
        
        if coverage_match:
            return {
                "coverage_position": coverage_match.group(1),
                "rationale": "Extracted using pattern matching",
                "citations": [],
                "sensitivity": "Pattern-based extraction used",
                "coverage_details": {
                    "covered_items": [],
                    "excluded_items": [],
                    "limitations": []
                }
            }
        
        return None
    
    def _get_rounds_completed(self) -> int:
        """
        Calculate the number of rounds completed.
        
        Returns:
            Number of completed rounds
        """
        # Each round has 3 turns (curator, interpreter, reviewer)
        total_turns = self.conversation.get_turn_count()
        
        # Subtract 1 for the initial supervisor message
        agent_turns = max(0, total_turns - 1)
        
        # Calculate rounds (round up for partial rounds)
        rounds = (agent_turns + 2) // 3
        
        return rounds
    
    def _error_decision(
        self,
        case_id: str,
        error_message: str
    ) -> Dict[str, Any]:
        """
        Create an error decision structure.
        
        Args:
            case_id: Case identifier
            error_message: Error description
            
        Returns:
            Error decision dictionary
        """
        return {
            "case_id": case_id,
            "decision": {
                "outcome": "Deny",
                "rationale": f"Processing error: {error_message}",
                "sensitivity": "Unable to process claim"
            },
            "citations": [],
            "objections": [
                {
                    "type": "Processing Error",
                    "status": "Blocking",
                    "message": error_message,
                    "evidence_reference": None
                }
            ],
            "evidence": [],
            "expense": {},
            "turns": [],
            "metadata": {
                "conversation_summary": {},
                "approval": False,
                "rounds_completed": 0,
                "error": error_message
            }
        }
    
    def get_conversation_history(self) -> Optional[ConversationHistory]:
        """
        Get the conversation history from the last collaboration.
        
        Returns:
            ConversationHistory instance, or None if no collaboration has run
        """
        return self.conversation
    
    def reset(self):
        """Reset the orchestrator state for a new collaboration."""
        self.conversation = None
        logger.info("SupervisorOrchestrator reset")
    
    def _format_evidence_response(self, evidence_result: Dict[str, Any]) -> str:
        """
        Format evidence curator result for conversation display.
        
        Args:
            evidence_result: Result from curator.invoke()
            
        Returns:
            Formatted string for conversation
        """
        try:
            # Build a concise, human-readable summary with optional JSON details
            images = evidence_result.get("evidence", []) or []
            expense = evidence_result.get("expense", {}) or {}
            evidence_count = len(images)
            total_amt = expense.get("total")
            try:
                total_fmt = f"${float(total_amt):,.2f}" if total_amt is not None else "N/A"
            except Exception:
                total_fmt = str(total_amt)

            # Summarize top observations per image (up to 3 images, 3 obs each)
            image_lines = []
            for img in images[:3]:
                name = img.get("image_name", "(unnamed)")
                obs = img.get("observations", []) or []
                inner = []
                for o in obs[:3]:
                    label = o.get("label", "finding")
                    sev = o.get("severity", "?")
                    loc = o.get("location_text", "location unknown")
                    inner.append(f"- {label} ({sev}) at {loc}")
                if not inner:
                    inner.append("- No discrete findings extracted")
                image_lines.append("  • " + name + "\n    " + "\n    ".join(inner))
            if evidence_count > 3:
                image_lines.append(f"  • (+{evidence_count - 3} additional image(s))")

            # Build message
            parts = [
                "Evidence Curator – Summary",
                "",
                f"• Images analyzed: {evidence_count}",
                f"• Expense total: {total_fmt}",
            ]
            if image_lines:
                parts.append("")
                parts.append("Top Findings:")
                parts.extend(image_lines)

            # Append collapsible JSON block for power users
            formatted_json = ResponseFormatter.format_json_response(evidence_result)
            parts.append("")
            parts.append("<details><summary>Show full evidence JSON</summary>")
            parts.append("<pre>" + formatted_json.replace("<", "&lt;") + "</pre>")
            parts.append("</details>")
            parts.append("")
            parts.append("This evidence is now ready for policy interpretation.")

            return "\n".join(parts)
            
        except Exception as e:
            logger.error(f"Failed to format evidence response: {str(e)}")
            return f"Evidence Curator completed processing. Raw result: {str(evidence_result)}"
    
    def _format_decision_response(self, decision_result: Dict[str, Any]) -> str:
        """
        Format policy interpreter result for conversation display.
        
        Args:
            decision_result: Result from interpreter.invoke()
            
        Returns:
            Formatted string for conversation
        """
        try:
            position = decision_result.get("coverage_position", "Unknown")
            rationale = decision_result.get("rationale", "No rationale provided")
            citations = decision_result.get("citations", []) or []

            # Build citation bullets (up to 5)
            cit_lines = []
            for c in citations[:5]:
                policy = c.get("policy", "?")
                section = c.get("section", "?")
                page = c.get("page", "?")
                text_excerpt = c.get("text_excerpt", "")
                if text_excerpt and len(text_excerpt) > 160:
                    text_excerpt = text_excerpt[:160] + "…"
                cit_lines.append(f"- {policy} — {section} (p.{page})\n  \"{text_excerpt}\"")
            if len(citations) > 5:
                cit_lines.append(f"- (+{len(citations) - 5} additional citation(s))")

            parts = [
                "Policy Interpreter – Coverage Decision",
                "",
                f"• Coverage Position: {position}",
                "",
                "Rationale:",
                rationale,
            ]
            if cit_lines:
                parts.append("")
                parts.append("Citations:")
                parts.extend(cit_lines)

            formatted_json = ResponseFormatter.format_json_response(decision_result)
            parts.append("")
            parts.append("<details><summary>Show full decision JSON</summary>")
            parts.append("<pre>" + formatted_json.replace("<", "&lt;") + "</pre>")
            parts.append("</details>")
            parts.append("")
            parts.append("This decision is now ready for compliance review.")

            return "\n".join(parts)
            
        except Exception as e:
            logger.error(f"Failed to format decision response: {str(e)}")
            return f"Policy Interpreter completed analysis. Raw result: {str(decision_result)}"
    
    def _format_review_response(self, review_result: Dict[str, Any]) -> str:
        """
        Format compliance reviewer result for conversation display.
        
        Args:
            review_result: Result from reviewer.invoke()
            
        Returns:
            Formatted string for conversation
        """
        try:
            approval = review_result.get("approval", False)
            objections = review_result.get("objections", []) or []
            blocking_count = sum(1 for o in objections if str(o.get("status", "")).lower() == "blocking")
            summary = review_result.get("summary", "Review completed")
            recs = review_result.get("recommendations", []) or []

            # Objection bullets
            obj_lines = []
            for o in objections[:8]:
                status = o.get("status", "").title()
                typ = o.get("type", "Objection")
                msg = o.get("message", "")
                obj_lines.append(f"- [{status}] {typ}: {msg}")
            if len(objections) > 8:
                obj_lines.append(f"- (+{len(objections) - 8} additional objection(s))")

            parts = [
                "Compliance Reviewer – Assessment",
                "",
                f"• Approval Status: {'APPROVED' if approval else 'NOT APPROVED'}",
                f"• Objections: {len(objections)} total ({blocking_count} blocking)",
                "",
                "Summary:",
                summary,
            ]
            if obj_lines:
                parts.append("")
                parts.append("Objections:")
                parts.extend(obj_lines)
            if recs:
                parts.append("")
                parts.append("Recommendations:")
                parts.extend([f"- [ ] {r}" for r in recs])

            formatted_json = ResponseFormatter.format_json_response(review_result)
            parts.append("")
            parts.append("<details><summary>Show full review JSON</summary>")
            parts.append("<pre>" + formatted_json.replace("<", "&lt;") + "</pre>")
            parts.append("</details>")

            return "\n".join(parts)
            
        except Exception as e:
            logger.error(f"Failed to format review response: {str(e)}")
            return f"Compliance Reviewer completed review. Raw result: {str(review_result)}"

