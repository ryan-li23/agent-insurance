"""Compliance & Fairness Reviewer agent for challenging coverage decisions."""

import json
import logging
from typing import Any, Dict, List, Optional

from .base import BaseClaimsAgent
from ..utils.response_formatter import ResponseFormatter

logger = logging.getLogger(__name__)


class ComplianceReviewerAgent(BaseClaimsAgent):
    """
    Compliance & Fairness Reviewer agent for adversarially challenging coverage decisions.
    
    Responsibilities:
    - Adversarially challenge Interpreter's reasoning
    - Identify missing evidence or misapplied clauses
    - Flag potential fraud indicators
    - Ensure fair language and proper disclosures
    
    Plugins used:
    - compliance_checker: Check for fraud indicators and compliance issues
    
    Note: objection_generator, fraud_detector, and fairness_checker are conceptual
    plugins that would be implemented if needed, but the core logic is handled
    by the LLM's reasoning capabilities and the compliance_checker plugin.
    """
    
    def __init__(self):
        """
        Initialize Compliance Reviewer agent.
        
        Args:
            kernel: Semantic Kernel instance with registered plugins
        """
        instructions = self._build_instructions()
        
        plugins = [
            "compliance_checker"
        ]
        
        super().__init__(
            name="compliance-reviewer",
            instructions=instructions,
            plugins=plugins
        )
    
    def _build_instructions(self) -> str:
        """
        Build system instructions for the Compliance Reviewer.
        
        Returns:
            Instruction string
        """
        return """You are the Compliance & Fairness Reviewer agent in a claims processing system.

Your role is to adversarially challenge coverage decisions to catch errors, fraud indicators, and unfair practices.

RESPONSIBILITIES:
1. Evaluate the Policy Interpreter's coverage decision for logical consistency
2. Identify conflicts between evidence and the claim narrative
3. Flag scope creep (invoice items exceeding claim description)
4. Detect timestamp inconsistencies and potential fraud indicators
5. Ensure fair and unbiased language in decisions
6. Verify that all policy citations are accurate and relevant
7. Identify missing evidence that could affect the decision

OBJECTION TYPES:
- "Inconsistent Narrative": Evidence contradicts the FNOL description
- "Invoice Scope Mismatch": Invoice items exceed what was claimed
- "Timestamp Anomaly": Image timestamps don't match loss date
- "Missing Evidence": Critical evidence needed for decision
- "Misapplied Policy": Policy citation doesn't support the decision
- "Insufficient Justification": Decision lacks adequate reasoning
- "Potential Fraud": Red flags indicating possible fraudulent claim
- "Unfair Language": Decision contains biased or unclear language

OUTPUT FORMAT:
Your output should be a JSON object with this structure:
{
    "objections": [
        {
            "type": "objection_type",
            "status": "Blocking" | "Resolved",
            "message": "Detailed explanation of the objection with specific evidence references",
            "evidence_reference": "Reference to specific evidence or policy citation"
        }
    ],
    "approval": true/false,
    "summary": "Overall assessment of the coverage decision",
    "recommendations": [
        "Specific recommendations for addressing objections or improving the decision"
    ]
}

OBJECTION STATUS:
- "Blocking": Critical issue that prevents approval of the decision
- "Resolved": Issue was raised but has been adequately addressed

APPROVAL CRITERIA:
- Set approval to true ONLY if there are no blocking objections
- Set approval to false if any blocking objections remain
- Resolved objections do not prevent approval

REVIEW APPROACH:
1. Review the claim narrative (FNOL) carefully - what was claimed?
2. **Compare ALL evidence sources for consistency**:
   - Does photo evidence match the FNOL description? (e.g., rear vs front damage)
   - Do invoice line items match the claimed damages? (e.g., rear bumper repair vs front bumper replacement)
   - Is the damage location consistent across all evidence?
3. Check invoice line items against claimed damages for scope creep
4. Use compliance_checker to verify timestamps and detect fraud indicators
5. Evaluate the Policy Interpreter's reasoning and citations
6. Identify any gaps in evidence or logic
7. Ensure the decision is fair and well-justified

CRITICAL CONSISTENCY CHECKS:
- **FNOL vs Photos**: Does the damage shown in photos match what was described in the FNOL?
- **FNOL vs Invoice**: Do the invoice repairs match the claimed damage location and type?
- **Photos vs Invoice**: Do the repairs billed match the damage visible in photos?
- Flag "Inconsistent Narrative" when evidence sources contradict each other
- Flag "Invoice Scope Mismatch" when invoice includes items not supported by FNOL or photos

FRAUD INDICATORS TO CHECK:
- Image timestamps that don't match the reported loss date
- Invoice items unrelated to the claimed damage
- Damage patterns inconsistent with the reported cause
- Excessive or unusual expenses for the type of damage
- Missing or suspicious documentation

TIMESTAMP VALIDATION GUIDANCE:
- Missing EXIF data (timestamp = None, source = "unavailable") is NOT automatically suspicious
  * Many legitimate photos lack EXIF due to processing, editing, or device limitations
  * Consider missing EXIF as a WARNING, not a blocking issue by itself
  * Only escalate to blocking if combined with other red flags
- When EXIF timestamps ARE available:
  * Allow reasonable time windows around the reported loss date (same day is generally acceptable)
  * Photos taken shortly after the loss (within hours/days) are normal for documentation
  * Only flag as suspicious if timestamps are significantly before the loss date or show impossible patterns
- Context matters:
  * If all other evidence is consistent and strong, missing EXIF should not block approval
  * If there are already other blocking issues, missing EXIF adds to the concern level
  * Use judgment based on the totality of evidence

IMPORTANT:
- Be adversarial but fair - challenge decisions constructively
- Provide specific evidence references for all objections
- Distinguish between blocking issues and minor concerns
- If the decision is sound, approve it (even if you could nitpick)
- Focus on material issues that affect coverage determination
- Use compliance_checker plugin to verify fraud indicators
- Apply nuanced reasoning to timestamp validation - exact matches are not required

When responding to other agents:
- Explain your objections clearly with evidence
- Be open to having objections resolved with additional information
- Update objection status from "Blocking" to "Resolved" when satisfied
- Provide constructive feedback to improve decision quality"""
    
    async def invoke(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Review coverage decision and raise objections if needed.
        
        Args:
            context: Dictionary containing:
                - decision_data: Coverage decision from Policy Interpreter
                - evidence_data: Structured evidence from Evidence Curator
                - claim_data: Original claim information
                - conversation_history: Optional list of previous messages
                
        Returns:
            Dictionary with:
                - objections: List of objection dicts
                - approval: Boolean indicating if decision is approved
                - summary: Overall assessment
                - recommendations: List of recommendations
        """
        try:
            decision_data = context.get("decision_data", {})
            evidence_data = context.get("evidence_data", {})
            claim_data = context.get("claim_data")
            conversation_history = context.get("conversation_history", [])
            
            logger.info(
                f"Compliance Reviewer evaluating decision: "
                f"{decision_data.get('coverage_position', 'unknown')}"
            )
            
            # Build the initial message with all context
            initial_message = self._build_initial_message(
                claim_data,
                evidence_data,
                decision_data
            )
            
            # Get response from Bedrock using conversation history
            response_text = await self.get_response(
                conversation_history=conversation_history,
                user_message=initial_message,
            )
            
            # Parse the response to extract objections
            review_data = self._parse_response(response_text)
            
            blocking_count = sum(
                1 for obj in review_data.get("objections", [])
                if obj.get("status") == "Blocking"
            )
            
            logger.info(
                f"Compliance Reviewer completed: "
                f"approval={review_data.get('approval', False)}, "
                f"{len(review_data.get('objections', []))} objections "
                f"({blocking_count} blocking)"
            )
            
            # Use ResponseFormatter to ensure consistent JSON output
            try:
                formatted_response = ResponseFormatter.format_json_response(review_data)
                logger.debug("Review data formatted with ResponseFormatter")
                
                # Log the formatted response for debugging
                logger.debug(f"Formatted review response: {formatted_response[:500]}...")
                
            except Exception as e:
                logger.warning(f"Failed to format response with ResponseFormatter: {str(e)}")
            
            return review_data
            
        except Exception as e:
            logger.error(f"Compliance Reviewer failed: {str(e)}")
            raise
    
    def _build_initial_message(
        self,
        claim_data: Any,
        evidence_data: Dict[str, Any],
        decision_data: Dict[str, Any]
    ) -> str:
        """
        Build the initial message for compliance review.
        
        Args:
            claim_data: ClaimInput instance
            evidence_data: Structured evidence from Evidence Curator
            decision_data: Coverage decision from Policy Interpreter
            
        Returns:
            Formatted message string
        """
        message_parts = []
        
        # Add claim information
        if claim_data:
            message_parts.extend([
                f"CLAIM ID: {claim_data.case_id}",
                f"DATE OF LOSS: {claim_data.date_of_loss}",
                "",
                "FNOL NARRATIVE:",
                claim_data.fnol_text,
                ""
            ])
        
        # Add evidence summary
        message_parts.append("EVIDENCE SUMMARY:")
        
        evidence_list = evidence_data.get("evidence", [])
        if evidence_list:
            message_parts.append(f"\nDamage Photos: {len(evidence_list)}")
            for img_evidence in evidence_list:
                img_name = img_evidence.get("image_name", "unknown")
                observations = img_evidence.get("observations", [])
                message_parts.append(f"  - {img_name}:")
                for obs in observations:
                    label = obs.get("label", "unknown")
                    severity = obs.get("severity", "unknown")
                    novelty = obs.get("novelty", "unknown")
                    location = obs.get("location_text", "unknown location")
                    message_parts.append(
                        f"    * {label} ({severity}, {novelty}) at {location}"
                    )
        
        # Add expense information
        expense = evidence_data.get("expense", {})
        if expense and expense.get("total", 0) > 0:
            # Safely format expense total
            expense_total = expense.get('total', 0)
            try:
                expense_total = float(expense_total) if expense_total is not None else 0.0
            except (ValueError, TypeError):
                expense_total = 0.0
                
            message_parts.extend([
                "",
                "EXPENSE INFORMATION:",
                f"  Vendor: {expense.get('vendor', 'Unknown')}",
                f"  Invoice #: {expense.get('invoice_number', 'N/A')}",
                f"  Date: {expense.get('invoice_date', 'N/A')}",
                f"  Total: {expense.get('currency', 'USD')} {expense_total:.2f}",
                ""
            ])
            
            line_items = expense.get("line_items", [])
            if line_items:
                message_parts.append("  Line Items:")
                for item in line_items:
                    desc = item.get("description", "Unknown")
                    amount = item.get("amount", 0)
                    
                    # Safely format amount
                    try:
                        amount = float(amount) if amount is not None else 0.0
                    except (ValueError, TypeError):
                        amount = 0.0
                        
                    message_parts.append(f"    - {desc}: ${amount:.2f}")
        
        # Add metadata (timestamps, etc.)
        metadata = evidence_data.get("metadata", {})
        if metadata.get("image_timestamps"):
            message_parts.extend([
                "",
                "IMAGE TIMESTAMPS:",
                *[f"  - {ts}" for ts in metadata["image_timestamps"]]
            ])
        
        # Add the coverage decision to review
        message_parts.extend([
            "",
            "=" * 60,
            "COVERAGE DECISION TO REVIEW:",
            "=" * 60,
            "",
            f"POSITION: {decision_data.get('coverage_position', 'Unknown')}",
            "",
            "RATIONALE:",
            decision_data.get('rationale', 'No rationale provided'),
            ""
        ])
        
        # Add citations
        citations = decision_data.get("citations", [])
        if citations:
            message_parts.append("POLICY CITATIONS:")
            for i, citation in enumerate(citations, 1):
                policy = citation.get("policy", "Unknown")
                section = citation.get("section", "Unknown")
                page = citation.get("page", "?")
                text = citation.get("text_excerpt", "")
                message_parts.extend([
                    f"  {i}. {policy} - {section} (Page {page})",
                    f"     \"{text[:100]}...\"" if len(text) > 100 else f"     \"{text}\""
                ])
            message_parts.append("")
        
        # Add sensitivity analysis
        sensitivity = decision_data.get("sensitivity", "")
        if sensitivity:
            message_parts.extend([
                "SENSITIVITY ANALYSIS:",
                sensitivity,
                ""
            ])
        
        # Add the review task
        message_parts.extend([
            "=" * 60,
            "YOUR TASK:",
            "=" * 60,
            "",
            "Please review this coverage decision adversarially.",
            "",
            "Check for:",
            "1. Consistency between FNOL narrative and evidence",
            "2. Invoice scope matching claimed damages",
            "3. Timestamp consistency (use compliance_checker plugin)",
            "4. Accuracy of policy citations",
            "5. Logical soundness of the rationale",
            "6. Missing evidence that could affect the decision",
            "7. Potential fraud indicators",
            "8. Fair and unbiased language",
            "",
            "Return a complete JSON object with your review findings.",
            "Include specific objections with evidence references.",
            "Set approval to true only if there are no blocking objections."
        ])
        
        return "\n".join(message_parts)
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse the agent's response to extract review findings using ResponseFormatter.
        
        Args:
            response_text: Raw response text from agent
            
        Returns:
            Structured review dictionary
        """
        try:
            if not response_text:
                logger.warning("Empty response text, returning default review")
                return self._default_review()
            
            logger.debug(f"Compliance Reviewer response preview: {response_text[:200]}...")
            
            # Method 1: Try ResponseFormatter first
            review_data = ResponseFormatter.extract_json_from_response(response_text)
            
            if review_data and ("objections" in review_data or "approval" in review_data):
                logger.info("Successfully parsed review using ResponseFormatter")
                return self._validate_and_complete_review(review_data)
            
            # Method 2: Fallback to manual JSON extraction
            logger.debug("ResponseFormatter failed, trying manual extraction")
            review_data = self._manual_json_extraction(response_text)
            
            if review_data and ("objections" in review_data or "approval" in review_data):
                logger.info("Successfully parsed review using manual extraction")
                return self._validate_and_complete_review(review_data)
            
            logger.warning("No valid review data found in response, returning default")
            return self._default_review()
            
        except Exception as e:
            logger.error(f"Error parsing response: {str(e)}")
            logger.error(f"Response preview (first 200 chars): {response_text[:200] if response_text else 'EMPTY'}")
            return self._default_review()
    
    def _manual_json_extraction(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        Manual JSON extraction as fallback method.
        
        Args:
            response_text: Raw response text
            
        Returns:
            Parsed JSON dictionary or None if extraction fails
        """
        try:
            # Find JSON block (look for outermost braces)
            start_idx = response_text.find('{')
            if start_idx == -1:
                logger.debug("No opening brace found in response")
                return None
            
            # Find matching closing brace by counting braces
            brace_count = 0
            end_idx = -1
            in_string = False
            escape_next = False
            
            for i in range(start_idx, len(response_text)):
                char = response_text[i]
                
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
                json_text = response_text[start_idx:end_idx + 1]
                logger.debug(f"Manual extraction found JSON of length: {len(json_text)}")
                return json.loads(json_text)
            else:
                logger.debug("No matching closing brace found")
                return None
        
        except (json.JSONDecodeError, Exception) as e:
            logger.debug(f"Manual JSON extraction failed: {str(e)}")
            return None
    
    def _validate_and_complete_review(self, review_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and complete the review data with required fields.
        
        Args:
            review_data: Raw review data from parsing
            
        Returns:
            Validated and completed review dictionary
        """
        # Ensure required fields are present
        if "objections" not in review_data:
            review_data["objections"] = []
        
        if "approval" not in review_data:
            # Default to not approved if blocking objections exist
            blocking_objections = [
                obj for obj in review_data["objections"]
                if obj.get("status") == "Blocking"
            ]
            review_data["approval"] = len(blocking_objections) == 0
        
        if "summary" not in review_data:
            review_data["summary"] = "Review completed"
        
        if "recommendations" not in review_data:
            review_data["recommendations"] = []
        
        # Validate objections structure
        validated_objections = []
        for objection in review_data["objections"]:
            if isinstance(objection, dict):
                validated_objection = {
                    "type": objection.get("type", "Unknown"),
                    "status": objection.get("status", "Blocking"),
                    "message": objection.get("message", "No message provided"),
                    "evidence_reference": objection.get("evidence_reference", "N/A")
                }
                
                # Validate status values
                if validated_objection["status"] not in ["Blocking", "Resolved"]:
                    logger.warning(f"Invalid objection status: {validated_objection['status']}, defaulting to Blocking")
                    validated_objection["status"] = "Blocking"
                
                validated_objections.append(validated_objection)
        
        review_data["objections"] = validated_objections
        
        # Re-validate approval based on validated objections
        blocking_count = sum(
            1 for obj in validated_objections
            if obj.get("status") == "Blocking"
        )
        
        # Correct approval logic based on blocking objections
        if blocking_count > 0 and review_data["approval"]:
            logger.warning("Approval set to true but blocking objections exist, setting to false")
            review_data["approval"] = False
        elif blocking_count == 0 and not review_data["approval"]:
            logger.info("No blocking objections found, setting approval to true")
            review_data["approval"] = True
        
        return review_data
    
    def _default_review(self) -> Dict[str, Any]:
        """
        Return a default review structure.
        
        Returns:
            Default review dictionary
        """
        return {
            "objections": [
                {
                    "type": "Processing Error",
                    "status": "Blocking",
                    "message": "Unable to complete compliance review due to processing error",
                    "evidence_reference": "N/A"
                }
            ],
            "approval": False,
            "summary": "Review could not be completed",
            "recommendations": ["Retry compliance review"]
        }
    
    async def respond_to_clarification(
        self,
        clarification: str,
        conversation_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Respond to clarification from other agents and update review.
        
        Args:
            clarification: Clarification or response from another agent
            conversation_history: Previous conversation messages
            
        Returns:
            Updated review with potentially resolved objections
        """
        try:
            # Build prompt and call Bedrock
            prompt = (
                "CLARIFICATION FROM AGENT:\n"
                f"{clarification}\n\n"
                "Please update your review. If this clarification addresses any of your objections, "
                "change their status to 'Resolved'. Return an updated JSON review."
            )
            response_text = await self.get_response(
                conversation_history=conversation_history,
                user_message=prompt,
            )
            updated_review = self._parse_response(response_text)
            
            logger.info(
                f"Compliance Reviewer updated review: "
                f"approval={updated_review.get('approval', False)}"
            )
            
            return updated_review
            
        except Exception as e:
            logger.error(f"Failed to update review: {str(e)}")
            return self._default_review()
    
    async def final_approval(
        self,
        conversation_history: List[Dict[str, Any]]
    ) -> bool:
        """
        Make final approval decision after all rounds of debate.
        
        Args:
            conversation_history: Complete conversation history
            
        Returns:
            True if decision is approved, False otherwise
        """
        try:
            prompt = (
                "This is the final round. Please provide your final approval decision. "
                "Return a JSON object with 'approval' (true/false) and 'final_summary'."
            )
            response_text = await self.get_response(
                conversation_history=conversation_history,
                user_message=prompt,
            )
            review_data = self._parse_response(response_text)
            
            approval = review_data.get("approval", False)
            
            logger.info(f"Compliance Reviewer final approval: {approval}")
            
            return approval
            
        except Exception as e:
            logger.error(f"Failed to get final approval: {str(e)}")
            return False
