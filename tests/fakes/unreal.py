"""A fake ``unreal`` module recording every call."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any


class FakeAsset:
    def __init__(
        self,
        ue: FakeUnreal,
        path: str,
        class_name: str = "StaticMesh",
        triangles: int = 0,
        height: float = 0.0,
        size: tuple[int, int] = (0, 0),
        collisions: int = 0,
        nanite: bool = False,
    ) -> None:
        self.ue = ue
        self.path = path
        self.class_name = class_name
        self.triangles = triangles
        self.height = height
        self.size = size
        self.collisions = collisions
        self.nanite = nanite
        self.tags: dict[str, str] = {}
        self.props: dict[str, Any] = {}

    def get_class(self) -> Any:
        return SimpleNamespace(get_name=lambda: self.class_name)

    def get_bounds(self) -> Any:
        return SimpleNamespace(box_extent=SimpleNamespace(z=self.height / 2))

    def blueprint_get_size_x(self) -> int:
        return self.size[0]

    def blueprint_get_size_y(self) -> int:
        return self.size[1]

    def set_editor_property(self, name: str, value: Any) -> None:
        self.ue.record("Asset.set_editor_property", (self.path, name, value), True)
        self.props[name] = value


class _Task:
    def __init__(self) -> None:
        self.props: dict[str, Any] = {}

    def set_editor_property(self, name: str, value: Any) -> None:
        self.props[name] = value


class _Transaction:
    def __init__(self, ue: FakeUnreal, label: str) -> None:
        ue.record("ScopedEditorTransaction", (label,), True)
        self.ue = ue

    def __enter__(self) -> _Transaction:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


class _AssetLibrary:
    def __init__(self, ue: FakeUnreal) -> None:
        self.ue = ue

    def list_assets(
        self, directory_path: str, recursive: bool = True, include_folder: bool = False
    ) -> list[str]:
        self.ue.record("EditorAssetLibrary.list_assets", (directory_path,), False)
        prefix = directory_path + "/"
        found = [p for p in self.ue.assets if p.startswith(prefix)]
        if not recursive:
            found = [p for p in found if "/" not in p[len(prefix) :]]
        return sorted(found)

    def load_asset(self, path: str) -> FakeAsset | None:
        self.ue.record("EditorAssetLibrary.load_asset", (path,), False)
        return self.ue.assets.get(path)

    def does_asset_exist(self, path: str) -> bool:
        self.ue.record("EditorAssetLibrary.does_asset_exist", (path,), False)
        return path in self.ue.assets

    def rename_asset(self, old: str, new: str) -> bool:
        self.ue.record("EditorAssetLibrary.rename_asset", (old, new), True)
        asset = self.ue.assets.pop(old)
        asset.path = new
        self.ue.assets[new] = asset
        return True

    def set_metadata_tag(self, obj: FakeAsset, tag: str, value: str) -> None:
        self.ue.record("EditorAssetLibrary.set_metadata_tag", (obj.path, tag, value), True)
        obj.tags[tag] = value

    def get_metadata_tag(self, obj: FakeAsset, tag: str) -> str:
        self.ue.record("EditorAssetLibrary.get_metadata_tag", (obj.path, tag), False)
        return obj.tags.get(tag, "")


class _MeshLibrary:
    def __init__(self, ue: FakeUnreal) -> None:
        self.ue = ue

    def get_number_triangles(self, obj: FakeAsset, lod: int) -> int:
        return obj.triangles

    def get_simple_collision_count(self, obj: FakeAsset) -> int:
        return obj.collisions

    def add_simple_collisions(self, obj: FakeAsset, shape: str) -> int:
        self.ue.record("EditorStaticMeshLibrary.add_simple_collisions", (obj.path, shape), True)
        obj.collisions += 1
        return 0

    def get_nanite_settings(self, obj: FakeAsset) -> Any:
        return SimpleNamespace(enabled=obj.nanite)

    def set_nanite_settings(self, obj: FakeAsset, settings: Any) -> None:
        self.ue.record("EditorStaticMeshLibrary.set_nanite_settings", (obj.path,), True)
        obj.nanite = settings.enabled


class _Tools:
    def __init__(self, ue: FakeUnreal) -> None:
        self.ue = ue

    def import_asset_tasks(self, tasks: list[_Task]) -> None:
        self.ue.record("AssetTools.import_asset_tasks", (len(tasks),), True)
        for task in tasks:
            path = task.props["destination_path"] + "/" + task.props["destination_name"]
            self.ue.add_asset(path)


class FakeUnreal:
    """Records calls as ``(name, args, mutating)``."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], bool]] = []
        self.assets: dict[str, FakeAsset] = {}
        self.EditorAssetLibrary = _AssetLibrary(self)
        self.EditorStaticMeshLibrary = _MeshLibrary(self)
        self.AssetToolsHelpers = SimpleNamespace(get_asset_tools=lambda: _Tools(self))
        self.ScriptingCollisionShapeType = SimpleNamespace(BOX="BOX")

    def record(self, name: str, args: tuple[Any, ...], mutating: bool) -> None:
        self.calls.append((name, args, mutating))

    @property
    def mutating_calls(self) -> list[tuple[str, tuple[Any, ...], bool]]:
        return [c for c in self.calls if c[2]]

    def add_asset(self, path: str, tags: dict[str, str] | None = None, **kwargs: Any) -> FakeAsset:
        asset = FakeAsset(self, path, **kwargs)
        for key, value in (tags or {}).items():
            asset.tags["provenance." + key] = value
        self.assets[path] = asset
        return asset

    def AssetImportTask(self) -> _Task:
        return _Task()

    def ScopedEditorTransaction(self, label: str) -> _Transaction:
        return _Transaction(self, label)


class Tripwire:
    """Any attribute access fails: proves nothing was called on the unreal module."""

    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"unexpected access to unreal.{name}")
