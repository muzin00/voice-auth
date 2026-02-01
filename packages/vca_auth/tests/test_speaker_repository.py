"""Tests for SpeakerRepository."""

import numpy as np
import pytest
from sqlmodel import Session
from vca_auth.models import EMBEDDING_DIM
from vca_auth.repositories import (
    SpeakerAlreadyExistsError,
    SpeakerNotFoundError,
    SpeakerRepository,
)


@pytest.fixture
def repo(session: Session) -> SpeakerRepository:
    """Create a SpeakerRepository instance."""
    return SpeakerRepository(session)


class TestCreateSpeaker:
    """Tests for create_speaker method."""

    def test_create_speaker_basic(self, repo: SpeakerRepository) -> None:
        """Test creating a basic speaker."""
        speaker = repo.create_speaker(speaker_id="user1")

        assert speaker.id is not None
        assert speaker.speaker_id == "user1"
        assert speaker.speaker_name is None
        assert speaker.pin_hash is None

    def test_create_speaker_with_all_fields(self, repo: SpeakerRepository) -> None:
        """Test creating a speaker with all fields."""
        speaker = repo.create_speaker(
            speaker_id="user1",
            speaker_name="Test User",
            pin_hash="a" * 64,
        )

        assert speaker.speaker_name == "Test User"
        assert speaker.pin_hash == "a" * 64

    def test_create_speaker_duplicate_raises(self, repo: SpeakerRepository) -> None:
        """Test that creating duplicate speaker raises error."""
        repo.create_speaker(speaker_id="user1")

        with pytest.raises(SpeakerAlreadyExistsError):
            repo.create_speaker(speaker_id="user1")


class TestGetSpeaker:
    """Tests for get_speaker methods."""

    def test_get_speaker_by_id(self, repo: SpeakerRepository) -> None:
        """Test getting speaker by speaker_id."""
        created = repo.create_speaker(speaker_id="user1", speaker_name="Test")
        fetched = repo.get_speaker_by_id("user1")

        assert fetched.id == created.id
        assert fetched.speaker_name == "Test"

    def test_get_speaker_by_id_not_found(self, repo: SpeakerRepository) -> None:
        """Test that getting nonexistent speaker raises error."""
        with pytest.raises(SpeakerNotFoundError):
            repo.get_speaker_by_id("nonexistent")

    def test_get_speaker_by_public_id(self, repo: SpeakerRepository) -> None:
        """Test getting speaker by public_id."""
        created = repo.create_speaker(speaker_id="user1")
        fetched = repo.get_speaker_by_public_id(created.public_id)

        assert fetched.id == created.id

    def test_get_speaker_by_public_id_not_found(self, repo: SpeakerRepository) -> None:
        """Test that getting by nonexistent public_id raises error."""
        with pytest.raises(SpeakerNotFoundError):
            repo.get_speaker_by_public_id("nonexistent")


class TestSpeakerExists:
    """Tests for speaker_exists method."""

    def test_speaker_exists_true(self, repo: SpeakerRepository) -> None:
        """Test speaker_exists returns True for existing speaker."""
        repo.create_speaker(speaker_id="user1")
        assert repo.speaker_exists("user1") is True

    def test_speaker_exists_false(self, repo: SpeakerRepository) -> None:
        """Test speaker_exists returns False for nonexistent speaker."""
        assert repo.speaker_exists("nonexistent") is False


class TestUpdateSpeakerPin:
    """Tests for update_speaker_pin method."""

    def test_update_speaker_pin(self, repo: SpeakerRepository) -> None:
        """Test updating speaker PIN."""
        repo.create_speaker(speaker_id="user1")
        updated = repo.update_speaker_pin("user1", "b" * 64)

        assert updated.pin_hash == "b" * 64

    def test_update_speaker_pin_to_none(self, repo: SpeakerRepository) -> None:
        """Test removing speaker PIN."""
        repo.create_speaker(speaker_id="user1", pin_hash="a" * 64)
        updated = repo.update_speaker_pin("user1", None)

        assert updated.pin_hash is None

    def test_update_speaker_pin_not_found(self, repo: SpeakerRepository) -> None:
        """Test updating nonexistent speaker raises error."""
        with pytest.raises(SpeakerNotFoundError):
            repo.update_speaker_pin("nonexistent", "a" * 64)


class TestDeleteSpeaker:
    """Tests for delete_speaker method."""

    def test_delete_speaker(self, repo: SpeakerRepository) -> None:
        """Test deleting a speaker."""
        repo.create_speaker(speaker_id="user1")
        repo.delete_speaker("user1")

        assert repo.speaker_exists("user1") is False

    def test_delete_speaker_not_found(self, repo: SpeakerRepository) -> None:
        """Test deleting nonexistent speaker raises error."""
        with pytest.raises(SpeakerNotFoundError):
            repo.delete_speaker("nonexistent")


