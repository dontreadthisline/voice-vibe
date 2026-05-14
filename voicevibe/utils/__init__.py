"""Utilities package. Re-exports all public and test-used symbols from submodules."""

from __future__ import annotations

from voicevibe.utils.concurrency import (
    AsyncExecutor,
    ConversationLimitException,
    run_sync,
)
from voicevibe.utils.display import compact_reduction_display
from voicevibe.utils.matching import name_matches
from voicevibe.utils.paths import is_dangerous_directory
from voicevibe.utils.platform import is_windows
from voicevibe.utils.retry import async_generator_retry, async_retry
from voicevibe.utils.tags import (
    CANCELLATION_TAG,
    KNOWN_TAGS,
    TOOL_ERROR_TAG,
    VIBE_STOP_EVENT_TAG,
    VIBE_WARNING_TAG,
    CancellationReason,
    TaggedText,
    get_user_cancellation_message,
    is_user_cancellation_event,
)
from voicevibe.utils.time import utc_now


def get_server_url_from_api_base(api_base: str) -> str | None:
    """Extract server URL from API base URL.

    Example: "https://api.mistral.ai/v1" -> "https://api.mistral.ai"
    """
    if "/v" in api_base:
        return api_base.rsplit("/v", 1)[0]
    return api_base


__all__ = [
    "CANCELLATION_TAG",
    "KNOWN_TAGS",
    "TOOL_ERROR_TAG",
    "VIBE_STOP_EVENT_TAG",
    "VIBE_WARNING_TAG",
    "AsyncExecutor",
    "CancellationReason",
    "ConversationLimitException",
    "TaggedText",
    "async_generator_retry",
    "async_retry",
    "compact_reduction_display",
    "get_server_url_from_api_base",
    "get_user_cancellation_message",
    "is_dangerous_directory",
    "is_user_cancellation_event",
    "is_windows",
    "name_matches",
    "run_sync",
    "utc_now",
]
