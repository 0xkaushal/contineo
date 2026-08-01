"""Text-to-Speech lifecycle events."""

from __future__ import annotations

from pydantic import Field

from contineo.events.base import BaseEvent, EventType


class TTSStartedEvent(BaseEvent):
    """Emitted when a TTS synthesis request begins.

    Attributes:
        event_type:  Always ``EventType.TTS_STARTED``.
        provider:    TTS provider name (e.g. ``elevenlabs``, ``openai``).
        voice_id:    Identifier of the voice being used.
        text:        The text being synthesised to speech.
        language:    BCP-47 language code (e.g. ``en-US``).
    """

    event_type: EventType = Field(
        default=EventType.TTS_STARTED,
        frozen=True,
        description="Discriminator — always tts.started",
    )
    provider: str = Field(description="TTS provider name")
    voice_id: str | None = Field(default=None, description="Voice identifier")
    text: str = Field(description="Text being synthesised")
    language: str | None = Field(default=None, description="BCP-47 language code")


class TTSCompletedEvent(BaseEvent):
    """Emitted when TTS synthesis completes.

    Attributes:
        event_type:        Always ``EventType.TTS_COMPLETED``.
        provider:          TTS provider name.
        voice_id:          Identifier of the voice used.
        duration_ms:       Time taken for synthesis in milliseconds.
        audio_duration_ms: Duration of the resulting audio in milliseconds.
        characters:        Number of characters synthesised (used for billing).
        cost_usd:          Estimated USD cost for this synthesis (optional).
    """

    event_type: EventType = Field(
        default=EventType.TTS_COMPLETED,
        frozen=True,
        description="Discriminator — always tts.completed",
    )
    provider: str = Field(description="TTS provider name")
    voice_id: str | None = Field(default=None, description="Voice identifier")
    duration_ms: float | None = Field(default=None, ge=0, description="Synthesis time in ms")
    audio_duration_ms: float | None = Field(
        default=None,
        ge=0,
        description="Duration of the resulting audio in ms",
    )
    characters: int | None = Field(
        default=None,
        ge=0,
        description="Number of characters synthesised",
    )
    cost_usd: float | None = Field(default=None, ge=0, description="Estimated USD cost")
