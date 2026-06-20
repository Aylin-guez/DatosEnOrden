# Demo Walkthrough

## What DatosEnOrden is

DatosEnOrden is a local explorer for public information already stored in PostgreSQL. It connects entities, claims, evidence, source records, and public relationships from several datasets.

## What the demo shows

- One public organization that appears across multiple sources
- ChileCompra contracts
- A Lobby meeting
- A Transparencia Activa role record
- A chronological timeline
- Source-backed evidence and neutral explanations

## What it does not claim

- No accusations
- No corruption claims
- No causal conclusions from ordering alone
- No inference beyond the stored records
- Sample data is clearly marked when applicable

## How to run the demo locally

```powershell
python scripts/demo_seed.py
python scripts/demo_status.py
streamlit run streamlit_app.py
```

If the database is already prepared, `demo_seed.py` is safe to run again.

## Suggested 2-minute demo script

1. Open the Home page and point to the demo banner.
2. Click `Comenzar demo` and open the recommended entity.
3. Show the graph view and explain that it connects stored records only.
4. Open the timeline tab and point out the event order.
5. Open the evidence area and show where each record comes from.
6. End with the neutral explanation that the platform only shows what is stored.

## Suggested screenshots to capture

- Home page with the demo banner and `Comenzar demo` panel
- Entity profile with the timeline tab visible
- Cross-dataset graph view
- Evidence section for the recommended entity
- Demo status output from `python scripts/demo_status.py`

## Neutral language warnings

- No accusations
- No corruption claims
- Evidence-based only
- Sample data clearly marked when applicable
