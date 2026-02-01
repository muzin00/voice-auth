"""Speaker repository for database operations."""

from datetime import UTC, datetime

import numpy as np
from sqlmodel import Session, select
from ulid import ULID

from vca_auth.models import DigitVoiceprint, Speaker


class SpeakerNotFoundError(Exception):
    """Raised when a speaker is not found."""

    pass


class SpeakerAlreadyExistsError(Exception):
    """Raised when attempting to create a speaker that already exists."""

    pass


class SpeakerRepository:
    """Repository for Speaker and DigitVoiceprint database operations."""

    def __init__(self, session: Session) -> None:
        """Initialize repository with a database session.

        Args:
            session: SQLModel database session
        """
        self.session = session

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

        Raises:
            SpeakerAlreadyExistsError: If speaker_id already exists
        """
        if self.speaker_exists(speaker_id):
            raise SpeakerAlreadyExistsError(f"Speaker '{speaker_id}' already exists")

        speaker = Speaker(
            speaker_id=speaker_id,
            speaker_name=speaker_name,
            pin_hash=pin_hash,
        )
        self.session.add(speaker)
        self.session.commit()
        self.session.refresh(speaker)
        return speaker

    def get_speaker_by_id(self, speaker_id: str) -> Speaker:
        """Get a speaker by their speaker_id.

        Args:
            speaker_id: The speaker's identifier

        Returns:
            The Speaker instance

        Raises:
            SpeakerNotFoundError: If speaker not found
        """
        statement = select(Speaker).where(Speaker.speaker_id == speaker_id)
        speaker = self.session.exec(statement).first()
        if speaker is None:
            raise SpeakerNotFoundError(f"Speaker '{speaker_id}' not found")
        return speaker

    def get_speaker_by_public_id(self, public_id: str) -> Speaker:
        """Get a speaker by their public_id (ULID).

        Args:
            public_id: The speaker's public ULID

        Returns:
            The Speaker instance

        Raises:
            SpeakerNotFoundError: If speaker not found
        """
        statement = select(Speaker).where(Speaker.public_id == public_id)
        speaker = self.session.exec(statement).first()
        if speaker is None:
            raise SpeakerNotFoundError(
                f"Speaker with public_id '{public_id}' not found"
            )
        return speaker

    def speaker_exists(self, speaker_id: str) -> bool:
        """Check if a speaker exists.

        Args:
            speaker_id: The speaker's identifier

        Returns:
            True if speaker exists, False otherwise
        """
        statement = select(Speaker).where(Speaker.speaker_id == speaker_id)
        return self.session.exec(statement).first() is not None

    def update_speaker_pin(self, speaker_id: str, pin_hash: str | None) -> Speaker:
        """Update a speaker's PIN hash.

        Args:
            speaker_id: The speaker's identifier
            pin_hash: New SHA-256 hash of PIN (or None to remove)

        Returns:
            The updated Speaker instance

        Raises:
            SpeakerNotFoundError: If speaker not found
        """
        speaker = self.get_speaker_by_id(speaker_id)
        speaker.pin_hash = pin_hash
        speaker.updated_at = datetime.now(UTC)
        self.session.add(speaker)
        self.session.commit()
        self.session.refresh(speaker)
        return speaker

    def delete_speaker(self, speaker_id: str) -> None:
        """Delete a speaker and all associated voiceprints.

        Args:
            speaker_id: The speaker's identifier

        Raises:
            SpeakerNotFoundError: If speaker not found
        """
        speaker = self.get_speaker_by_id(speaker_id)
        self.session.delete(speaker)
        self.session.commit()

    def add_voiceprint(
        self, speaker_id: str, digit: str, embedding: np.ndarray
    ) -> DigitVoiceprint:
        """Add or update a voiceprint for a speaker.

        Args:
            speaker_id: The speaker's identifier
            digit: The digit ("0" to "9")
            embedding: numpy array of shape (512,) with float32 dtype

        Returns:
            The created or updated DigitVoiceprint instance

        Raises:
            SpeakerNotFoundError: If speaker not found
        """
        speaker = self.get_speaker_by_id(speaker_id)

        # Check for existing voiceprint
        statement = select(DigitVoiceprint).where(
            DigitVoiceprint.speaker_id == speaker.id,
            DigitVoiceprint.digit == digit,
        )
        existing = self.session.exec(statement).first()

        if existing:
            # Update existing voiceprint
            existing.embedding = DigitVoiceprint.serialize_embedding(embedding)
            existing.public_id = str(ULID())
            existing.created_at = datetime.now(UTC)
            self.session.add(existing)
            self.session.commit()
            self.session.refresh(existing)
            return existing

        # Create new voiceprint
        voiceprint = DigitVoiceprint(
            speaker_id=speaker.id,  # type: ignore[arg-type]
            digit=digit,
            embedding=DigitVoiceprint.serialize_embedding(embedding),
        )
        self.session.add(voiceprint)
        self.session.commit()
        self.session.refresh(voiceprint)
        return voiceprint

    def add_voiceprints_bulk(
        self, speaker_id: str, embeddings: dict[str, np.ndarray]
    ) -> list[DigitVoiceprint]:
        """Add or update multiple voiceprints for a speaker.

        Args:
            speaker_id: The speaker's identifier
            embeddings: Dictionary mapping digits to embeddings

        Returns:
            List of created/updated DigitVoiceprint instances

        Raises:
            SpeakerNotFoundError: If speaker not found
        """
        speaker = self.get_speaker_by_id(speaker_id)
        voiceprints = []

        for digit, embedding in embeddings.items():
            # Check for existing voiceprint
            statement = select(DigitVoiceprint).where(
                DigitVoiceprint.speaker_id == speaker.id,
                DigitVoiceprint.digit == digit,
            )
            existing = self.session.exec(statement).first()

            if existing:
                # Update existing
                existing.embedding = DigitVoiceprint.serialize_embedding(embedding)
                existing.public_id = str(ULID())
                existing.created_at = datetime.now(UTC)
                self.session.add(existing)
                voiceprints.append(existing)
            else:
                # Create new
                voiceprint = DigitVoiceprint(
                    speaker_id=speaker.id,  # type: ignore[arg-type]
                    digit=digit,
                    embedding=DigitVoiceprint.serialize_embedding(embedding),
                )
                self.session.add(voiceprint)
                voiceprints.append(voiceprint)

        self.session.commit()
        for vp in voiceprints:
            self.session.refresh(vp)
        return voiceprints

    def get_voiceprints(self, speaker_id: str) -> dict[str, np.ndarray]:
        """Get all voiceprints for a speaker.

        Args:
            speaker_id: The speaker's identifier

        Returns:
            Dictionary mapping digits to embedding arrays

        Raises:
            SpeakerNotFoundError: If speaker not found
        """
        speaker = self.get_speaker_by_id(speaker_id)
        statement = select(DigitVoiceprint).where(
            DigitVoiceprint.speaker_id == speaker.id
        )
        results = self.session.exec(statement).all()
        return {
            vp.digit: DigitVoiceprint.deserialize_embedding(vp.embedding)
            for vp in results
        }

    def get_voiceprint(self, speaker_id: str, digit: str) -> np.ndarray:
        """Get a specific voiceprint for a speaker.

        Args:
            speaker_id: The speaker's identifier
            digit: The digit ("0" to "9")

        Returns:
            numpy array of shape (512,) with float32 dtype

        Raises:
            SpeakerNotFoundError: If speaker not found
            ValueError: If voiceprint for digit not found
        """
        speaker = self.get_speaker_by_id(speaker_id)
        statement = select(DigitVoiceprint).where(
            DigitVoiceprint.speaker_id == speaker.id,
            DigitVoiceprint.digit == digit,
        )
        voiceprint = self.session.exec(statement).first()
        if voiceprint is None:
            raise ValueError(
                f"Voiceprint for digit '{digit}' not found for speaker '{speaker_id}'"
            )
        return DigitVoiceprint.deserialize_embedding(voiceprint.embedding)

    def has_complete_voiceprints(self, speaker_id: str) -> bool:
        """Check if a speaker has voiceprints for all digits (0-9).

        Args:
            speaker_id: The speaker's identifier

        Returns:
            True if speaker has all 10 digit voiceprints

        Raises:
            SpeakerNotFoundError: If speaker not found
        """
        voiceprints = self.get_voiceprints(speaker_id)
        required_digits = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9"}
        return set(voiceprints.keys()) == required_digits
