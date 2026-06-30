# Sanciones y Procedimientos

Status: prototype

Local role: local prototype for administrative procedure and resolution records.

Data policy:

- `LOCAL_TEST_DATA`
- `NOT_OFFICIAL_DATA`
- No external API calls.
- No scraping.
- No inference of delito, corrupcion, riesgo, irregularidad or responsibility.

Commands:

- Loader: `python scripts/load_sanciones_procedimientos_sample.py`
- Summary: `python scripts/sanciones_procedimientos_summary.py`

Connects:

- Organismo
- Empresa
- Persona
- Procedimiento administrativo
- Resolucion administrativa

Notes:

- This source is only a source factory prototype.
- Records are local examples for product demonstration.
- A future official integration must define source URLs, legal basis, update cadence, provenance, and reconciliation rules before production use.
