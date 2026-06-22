# DatosEnOrden Reflex prototype

This folder is retained for legacy notes. The runnable Reflex app now lives at
the repository root in `reflex_app/`.

Run from the repository root:

```powershell
$env:PYTHONPATH="src"
reflex run
```

The app reads the same local PostgreSQL source of truth as the Streamlit
prototype. It does not add datasets or call external APIs.
