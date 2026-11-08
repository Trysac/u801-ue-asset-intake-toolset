# Stack

## Used

| Tool | Why |
|---|---|
| Python >= 3.10 | Lowest supported version; the package uses only the standard library at runtime. |
| uv | Environment and build management for local development. |
| hatchling | Build backend declared in the project metadata; no setup.py. |
| ruff | Lint and format. |
| mypy (strict) | Type checking; the package ships `py.typed`. |
| pytest + pytest-cov | Test runner and branch coverage. |
| hypothesis (dev, >=6.100,<7) | Allowed as a development dependency for property tests; no property tests are present in the reviewed tree. |
| gitleaks | Secret scanning. |
| GitHub Actions + Dependabot | Continuous integration and dependency updates. |

## Discarded

| Tool | Why not |
|---|---|
| Poetry | uv covers the same needs with standard dependency groups. |
| black + isort + flake8 | Replaced by ruff: one tool instead of three. |
| tox / nox | Multi-environment runs are handled in CI. |
| Shell scripts for gates | Not portable to Windows. |
