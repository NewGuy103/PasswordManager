import asyncio
import typing
import logging

import secrets

from datetime import datetime, timezone
import uuid

from sqlalchemy.pool import AsyncAdaptedQueuePool
from sqlalchemy.ext.asyncio import create_async_engine

from sqlmodel import select, SQLModel, true
from sqlmodel.ext.asyncio.session import AsyncSession

from .config import settings

from ..models.dbtables import Users, UserSessions, PasswordGroups, PasswordEntry
from ..models.common import UserInfo
from ..models.pwdcontext import pwd_context

from ..models.entries import EntryPublicGet
from ..models.groups import GroupPublicGet, GroupPublicChildren, GroupPublicModify

if typing.TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine


logger: logging.Logger = logging.getLogger("syncserver")
async_engine: 'AsyncEngine' = create_async_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    poolclass=AsyncAdaptedQueuePool,
    echo=False
)


DEFAULT_CHUNK_SIZE: int = 25 * 1024 * 1024  # 25 MiB


class MainDatabase:
    """Main database class.
    
    `override_engine()` is available for tests or to allow changing
    the database engine before calling `async setup()`.
    """
    def __init__(self, async_engine: 'AsyncEngine'):
        self.async_engine: 'AsyncEngine' = async_engine
    
    def override_engine(self, async_engine: 'AsyncEngine'):
        self.async_engine: 'AsyncEngine' = async_engine

    async def setup(self):
        """Sets up the database and runs first-run checks.
        
        This must be called first before using the child methods.
        """
        # Let Alembic handle creating the schema
        async with self.async_engine.begin() as conn:
            # await conn.run_sync(SQLModel.metadata.drop_all)
            await conn.run_sync(SQLModel.metadata.create_all)

        self.users = UserMethods(self)
        self.sessions = SessionMethods(self)

        self.groups = PasswordGroupMethods(self)
        self.entries = PasswordEntryMethods(self)
        
        async with AsyncSession(self.async_engine) as session:
            if not await self.get_user(session, settings.FIRST_USER_NAME):
                await self.users.add_user(session, settings.FIRST_USER_NAME, settings.FIRST_USER_PASSWORD)

    async def get_user(self, session: AsyncSession, username: str) -> Users | None:
        if not isinstance(username, str):
            raise TypeError("username is not a string")

        statement = select(Users).where(Users.username == username)
        result = await session.exec(statement)
        user: Users | None = result.one_or_none()

        if not user:
            return None

        return user
    
    async def close(self):
        await self.async_engine.dispose()


class UserMethods:
    def __init__(self, parent: MainDatabase):
        self.parent = parent
        self.async_engine = parent.async_engine

    async def add_user(self, session: AsyncSession, username: str, password: str) -> bool:
        if not isinstance(username, str):
            raise TypeError("username is not a string")

        if not isinstance(password, str):
            raise TypeError("password is not a string")
        
        stored_user: Users | None = await self.parent.get_user(session, username)
        if stored_user:
            return False

        hashed_pw: str = await asyncio.to_thread(pwd_context.hash, password)
        user = Users(username=username, hashed_password=hashed_pw)

        session.add(user)
        await session.commit()

        # Auto-create the Root group
        await self.parent.groups.create_group(session, username, 'Root', parent_id=None)
        return True
    
    async def verify_user(self, session: AsyncSession, username: str, password: str) -> str | bool:
        if not isinstance(username, str):
            raise TypeError("username is not a string")

        if not isinstance(password, str):
            raise TypeError("password is not a string")
        
        user: Users | None = await self.parent.get_user(session, username)
        if not user:
            return False

        hash_valid, new_hash = await asyncio.to_thread(
            pwd_context.verify_and_update,
            password, user.hashed_password
        )

        if not hash_valid:
            return False
        
        if new_hash:
            user.hashed_password = new_hash

        session.add(user)
        await session.commit()

        return True
    
    async def delete_user(self, session: AsyncSession, username: str):
        if not isinstance(username, str):
            raise TypeError("username is not a string")

        existing_user: Users | None = await self.parent.get_user(session, username)
        if not existing_user:
            return False
        
        if username == settings.FIRST_USER_NAME:
            raise ValueError("Cannot delete the admin user defined in the environment")
        
        result = await session.exec(select(Users).where(Users.user_id == existing_user.user_id))
        user: Users = result.one()

        await session.delete(user)
        await session.commit()
        
        return True


