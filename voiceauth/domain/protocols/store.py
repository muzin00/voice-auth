"""Store Protocol for data persistence."""

from typing import Protocol

import numpy as np

from voiceauth.domain.models.speaker import Speaker
from voiceauth.domain.models.voiceprint import Voiceprint


class SpeakerStoreProtocol(Protocol):
    """Protocol for Speaker data persistence."""

    def create_speaker(
        self,
        speaker_id: str,
        speaker_name: str | None = None,
        pin_hash: str | None = None,
    ) -> Speaker:
        """Create a new speaker.

        Args:
            speaker_id: Unique identifier for the speaker
            speaker_name: Optional display name
            pin_hash: Optional SHA-256 hash of PIN

        Returns:
            The created Speaker instance
        """
        ...

    def get_speaker_by_id(self, speaker_id: str) -> Speaker:
        """Get a speaker by their speaker_id.

        Args:
            speaker_id: The speaker's identifier

        Returns:
            The Speaker instance
        """
        ...

    def get_speaker_by_public_id(self, public_id: str) -> Speaker:
        """Get a speaker by their public_id (ULID).

        Args:
            public_id: The speaker's public ULID

        Returns:
            The Speaker instance
        """
        ...

    def speaker_exists(self, speaker_id: str) -> bool:
        """Check if a speaker exists.

        Args:
            speaker_id: The speaker's identifier

        Returns:
            True if speaker exists, False otherwise
        """
        ...

    def update_speaker_pin(self, speaker_id: str, pin_hash: str | None) -> Speaker:
        """Update a speaker's PIN hash.

        Args:
            speaker_id: The speaker's identifier
            pin_hash: New SHA-256 hash of PIN (or None to remove)

        Returns:
            The updated Speaker instance
        """
        ...

    def delete_speaker(self, speaker_id: str) -> None:
        """Delete a speaker and all associated voiceprints.

        Args:
            speaker_id: The speaker's identifier
        """
        ...

    def add_voiceprint(self, speaker_id: str, embedding: np.ndarray) -> Voiceprint:
        """Add or update a voiceprint for a speaker.

        Args:
            speaker_id: The speaker's identifier
            embedding: numpy array of shape (512,) with float32 dtype

        Returns:
            The created or updated Voiceprint instance
        """
        ...

    def get_voiceprint(self, speaker_id: str) -> np.ndarray:
        """Get the voiceprint embedding for a speaker.

        Args:
            speaker_id: The speaker's identifier

        Returns:
            numpy array of shape (512,) with float32 dtype
        """
        ...

    def has_voiceprint(self, speaker_id: str) -> bool:
        """Check if a speaker has a voiceprint.

        Args:
            speaker_id: The speaker's identifier

        Returns:
            True if speaker has a voiceprint
        """
        ...
