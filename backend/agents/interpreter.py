"""Policy Interpreter agent for mapping claim evidence to policy clauses."""

import json
import logging
from typing import Any, Dict, List, Optional

from .base import BaseClaimsAgent
from ..utils.response_formatter import ResponseFormatter

logger = logging.getLogger(__name__)


class PolicyInterpreterAgent(BaseClaimsAgent):
    """
    Policy Interpreter agent for mapping claim facts to policy clauses.
    
    Responsibilities:
    - Map claim evidence to specific policy clauses
    - Provide coverage recommendations with citations
    - Explain what additional evidence would change decisions
    - Handle both HO-3 (homeowners) and PAP (auto) policies
    
    Plugins used:
    - policy_retriever: Query FAISS vector store for relevant policy sections
    
    Note: citation_formatter and coverage_analyzer are conceptual plugins
    that would be implemented if needed, but the core logic is handled
    by the LLM's reasoning capabilities.
    """
    
    def __init__(self):
        """
        Initialize Policy Interpreter agent.
        
        Args:
            kernel: Semantic Kernel instance with registered plugins
        """
        instructions = self._build_instructions()
        
        plugins = [
            "policy_retriever"
        ]
        
        super().__init__(
            name="policy-interpreter",
            instructions=instructions,
            plugins=plugins
        )
    
    def _build_instructions(self) -> str:
        """
        Build system instructions for the Policy Interpreter.
        
        Returns:
            Instruction string
        """
        return """You are the Policy Interpreter agent in a claims processing system.

Your role is to map claim evidence to specific policy clauses and provide coverage recommendations.

RESPONSIBILITIES:
1. Review evidence provided by the Evidence Curator
2. Query the policy knowledge base using policy_retriever to find relevant clauses
3. Map claim facts to specific policy provisions
4. Determine coverage applicability (Pay, Partial, or Deny)
5. Provide detailed rationale with specific policy citations
6. Identify applicable exclusions or limitations
7. Explain what additional evidence would change the decision

POLICY TYPES:
- HO-3: Homeowners insurance policy
- PAP: Personal Auto Policy

OUTPUT FORMAT:
Your output should be a JSON object with this structure:
{
    "coverage_position": "Pay" | "Partial" | "Deny",
    "rationale": "Detailed explanation of the coverage decision, referencing specific policy provisions and how they apply to the claim facts",
    "citations": [
        {
            "policy": "policy_name",
            "section": "section_name",
            "page": page_number,
            "text_excerpt": "relevant_policy_text"
        }
    ],
    "sensitivity": "What evidence or circumstances would change this decision",
    "coverage_details": {
        "covered_items": ["list of covered items/damages"],
        "excluded_items": ["list of excluded items/damages"],
        "limitations": ["any applicable limitations or sub-limits"],
        "deductible_applies": true/false,
        "estimated_covered_amount": 0.0
    }
}

DECISION GUIDELINES:
1. "Pay" - Full coverage applies, no exclusions triggered
2. "Partial" - Some items covered, some excluded, or coverage subject to limitations
3. "Deny" - Loss is excluded or not covered under the policy

CITATION REQUIREMENTS:
- Always cite specific policy sections with page numbers
- Include relevant text excerpts from the policy
- Reference both coverage grants and applicable exclusions
- Use policy_retriever to find accurate policy language

REASONING APPROACH:
1. Review all evidence provided (FNOL, photos, invoices)
2. Identify the cause of loss from the evidence
3. Determine which coverage section applies
4. Check for applicable exclusions
5. Consider any limitations or conditions
6. Map evidence to policy requirements
7. Provide clear reasoning for your decision

YOUR PRIMARY ROLE:
- **Focus on policy coverage determination**: Does the claim fall under covered perils?
- **Map evidence to policy provisions**: Which sections apply?
- **Identify applicable exclusions**: Are there policy exclusions that apply?
- **Determine coverage position**: Pay, Partial, or Deny based on policy language

EVIDENCE REVIEW:
- Review all evidence sources (FNOL narrative, photo observations, invoice line items)
- Use the evidence to understand what is being claimed
- Base your coverage determination on whether the claimed loss is covered by the policy
- You may note obvious inconsistencies in your rationale, but your primary job is policy interpretation
- The Compliance Reviewer will perform detailed fraud detection and consistency checks

IMPORTANT:
- Base decisions on actual policy language, not general insurance principles
- Be specific about which policy provisions apply
- Explain your reasoning clearly with policy citations
- Identify gaps in evidence that affect the decision
- Consider both coverage grants and applicable exclusions
- Do not make assumptions beyond the evidence provided
- Your role is policy interpretation, not fraud detection or evidence validation

When responding to other agents:
- Defend your coverage position with policy citations
- Address objections with additional policy analysis
- Clarify ambiguous policy language
- Explain how different evidence would affect coverage"""
    
    async def invoke(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map evidence to policy clauses and provide coverage recommendation.
        
        Args:
            context: Dictionary containing:
                - evidence_data: Structured evidence from Evidence Curator
                - claim_data: Original claim information
                - conversation_history: Optional list of previous messages
                
        Returns:
            Dictionary with:
                - coverage_position: "Pay", "Partial", or "Deny"
                - rationale: Detailed explanation
                - citations: List of policy citations
                - sensitivity: What would change the decision
                - coverage_details: Detailed coverage breakdown
        """
        try:
            evidence_data = context.get("evidence_data", {})
            claim_data = context.get("claim_data")
            conversation_history = context.get("conversation_history", [])
            
            logger.info(
                f"Policy Interpreter analyzing claim: {claim_data.case_id if claim_data else 'unknown'}"
            )
            
            # Build the initial message with evidence and claim information
            initial_message = self._build_initial_message(claim_data, evidence_data)
            
            # Get response from Bedrock using conversation history
            response_text = await self.get_response(
                conversation_history=conversation_history,
                user_message=initial_message,
            )
            
            # Parse the response to extract coverage decision
            decision_data = self._parse_response(response_text)
            
            logger.info(
                f"Policy Interpreter decision: {decision_data.get('coverage_position', 'unknown')} "
                f"with {len(decision_data.get('citations', []))} citations"
            )
            
            # Use ResponseFormatter to ensure consistent JSON output
            try:
                formatted_response = ResponseFormatter.format_json_response(decision_data)
                logger.debug("Decision data formatted with ResponseFormatter")
                
                # Log the formatted response for debugging
                logger.debug(f"Formatted decision response: {formatted_response[:500]}...")
                
            except Exception as e:
                logger.warning(f"Failed to format response with ResponseFormatter: {str(e)}")
            
            return decision_data
            
        except Exception as e:
            logger.error(f"Policy Interpreter failed: {str(e)}")
            raise
    
    def _build_initial_message(
        self,
        claim_data: Any,
        evidence_data: Dict[str, Any]
    ) -> str:
        """
        Build the initial message for policy interpretation.
        
        Args:
            claim_data: ClaimInput instance
            evidence_data: Structured evidence from Evidence Curator
            
        Returns:
            Formatted message string
        """
        message_parts = []
        
        if claim_data:
            message_parts.extend([
                f"CLAIM ID: {claim_data.case_id}",
                f"DATE OF LOSS: {claim_data.date_of_loss}",
                "",
                "FNOL NARRATIVE:",
                claim_data.fnol_text,
                ""
            ])
        
        # Add FNOL summary if available
        fnol_summary = evidence_data.get("fnol_summary", "")
        if fnol_summary:
            message_parts.extend([
                "FNOL EXTRACTED CONTENT:",
                fnol_summary,
                ""
            ])
        
        # Add evidence summary
        message_parts.append("EVIDENCE SUMMARY:")
        
        # Include ALL image evidence details (not just first 3)
        evidence_list = evidence_data.get("evidence", [])
        if evidence_list:
            message_parts.append(f"\nDamage Photos Analyzed: {len(evidence_list)}")
            for img_evidence in evidence_list:
                img_name = img_evidence.get("image_name", "unknown")
                observations = img_evidence.get("observations", [])
                global_assessment = img_evidence.get("global_assessment", {})
                
                message_parts.append(f"\n  Photo: {img_name}")
                message_parts.append(f"  Total Observations: {len(observations)}")
                
                # Include global assessment
                if global_assessment:
                    overall_severity = global_assessment.get("overall_severity", "unknown")
                    damage_summary = global_assessment.get("damage_summary", "")
                    message_parts.append(f"  Overall Severity: {overall_severity}")
                    if damage_summary:
                        message_parts.append(f"  Summary: {damage_summary}")
                
                # Include ALL observations (not just first 3)
                if observations:
                    message_parts.append("  Observations:")
                    for obs in observations:
                        label = obs.get("label", "unknown")
                        severity = obs.get("severity", "unknown")
                        location = obs.get("location_text", "unknown location")
                        confidence = obs.get("confidence", 0)
                        
                        # Safely format confidence
                        try:
                            confidence = float(confidence) if confidence is not None else 0.0
                        except (ValueError, TypeError):
                            confidence = 0.0
                            
                        message_parts.append(f"    - {label} ({severity}, confidence: {confidence:.2f}) at {location}")
        
        # Include FULL expense data with all line items
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
                "INVOICE DETAILS:",
                f"  Vendor: {expense.get('vendor', 'Unknown')}",
                f"  Invoice #: {expense.get('invoice_number', 'N/A')}",
                f"  Invoice Date: {expense.get('invoice_date', 'N/A')}",
                f"  Total: {expense.get('currency', 'USD')} {expense_total:.2f}",
                ""
            ])
            
            # Include ALL line items
            line_items = expense.get('line_items', [])
            if line_items:
                message_parts.append("  Line Items:")
                for item in line_items:
                    desc = item.get('description', 'Unknown')
                    qty = item.get('quantity', 1) or 1
                    unit_price = item.get('unit_price') or 0
                    amount = item.get('amount') or 0
                    category = item.get('category', 'other')
                    
                    # Ensure numeric values are not None
                    try:
                        unit_price = float(unit_price) if unit_price is not None else 0.0
                        amount = float(amount) if amount is not None else 0.0
                        qty = int(qty) if qty is not None else 1
                    except (ValueError, TypeError):
                        unit_price = 0.0
                        amount = 0.0
                        qty = 1
                    
                    message_parts.append(
                        f"    - {desc} (Qty: {qty}, Unit: ${unit_price:.2f}, "
                        f"Total: ${amount:.2f}, Category: {category})"
                    )
                
                # Safely format total
                total = expense.get('total', 0)
                try:
                    total = float(total) if total is not None else 0.0
                except (ValueError, TypeError):
                    total = 0.0
                message_parts.append(f"  Grand Total: ${total:.2f}")
        
        message_parts.extend([
            "",
            "TASK:",
            "Please analyze this claim and provide a coverage determination.",
            "",
            "Use policy_retriever to query the policy knowledge base for relevant clauses.",
            "Consider both coverage grants and applicable exclusions.",
            "Provide a detailed rationale with specific policy citations.",
            "",
            "Return a complete JSON object with your coverage decision."
        ])
        
        return "\n".join(message_parts)
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse the agent's response to extract coverage decision using ResponseFormatter.
        
        Args:
            response_text: Raw response text from agent
            
        Returns:
            Structured decision dictionary
        """
        try:
            if not response_text:
                logger.warning("Empty response text, returning default decision")
                return self._default_decision()
            
            logger.debug(f"Policy Interpreter response preview: {response_text[:200]}...")
            
            # Method 1: Try ResponseFormatter first
            decision_data = ResponseFormatter.extract_json_from_response(response_text)
            
            if decision_data and "coverage_position" in decision_data:
                logger.info("Successfully parsed decision using ResponseFormatter")
                return self._validate_and_complete_decision(decision_data)
            
            # Method 2: Fallback to manual JSON extraction
            logger.debug("ResponseFormatter failed, trying manual extraction")
            decision_data = self._manual_json_extraction(response_text)
            
            if decision_data and "coverage_position" in decision_data:
                logger.info("Successfully parsed decision using manual extraction")
                return self._validate_and_complete_decision(decision_data)
            
            logger.warning("No valid decision data found in response, returning default")
            return self._default_decision()
            
        except Exception as e:
            logger.error(f"Error parsing response: {str(e)}")
            logger.error(f"Response preview (first 200 chars): {response_text[:200] if response_text else 'EMPTY'}")
            return self._default_decision()
    
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
    
    def _validate_and_complete_decision(self, decision_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and complete the decision data with required fields.
        
        Args:
            decision_data: Raw decision data from parsing
            
        Returns:
            Validated and completed decision dictionary
        """
        # Ensure required fields are present
        if "coverage_position" not in decision_data:
            decision_data["coverage_position"] = "Deny"
        
        if "rationale" not in decision_data:
            decision_data["rationale"] = "Unable to determine coverage"
        
        if "citations" not in decision_data:
            decision_data["citations"] = []
        
        if "sensitivity" not in decision_data:
            decision_data["sensitivity"] = "Additional evidence needed"
        
        # Ensure coverage_details structure exists
        if "coverage_details" not in decision_data:
            decision_data["coverage_details"] = {}
        
        coverage_details = decision_data["coverage_details"]
        if "covered_items" not in coverage_details:
            coverage_details["covered_items"] = []
        
        if "excluded_items" not in coverage_details:
            coverage_details["excluded_items"] = []
        
        if "limitations" not in coverage_details:
            coverage_details["limitations"] = []
        
        if "deductible_applies" not in coverage_details:
            coverage_details["deductible_applies"] = False
        
        if "estimated_covered_amount" not in coverage_details:
            coverage_details["estimated_covered_amount"] = 0.0
        
        # Validate coverage_position values
        valid_positions = ["Pay", "Partial", "Deny"]
        if decision_data["coverage_position"] not in valid_positions:
            logger.warning(f"Invalid coverage position: {decision_data['coverage_position']}, defaulting to Deny")
            decision_data["coverage_position"] = "Deny"
        
        return decision_data
    
    def _default_decision(self) -> Dict[str, Any]:
        """
        Return a default decision structure.
        
        Returns:
            Default decision dictionary
        """
        return {
            "coverage_position": "Deny",
            "rationale": "Unable to determine coverage due to processing error",
            "citations": [],
            "sensitivity": "Additional evidence and policy review needed",
            "coverage_details": {
                "covered_items": [],
                "excluded_items": [],
                "limitations": [],
                "deductible_applies": False,
                "estimated_covered_amount": 0.0
            }
        }
    
    async def respond_to_objection(
        self,
        objection: str,
        conversation_history: List[Dict[str, Any]]
    ) -> str:
        """
        Respond to an objection from the Compliance Reviewer.
        
        Args:
            objection: Objection message from reviewer
            conversation_history: Previous conversation messages
            
        Returns:
            Response addressing the objection
        """
        try:
            # Build prompt and call Bedrock
            prompt = (
                "OBJECTION FROM COMPLIANCE REVIEWER:\n"
                f"{objection}\n\n"
                "Please address this objection with additional policy analysis or revised reasoning."
            )
            response_text = await self.get_response(
                conversation_history=conversation_history,
                user_message=prompt,
            )
            return response_text
            
        except Exception as e:
            logger.error(f"Failed to respond to objection: {str(e)}")
            return f"I acknowledge the objection but encountered an error: {str(e)}"
    
    async def revise_decision(
        self,
        feedback: str,
        conversation_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Revise the coverage decision based on feedback.
        
        Args:
            feedback: Feedback requiring decision revision
            conversation_history: Previous conversation messages
            
        Returns:
            Revised decision dictionary
        """
        try:
            prompt = (
                "FEEDBACK:\n"
                f"{feedback}\n\n"
                "Please provide a revised coverage decision in JSON format."
            )
            response_text = await self.get_response(
                conversation_history=conversation_history,
                user_message=prompt,
            )
            revised_decision = self._parse_response(response_text)
            
            logger.info(
                f"Policy Interpreter revised decision: {revised_decision.get('coverage_position', 'unknown')}"
            )
            
            return revised_decision
            
        except Exception as e:
            logger.error(f"Failed to revise decision: {str(e)}")
            return self._default_decision()