class SessionMethods:
    def __init__(self, parent: MainDatabase):
        self.parent = parent
        self.async_engine = parent.async_engine

    async def create_session_token(self, session: AsyncSession, username: str, expiry_date: datetime) -> str:
        if not isinstance(username, str):
            raise TypeError("username is not a string")

        date_today: datetime = datetime.now(timezone.utc)
        if date_today > expiry_date:
            raise ValueError("datetime provided has already expired")

        session_token: str = secrets.token_urlsafe(32)
        user: Users = await self.parent.get_user(session, username)
        if not user:
            raise ValueError(f"user '{username}' does not exist")

        new_session: UserSessions = UserSessions(
            session_token=session_token,
            user_id=user.user_id,
            expiry_date=expiry_date
        )
        session.add(new_session)
        await session.commit()

        return session_token
    
    async def get_token_info(self, session: AsyncSession, token: str) -> UserInfo | str:
        if not isinstance(token, str):
            raise TypeError("token is not a string")
        
        result = await session.exec(
            select(UserSessions).where(UserSessions.session_token == token)
        )
        user_session: UserSessions | None = result.one_or_none()

        if not user_session:
            raise ValueError("session token invalid")

        userinfo = UserInfo(username=user_session.user.username)
        return userinfo

    async def check_session_validity(self, session: AsyncSession, token: str) -> bool:
        if not isinstance(token, str):
            raise TypeError("token is not a string")

        statement = select(UserSessions).where(UserSessions.session_token == token)
        result = await session.exec(statement)

        user_session: UserSessions | None = result.one_or_none()
        if not user_session:
            return False

        expiry_date: datetime = user_session.expiry_date
        current_date: datetime = datetime.now(timezone.utc)

        is_not_expired: bool = expiry_date > current_date
        return is_not_expired
    
    async def revoke_session(self, session: AsyncSession, token: str):
        if not isinstance(token, str):
            raise TypeError("token is not a string")

        statement = select(UserSessions).where(UserSessions.session_token == token)
        result = await session.exec(statement)
        user_session: UserSessions | None = result.one_or_none()

        if not user_session:
            raise ValueError('invalid session token')
        
        await session.delete(user_session)
        await session.commit()
        
        return True


