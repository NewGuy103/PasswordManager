from fastapi import APIRouter, HTTPException

from ..deps import UserAuthDep, SessionDep, CheckGroupValidDep
from ..internal.database import database
from ..models.common import GenericSuccess
from ..models.groups import (
    GroupCreate, GroupPublicGet, GroupRename, 
    GroupPublicModify, GroupMove
)

router = APIRouter(prefix='/groups', tags=['groups'])
group_router = APIRouter(prefix='/{group_id}')


@router.get('/')
async def retrieve_top_level_groups(user: UserAuthDep, session: SessionDep) -> list[GroupPublicGet]:
    groups: list[GroupPublicGet] = await database.groups.get_children_of_root(session, user.username)
    return groups


@router.post('/')
async def create_group(data: GroupCreate, user: UserAuthDep, session: SessionDep) -> GroupPublicModify:
    if not await database.groups.check_group_exists(session, user.username, data.parent_id):
        raise HTTPException(status_code=400, detail="Parent group not found")
    
    # Allow multiple groups with the same name, they will be referenced by their UUID anyway
    group_created: GroupPublicModify | bool = await database.groups.create_group(
        session, user.username,
        data.group_name, parent_id=data.parent_id
    )
    return group_created


@group_router.delete('/')
async def delete_group(group_id: CheckGroupValidDep, user: UserAuthDep, session: SessionDep) -> GenericSuccess:
    group_deleted: bool = await database.groups.delete_group(session, user.username, group_id)
    if not group_deleted:
        raise HTTPException(status_code=400, detail="Cannot delete top-level group")
    
    return {'success': True}


@group_router.put('/')
async def rename_group(
    group_id: CheckGroupValidDep, data: GroupRename, 
    user: UserAuthDep, session: SessionDep
) -> GroupPublicModify:
    group_renamed: GroupPublicModify | bool = await database.groups.rename_group(
        session, user.username, group_id, data.new_name
    )
    
    return group_renamed


@group_router.get('/children')
async def get_group_children(
    group_id: CheckGroupValidDep, 
    user: UserAuthDep, session: SessionDep
) -> list[GroupPublicGet]:
    groups: list[GroupPublicGet] = await database.groups.get_children_of_group(
        session, user.username, group_id
    )
    return groups


@group_router.post('/move')
async def move_to_new_parent(
    group_id: CheckGroupValidDep,
    data: GroupMove, user: UserAuthDep, 
    session: SessionDep
) -> GroupPublicModify:
    """Moves the current group to a new parent."""
    if await database.groups.check_group_is_root(session, user.username, group_id):
        raise HTTPException(status_code=400, detail="Cannot move the top-level group")
    
    group_moved: GroupPublicModify | bool = await database.groups.move_to_new_parent(
        session, user.username, group_id, data.new_parent_id
    )
    if not group_moved:
        raise HTTPException(status_code=404, detail="Parent group not found")
    
    return group_moved
