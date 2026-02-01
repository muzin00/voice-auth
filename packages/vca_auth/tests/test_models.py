"""Tests for vca_auth models."""

import numpy as np
from sqlmodel import Session
from vca_auth.models import EMBEDDING_DIM, DigitVoiceprint, Speaker


class TestSpeaker:
    """Tests for Speaker model."""

    def test_create_speaker(self, session: Session) -> None:
        """Test creating a speaker."""
        speaker = Speaker(speaker_id="test_user", speaker_name="Test User")
        session.add(speaker)
        session.commit()
        session.refresh(speaker)

        assert speaker.id is not None
        assert speaker.public_id is not None
        assert len(speaker.public_id) == 26  # ULID length
        assert speaker.speaker_id == "test_user"
        assert speaker.speaker_name == "Test User"
        assert speaker.pin_hash is None
        assert speaker.created_at is not None
        assert speaker.updated_at is not None

    def test_speaker_with_pin_hash(self, session: Session) -> None:
        """Test creating a speaker with PIN hash."""
        pin_hash = "a" * 64  # SHA-256 produces 64 hex chars
        speaker = Speaker(
            speaker_id="test_user",
            speaker_name="Test User",
            pin_hash=pin_hash,
        )
        session.add(speaker)
        session.commit()
        session.refresh(speaker)

        assert speaker.pin_hash == pin_hash

    def test_public_id_is_unique(self, session: Session) -> None:
        """Test that public_id is automatically generated and unique."""
        speaker1 = Speaker(speaker_id="user1")
        speaker2 = Speaker(speaker_id="user2")
        session.add_all([speaker1, speaker2])
        session.commit()

        assert speaker1.public_id != speaker2.public_id


class TestDigitVoiceprint:
    """Tests for DigitVoiceprint model."""

    def test_create_voiceprint(self, session: Session) -> None:
        """Test creating a voiceprint."""
        speaker = Speaker(speaker_id="test_user")
        session.add(speaker)
        session.commit()
        session.refresh(speaker)

        embedding = np.random.randn(EMBEDDING_DIM).astype(np.float32)
        assert speaker.id is not None
        voiceprint = DigitVoiceprint(
            speaker_id=speaker.id,
            digit="5",
            embedding=DigitVoiceprint.serialize_embedding(embedding),
        )
        session.add(voiceprint)
        session.commit()
        session.refresh(voiceprint)

        assert voiceprint.id is not None
        assert voiceprint.public_id is not None
        assert voiceprint.digit == "5"
        assert voiceprint.speaker_id == speaker.id

    def test_serialize_deserialize_embedding(self) -> None:
        """Test embedding serialization and deserialization."""
        original = np.random.randn(EMBEDDING_DIM).astype(np.float32)
        serialized = DigitVoiceprint.serialize_embedding(original)
        deserialized = DigitVoiceprint.deserialize_embedding(serialized)

        assert isinstance(serialized, bytes)
        assert len(serialized) == EMBEDDING_DIM * 4  # 4 bytes per float32
        np.testing.assert_array_almost_equal(original, deserialized)

    def test_embedding_dimension(self) -> None:
        """Test that EMBEDDING_DIM is 512."""
        assert EMBEDDING_DIM == 512

    def test_voiceprint_relationship(self, session: Session) -> None:
        """Test voiceprint relationship to speaker."""
        speaker = Speaker(speaker_id="test_user")
        session.add(speaker)
        session.commit()
        session.refresh(speaker)

        embedding = np.random.randn(EMBEDDING_DIM).astype(np.float32)
        assert speaker.id is not None
        voiceprint = DigitVoiceprint(
            speaker_id=speaker.id,
            digit="0",
            embedding=DigitVoiceprint.serialize_embedding(embedding),
        )
        session.add(voiceprint)
        session.commit()
        session.refresh(voiceprint)

        assert voiceprint.speaker.speaker_id == "test_user"

    def test_cascade_delete(self, session: Session) -> None:
        """Test that deleting a speaker deletes associated voiceprints."""
        speaker = Speaker(speaker_id="test_user")
        session.add(speaker)
        session.commit()
        session.refresh(speaker)

        embedding = np.random.randn(EMBEDDING_DIM).astype(np.float32)
        assert speaker.id is not None
        voiceprint = DigitVoiceprint(
            speaker_id=speaker.id,
            digit="0",
            embedding=DigitVoiceprint.serialize_embedding(embedding),
        )
        session.add(voiceprint)
        session.commit()

        voiceprint_id = voiceprint.id
        session.delete(speaker)
        session.commit()

        # Verify voiceprint was deleted
        from sqlmodel import select

        result = session.exec(
            select(DigitVoiceprint).where(DigitVoiceprint.id == voiceprint_id)
        ).first()
        assert result is None
