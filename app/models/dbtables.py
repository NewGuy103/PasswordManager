from typing import Optional
import uuid
import secrets

from datetime import datetime, timedelta, timezone
from sqlmodel import Column, SQLModel, Field, DateTime, Relationship, TypeDecorator


class TZDateTime(TypeDecorator):
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if not value.tzinfo or value.tzinfo.utcoffset(value) is None:
                raise TypeError("tzinfo is required")
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = value.replace(tzinfo=timezone.utc)
        return value


class UserBase(SQLModel):
    user_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    username: str = Field(max_length=30, nullable=False, unique=True, index=True, min_length=1)
    hashed_password: str = Field(max_length=100, nullable=False)


class Users(UserBase, table=True):
    sessions: list['UserSessions'] = Relationship(
        back_populates='user', 
        sa_relationship_kwargs={'lazy': 'selectin'},
        passive_deletes='all'
    )
    groups: list['PasswordGroups'] = Relationship(
        back_populates='user',
        sa_relationship_kwargs={'lazy': 'selectin'},
        passive_deletes='all'
    )


class UserSessions(SQLModel, table=True):
    session_token: str = Field(
        primary_key=True, max_length=45, 
        default_factory=lambda: secrets.token_urlsafe(32)
    )
    expiry_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(15),
        sa_column=Column(TZDateTime, index=True)
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TZDateTime)
    )
    user_id: uuid.UUID = Field(foreign_key='users.user_id', ondelete='CASCADE')
    user: Users = Relationship(
        back_populates='sessions', 
        sa_relationship_kwargs={'lazy': 'selectin'}
    )


# TODO: Make this self-referential so groups can have child/parent groups
class PasswordGroups(SQLModel, table=True):
    group_id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    group_name: str = Field(min_length=1, nullable=False, index=True)

    user_id: uuid.UUID = Field(foreign_key='users.user_id', ondelete='CASCADE')

    entries: list['PasswordEntry'] = Relationship(
        back_populates='group',
        sa_relationship_kwargs={'lazy': 'selectin'},
        passive_deletes='all'
    )
    user: Users = Relationship(
        back_populates='groups', 
        sa_relationship_kwargs={'lazy': 'selectin'}
    )


# TODO: Add metadata and encryption
class PasswordEntry(SQLModel, table=True):
    entry_id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    entry_name: str = Field(min_length=1, nullable=False, index=True)

    entry_data: str = Field(min_length=1, nullable=False)

    group_id: uuid.UUID = Field(foreign_key='passwordgroups.group_id', ondelete='CASCADE')
    group: PasswordGroups = Relationship(
        back_populates='entries',
        sa_relationship_kwargs={'lazy': 'selectin'}
    )
