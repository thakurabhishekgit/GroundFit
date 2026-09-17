"""
Alignment run endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.models.resume import AlignmentRun
from app.schemas.resume import AlignConfirmRequest, AlignRequest, AlignmentRunOut
from app.services import align_service


router = APIRouter(prefix="/align", tags=["align"])


@router.post(
    "",
    response_model=AlignmentRunOut,
    summary="Run JD ↔ resume alignment (hybrid pipeline)",
)
async def start_align(
    payload: AlignRequest,
    user: CurrentUser,
    db: DbSession,
) -> AlignmentRunOut:
    """
    Pipeline: extract JD skills → match graph → rewrite sections → verify.

    Returns draft LaTeX + warnings. Use /confirm for Add/Skip (no regen),
    then /finalize for a single final rewrite.
    """
    try:
        run = await align_service.run_alignment(db, user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Alignment failed: {exc}",
        ) from exc
    return AlignmentRunOut.model_validate(run)


@router.get("/{run_id}", response_model=AlignmentRunOut, summary="Get alignment run")
async def get_align(run_id: UUID, user: CurrentUser, db: DbSession) -> AlignmentRunOut:
    """Fetch a single alignment run owned by the current user."""
    run = await _get_owned_run(db, user.id, run_id)
    return AlignmentRunOut.model_validate(run)


@router.post(
    "/{run_id}/confirm",
    response_model=AlignmentRunOut,
    summary="Save Add/Skip decisions (does not regenerate LaTeX)",
)
async def confirm_align(
    run_id: UUID,
    payload: AlignConfirmRequest,
    user: CurrentUser,
    db: DbSession,
) -> AlignmentRunOut:
    """
    Record user decisions on warnings only.

    Does NOT call OpenAI. Click Finalize Resume after decisions are complete.
    """
    run = await _get_owned_run(db, user.id, run_id)
    updated = await align_service.save_warning_decisions(db, run, payload.actions, user)
    return AlignmentRunOut.model_validate(updated)


@router.post(
    "/{run_id}/finalize",
    response_model=AlignmentRunOut,
    summary="One-shot final LaTeX rewrite after Add/Skip decisions",
)
async def finalize_align(
    run_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> AlignmentRunOut:
    """
    Regenerate LaTeX once using add_anyway overrides; skipped tokens stay out.

    Project count is enforced — no add/remove projects.
    """
    run = await _get_owned_run(db, user.id, run_id)
    try:
        updated = await align_service.finalize_alignment(db, run, user)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Finalize failed: {exc}",
        ) from exc
    return AlignmentRunOut.model_validate(updated)


async def _get_owned_run(db: DbSession, user_id: UUID, run_id: UUID) -> AlignmentRun:
    """Internal helper for ownership checks."""
    result = await db.execute(
        select(AlignmentRun).where(
            AlignmentRun.id == run_id,
            AlignmentRun.user_id == user_id,
            AlignmentRun.is_deleted.is_(False),
        )
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alignment run not found")
    return run
