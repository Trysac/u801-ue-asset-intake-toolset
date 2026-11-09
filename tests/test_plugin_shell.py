"""The Content/Python toolset module forwards every tool to the MCP layer with ``unreal``."""

from __future__ import annotations

import importlib.util
import inspect
import json
import sys
import types
from pathlib import Path
from typing import Any

import pytest

from tests.fakes.unreal import FakeUnreal

ROOT = Path(__file__).resolve().parents[1]
SHELLS = sorted((ROOT / "plugin").glob("*/Content/Python/*_mcp.py"))


@pytest.fixture
def shell(monkeypatch: pytest.MonkeyPatch) -> Any:
    fake = FakeUnreal()
    fake.uclass = lambda: lambda cls: cls  # type: ignore[attr-defined]
    fake.ToolsetDefinition = type("ToolsetDefinition", (), {})  # type: ignore[attr-defined]
    registry = types.ModuleType("toolset_registry")
    registry.tool_call = lambda fn: setattr(fn, "is_tool", True) or fn  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "unreal", fake)
    monkeypatch.setitem(sys.modules, "toolset_registry", registry)
    assert len(SHELLS) == 1
    spec = importlib.util.spec_from_file_location("shell_under_test", SHELLS[0])
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, fake


def _toolset(module: Any) -> Any:
    classes = [
        c for _, c in inspect.getmembers(module, inspect.isclass) if c.__module__ == module.__name__
    ]
    assert len(classes) == 1
    return classes[0]


def test_every_mcp_function_is_a_documented_tool(shell: Any) -> None:
    module, _ = shell
    toolset = _toolset(module)
    from ue_asset_intake_toolset import mcp

    public = {
        n
        for n, f in inspect.getmembers(mcp, inspect.isfunction)
        if f.__module__ == mcp.__name__ and not n.startswith("_") and n != "to_json"
    }
    tools = {n for n, f in vars(toolset).items() if isinstance(f, staticmethod)}
    assert public == tools
    for name in tools:
        fn = getattr(toolset, name)
        assert getattr(fn, "is_tool", False), name
        doc = inspect.getdoc(fn) or ""
        assert "Args:" in doc or not inspect.signature(fn).parameters, name
        assert "Returns:" in doc, name
        assert inspect.signature(fn).return_annotation in (str, "str")
        assert "ue" not in inspect.signature(fn).parameters


def test_tools_forward_with_unreal(shell: Any) -> None:
    module, fake = shell
    toolset = _toolset(module)
    out = json.loads(toolset.import_static_mesh("C:/a.fbx", "/Game/P"))
    assert out["dry_run"] is True
    assert json.loads(toolset.validate_assets("/Game/P"))["summary"]
    assert json.loads(toolset.fix_assets("[]"))["applied"] == []
    assert json.loads(toolset.export_provenance_log("/Game/P"))["count"] == 0
    assert "error" in json.loads(toolset.write_provenance("/Game/P/SM_A", "{}"))
    assert json.loads(toolset.import_batch("[]"))["cursor"] is None
    assert fake.mutating_calls == []
