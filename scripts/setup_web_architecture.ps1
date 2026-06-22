# scripts/setup_web_architecture.ps1
$ErrorActionPreference = "Stop"

Write-Host "Creating DatosEnOrden web architecture..." -ForegroundColor Cyan

$dirs = @(
  "web",
  "web\landing",
  "web\landing\assets",
  "web\reflex_app",
  "src\datosenorden\web",
  "docs\deployment"
)

foreach ($dir in $dirs) {
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

@"
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>DatosEnOrden</title>
  <meta name="description" content="Explorador de datos públicos en desarrollo." />
  <link rel="stylesheet" href="./assets/styles.css" />
</head>
<body>
  <main class="page">
    <section class="hero">
      <p class="eyebrow">Proyecto en desarrollo</p>
      <h1>DatosEnOrden</h1>
      <p class="subtitle">
        Explorador de datos públicos para conectar organismos, contratos,
        presupuesto, lobby, transparencia y evidencia.
      </p>
      <div class="actions">
        <a href="#estado" class="button primary">Ver estado del proyecto</a>
        <a href="https://github.com/Aylin-guez/DatosEnOrden" class="button secondary">GitHub</a>
      </div>
    </section>

    <section id="estado" class="grid">
      <article class="card">
        <h2>Qué conecta</h2>
        <p>ChileCompra, Lobby, Transparencia Activa y prototipos de presupuesto.</p>
      </article>
      <article class="card">
        <h2>Qué muestra</h2>
        <p>Relaciones públicas, evidencias, cronologías y vistas de investigación por entidad.</p>
      </article>
      <article class="card">
        <h2>Qué no afirma</h2>
        <p>No acusa ni interpreta irregularidades. Sólo organiza información disponible y evidencia asociada.</p>
      </article>
    </section>

    <section class="notice">
      <h2>Próximamente</h2>
      <p>
        Esta página será el punto de entrada público de DatosEnOrden.
        La demo actual funciona localmente mientras se prepara una versión web desplegable.
      </p>
    </section>
  </main>
</body>
</html>
"@ | Set-Content -Encoding UTF8 "web\landing\index.html"

@"
:root {
  --bg: #071516;
  --panel: #0e2426;
  --panel-2: #123033;
  --text: #eaf7f6;
  --muted: #a8c4c2;
  --accent: #45d6c2;
  --border: rgba(255,255,255,0.10);
}

* { box-sizing: border-box; }

body {
  margin: 0;
  font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background:
    radial-gradient(circle at top left, rgba(69,214,194,0.18), transparent 35%),
    var(--bg);
  color: var(--text);
}

.page {
  width: min(1120px, calc(100% - 32px));
  margin: 0 auto;
  padding: 72px 0;
}

.hero {
  padding: 64px 0 48px;
}

.eyebrow {
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.16em;
  font-size: 0.82rem;
  font-weight: 700;
}

h1 {
  margin: 0;
  font-size: clamp(3rem, 7vw, 6.5rem);
  letter-spacing: -0.07em;
}

.subtitle {
  max-width: 760px;
  color: var(--muted);
  font-size: clamp(1.1rem, 2vw, 1.45rem);
  line-height: 1.6;
}

.actions {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  margin-top: 30px;
}

.button {
  display: inline-flex;
  text-decoration: none;
  border-radius: 999px;
  padding: 12px 18px;
  font-weight: 700;
  border: 1px solid var(--border);
}

.primary {
  background: var(--accent);
  color: #062020;
}

.secondary {
  color: var(--text);
  background: rgba(255,255,255,0.05);
}

.grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 18px;
}

.card,
.notice {
  background: linear-gradient(180deg, var(--panel), var(--panel-2));
  border: 1px solid var(--border);
  border-radius: 24px;
  padding: 24px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.25);
}

.card h2,
.notice h2 {
  margin-top: 0;
}

.card p,
.notice p {
  color: var(--muted);
  line-height: 1.6;
}

.notice {
  margin-top: 18px;
}

@media (max-width: 800px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
"@ | Set-Content -Encoding UTF8 "web\landing\assets\styles.css"

@"
# DatosEnOrden web architecture

## Current goal

Prepare DatosEnOrden for two parallel paths:

1. Static public landing page for datosenorden.cl.
2. Future Python web app using Reflex or another frontend over a frontend-independent service layer.

## Security notes

- Do not expose the local PostgreSQL database publicly.
- Do not deploy `.env`.
- Do not commit secrets.
- Do not expose database credentials in frontend code.
- Public web apps should use a hosted database or read-only API layer.
- Demo/sample data must remain clearly labeled when applicable.

## Current folders

- `web/landing/`: static landing page.
- `web/reflex_app/`: future Reflex prototype.
- `src/datosenorden/web/`: future frontend-independent service layer.
"@ | Set-Content -Encoding UTF8 "docs\deployment\WEB_ARCHITECTURE.md"

@"
# Placeholder for future Reflex prototype.

This folder is intentionally separate from the current Streamlit prototype.

Streamlit remains the local demo.
Reflex will be introduced after the frontend-independent service layer is stable.
"@ | Set-Content -Encoding UTF8 "web\reflex_app\README.md"

@"
"""Frontend-independent service layer for future web apps.

This package should expose plain Python functions that return dict/list data
for Streamlit, Reflex, FastAPI or any future frontend.
"""
"@ | Set-Content -Encoding UTF8 "src\datosenorden\web\__init__.py"

Write-Host "Done." -ForegroundColor Green
Write-Host "Created static landing in web\landing\index.html"
Write-Host "Created web architecture docs in docs\deployment\WEB_ARCHITECTURE.md"