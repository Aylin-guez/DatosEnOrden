# Reflex Troubleshooting

This guide is for local development on the Reflex prototype. It does not deploy
DatosEnOrden and must not expose PostgreSQL publicly.

## Slow First Startup

The first `reflex run` can be slow on Windows because Reflex may install or
verify frontend packages, generate `.web/` files, and prepare a Node/Vite
development server. Later starts are usually faster once the frontend cache is
warm.

If startup appears stuck, run diagnostics first instead of changing application
code.

## Run Diagnostics

From the repository root:

```powershell
python scripts/web/check_reflex_environment.py
```

The script checks:

- current working directory
- Python executable and version
- Reflex import/version
- Node and npm versions
- Node minimum version `>= 22.12.0`
- `rxconfig.py`
- Reflex app module import
- `DATABASE_URL`
- PostgreSQL `select 1`
- ports `3000`, `3001`, `8000`, and `8001`

## Node Version Issue

Reflex frontend tooling depends on Node. DatosEnOrden expects Node
`>= 22.12.0` for the local Reflex prototype.

Check manually:

```powershell
node --version
npm --version
```

If Node is older, install a current LTS/current version and restart the terminal
before running Reflex again.

## Python Launcher Issue

On Windows, `python` may point to the Microsoft Store launcher instead of a real
interpreter. Check:

```powershell
Get-Command python -All
python --version
```

Use the real Python executable that has the project dependencies installed.

## Windows vs WSL

Reflex may warn that WSL is recommended. This is mostly about frontend install
and filesystem performance. Windows can still work, but WSL often gives faster
Node package operations and fewer file-watching issues.

## Compile Dry Run

Use this to validate the Reflex app without starting the dev server:

```powershell
$env:PYTHONPATH="src"
reflex compile --dry --no-rich
```

## Run With Fixed Ports

Use fixed ports when `3000` or `8000` are occupied or when the browser keeps
stale dev-server state.

```powershell
scripts/web/run_reflex_dev.ps1
```

The runner changes into the repository root, prints diagnostics, sets
`PYTHONPATH`, and runs:

```powershell
python -m reflex run --frontend-port 3001 --backend-port 8001
```

## PostgreSQL Notes

The Reflex prototype reads PostgreSQL through the existing service layer and
configuration utilities. It should never connect directly from the browser, and
local PostgreSQL should never be exposed publicly.
