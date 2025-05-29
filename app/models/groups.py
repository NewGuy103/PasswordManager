import uuid
from typing import Annotated
from pydantic import BaseModel, Field


GroupName = Annotated[str, Field(min_length=1)]


class GroupBase(BaseModel):
    group_name: GroupName
    parent_id: uuid.UUID | None  # None for the top-level group


class GroupCreate(GroupBase):
    group_name: GroupName
    parent_id: uuid.UUID


class GroupPublic(GroupBase):
    group_id: uuid.UUID


class GroupPublicModify(GroupPublic):
    """
    Leave out `child_groups` list for operations like create and rename.
    """
    pass


class GroupPublicGet(GroupPublic):
    child_groups: list['GroupPublicChildren']


# Leave out child_groups intentionally
class GroupPublicChildren(GroupPublic):
    parent_id: uuid.UUID


# Simple models
class GroupRename(BaseModel):
    new_name: GroupName


class GroupMove(BaseModel):
    new_parent_id: uuid.UUID
