# Public content expansion 2026 — official source inventory

Research date: 2026-08-23. This inventory is a discovery record, not public
product copy and not an assertion that an initiative has a particular effect.

## Escuelas Protegidas

| Field | Verified official value |
| --- | --- |
| Official name | Establece medidas de seguridad, orden y respeto para la comunidad educativa |
| Bulletin | 18.156-04 |
| Origin | Executive message, Chamber of Deputies |
| Entry | 2026-04-07 |
| Public status | Finished processing; Law 21.827, Official Gazette 2026-08-12 |
| Current-law source | LeyChile `idNorma=1226950`, version `2026-08-12` |

Official source URLs:

- Chamber processing record: `https://www.camara.cl/legislacion/proyectosdeley/tramitacion.aspx?prmBOLETIN=18156-04&prmID=18814`
- LeyChile current text: `https://www.bcn.cl/leychile/navegar?idNorma=1226950&idVersion=2026-08-12`
- Chamber vote detail example: `https://www.camara.cl/legislacion/sala_sesiones/votacion_detalle.aspx?prmIdVotacion=88705`

Available primary material: message, executive indications, commission report,
Chamber and Senate processing, individual Chamber vote pages, final published
law and current version. The published text expressly permits a sponsor to put
review of backpacks, bags and other personal effects (excluding clothing) in
its internal rules; it also contains rights, procedure and non-forcing limits.

Known limitations: the discovery record alone does not verify every vote,
including every vote on the final text. The Chamber does, however, publish an
individual vote for a renewed indication that would have excluded mobile
devices and prohibited their physical or digital examination, access to content,
unlocking, or display. That indication was rejected 60-89 (no abstentions) on
2026-04-21: `https://www.camara.cl/legislacion/sala_sesiones/votacion_detalle.aspx?prmIdVotacion=88690`.
The verified LeyChile fragment does not itself establish a specific phone rule;
that absence must not be presented as a general legal conclusion without a
complete, reviewed final-text extraction.

Candidate question: “¿Qué puede revisar ahora un establecimiento educacional y
cuáles son los límites de esa facultad?”

## Reconstrucción nacional y desarrollo económico y social

| Field | Verified official value |
| --- | --- |
| Official name | Para la reconstrucción nacional y el desarrollo económico y social |
| Bulletin | 18.216-05 |
| Origin | Executive message |
| Verified Senate event | General approval: 26 for, 23 against, 1 abstention on 2026-06-24 |
| Verified later event | Mixed Commission dispatched and sent to Chamber on 2026-07-22 |
| Current discovery status | In processing; no final law is asserted by this inventory |

Official source URLs:

- Senate general-vote report: `https://www.senado.cl/comunicaciones/noticias/senado-aprueba-en-general-proyecto-de-reconstruccion-nacional-y-desarrollo`
- Senate Mixed Commission session: `https://www.senado.cl/actividad-legislativa/comisiones/1482/22778`
- Official executive indication: `https://tramitacion.senado.cl/appsenado/index.php?mo=tramitacion&ac=getDocto&iddocto=36193&tipodoc=ofic`
- Chamber voting index: `https://www.camara.cl/legislacion/sala_sesiones/votaciones.aspx`

Available primary material: message, indication, committee material, Senate
general vote, mixed-commission record, and Chamber voting records. The Senate
itself uses “megarreforma” in a news item; it is not an official project name.

Known limitations: final consolidated text, a publication, a veto, and a
Constitutional Court decision are not established by this inventory. They must
remain absent/unknown until their primary source is imported.

Candidate question: “¿Qué cambia realmente la iniciativa y cómo fue
modificándose durante su tramitación?”

## Security, exception powers and rights discovery

| Topic | Official identification | Discovery result |
| --- | --- | --- |
| States of exception / identity control | Bulletin 18.258-07, executive message dated 2026-05-18 | Primary message and Chamber committee processing found; insufficient reviewed material for a citizen expedient |
| Emergency extension | Senate matter S 2741-14 | A completed congressional approval of an extension was found; it is an event, not yet a sufficiently bounded rights/faculties expedition |

The security topics are deferred pending the exact bill record, complete text,
legislative status, controls and primary documentary evidence.

### Bulletin 18.258-07 acquisition closure

| Field | Certified corpus status |
| --- | --- |
| Bulletin | 18.258-07 |
| Status | `BLOCKED_PRIMARY_PROJECT_TEXT` |
| Current law | Law 18.415 acquired from LeyChile (`idNorma=29824`, effective current version `1990-01-24`) |
| Original project | `NOT_ACQUIRED` |
| Comparative | `NOT_ACQUIRED` |
| Chamber primary document | Direct public message resource returned HTTP 403; no bypass attempted |
| BCN | No primary or full reproduction located |
| Senate | Public project reference located; no primary text acquired |
| BCN minute | `SUMMARY_ONLY` |
| Materialization gate | `FAIL` |

The citizen expedient is intentionally not materialized. The current DEO corpus
does not permit us to certify the bill's primary text and its comparative with
sufficient provenance. This does not assert that those documents do not exist;
only that they are not acquired in the DEO corpus.

## LeyChile minimum vertical-slice feasibility

**PASS, subject to a narrow contract.** LeyChile supplies stable canonical URLs
with `idNorma` and `idVersion`, plus title, number, current text and publication
metadata. It can close the project-to-current-law chain for a selected law.

The suitable first slice is a read-only, one-law ingestion contract: persist
canonical URL, norm id, law number, version date, title, publication date and
selected verified text fragments. It must not crawl LeyChile, infer a connector
state, or claim a law is current without the canonical version metadata.
