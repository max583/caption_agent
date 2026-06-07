"""LLM configuration profiles — CRUD + activate endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..config.manager import ConfigManager
from ..models import LLMProfile
from ..schemas.llm_profile import (
    LLMProfileCreate,
    LLMProfileOut,
    LLMProfileSnapshot,
    LLMProfileUpdate,
)
from ..storage.session import get_session

router = APIRouter(prefix="/api/llm-profiles", tags=["llm-profiles"])


def _snapshot_to_json(snapshot: LLMProfileSnapshot) -> str:
    return snapshot.model_dump_json()


def _json_to_snapshot(raw: str) -> LLMProfileSnapshot:
    return LLMProfileSnapshot.model_validate_json(raw)


def _profile_out(profile: LLMProfile) -> LLMProfileOut:
    return LLMProfileOut(
        id=profile.id,
        name=profile.name,
        description=profile.description,
        is_active=profile.is_active,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        snapshot=_json_to_snapshot(profile.config_json),
    )


def _get_or_404(profile_id: int, session: Session) -> LLMProfile:
    p = session.get(LLMProfile, profile_id)
    if p is None:
        raise HTTPException(status_code=404, detail=f"LLM profile {profile_id} not found")
    return p


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@router.get("", response_model=list[LLMProfileOut])
def list_profiles(session: Session = Depends(get_session)) -> list[LLMProfileOut]:
    """Return all profiles ordered by creation time."""
    profiles = session.query(LLMProfile).order_by(LLMProfile.created_at).all()
    return [_profile_out(p) for p in profiles]


@router.post("", response_model=LLMProfileOut, status_code=status.HTTP_201_CREATED)
def create_profile(
    body: LLMProfileCreate,
    session: Session = Depends(get_session),
) -> LLMProfileOut:
    """Create a new profile.

    If ``snapshot`` is omitted, the server snapshots the current flat config.
    """
    existing = session.query(LLMProfile).filter(LLMProfile.name == body.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Profile with name '{body.name}' already exists.",
        )

    if body.snapshot is None:
        mgr = ConfigManager(session)
        snapshot = mgr.snapshot_current_llm()
    else:
        snapshot = body.snapshot

    profile = LLMProfile(
        name=body.name,
        description=body.description,
        config_json=_snapshot_to_json(snapshot),
    )
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return _profile_out(profile)


@router.get("/{profile_id}", response_model=LLMProfileOut)
def get_profile(
    profile_id: int,
    session: Session = Depends(get_session),
) -> LLMProfileOut:
    return _profile_out(_get_or_404(profile_id, session))


@router.patch("/{profile_id}", response_model=LLMProfileOut)
def update_profile(
    profile_id: int,
    body: LLMProfileUpdate,
    session: Session = Depends(get_session),
) -> LLMProfileOut:
    """Rename, update description, or overwrite snapshot."""
    profile = _get_or_404(profile_id, session)

    if body.name is not None and body.name != profile.name:
        conflict = session.query(LLMProfile).filter(LLMProfile.name == body.name).first()
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Profile with name '{body.name}' already exists.",
            )
        profile.name = body.name

    if body.description is not None:
        profile.description = body.description

    if body.snapshot is not None:
        profile.config_json = _snapshot_to_json(body.snapshot)

    session.commit()
    session.refresh(profile)
    return _profile_out(profile)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(
    profile_id: int,
    session: Session = Depends(get_session),
) -> None:
    """Delete a profile. Returns 409 if the profile is currently active."""
    profile = _get_or_404(profile_id, session)
    if profile.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete the active profile. Switch to another profile first.",
        )
    session.delete(profile)
    session.commit()


# ---------------------------------------------------------------------------
# Activate
# ---------------------------------------------------------------------------


@router.post("/{profile_id}/activate", response_model=LLMProfileOut)
def activate_profile(
    profile_id: int,
    session: Session = Depends(get_session),
) -> LLMProfileOut:
    """Copy the profile's snapshot into the configuration table and mark it active.

    Clears ``is_active`` on all other profiles first to maintain the at-most-one-active
    invariant (enforced here in application layer).
    """
    profile = _get_or_404(profile_id, session)

    # Clear any currently active profile.
    session.query(LLMProfile).filter(
        LLMProfile.is_active.is_(True),
        LLMProfile.id != profile_id,
    ).update({"is_active": False}, synchronize_session="fetch")

    # Apply snapshot to the flat configuration table.
    snapshot = _json_to_snapshot(profile.config_json)
    mgr = ConfigManager(session)
    mgr.apply_llm_snapshot(snapshot)

    profile.is_active = True
    session.commit()
    session.refresh(profile)
    return _profile_out(profile)