class PasswordGroupMethods:
    def __init__(self, parent: MainDatabase):
        self.parent = parent
        self.async_engine = parent.async_engine

    async def create_group(
        self, session: AsyncSession, 
        username: str, group_name: str,
        parent_id: uuid.UUID | None = None
    ) -> GroupPublicModify | bool:
        user: Users = await self.parent.get_user(session, username)
        if not user:
            raise ValueError("user does not exist")

        # So the 'Root' group can be created without a parent
        if parent_id:
            result2 = await session.exec(
                select(PasswordGroups)
                .where(
                    PasswordGroups.user_id == user.user_id,
                    PasswordGroups.group_id == parent_id
                )
            )
            parent_model = result2.one()
            existing_parent_id = parent_model.group_id
        else:
            assert group_name == 'Root', 'Cannot create group without parent unless its Root'
            existing_parent_id = None

            result3 = await session.exec(
                select(PasswordGroups)
                .where(
                    PasswordGroups.user_id == user.user_id,
                    PasswordGroups.is_root == true()
                )
            )
            root_model = result3.one_or_none()

            if root_model:
                raise RuntimeError("Attempted to recreate top-level group")
        
        new_group = PasswordGroups(
            group_name=group_name,
            user_id=user.user_id,
            parent_id=existing_parent_id,
            is_root=True if not parent_id else False
        )
        session.add(new_group)

        group_public = GroupPublicModify(
            group_name=group_name,
            parent_id=parent_id,
            group_id=new_group.group_id
        )

        await session.commit()
        return group_public
    
    async def get_children_of_root(self, session: AsyncSession, username: str) -> list[GroupPublicGet]:
        user: Users = await self.parent.get_user(session, username)
        if not user:
            raise ValueError("user does not exist")

        result = await session.exec(
            select(PasswordGroups)
            .where(
                PasswordGroups.user_id == user.user_id,
                PasswordGroups.is_root == true()
            )
        )
        root_group = result.one()

        models: list[GroupPublicGet] = []
        child_models: list[GroupPublicChildren] = []

        await session.refresh(root_group)
        for child in root_group.child_groups:
            child_model = GroupPublicChildren(
                group_name=child.group_name,
                parent_id=child.parent_id,
                group_id=child.group_id
            )
            child_models.append(child_model)
        
        model = GroupPublicGet(
            group_name=root_group.group_name,
            parent_id=None,
            group_id=root_group.group_id,
            child_groups=child_models
        )

        models.append(model)
        return models

    async def get_children_of_group(self, session: AsyncSession, username: str, group_id: uuid.UUID) -> list[GroupPublicGet]:
        user: Users = await self.parent.get_user(session, username)
        if not user:
            raise ValueError("user does not exist")

        result = await session.exec(
            select(PasswordGroups)
            .where(
                PasswordGroups.user_id == user.user_id,
                PasswordGroups.group_id == group_id
            )
        )
        group = result.one()

        if group.is_root:
            # Make it so that getting children of /groups/{root_id} is an alias of /groups/
            return await self.get_children_of_root(session, username)
        
        models: list[GroupPublicGet] = []
        child_models: list[GroupPublicChildren] = []

        await session.refresh(group)
        for child in group.child_groups:
            child_model = GroupPublicChildren(
                group_name=child.group_name,
                parent_id=child.parent_id,
                group_id=child.group_id
            )
            child_models.append(child_model)
        
        model = GroupPublicGet(
            group_name=group.group_name,
            parent_id=group.parent_id,
            group_id=group.group_id,
            child_groups=child_models
        )

        models.append(model)
        return models

    async def delete_group(self, session: AsyncSession, username: str, group_id: uuid.UUID) -> bool:
        user: Users = await self.parent.get_user(session, username)
        if not user:
            raise ValueError("user does not exist")

        result = await session.exec(
            select(PasswordGroups)
            .where(
                PasswordGroups.user_id == user.user_id,
                PasswordGroups.group_id == group_id
            )
        )
        group = result.one()

        if group.is_root:
            return False
        
        await session.delete(group)
        await session.commit()

        return True

    async def rename_group(
        self, session: AsyncSession, 
        username: str, group_id: uuid.UUID, 
        new_name: str
    ) -> GroupPublicModify:
        user: Users = await self.parent.get_user(session, username)
        if not user:
            raise ValueError("user does not exist")

        result = await session.exec(
            select(PasswordGroups)
            .where(
                PasswordGroups.user_id == user.user_id,
                PasswordGroups.group_id == group_id
            )
        )
        group = result.one()

        group.group_name = new_name
        session.add(group)

        group_public = GroupPublicModify(
            group_name=new_name,
            parent_id=group.parent_id,
            group_id=group.group_id
        )

        await session.commit()
        return group_public
    
    async def move_to_new_parent(
        self, session: AsyncSession,
        username: str, group_id: uuid.UUID,
        new_parent_id: uuid.UUID
    ) -> GroupPublicModify | bool:
        user: Users = await self.parent.get_user(session, username)
        if not user:
            raise ValueError("user does not exist")

        result = await session.exec(
            select(PasswordGroups)
            .where(
                PasswordGroups.user_id == user.user_id,
                PasswordGroups.group_id == group_id
            )
        )
        group = result.one()

        if group.is_root:
            raise ValueError("group is top-level Root")
        
        result = await session.exec(
            select(PasswordGroups)
            .where(
                PasswordGroups.user_id == user.user_id,
                PasswordGroups.group_id == new_parent_id
            )
        )
        parent_model = result.one_or_none()

        if not parent_model:
            return False
        
        group.parent_id = parent_model.group_id
        session.add(group)

        group_public = GroupPublicModify(
            group_name=group.group_name,
            parent_id=parent_model.group_id,
            group_id=group.group_id
        )

        await session.commit()
        return group_public

    async def check_group_exists(self, session: AsyncSession, username: str, group_id: uuid.UUID) -> bool:
        user: Users = await self.parent.get_user(session, username)
        if not user:
            raise ValueError("user does not exist")

        result = await session.exec(
            select(PasswordGroups)
            .where(
                PasswordGroups.user_id == user.user_id,
                PasswordGroups.group_id == group_id
            )
        )
        group = result.one_or_none()
        if not group:
            return False
        
        return True
    
    async def check_group_is_root(self, session: AsyncSession, username: str, group_id: uuid.UUID) -> bool:
        user: Users = await self.parent.get_user(session, username)
        if not user:
            raise ValueError("user does not exist")

        result = await session.exec(
            select(PasswordGroups)
            .where(
                PasswordGroups.user_id == user.user_id,
                PasswordGroups.group_id == group_id
            )
        )
        group = result.one()
        if not group:
            return False
        
        if not group.is_root:
            return False
        
        return True


