import uuid

from typing import Annotated
from pydantic import BaseModel, Field, AnyUrl


class EntryBase(BaseModel):
    entry_name: Annotated[str, Field(min_length=1)]
    entry_username: str

    entry_password: str
    entry_url: AnyUrl


class EntryCreate(EntryBase):
    pass


class EntryUpdate(EntryBase):
    pass


class EntryPublicGet(EntryBase):
    entry_id: uuid.UUID
    group_id: uuid.UUID
