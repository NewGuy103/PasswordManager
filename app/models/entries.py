import uuid

from typing import Annotated
from pydantic import BaseModel, Field


GroupName = Annotated[str, Field(min_length=1)]


class EntryBase(BaseModel):
    entry_name: Annotated[str, Field(min_length=1)]
    entry_data: Annotated[str, Field(min_length=1)]


class EntryCreate(EntryBase):
    pass


class EntryPublicGet(EntryBase):
    entry_id: uuid.UUID
    group_name: GroupName
