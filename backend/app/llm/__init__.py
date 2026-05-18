"""LLM integration for FinAlly chat.

Public API:
- :class:`ChatResponse` — parsed structured output from the LLM.
- :func:`generate_chat_response` — async call to OpenRouter via LiteLLM with
  Cerebras as the inference provider. Honors ``LLM_MOCK=true`` for tests.
"""

from .client import ChatResponse, generate_chat_response

__all__ = ["ChatResponse", "generate_chat_response"]
