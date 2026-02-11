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

    def add_voiceprint(
        self, speaker_id: str, digit: str, embedding: np.ndarray
    ) -> Voiceprint:
        """Add or update a voiceprint for a speaker.

        Args:
            speaker_id: The speaker's identifier
            digit: The digit ("0" to "9")
            embedding: numpy array of shape (512,) with float32 dtype

        Returns:
            The created or updated Voiceprint instance
        """
        ...

    def add_voiceprints_bulk(
        self, speaker_id: str, embeddings: dict[str, np.ndarray]
    ) -> list[Voiceprint]:
        """Add or update multiple voiceprints for a speaker.

        Args:
            speaker_id: The speaker's identifier
            embeddings: Dictionary mapping digits to embeddings

        Returns:
            List of created/updated Voiceprint instances
        """
        ...

    def get_voiceprints(self, speaker_id: str) -> dict[str, np.ndarray]:
        """Get all voiceprints for a speaker.

        Args:
            speaker_id: The speaker's identifier

        Returns:
            Dictionary mapping digits to embedding arrays
        """
        ...

    def get_voiceprint(self, speaker_id: str, digit: str) -> np.ndarray:
        """Get a specific voiceprint for a speaker.

        Args:
            speaker_id: The speaker's identifier
            digit: The digit ("0" to "9")

        Returns:
            numpy array of shape (512,) with float32 dtype
        """
        ...

    def has_complete_voiceprints(self, speaker_id: str) -> bool:
        """Check if a speaker has voiceprints for all digits (0-9).

        Args:
            speaker_id: The speaker's identifier

        Returns:
            True if speaker has all 10 digit voiceprints
        """
        ...
