from __future__ import annotations

from html import escape
from textwrap import wrap

from datosenorden.maintenance.traceability_inspector import TraceCompactSummary


def render_trace_graph_html(summaries: tuple[TraceCompactSummary, ...], external_id: str) -> str:
    title = f"Primer grafo exportable: {external_id}"
    subtitle = "Servicio de Salud Arauco \u2192 Orden de compra \u2192 Proveedor"

    sections = []
    for index, summary in enumerate(summaries, start=1):
        sections.append(_render_card(summary, index, len(summaries)))

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(title)}</title>
  <style>
    :root {{
      --bg: #f5f1ea;
      --panel: #ffffff;
      --ink: #1f2933;
      --muted: #52616b;
      --line: #d8cfc2;
      --buyer: #edf4ff;
      --order: #f4f0e8;
      --supplier: #edf8ef;
      --accent: #0f766e;
      --shadow: 0 18px 50px rgba(31, 41, 51, 0.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
      background:
        radial-gradient(circle at top left, rgba(15, 118, 110, 0.12), transparent 30%),
        linear-gradient(180deg, #faf7f1, var(--bg));
    }}
    .page {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    .hero {{
      background: rgba(255, 255, 255, 0.82);
      border: 1px solid rgba(82, 97, 107, 0.15);
      border-radius: 24px;
      box-shadow: var(--shadow);
      padding: 24px 28px;
      margin-bottom: 24px;
      backdrop-filter: blur(6px);
    }}
    .hero h1 {{
      margin: 0 0 8px;
      font-size: clamp(28px, 3vw, 40px);
      line-height: 1.1;
    }}
    .hero p {{
      margin: 0;
      color: var(--muted);
      font-size: 1rem;
    }}
    .card {{
      background: rgba(255, 255, 255, 0.9);
      border: 1px solid rgba(82, 97, 107, 0.14);
      border-radius: 24px;
      box-shadow: var(--shadow);
      padding: 20px;
      margin-bottom: 20px;
    }}
    .card h2 {{
      margin: 0 0 8px;
      font-size: 1.2rem;
    }}
    .meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      color: var(--muted);
      font-size: 0.95rem;
      margin-bottom: 14px;
    }}
    .meta strong {{
      color: var(--ink);
    }}
    .svg-wrap {{
      overflow-x: auto;
      border: 1px solid var(--line);
      border-radius: 18px;
      background: linear-gradient(180deg, #fff, #fbf8f2);
    }}
    svg {{
      display: block;
      width: 100%;
      min-width: 980px;
      height: auto;
    }}
    .footer {{
      margin-top: 12px;
      display: grid;
      gap: 8px;
      color: var(--muted);
      font-size: 0.95rem;
    }}
    .footer a {{
      color: var(--accent);
      word-break: break-word;
    }}
    .badge {{
      display: inline-block;
      padding: 5px 10px;
      border-radius: 999px;
      font-size: 0.8rem;
      font-weight: 600;
      letter-spacing: 0.02em;
      background: rgba(15, 118, 110, 0.08);
      color: var(--accent);
    }}
  </style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <div class="badge">DatosEnOrden</div>
      <h1>{escape(title)}</h1>
      <p>{escape(subtitle)}</p>
    </section>
    {"".join(sections)}
  </main>
</body>
</html>
"""


def _render_card(summary: TraceCompactSummary, index: int, total: int) -> str:
    buyer = summary.buyer_organization or "Sin comprador"
    order_name = summary.contract_name or "Orden de compra"
    supplier = summary.supplier_company or "Sin proveedor"
    evidence_url = summary.public_evidence_url or "#"

    buyer_lines = _wrap_lines(buyer)
    order_lines = _wrap_lines(order_name)
    supplier_lines = _wrap_lines(supplier)

    return f"""
    <section class="card">
      <h2>Grafo {index} de {total}</h2>
      <div class="meta">
        <span><strong>external_id:</strong> {escape(summary.external_id)}</span>
        <span><strong>source_record:</strong> {escape(summary.source_record_id)}</span>
        <span><strong>status:</strong> {escape(summary.source_record_status)}</span>
        <span><strong>claims:</strong> {summary.claims_count}</span>
        <span><strong>public_relationships:</strong> {summary.public_relationships_count}</span>
      </div>
      <div class="svg-wrap">
        <svg viewBox="0 0 980 280" role="img" aria-label="Grafo de trazabilidad">
          <defs>
            <marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto" markerUnits="strokeWidth">
              <path d="M0,0 L10,5 L0,10 z" fill="#5b6570" />
            </marker>
          </defs>
          <text x="490" y="34" text-anchor="middle" fill="#52616b" font-size="15" font-weight="600">
            Servicio de Salud Arauco \u2192 Orden de compra \u2192 Proveedor
          </text>

          <line x1="250" y1="140" x2="410" y2="140" stroke="#5b6570" stroke-width="4" marker-end="url(#arrow)" />
          <line x1="570" y1="140" x2="730" y2="140" stroke="#5b6570" stroke-width="4" marker-end="url(#arrow)" />

          <g data-full-label="{escape(buyer)}" data-role="buyer">
            <rect x="40" y="85" width="210" height="110" rx="18" fill="#edf4ff" stroke="#9ab6de" stroke-width="2" />
            <text x="145" y="118" text-anchor="middle" fill="#1f2933" font-size="13" font-weight="700">Comprador</text>
            {_render_svg_text(buyer_lines, 145, 140)}
          </g>

          <g data-full-label="{escape(order_name)}" data-role="order">
            <rect x="320" y="85" width="210" height="110" rx="18" fill="#f4f0e8" stroke="#d4c4ad" stroke-width="2" />
            <text x="425" y="118" text-anchor="middle" fill="#1f2933" font-size="13" font-weight="700">Orden de compra</text>
            {_render_svg_text(order_lines, 425, 140)}
          </g>

          <g data-full-label="{escape(supplier)}" data-role="supplier">
            <rect x="600" y="85" width="210" height="110" rx="18" fill="#edf8ef" stroke="#a9d5b2" stroke-width="2" />
            <text x="705" y="118" text-anchor="middle" fill="#1f2933" font-size="13" font-weight="700">Proveedor</text>
            {_render_svg_text(supplier_lines, 705, 140)}
          </g>
        </svg>
      </div>
      <div class="footer">
        <div><strong>Public evidence:</strong> <a href="{escape(evidence_url)}">{escape(evidence_url)}</a></div>
      </div>
    </section>
    """


def _render_svg_text(lines: list[str], x: int, y: int) -> str:
    if not lines:
        lines = ["N/D"]

    tspans = []
    start_y = y - 6 * (len(lines) - 1)
    for index, line in enumerate(lines):
        tspans.append(
            f'<tspan x="{x}" y="{start_y + index * 18}" text-anchor="middle">{escape(line)}</tspan>'
        )
    return f'<text fill="#344050" font-size="12" font-weight="500">{"".join(tspans)}</text>'


def _wrap_lines(value: str, width: int = 22) -> list[str]:
    wrapped = wrap(value, width=width, break_long_words=False, break_on_hyphens=False)
    return wrapped or [value]
