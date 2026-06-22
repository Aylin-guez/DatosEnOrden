# DatosEnOrden Reflex prototype

This is a minimal local Reflex frontend over `datosenorden.web.app_services`.

Run from this folder:

```powershell
$env:PYTHONPATH="..\..\src"
reflex run
```

The app reads the same local PostgreSQL source of truth as the Streamlit
prototype. It does not add datasets or call external APIs.
