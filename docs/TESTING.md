# Testing

## Running

```sh
uv run pytest --cov=ue_asset_intake_toolset   # tests with branch coverage report
```

## Policy

- The coverage target for `src/ue_asset_intake_toolset` is 85 %.
- Tests call the public API and assert return values, raised `IntakeError` codes and messages, and the calls recorded on the fake unreal module.
- Tests are intended to be deterministic: no network, no wall clock, no dependence on test order.

## Existing tests

- `tests/test_adapter.py`: exercises the adapter against a fake `unreal` module (`FakeUnreal`) with a `Tripwire` that fails on unexpected mutating calls. It covers a dry-run static mesh import under `/Game/Props`, asserting that the summary starts with `dry run`, that no mutating call is recorded, and that the planned asset path is `/Game/Props/SM_MyCoolMesh`.

No test module for the core is present in the reviewed tree. The Hypothesis properties, golden files under `tests/golden/` and the fake module under `tests/fakes/` named in the specification are not present in the reviewed tree, so this document does not describe them as existing.

## Not tested

No test runs inside Unreal Engine. All adapter behaviour is checked only against the fake module.
