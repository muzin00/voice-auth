"""Database exceptions."""


class DatabaseError(Exception):
    """Base exception for database operations."""

    pass


class SpeakerNotFoundError(DatabaseError):
    """Raised when a speaker is not found."""

    pass


class SpeakerAlreadyExistsError(DatabaseError):
    """Raised when attempting to create a speaker that already exists."""

    pass


class VoiceprintNotFoundError(DatabaseError):
    """Raised when a voiceprint is not found."""

    pass
