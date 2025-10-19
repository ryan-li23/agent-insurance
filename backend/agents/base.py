"""Base agent class for Claims Coverage Reasoner agents (AWS Bedrock)."""

import logging
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod

from ..utils.bedrock_client import BedrockClient
from ..utils.config import Config

logger = logging.getLogger(__name__)


class BaseClaimsAgent(ABC):
    """
    Base class for all claims processing agents using AWS Bedrock.
    
    Attributes:
        name: Agent name/identifier
        instructions: System instructions for the agent
        plugins: List of plugin names (for bookkeeping)
        bedrock: BedrockClient for LLM calls
    """

    def __init__(
        self,
        name: str,
        instructions: str,
        plugins: Optional[List[str]] = None,
        bedrock: Optional[BedrockClient] = None,
    ):
        self.name = name
        self.instructions = instructions
        self.plugins = plugins or []

        if bedrock is not None:
            self.bedrock = bedrock
        else:
            config = Config.load()
            self.bedrock = BedrockClient(
                region=config.aws_region,
                model_id=config.bedrock.model_id,
                embedding_model_id=config.bedrock.embedding_model_id,
                timeout=config.bedrock.timeout,
                max_retries=config.bedrock.max_retries,
            )
        # Cache Bedrock Agents (managed) config
        self._agents_cfg = Config.load().bedrock_agents

        logger.info(
            f"Initialized {self.__class__.__name__}: {name} with {len(self.plugins)} plugins"
        )

    @abstractmethod
    async def invoke(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process agent turn with access to tools/plugins."""
        pass

    async def get_response(
        self,
        conversation_history: Optional[List[Dict[str, Any]]],
        user_message: str,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> str:
        """
        Get a text response from Bedrock using the Converse API.
        - conversation_history: list of dicts [{'role': 'user'|'assistant', 'content': [{'text': str}]}]
        - user_message: the current prompt to append as the final user turn
        """
        try:
            # If using managed Agents for Bedrock and configured for this role, invoke it
            if getattr(self._agents_cfg, "enabled", False):
                role_to_ids = {
                    "evidence-curator": (self._agents_cfg.curator_agent_id, self._agents_cfg.curator_alias_id),
                    "policy-interpreter": (self._agents_cfg.interpreter_agent_id, self._agents_cfg.interpreter_alias_id),
                    "compliance-reviewer": (self._agents_cfg.reviewer_agent_id, self._agents_cfg.reviewer_alias_id),
                }
                agent_id, alias_id = role_to_ids.get(self.name, ("", ""))
                if agent_id and alias_id:
                    # Note: Agents maintain session state; we send current user prompt.
                    response_text = await self.bedrock.invoke_managed_agent(
                        agent_id=agent_id,
                        agent_alias_id=alias_id,
                        input_text=user_message,
                        session_id=None,
                    )
                    logger.debug(f"{self.name} (managed agent) response: {response_text[:100]}...")
                    return response_text

            # Default: direct model invocation via Converse API
            messages: List[Dict[str, Any]] = []
            if conversation_history:
                messages.extend(conversation_history)
            messages.append({"role": "user", "content": [{"text": user_message}]})

            system_prompts = [{"text": self.instructions}]
            result = await self.bedrock.invoke_nova_pro(
                messages=messages,
                system_prompts=system_prompts,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Parse text content from Bedrock response shape
            outputs = result.get("content", [])
            text_parts: List[str] = []
            for item in outputs:
                if isinstance(item, dict) and item.get("text"):
                    text_parts.append(item["text"])
            response_text = "\n".join(text_parts) if text_parts else ""

            logger.debug(f"{self.name} generated response: {response_text[:100]}...")
            return response_text

        except Exception as e:
            logger.error(f"Error getting response from {self.name}: {str(e)}")
            raise

    def get_plugin_names(self) -> List[str]:
        return self.plugins.copy()

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, plugins={self.plugins})"
