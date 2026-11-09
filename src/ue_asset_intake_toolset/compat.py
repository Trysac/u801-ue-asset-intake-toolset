"""Resolve Unreal APIs that moved between engine versions.

UE 5.x deprecates the ``Editor*Library`` classes in favor of editor subsystems. These helpers prefer
the subsystem and fall back to the legacy library, so the adapter works on UE 5.8 and on older 5.x
builds. Which one the editor actually exposes is confirmed by ``tests/ue_smoke.py`` in Unreal.
"""

from __future__ import annotations

from typing import Any


def static_mesh_api(ue: Any) -> Any:
    """Return ``StaticMeshEditorSubsystem`` when available, else ``EditorStaticMeshLibrary``."""
    subsystem_cls = getattr(ue, "StaticMeshEditorSubsystem", None)
    getter = getattr(ue, "get_editor_subsystem", None)
    if subsystem_cls is not None and getter is not None:
        subsystem = getter(subsystem_cls)
        if subsystem is not None:
            return subsystem
    return ue.EditorStaticMeshLibrary


def box_collision_shape(ue: Any) -> Any:
    """Return the BOX member of the simple-collision enum (renamed across versions)."""
    for name in ("ScriptCollisionShapeType", "ScriptingCollisionShapeType"):
        enum = getattr(ue, name, None)
        if enum is not None:
            return enum.BOX
    raise AttributeError("unreal exposes no simple-collision shape enum")
