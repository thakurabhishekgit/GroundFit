"""API v1 router aggregate."""

from fastapi import APIRouter

from app.api.v1 import align, auth, context, lists, resumes


api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(context.router)
api_router.include_router(resumes.router)
api_router.include_router(align.router)
api_router.include_router(lists.router)
