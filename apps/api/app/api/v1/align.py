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

    Returns run with result_latex + warnings. Strict mode never invents
    missing skills; warnings list orphans for UI confirm.
    """
    try:
        run = await align_service.run_alignment(db, user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        # run row may already be marked failed
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
    summary="Confirm warning overrides on an alignment run",
)
async def confirm_align(
    run_id: UUID,
    payload: AlignConfirmRequest,
    user: CurrentUser,
    db: DbSession,
) -> AlignmentRunOut:
    """
    Record user decisions on warnings (add_anyway / skip / use_suggestion).

    MVP stores actions on warnings_json; full re-rewrite on override can come later.
    """
    run = await _get_owned_run(db, user.id, run_id)
    warnings = list(run.warnings_json or [])
    action_map = {
        str(a.get("token")): a.get("user_action")
        for a in payload.actions
        if a.get("token")
    }
    for warning in warnings:
        token = str(warning.get("token"))
        if token in action_map:
            warning["user_action"] = action_map[token]
    run.warnings_json = warnings
    run.status = "done"
    run.updated_by_id = user.id
    await db.commit()
    await db.refresh(run)
    return AlignmentRunOut.model_validate(run)


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
