"""
Experience context + skill graph endpoints.
"""

from fastapi import APIRouter, HTTPException, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.context import (
    ConfirmGraphRequest,
    ContextBundleOut,
    ExperienceContextOut,
    ExperienceContextUpsert,
    ExtractPreviewOut,
    SkillOut,
)
from app.services import context_service


router = APIRouter(prefix="/context", tags=["context"])


@router.get(
    "",
    response_model=ContextBundleOut,
    summary="Get full experience context bundle",
)
async def get_context(user: CurrentUser, db: DbSession) -> ContextBundleOut:
    """Return raw context + skills/evidence + roles + projects for the dashboard."""
    return await context_service.get_context_bundle(db, user)


@router.put(
    "",
    response_model=ExperienceContextOut,
    summary="Save raw experience narrative",
)
async def put_context(
    payload: ExperienceContextUpsert,
    user: CurrentUser,
    db: DbSession,
) -> ExperienceContextOut:
    """Upsert the user's ExperienceContext.raw_text (source of truth dump)."""
    ctx = await context_service.upsert_raw_context(db, user, payload)
    return ExperienceContextOut.model_validate(ctx)


@router.post(
    "/extract",
    response_model=ExtractPreviewOut,
    summary="LLM-extract skill graph preview (not saved)",
)
async def extract_context(
    payload: ExperienceContextUpsert,
    user: CurrentUser,
    db: DbSession,
) -> ExtractPreviewOut:
    """
    Persist raw text, then run OpenAI extraction.

    Returns a draft graph for the review UI — call /context/confirm to save skills.
    """
    await context_service.upsert_raw_context(db, user, payload)
    try:
        return await context_service.extract_skill_graph_preview(payload.raw_text)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Extraction failed: {exc}",
        ) from exc


@router.post(
    "/confirm",
    response_model=list[SkillOut],
    summary="Confirm and save reviewed skill graph",
)
async def confirm_context(
    payload: ConfirmGraphRequest,
    user: CurrentUser,
    db: DbSession,
) -> list[SkillOut]:
    """Write user-accepted skills + evidence into Postgres."""
    skills = await context_service.confirm_skill_graph(db, user, payload)
    # reload with evidence
    bundle = await context_service.get_context_bundle(db, user)
    return bundle.skills