class TestAddVoiceprint:
    """Tests for add_voiceprint method."""

    def test_add_voiceprint(self, repo: SpeakerRepository) -> None:
        """Test adding a voiceprint."""
        repo.create_speaker(speaker_id="user1")
        embedding = np.random.randn(EMBEDDING_DIM).astype(np.float32)

        voiceprint = repo.add_voiceprint("user1", "5", embedding)

        assert voiceprint.digit == "5"
        assert voiceprint.speaker_id is not None

    def test_add_voiceprint_updates_existing(self, repo: SpeakerRepository) -> None:
        """Test that adding voiceprint for same digit updates it."""
        repo.create_speaker(speaker_id="user1")
        embedding1 = np.ones(EMBEDDING_DIM, dtype=np.float32)
        embedding2 = np.zeros(EMBEDDING_DIM, dtype=np.float32)

        vp1 = repo.add_voiceprint("user1", "5", embedding1)
        original_public_id = vp1.public_id
        vp2 = repo.add_voiceprint("user1", "5", embedding2)

        # Public ID should change when updated
        assert original_public_id != vp2.public_id

        # Verify the stored embedding is the new one
        stored = repo.get_voiceprint("user1", "5")
        np.testing.assert_array_equal(stored, embedding2)

    def test_add_voiceprint_speaker_not_found(self, repo: SpeakerRepository) -> None:
        """Test adding voiceprint to nonexistent speaker raises error."""
        embedding = np.random.randn(EMBEDDING_DIM).astype(np.float32)

        with pytest.raises(SpeakerNotFoundError):
            repo.add_voiceprint("nonexistent", "5", embedding)


class TestAddVoiceprintsBulk:
    """Tests for add_voiceprints_bulk method."""

    def test_add_voiceprints_bulk(self, repo: SpeakerRepository) -> None:
        """Test adding multiple voiceprints at once."""
        repo.create_speaker(speaker_id="user1")
        embeddings = {
            str(i): np.random.randn(EMBEDDING_DIM).astype(np.float32) for i in range(10)
        }

        voiceprints = repo.add_voiceprints_bulk("user1", embeddings)

        assert len(voiceprints) == 10
        assert repo.has_complete_voiceprints("user1") is True

    def test_add_voiceprints_bulk_partial_update(self, repo: SpeakerRepository) -> None:
        """Test bulk add with some existing voiceprints."""
        repo.create_speaker(speaker_id="user1")

        # Add some initial voiceprints
        for i in range(5):
            embedding = np.random.randn(EMBEDDING_DIM).astype(np.float32)
            repo.add_voiceprint("user1", str(i), embedding)

        # Bulk add all 10 (should update existing, create new)
        new_embeddings = {
            str(i): np.random.randn(EMBEDDING_DIM).astype(np.float32) for i in range(10)
        }
        voiceprints = repo.add_voiceprints_bulk("user1", new_embeddings)

        assert len(voiceprints) == 10
        assert repo.has_complete_voiceprints("user1") is True


class TestGetVoiceprints:
    """Tests for get_voiceprints method."""

    def test_get_voiceprints(self, repo: SpeakerRepository) -> None:
        """Test getting all voiceprints for a speaker."""
        repo.create_speaker(speaker_id="user1")
        expected = {}
        for i in range(5):
            embedding = np.random.randn(EMBEDDING_DIM).astype(np.float32)
            repo.add_voiceprint("user1", str(i), embedding)
            expected[str(i)] = embedding

        result = repo.get_voiceprints("user1")

        assert len(result) == 5
        for digit, embedding in expected.items():
            np.testing.assert_array_almost_equal(result[digit], embedding)

    def test_get_voiceprints_empty(self, repo: SpeakerRepository) -> None:
        """Test getting voiceprints when none exist."""
        repo.create_speaker(speaker_id="user1")
        result = repo.get_voiceprints("user1")
        assert result == {}


class TestGetVoiceprint:
    """Tests for get_voiceprint method."""

    def test_get_voiceprint(self, repo: SpeakerRepository) -> None:
        """Test getting a specific voiceprint."""
        repo.create_speaker(speaker_id="user1")
        embedding = np.random.randn(EMBEDDING_DIM).astype(np.float32)
        repo.add_voiceprint("user1", "5", embedding)

        result = repo.get_voiceprint("user1", "5")
        np.testing.assert_array_almost_equal(result, embedding)

    def test_get_voiceprint_not_found(self, repo: SpeakerRepository) -> None:
        """Test getting nonexistent voiceprint raises error."""
        repo.create_speaker(speaker_id="user1")

        with pytest.raises(ValueError, match="Voiceprint for digit '5' not found"):
            repo.get_voiceprint("user1", "5")


class TestHasCompleteVoiceprints:
    """Tests for has_complete_voiceprints method."""

    def test_has_complete_voiceprints_true(self, repo: SpeakerRepository) -> None:
        """Test has_complete_voiceprints returns True with all digits."""
        repo.create_speaker(speaker_id="user1")
        for i in range(10):
            embedding = np.random.randn(EMBEDDING_DIM).astype(np.float32)
            repo.add_voiceprint("user1", str(i), embedding)

        assert repo.has_complete_voiceprints("user1") is True

    def test_has_complete_voiceprints_false_partial(
        self, repo: SpeakerRepository
    ) -> None:
        """Test has_complete_voiceprints returns False with partial digits."""
        repo.create_speaker(speaker_id="user1")
        for i in range(5):
            embedding = np.random.randn(EMBEDDING_DIM).astype(np.float32)
            repo.add_voiceprint("user1", str(i), embedding)

        assert repo.has_complete_voiceprints("user1") is False

    def test_has_complete_voiceprints_false_empty(
        self, repo: SpeakerRepository
    ) -> None:
        """Test has_complete_voiceprints returns False with no voiceprints."""
        repo.create_speaker(speaker_id="user1")
        assert repo.has_complete_voiceprints("user1") is False
