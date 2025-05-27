from fastapi import APIRouter
from . import auth, groups, utils, entries

router = APIRouter(prefix='/api')
router.include_router(auth.router)

# Groups stuff
g_main_router = groups.router
g_name_router = groups.group_router

g_name_router.include_router(entries.router)
g_main_router.include_router(groups.group_router)

router.include_router(g_main_router)

# Utils/misc
router.include_router(utils.router)
