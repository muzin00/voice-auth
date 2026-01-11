from sqlmodel import Field, SQLModel


class Speaker(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    speaker_id: str = Field(index=True, unique=True, max_length=100)
    speaker_name: str | None = Field(default=None, max_length=100)
