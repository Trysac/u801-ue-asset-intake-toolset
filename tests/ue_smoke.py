"""In-editor smoke test (NOT collected by pytest). Run inside Unreal Editor 5.8 with the plugin on.

Output Log > Cmd > Python:  py "<repo>/tests/ue_smoke.py"
It writes ``<Project>/Saved/Smoke/u801-ue-asset-intake-toolset.json`` with one entry per step.
It creates assets only under /Game/__Smoke_AssetIntake__ (delete that folder by hand afterwards);
it never deletes anything.
"""

import json
import time
import traceback
from pathlib import Path

import unreal

FOLDER = "/Game/__Smoke_AssetIntake__"
REPO = "u801-ue-asset-intake-toolset"
CUBE_OBJ = """o SmokeCube
v -50 -50 0
v 50 -50 0
v 50 50 0
v -50 50 0
v -50 -50 100
v 50 -50 100
v 50 50 100
v -50 50 100
f 1 2 3 4
f 5 8 7 6
f 1 5 6 2
f 2 6 7 3
f 3 7 8 4
f 5 1 4 8
"""
PROVENANCE = {
    "origin": "in_engine",
    "tool": "ue_smoke.py",
    "plan": "n/a",
    "prompt_ref": "",
    "license": "MIT",
    "source_url": "",
    "created_at": "2026-11-10T00:00:00Z",
}


def main() -> None:
    from ue_asset_intake_toolset import compat, mcp

    saved = Path(unreal.Paths.project_saved_dir())
    out_dir = saved / "Smoke"
    out_dir.mkdir(parents=True, exist_ok=True)
    cube = out_dir / "smoke_cube.obj"
    cube.write_text(CUBE_OBJ, encoding="utf-8")
    results = []

    def step(name, fn):
        started = time.time()
        try:
            value = fn()
            parsed = json.loads(value) if isinstance(value, str) else value
            ok = not (isinstance(parsed, dict) and "error" in parsed)
            results.append({"step": name, "ok": ok, "result": parsed})
        except Exception:  # the smoke test records every failure instead of stopping
            results.append({"step": name, "ok": False, "error": traceback.format_exc()[-2000:]})
        results[-1]["seconds"] = round(time.time() - started, 3)

    step("api: static mesh", lambda: {"api": type(compat.static_mesh_api(unreal)).__name__})
    step("api: collision enum", lambda: {"box": str(compat.box_collision_shape(unreal))})
    step(
        "toolset module imports",
        lambda: {"module": __import__("asset_intake_toolset_mcp").__name__},
    )
    step("dry run import", lambda: mcp.import_static_mesh(unreal, str(cube), FOLDER))
    step(
        "real import",
        lambda: mcp.import_static_mesh(
            unreal,
            str(cube),
            FOLDER,
            "SmokeCube",
            provenance_json=json.dumps(PROVENANCE),
            dry_run=False,
        ),
    )
    step("validate", lambda: mcp.validate_assets(unreal, FOLDER))
    step(
        "fix dry run",
        lambda: mcp.fix_assets(
            unreal,
            json.dumps(
                [{"fix": "toggle_nanite", "asset": f"{FOLDER}/SM_SmokeCube", "enabled": True}]
            ),
        ),
    )
    step("export provenance", lambda: mcp.export_provenance_log(unreal, FOLDER, "json"))

    report = {
        "repo": REPO,
        "engine": unreal.SystemLibrary.get_engine_version(),
        "passed": sum(r["ok"] for r in results),
        "total": len(results),
        "steps": results,
    }
    target = out_dir / f"{REPO}.json"
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    unreal.log(f"[smoke] {REPO}: {report['passed']}/{report['total']} ok -> {target}")


main()
