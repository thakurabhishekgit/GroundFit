"""
CRUD for structured Experience (roles + work items) and personal Projects.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.context import ExperienceContext, Project, Role, RoleWorkItem
from app.models.user import User
from app.schemas.context import (
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
    RoleCreate,
    RoleOut,
    RoleUpdate,
    RoleWorkItemIn,
    RoleWorkItemOut,
    RoleWorkItemUpdate,
)


def _norm_tech(tech: list[str] | None) -> list[str] | None:
    if tech is None:
        return None
    cleaned = [t.strip() for t in tech if t and str(t).strip()]
    return cleaned or None


async def list_roles(db: AsyncSession, user: User) -> list[RoleOut]:
    result = await db.execute(
        select(Role)
        .where(Role.user_id == user.id, Role.is_deleted.is_(False))
        .options(selectinload(Role.work_items))
        .order_by(Role.created_at.desc())
    )
    roles = list(result.scalars().unique().all())
    out: list[RoleOut] = []
    for role in roles:
        items = [w for w in (role.work_items or []) if not w.is_deleted]
        role.work_items = items
        out.append(RoleOut.model_validate(role))
    return out


async def create_role(db: AsyncSession, user: User, payload: RoleCreate) -> RoleOut:
    role = Role(
        user_id=user.id,
        title=payload.title.strip(),
        org=(payload.org or "").strip() or None,
        start_date=payload.start_date,
        end_date=payload.end_date,
        ownership=payload.ownership,
        description=payload.description,
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)
    role.work_items = []
    await _sync_raw_narrative(db, user)
    return RoleOut.model_validate(role)


async def update_role(
    db: AsyncSession, user: User, role_id: UUID, payload: RoleUpdate
) -> RoleOut:
    role = await _get_role(db, user.id, role_id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        if key in ("title", "org") and isinstance(value, str):
            value = value.strip() or None
            if key == "title" and not value:
                raise HTTPException(status_code=422, detail="title is required")
        setattr(role, key, value)
    role.updated_by_id = user.id
    await db.commit()
    result = await db.execute(
        select(Role)
        .where(Role.id == role.id)
        .options(selectinload(Role.work_items))
    )
    role = result.scalar_one()
    role.work_items = [w for w in (role.work_items or []) if not w.is_deleted]
    await _sync_raw_narrative(db, user)
    return RoleOut.model_validate(role)


async def delete_role(db: AsyncSession, user: User, role_id: UUID) -> None:
    role = await _get_role(db, user.id, role_id)
    role.is_deleted = True
    role.updated_by_id = user.id
    for item in role.work_items or []:
        item.is_deleted = True
    await db.commit()
    await _sync_raw_narrative(db, user)


async def create_work_item(
    db: AsyncSession, user: User, role_id: UUID, payload: RoleWorkItemIn
) -> RoleWorkItemOut:
    role = await _get_role(db, user.id, role_id)
    item = RoleWorkItem(
        role_id=role.id,
        name=payload.name.strip(),
        summary=payload.summary,
        technical=payload.technical,
        tech=_norm_tech(payload.tech),
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    await _sync_raw_narrative(db, user)
    return RoleWorkItemOut.model_validate(item)


async def update_work_item(
    db: AsyncSession, user: User, item_id: UUID, payload: RoleWorkItemUpdate
) -> RoleWorkItemOut:
    item = await _get_work_item(db, user.id, item_id)
    data = payload.model_dump(exclude_unset=True)
    if "tech" in data:
        data["tech"] = _norm_tech(data["tech"])
    if "name" in data and data["name"] is not None:
        data["name"] = data["name"].strip()
    for key, value in data.items():
        setattr(item, key, value)
    item.updated_by_id = user.id
    await db.commit()
    await db.refresh(item)
    await _sync_raw_narrative(db, user)
    return RoleWorkItemOut.model_validate(item)


async def delete_work_item(db: AsyncSession, user: User, item_id: UUID) -> None:
    item = await _get_work_item(db, user.id, item_id)
    item.is_deleted = True
    item.updated_by_id = user.id
    await db.commit()
    await _sync_raw_narrative(db, user)


async def list_projects(db: AsyncSession, user: User) -> list[ProjectOut]:
    result = await db.execute(
        select(Project)
        .where(Project.user_id == user.id, Project.is_deleted.is_(False))
        .order_by(Project.created_at.desc())
    )
    return [ProjectOut.model_validate(p) for p in result.scalars().all()]


async def create_project(
    db: AsyncSession, user: User, payload: ProjectCreate
) -> ProjectOut:
    project = Project(
        user_id=user.id,
        name=payload.name.strip(),
        problem=payload.problem,
        architecture=payload.architecture,
        description=payload.description,
        tech=_norm_tech(payload.tech),
        metrics_json=payload.metrics_json,
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    await _sync_raw_narrative(db, user)
    return ProjectOut.model_validate(project)


async def update_project(
    db: AsyncSession, user: User, project_id: UUID, payload: ProjectUpdate
) -> ProjectOut:
    project = await _get_project(db, user.id, project_id)
    data = payload.model_dump(exclude_unset=True)
    if "tech" in data:
        data["tech"] = _norm_tech(data["tech"])
    if "name" in data and data["name"] is not None:
        data["name"] = data["name"].strip()
    for key, value in data.items():
        setattr(project, key, value)
    project.updated_by_id = user.id
    await db.commit()
    await db.refresh(project)
    await _sync_raw_narrative(db, user)
    return ProjectOut.model_validate(project)


async def delete_project(db: AsyncSession, user: User, project_id: UUID) -> None:
    project = await _get_project(db, user.id, project_id)
    project.is_deleted = True
    project.updated_by_id = user.id
    await db.commit()
    await _sync_raw_narrative(db, user)


async def build_structured_evidence_blob(db: AsyncSession, user_id: UUID) -> str:
    """Format roles / work-items / personal projects for the align rewriter."""
    roles_result = await db.execute(
        select(Role)
        .where(Role.user_id == user_id, Role.is_deleted.is_(False))
        .options(selectinload(Role.work_items))
        .order_by(Role.created_at.asc())
    )
    roles = list(roles_result.scalars().unique().all())
    projects_result = await db.execute(
        select(Project)
        .where(Project.user_id == user_id, Project.is_deleted.is_(False))
        .order_by(Project.created_at.asc())
    )
    projects = list(projects_result.scalars().all())

    lines: list[str] = []
    if roles:
        lines.append("## Experience (company roles)")
        for role in roles:
            header = f"- Role: {role.title}"
            if role.org:
                header += f" @ {role.org}"
            lines.append(header)
            if role.ownership:
                lines.append(f"  ownership: {role.ownership}")
            if role.description:
                lines.append(f"  narrative: {role.description}")
            for item in role.work_items or []:
                if item.is_deleted:
                    continue
                lines.append(f"  Work item: {item.name}")
                if item.summary:
                    lines.append(f"    what: {item.summary}")
                if item.technical:
                    lines.append(f"    technical: {item.technical}")
                if item.tech:
                    lines.append(f"    skills: {', '.join(item.tech)}")

    if projects:
        lines.append("## Personal projects")
        for project in projects:
            lines.append(f"- Project: {project.name}")
            if project.problem:
                lines.append(f"  what: {project.problem}")
            if project.architecture:
                lines.append(f"  technical: {project.architecture}")
            if project.description:
                lines.append(f"  details: {project.description}")
            if project.tech:
                lines.append(f"  skills: {', '.join(project.tech)}")

    return "\n".join(lines) if lines else ""


async def collect_tech_skill_names(db: AsyncSession, user_id: UUID) -> set[str]:
    """Canonical skill names from tech tags on work items + personal projects."""
    from app.services.latex_utils import normalize_skill_name

    names: set[str] = set()
    roles_result = await db.execute(
        select(Role)
        .where(Role.user_id == user_id, Role.is_deleted.is_(False))
        .options(selectinload(Role.work_items))
    )
    for role in roles_result.scalars().unique().all():
        for item in role.work_items or []:
            if item.is_deleted or not item.tech:
                continue
            for t in item.tech:
                n = normalize_skill_name(t)
                if n:
                    names.add(n)
    projects_result = await db.execute(
        select(Project).where(Project.user_id == user_id, Project.is_deleted.is_(False))
    )
    for project in projects_result.scalars().all():
        if not project.tech:
            continue
        for t in project.tech:
            n = normalize_skill_name(t)
            if n:
                names.add(n)
    return names


async def _sync_raw_narrative(db: AsyncSession, user: User) -> None:
    """Keep ExperienceContext.raw_text in sync for extract / legacy."""
    blob = await build_structured_evidence_blob(db, user.id)
    result = await db.execute(
        select(ExperienceContext).where(
            ExperienceContext.user_id == user.id,
            ExperienceContext.is_deleted.is_(False),
        )
    )
    ctx = result.scalar_one_or_none()
    if ctx is None:
        if not blob:
            return
        ctx = ExperienceContext(
            user_id=user.id,
            raw_text=blob,
            created_by_id=user.id,
            updated_by_id=user.id,
        )
        db.add(ctx)
    else:
        # Preserve any manual notes above a marker if present
        notes = ""
        if "\n## Experience" in (ctx.raw_text or "") or "\n## Personal projects" in (
            ctx.raw_text or ""
        ):
            pass
        elif ctx.raw_text and not ctx.raw_text.startswith("## "):
            # Old freeform text — keep as notes prefix once
            if "<!-- structured -->" not in ctx.raw_text:
                notes = ctx.raw_text.strip() + "\n\n"
        structured = (notes + blob).strip() if blob else (ctx.raw_text or "")
        ctx.raw_text = structured
        ctx.updated_by_id = user.id
    await db.commit()


async def _get_role(db: AsyncSession, user_id: UUID, role_id: UUID) -> Role:
    result = await db.execute(
        select(Role)
        .where(
            Role.id == role_id,
            Role.user_id == user_id,
            Role.is_deleted.is_(False),
        )
        .options(selectinload(Role.work_items))
    )
    role = result.scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return role


async def _get_work_item(db: AsyncSession, user_id: UUID, item_id: UUID) -> RoleWorkItem:
    result = await db.execute(
        select(RoleWorkItem)
        .join(Role, Role.id == RoleWorkItem.role_id)
        .where(
            RoleWorkItem.id == item_id,
            RoleWorkItem.is_deleted.is_(False),
            Role.user_id == user_id,
            Role.is_deleted.is_(False),
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Work item not found"
        )
    return item


async def _get_project(db: AsyncSession, user_id: UUID, project_id: UUID) -> Project:
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == user_id,
            Project.is_deleted.is_(False),
        )
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )
    return project
