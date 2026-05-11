"""Test LLM module availability."""
from __future__ import annotations

import asyncio
import os

import pytest

from voicevibe.config import ModelConfig, ProviderConfig
from voicevibe.llm.backend.factory import BACKEND_FACTORY
from voicevibe.types import Backend, LLMMessage, Role


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("MISTRAL_API_KEY"),
    reason="MISTRAL_API_KEY not set"
)
async def test_mistral_llm() -> None:
    """Test Mistral LLM backend streaming."""
    provider = ProviderConfig(
        name="mistral",
        api_base="https://api.mistral.ai/v1",
        api_key_env_var="MISTRAL_API_KEY",
        backend="mistral",
    )
    model = ModelConfig(
        name="mistral-small-latest",
        provider="mistral",
        alias="mistral-small",
    )

    backend = BACKEND_FACTORY[Backend.MISTRAL](provider=provider)
    messages = [LLMMessage(role=Role.user, content="Say 'hello' in one word")]

    print("Testing Mistral LLM...")
    async for chunk in backend.complete_streaming(
        model=model,
        messages=messages,
        tools=None,
        temperature=0.1,
        max_tokens=None,
        tool_choice=None,
        extra_headers=None,
    ):
        if chunk.message.content:
            print(chunk.message.content, end="", flush=True)
    print("\nLLM module works!")


if __name__ == "__main__":
    if not os.getenv("MISTRAL_API_KEY"):
        print("Please set MISTRAL_API_KEY environment variable")
        exit(1)
    asyncio.run(test_mistral_llm())
