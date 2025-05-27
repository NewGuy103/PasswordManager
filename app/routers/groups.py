from fastapi import APIRouter, HTTPException

from ..deps import UserAuthDep, SessionDep
from ..internal.database import database
from ..models.common import GenericSuccess
from ..models.groups import GroupCreate, GroupPublicGet, GroupRename, CannotBeRoot

router = APIRouter(prefix='/groups', tags=['groups'])
group_router = APIRouter(prefix='/{group_name}')


@router.get('/')
async def retrieve_all_groups(user: UserAuthDep, session: SessionDep) -> list[GroupPublicGet]:
    groups: list[GroupPublicGet] = await database.groups.get_all_groups(session, user.username)
    return groups


@router.post('/')
async def create_group(data: GroupCreate, user: UserAuthDep, session: SessionDep) -> GroupPublicGet:
    group_created: GroupPublicGet | bool = await database.groups.create_group(session, user.username, data.group_name)
    if not group_created:
        raise HTTPException(status_code=409, detail="Group already exists")

    return group_created


@group_router.delete('/')
async def delete_group(group_name: CannotBeRoot, user: UserAuthDep, session: SessionDep) -> GenericSuccess:
    group_deleted: bool = await database.groups.delete_group(session, user.username, group_name)
    if not group_deleted:
        raise HTTPException(status_code=404, detail="Group name not found")
    
    return {'success': True}


@group_router.put('/')
async def rename_group(
    group_name: CannotBeRoot, data: GroupRename, 
    user: UserAuthDep, session: SessionDep
) -> GroupPublicGet:
    group_renamed: GroupPublicGet | bool = await database.groups.rename_group(
        session, user.username, group_name, data.new_name
    )
    if not group_renamed:
        raise HTTPException(status_code=404, detail="Group name not found")
    
    return group_renamed