class PasswordEntryMethods:
    def __init__(self, parent: MainDatabase):
        self.parent = parent
        self.async_engine = parent.async_engine

    async def create_entry(
        self, session: AsyncSession, 
        username: str, group_id: uuid.UUID,
        entry_name: str, entry_data: str
    ) -> EntryPublicGet | bool:
        user: Users = await self.parent.get_user(session, username)
        if not user:
            raise ValueError("user does not exist")

        result = await session.exec(
            select(PasswordGroups)
            .where(
                PasswordGroups.user_id == user.user_id,
                PasswordGroups.group_id == group_id
            )
        )
        group = result.one_or_none()

        if not group:
            return False
        
        # TODO: Encrypt password entries so its safer in the database
        new_entry = PasswordEntry(
            entry_name=entry_name,
            entry_data=entry_data,
            group_id=group.group_id
        )
        session.add(new_entry)

        entry_public = EntryPublicGet(
            entry_id=new_entry.entry_id,
            entry_name=entry_name,
            entry_data=entry_data,
            group_name=group.group_name,
            group_id=group_id
        )

        await session.commit()
        return entry_public
    
    async def get_entries_by_group(
        self, session: AsyncSession, 
        username: str, group_id: uuid.UUID,
        amount: int = 100, offset: int = 0
    ) -> list[EntryPublicGet] | bool:
        user: Users = await self.parent.get_user(session, username)
        if not user:
            raise ValueError("user does not exist")

        result = await session.exec(
            select(PasswordGroups)
            .where(
                PasswordGroups.user_id == user.user_id,
                PasswordGroups.group_id == group_id
            )
        )
        existing_group = result.one_or_none()

        if not existing_group:
            return False
        
        result = await session.exec(
            select(PasswordEntry, PasswordGroups)
            .join(PasswordGroups)
            .where(
                PasswordEntry.group_id == existing_group.group_id
            )
            .limit(amount)
            .offset(offset)
        )
        entries = result.all()

        entries_public: list[EntryPublicGet] = []
        for entry, group in entries:
            entry_public = EntryPublicGet(
                entry_name=entry.entry_name,
                entry_data=entry.entry_data,
                entry_id=entry.entry_id,
                group_name=group.group_name,
                group_id=group.group_id
            )
            entries_public.append(entry_public)
        
        return entries_public
    
    async def delete_entry_by_id(
        self, session: AsyncSession, 
        username: str, entry_id: uuid.UUID
    ) -> bool:
        user: Users = await self.parent.get_user(session, username)
        if not user:
            raise ValueError("user does not exist")

        result = await session.exec(
            select(PasswordEntry)
            .join(PasswordGroups)
            .where(
                PasswordGroups.user_id == user.user_id,
                PasswordEntry.entry_id == entry_id
            )
        )
        entry = result.one_or_none()

        if not entry:
            return False

        await session.delete(entry)
        await session.commit()
        
        return True
    
    async def replace_entry_data(
        self, session: AsyncSession, 
        username: str, entry_id: uuid.UUID,
        entry_data: str
    ) -> EntryPublicGet | bool:
        user: Users = await self.parent.get_user(session, username)
        if not user:
            raise ValueError("user does not exist")

        result = await session.exec(
            select(PasswordEntry)
            .join(PasswordGroups)
            .where(
                PasswordGroups.user_id == user.user_id,
                PasswordEntry.entry_id == entry_id
            )
        )
        entry = result.one_or_none()

        if not entry:
            return False
        
        entry.entry_data = entry_data
        session.add(entry)

        entry_public = EntryPublicGet(
            entry_id=entry.entry_id,
            entry_name=entry.entry_name,
            entry_data=entry_data,
            group_name=entry.group.group_name,
            group_id=entry.group.group_id
        )
        await session.commit()
        return entry_public


database: MainDatabase = MainDatabase(async_engine)
