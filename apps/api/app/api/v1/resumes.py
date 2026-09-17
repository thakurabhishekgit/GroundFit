"""
Resume CRUD endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.models.resume import Resume
from app.schemas.resume import ResumeCreate, ResumeOut


router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.get("", response_model=list[ResumeOut], summary="List my resumes")
async def list_resumes(user: CurrentUser, db: DbSession) -> list[ResumeOut]:
    """Return all non-deleted resumes for the current user."""
    result = await db.execute(
        select(Resume)
        .where(Resume.user_id == user.id, Resume.is_deleted.is_(False))
        .order_by(Resume.created_at.desc())
    )
    return [ResumeOut.model_validate(r) for r in result.scalars().all()]


@router.post("", response_model=ResumeOut, status_code=status.HTTP_201_CREATED, summary="Create resume")
async def create_resume(
    payload: ResumeCreate,
    user: CurrentUser,
    db: DbSession,
) -> ResumeOut:
    """Store a LaTeX resume version."""
    resume = Resume(
        user_id=user.id,
        title=payload.title,
        latex_source=payload.latex_source,
        version=1,
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)
    return ResumeOut.model_validate(resume)


@router.get("/{resume_id}", response_model=ResumeOut, summary="Get resume by id")
async def get_resume(resume_id: UUID, user: CurrentUser, db: DbSession) -> ResumeOut:
    """Fetch one resume owned by the current user."""
    resume = await _get_owned_resume(db, user.id, resume_id)
    return ResumeOut.model_validate(resume)


@router.put("/{resume_id}", response_model=ResumeOut, summary="Update resume LaTeX")
async def update_resume(
    resume_id: UUID,
    payload: ResumeCreate,
    user: CurrentUser,
    db: DbSession,
) -> ResumeOut:
    """Replace title/source and bump version."""
    resume = await _get_owned_resume(db, user.id, resume_id)
    resume.title = payload.title
    resume.latex_source = payload.latex_source
    resume.version += 1
    resume.updated_by_id = user.id
    await db.commit()
    await db.refresh(resume)
    return ResumeOut.model_validate(resume)


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Soft-delete resume")
async def delete_resume(resume_id: UUID, user: CurrentUser, db: DbSession) -> None:
    """Soft-delete a resume (is_deleted=True)."""
    resume = await _get_owned_resume(db, user.id, resume_id)
    resume.is_deleted = True
    resume.updated_by_id = user.id
    await db.commit()


async def _get_owned_resume(db: DbSession, user_id: UUID, resume_id: UUID) -> Resume:
    """Internal helper: resume must belong to user and not be deleted."""
    result = await db.execute(
        select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id == user_id,
            Resume.is_deleted.is_(False),
        )
    )
    resume = result.scalar_one_or_none()
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    return resume
