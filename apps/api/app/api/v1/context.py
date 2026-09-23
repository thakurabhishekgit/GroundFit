"""
Experience context + skill graph + structured roles/projects endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.context import (
    ConfirmGraphRequest,
    ContextBundleOut,
    ExperienceContextOut,
    ExperienceContextUpsert,
    ExtractPreviewOut,
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
    RoleCreate,
    RoleOut,
    RoleUpdate,
    RoleWorkItemIn,
    RoleWorkItemOut,
    RoleWorkItemUpdate,
    SkillOut,
)
from app.services import context_service, structure_service


router = APIRouter(prefix="/context", tags=["context"])


@router.get(
    "",
    response_model=ContextBundleOut,
    summary="Get full experience context bundle",
)
async def get_context(user: CurrentUser, db: DbSession) -> ContextBundleOut:
    return await context_service.get_context_bundle(db, user)


@router.put(
    "",
    response_model=ExperienceContextOut,
    summary="Save optional notes / legacy narrative",
)
async def put_context(
    payload: ExperienceContextUpsert,
    user: CurrentUser,
    db: DbSession,
) -> ExperienceContextOut:
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
    text = (payload.raw_text or "").strip()
    if not text:
        # Build from structured blocks if narrative empty
        text = await structure_service.build_structured_evidence_blob(db, user.id)
    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Add experience/projects first (or paste narrative text)",
        )
    await context_service.upsert_raw_context(
        db, user, ExperienceContextUpsert(raw_text=text)
    )
    try:
        return await context_service.extract_skill_graph_preview(text)
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
    await context_service.confirm_skill_graph(db, user, payload)
    bundle = await context_service.get_context_bundle(db, user)
    return bundle.skills


# --- Roles (company experience) ---


@router.get("/roles", response_model=list[RoleOut])
async def get_roles(user: CurrentUser, db: DbSession) -> list[RoleOut]:
    return await structure_service.list_roles(db, user)


@router.post("/roles", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
async def post_role(
    payload: RoleCreate, user: CurrentUser, db: DbSession
) -> RoleOut:
    return await structure_service.create_role(db, user, payload)


@router.patch("/roles/{role_id}", response_model=RoleOut)
async def patch_role(
    role_id: UUID, payload: RoleUpdate, user: CurrentUser, db: DbSession
) -> RoleOut:
    return await structure_service.update_role(db, user, role_id, payload)


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_role(role_id: UUID, user: CurrentUser, db: DbSession) -> None:
    await structure_service.delete_role(db, user, role_id)


@router.post(
    "/roles/{role_id}/work-items",
    response_model=RoleWorkItemOut,
    status_code=status.HTTP_201_CREATED,
)
async def post_work_item(
    role_id: UUID,
    payload: RoleWorkItemIn,
    user: CurrentUser,
    db: DbSession,
) -> RoleWorkItemOut:
    return await structure_service.create_work_item(db, user, role_id, payload)


@router.patch("/work-items/{item_id}", response_model=RoleWorkItemOut)
async def patch_work_item(
    item_id: UUID,
    payload: RoleWorkItemUpdate,
    user: CurrentUser,
    db: DbSession,
) -> RoleWorkItemOut:
    return await structure_service.update_work_item(db, user, item_id, payload)


@router.delete("/work-items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_work_item(
    item_id: UUID, user: CurrentUser, db: DbSession
) -> None:
    await structure_service.delete_work_item(db, user, item_id)


# --- Personal projects ---


@router.get("/projects", response_model=list[ProjectOut])
async def get_projects(user: CurrentUser, db: DbSession) -> list[ProjectOut]:
    return await structure_service.list_projects(db, user)


@router.post("/projects", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def post_project(
    payload: ProjectCreate, user: CurrentUser, db: DbSession
) -> ProjectOut:
    return await structure_service.create_project(db, user, payload)


@router.patch("/projects/{project_id}", response_model=ProjectOut)
async def patch_project(
    project_id: UUID,
    payload: ProjectUpdate,
    user: CurrentUser,
    db: DbSession,
) -> ProjectOut:
    return await structure_service.update_project(db, user, project_id, payload)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_project(
    project_id: UUID, user: CurrentUser, db: DbSession
) -> None:
    await structure_service.delete_project(db, user, project_id)
