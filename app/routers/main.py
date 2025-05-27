from fastapi import APIRouter
from . import auth

router = APIRouter(prefix='/api')
router.include_router(auth.router)
