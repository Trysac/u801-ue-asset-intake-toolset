# ue-asset-intake-toolset

[![PyPI version](https://img.shields.io/pypi/v/trysac-ue-asset-intake-toolset)](https://pypi.org/project/trysac-ue-asset-intake-toolset/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-ue-asset-intake-toolset)](LICENSE)
[![CI](https://github.com/Trysac/u801-ue-asset-intake-toolset/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u801-ue-asset-intake-toolset/actions/workflows/ci.yml)

Pure core and unreal adapter of an Unreal MCP toolset that imports, validates and normalizes 3D assets and textures with a provenance log.

## Problem

Describe in two or three sentences the concrete problem this utility solves, who hits it, and what
they do today without it. Replace this paragraph when the first real feature lands.

## Install

```sh
pip install trysac-ue-asset-intake-toolset
# or
uv add trysac-ue-asset-intake-toolset
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
import ue_asset_intake_toolset

# normalize() trims surrounding whitespace and lower-cases the text.
print(ue_asset_intake_toolset.normalize("  Hello World "))  # -> "hello world"

# Blank input is rejected explicitly instead of returning an empty string.
try:
    ue_asset_intake_toolset.normalize("   ")
except ValueError as exc:
    print(f"rejected: {exc}")
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
