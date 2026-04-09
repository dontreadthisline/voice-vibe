from __future__ import annotations

from voicevibe.llm.backend.generic import GenericBackend
from voicevibe.llm.backend.mistral import MistralBackend
from voicevibe.types import Backend

BACKEND_FACTORY = {Backend.MISTRAL: MistralBackend, Backend.GENERIC: GenericBackend}
