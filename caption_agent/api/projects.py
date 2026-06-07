"""Project CRUD endpoints: GET/POST /api/projects, GET/PATCH/DELETE /api/projects/{id}."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..logging_setup.business_logger import BusinessLogger
from ..models import Project
from ..schemas.policy import CaptionPolicyConfig, get_project_policy
from ..schemas.projects import ProjectCreate, ProjectOut, ProjectUpdate
from ..storage.session import get_session
from .deps import get_project_or_404
from .stats import build_project_out

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
def list_projects(session: Session = Depends(get_session)) -> list[ProjectOut]:
    projects = session.query(Project).order_by(Project.created_at.desc()).all()
    return [build_project_out(p, session) for p in projects]


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    body: ProjectCreate,
    session: Session = Depends(get_session),
) -> ProjectOut:
    existing = session.query(Project).filter(Project.name == body.name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Project name '{body.name}' already exists")
    project = Project(
        name=body.name,
        description=body.description,
        trigger_token=body.trigger_token,
        default_source_type=body.default_source_type,
        default_branch=body.default_branch,
        default_output_policy=body.default_output_policy,
        lora_type=body.lora_type,
        base_model_family=body.base_model_family,
    )
    session.add(project)
    session.flush()
    BusinessLogger(session).info(
        "project_created",
        f"Project created: {project.name!r}",
        project_id=project.id,
    )
    return build_project_out(project, session)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: int,
    session: Session = Depends(get_session),
) -> ProjectOut:
    project = get_project_or_404(project_id, session)
    return build_project_out(project, session)


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    body: ProjectUpdate,
    session: Session = Depends(get_session),
) -> ProjectOut:
    project = get_project_or_404(project_id, session)
    if body.name is not None and body.name != project.name:
        existing = session.query(Project).filter(Project.name == body.name).first()
        if existing:
            raise HTTPException(status_code=409, detail=f"Project name '{body.name}' already exists")
        project.name = body.name
    if body.description is not None:
        project.description = body.description
    if body.default_source_type is not None:
        project.default_source_type = body.default_source_type
    if body.default_branch is not None:
        project.default_branch = body.default_branch
    if body.default_output_policy is not None:
        project.default_output_policy = body.default_output_policy
    if body.trigger_token is not None:
        project.trigger_token = body.trigger_token
    if body.lora_type is not None:
        project.lora_type = body.lora_type
    if body.base_model_family is not None:
        project.base_model_family = body.base_model_family
    BusinessLogger(session).info(
        "project_updated",
        f"Project updated: {project.name!r}",
        project_id=project.id,
    )
    return build_project_out(project, session)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    session: Session = Depends(get_session),
) -> None:
    project = get_project_or_404(project_id, session)
    BusinessLogger(session).info(
        "project_deleted",
        f"Project deleted: {project.name!r} (id={project_id})",
    )
    session.delete(project)


# ---- Caption policy endpoints (D-114) ----

@router.get("/{project_id}/policy")
def get_policy(
    project_id: int,
    session: Session = Depends(get_session),
) -> dict:
    """Return the project's caption policy (project defaults when caption_policy is NULL)."""
    project = get_project_or_404(project_id, session)
    return get_project_policy(project).model_dump()


@router.put("/{project_id}/policy")
def update_policy(
    project_id: int,
    body: CaptionPolicyConfig,
    session: Session = Depends(get_session),
) -> dict:
    """Save a caption policy for the project; replaces any previous policy."""
    project = get_project_or_404(project_id, session)
    project.caption_policy = body.model_dump()
    BusinessLogger(session).info(
        "project_policy_updated",
        f"Caption policy updated for project {project.name!r} (id={project_id})",
        project_id=project_id,
    )
    return body.model_dump()


@router.delete("/{project_id}/policy", status_code=status.HTTP_200_OK)
def reset_policy(
    project_id: int,
    session: Session = Depends(get_session),
) -> dict:
    """Reset the project's caption policy to NULL (restores project defaults)."""
    project = get_project_or_404(project_id, session)
    project.caption_policy = None
    BusinessLogger(session).info(
        "project_policy_reset",
        f"Caption policy reset to defaults for project {project.name!r} (id={project_id})",
        project_id=project_id,
    )
    return CaptionPolicyConfig().model_dump()
