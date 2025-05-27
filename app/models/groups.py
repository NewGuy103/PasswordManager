import uuid
from typing import Annotated
from pydantic import BaseModel, AfterValidator, Field


def check_is_root(value: str):
    if value == 'Root':
        raise ValueError("group_name cannot be 'Root'")
    
    return value


GroupName = Annotated[str, Field(min_length=1)]
CannotBeRoot = Annotated[GroupName, AfterValidator(check_is_root)]

class GroupBase(BaseModel):
    group_name: GroupName


class GroupCreate(GroupBase):
    group_name: CannotBeRoot


class GroupPublicGet(GroupBase):
    group_id: uuid.UUID


class GroupRename(BaseModel):
    new_name: CannotBeRoot
