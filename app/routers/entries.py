import uuid
from fastapi import APIRouter, HTTPException
from pydantic import NonNegativeInt, PositiveInt
from ..deps import UserAuthDep, SessionDep, CheckGroupValidDep
from ..internal.database import database
from ..models.common import GenericSuccess
from ..models.entries import EntryPublicGet, EntryCreate, EntryUpdate

# This router is under /groups/{group_id}
router = APIRouter(prefix='/entries')


@router.post('/')
async def create_password_entry(
    group_id: CheckGroupValidDep, data: EntryCreate, 
    user: UserAuthDep, session: SessionDep
) -> EntryPublicGet:
    entry_created: EntryPublicGet = await database.entries.create_entry(
        session, user.username, group_id, data.entry_name,
        data.entry_username, data.entry_password, str(data.entry_url)
    )
    if not entry_created:
        raise HTTPException(status_code=400, detail="Parent group is invalid")
    
    return entry_created


@router.get('/')
async def get_group_entries(
    group_id: CheckGroupValidDep, user: UserAuthDep, 
    session: SessionDep, amount: PositiveInt = 100,
    offset: NonNegativeInt = 0
) -> list[EntryPublicGet]:
    entries_public: list[EntryPublicGet] = await database.entries.get_entries_by_group(
        session, user.username, group_id,
        amount=amount, offset=offset
    )
    
    return entries_public


@router.delete('/{entry_id}')
async def delete_password_entry(
    group_id: CheckGroupValidDep, entry_id: uuid.UUID,
    user: UserAuthDep, session: SessionDep
) -> GenericSuccess:
    entry_deleted: bool = await database.entries.delete_entry_by_id(
        session, user.username, entry_id
    )
    if not entry_deleted:
        raise HTTPException(status_code=404, detail="Password entry not found")
    
    return {'success': True}


@router.put('/{entry_id}')
async def change_entry_data(
    group_id: CheckGroupValidDep, entry_id: uuid.UUID,
    data: EntryUpdate,
    user: UserAuthDep, session: SessionDep
) -> EntryPublicGet:
    entry_modified: EntryPublicGet | bool = await database.entries.update_entry_data(
        session, user.username, entry_id, data.entry_name, 
        data.entry_username, data.entry_password, str(data.entry_url)
    )
    if not entry_modified:
        raise HTTPException(status_code=404, detail="Password entry not found")
    
    return entry_modified
