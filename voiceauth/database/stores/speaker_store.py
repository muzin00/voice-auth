"""Speaker store for database operations."""

from datetime import UTC, datetime

import numpy as np
import ulid
from sqlmodel import Session, select

from voiceauth.database.exceptions import (
    SpeakerAlreadyExistsError,
    SpeakerNotFoundError,
    VoiceprintNotFoundError,
)
from voiceauth.database.models import SpeakerModel, VoiceprintModel
from voiceauth.domain.models import Speaker, Voiceprint


class SpeakerStore:
    """Store for Speaker and Voiceprint database operations.

    Implements SpeakerStoreProtocol from voiceauth.domain.protocols.store.
    """

    def __init__(self, session: Session) -> None:
        """Initialize store with a database session.

        Args:
            session: SQLModel database session
        """
        self.session = session

    def _to_domain_speaker(self, model: SpeakerModel) -> Speaker:
        """Convert database model to domain model."""
        return Speaker(
            id=model.id,
            public_id=model.public_id,
            speaker_id=model.speaker_id,
            speaker_name=model.speaker_name,
            pin_hash=model.pin_hash,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_domain_voiceprint(self, model: VoiceprintModel) -> Voiceprint:
        """Convert database model to domain model."""
        return Voiceprint(
            id=model.id,
            public_id=model.public_id,
            speaker_id=model.speaker_id,
            digit=model.digit,
            embedding=model.embedding,
            created_at=model.created_at,
        )

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

        model = SpeakerModel(
            speaker_id=speaker_id,
            speaker_name=speaker_name,
            pin_hash=pin_hash,
        )
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return self._to_domain_speaker(model)

    def get_speaker_by_id(self, speaker_id: str) -> Speaker:
        """Get a speaker by their speaker_id.

        Args:
            speaker_id: The speaker's identifier

        Returns:
            The Speaker instance

        Raises:
            SpeakerNotFoundError: If speaker not found
        """
        statement = select(SpeakerModel).where(SpeakerModel.speaker_id == speaker_id)
        model = self.session.exec(statement).first()
        if model is None:
            raise SpeakerNotFoundError(f"Speaker '{speaker_id}' not found")
        return self._to_domain_speaker(model)

    def get_speaker_by_public_id(self, public_id: str) -> Speaker:
        """Get a speaker by their public_id (ULID).

        Args:
            public_id: The speaker's public ULID

        Returns:
            The Speaker instance

        Raises:
            SpeakerNotFoundError: If speaker not found
        """
        statement = select(SpeakerModel).where(SpeakerModel.public_id == public_id)
        model = self.session.exec(statement).first()
        if model is None:
            raise SpeakerNotFoundError(
                f"Speaker with public_id '{public_id}' not found"
            )
        return self._to_domain_speaker(model)

    def speaker_exists(self, speaker_id: str) -> bool:
        """Check if a speaker exists.

        Args:
            speaker_id: The speaker's identifier

        Returns:
            True if speaker exists, False otherwise
        """
        statement = select(SpeakerModel).where(SpeakerModel.speaker_id == speaker_id)
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
        statement = select(SpeakerModel).where(SpeakerModel.speaker_id == speaker_id)
        model = self.session.exec(statement).first()
        if model is None:
            raise SpeakerNotFoundError(f"Speaker '{speaker_id}' not found")

        model.pin_hash = pin_hash
        model.updated_at = datetime.now(UTC)
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return self._to_domain_speaker(model)

    def delete_speaker(self, speaker_id: str) -> None:
        """Delete a speaker and all associated voiceprints.

        Args:
            speaker_id: The speaker's identifier

        Raises:
            SpeakerNotFoundError: If speaker not found
        """
        statement = select(SpeakerModel).where(SpeakerModel.speaker_id == speaker_id)
        model = self.session.exec(statement).first()
        if model is None:
            raise SpeakerNotFoundError(f"Speaker '{speaker_id}' not found")

        self.session.delete(model)
        self.session.commit()

    def _get_speaker_model(self, speaker_id: str) -> SpeakerModel:
        """Get speaker model by speaker_id."""
        statement = select(SpeakerModel).where(SpeakerModel.speaker_id == speaker_id)
        model = self.session.exec(statement).first()
        if model is None:
            raise SpeakerNotFoundError(f"Speaker '{speaker_id}' not found")
        return model

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

        Raises:
            SpeakerNotFoundError: If speaker not found
        """
        speaker_model = self._get_speaker_model(speaker_id)

        # Check for existing voiceprint
        statement = select(VoiceprintModel).where(
            VoiceprintModel.speaker_id == speaker_model.id,
            VoiceprintModel.digit == digit,
        )
        existing = self.session.exec(statement).first()

        if existing:
            # Update existing voiceprint
            existing.embedding = VoiceprintModel.serialize_embedding(embedding)
            existing.public_id = str(ulid.new())
            existing.created_at = datetime.now(UTC)
            self.session.add(existing)
            self.session.commit()
            self.session.refresh(existing)
            return self._to_domain_voiceprint(existing)

        # Create new voiceprint
        model = VoiceprintModel(
            speaker_id=speaker_model.id,
            digit=digit,
            embedding=VoiceprintModel.serialize_embedding(embedding),
        )
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return self._to_domain_voiceprint(model)

    def add_voiceprints_bulk(
        self, speaker_id: str, embeddings: dict[str, np.ndarray]
    ) -> list[Voiceprint]:
        """Add or update multiple voiceprints for a speaker.

        Args:
            speaker_id: The speaker's identifier
            embeddings: Dictionary mapping digits to embeddings

        Returns:
            List of created/updated Voiceprint instances

        Raises:
            SpeakerNotFoundError: If speaker not found
        """
        speaker_model = self._get_speaker_model(speaker_id)
        voiceprints: list[VoiceprintModel] = []

        for digit, embedding in embeddings.items():
            # Check for existing voiceprint
            statement = select(VoiceprintModel).where(
                VoiceprintModel.speaker_id == speaker_model.id,
                VoiceprintModel.digit == digit,
            )
            existing = self.session.exec(statement).first()

            if existing:
                # Update existing
                existing.embedding = VoiceprintModel.serialize_embedding(embedding)
                existing.public_id = str(ulid.new())
                existing.created_at = datetime.now(UTC)
                self.session.add(existing)
                voiceprints.append(existing)
            else:
                # Create new
                model = VoiceprintModel(
                    speaker_id=speaker_model.id,
                    digit=digit,
                    embedding=VoiceprintModel.serialize_embedding(embedding),
                )
                self.session.add(model)
                voiceprints.append(model)

        self.session.commit()
        for vp in voiceprints:
            self.session.refresh(vp)
        return [self._to_domain_voiceprint(vp) for vp in voiceprints]

    def get_voiceprints(self, speaker_id: str) -> dict[str, np.ndarray]:
        """Get all voiceprints for a speaker.

        Args:
            speaker_id: The speaker's identifier

        Returns:
            Dictionary mapping digits to embedding arrays

        Raises:
            SpeakerNotFoundError: If speaker not found
        """
        speaker_model = self._get_speaker_model(speaker_id)
        statement = select(VoiceprintModel).where(
            VoiceprintModel.speaker_id == speaker_model.id
        )
        results = self.session.exec(statement).all()
        return {
            vp.digit: VoiceprintModel.deserialize_embedding(vp.embedding)
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
            VoiceprintNotFoundError: If voiceprint for digit not found
        """
        speaker_model = self._get_speaker_model(speaker_id)
        statement = select(VoiceprintModel).where(
            VoiceprintModel.speaker_id == speaker_model.id,
            VoiceprintModel.digit == digit,
        )
        model = self.session.exec(statement).first()
        if model is None:
            raise VoiceprintNotFoundError(
                f"Voiceprint for digit '{digit}' not found for speaker '{speaker_id}'"
            )
        return VoiceprintModel.deserialize_embedding(model.embedding)

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
