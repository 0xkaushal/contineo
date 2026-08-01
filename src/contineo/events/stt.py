"""Speech-to-Text lifecycle events."""

from __future__ import annotations

from pydantic import Field

from contineo.events.base import BaseEvent, EventType


class STTStartedEvent(BaseEvent):
    """Emitted when a speech recognition request begins.

    Attributes:
        event_type:      Always ``EventType.STT_STARTED``.
        provider:        STT provider name (e.g. ``deepgram``, ``openai``).
        language:        BCP-47 language code hint provided to the provider.
        audio_duration_ms: Duration of the audio being transcribed (if known).
    """

    event_type: EventType = Field(
        default=EventType.STT_STARTED,
        frozen=True,
        description="Discriminator — always stt.started",
    )
    provider: str = Field(description="STT provider name")
    language: str | None = Field(default=None, description="BCP-47 language hint")
    audio_duration_ms: float | None = Field(
        default=None,
        ge=0,
        description="Duration of the audio being transcribed in ms",
    )


class STTCompletedEvent(BaseEvent):
    """Emitted when speech recognition completes.

    Attributes:
        event_type:        Always ``EventType.STT_COMPLETED``.
        provider:          STT provider name.
        transcript:        The recognised text.
        language_detected: BCP-47 code of the detected language (optional).
        confidence:        Recognition confidence score 0–1 (optional).
        duration_ms:       Time taken for recognition in milliseconds.
        audio_duration_ms: Duration of the transcribed audio in milliseconds.
        cost_usd:          Estimated USD cost for this transcription (optional).
    """

    event_type: EventType = Field(
        default=EventType.STT_COMPLETED,
        frozen=True,
        description="Discriminator — always stt.completed",
    )
    provider: str = Field(description="STT provider name")
    transcript: str | None = Field(default=None, description="Recognised text")
    language_detected: str | None = Field(
        default=None,
        description="BCP-47 code of the detected language",
    )
    confidence: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Recognition confidence score (0–1)",
    )
    duration_ms: float | None = Field(default=None, ge=0, description="Recognition time in ms")
    audio_duration_ms: float | None = Field(
        default=None,
        ge=0,
        description="Duration of the transcribed audio in ms",
    )
    cost_usd: float | None = Field(default=None, ge=0, description="Estimated USD cost")
