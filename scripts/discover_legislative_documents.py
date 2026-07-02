from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from datosenorden.adapters.legislature import LegislativeDocumentResolver  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("usage: python scripts/discover_legislative_documents.py <boletin>")
        return 2

    bulletin_id = args[0]
    catalog = LegislativeDocumentResolver().discover(bulletin_id)
    print(f"Boletin: {catalog.bulletin_id}")
    print(f"Fuente: {catalog.source}")
    print(f"URL proyecto: {catalog.project_url}")
    print(f"Documentos encontrados: {len(catalog.documents)}")
    for index, document in enumerate(catalog.documents, start=1):
        print("")
        print(f"{index}. {document.title}")
        print(f"   Tipo: {document.type}")
        print(f"   URL oficial: {document.url}")
        print(f"   Formato: {document.format}")
        print(f"   Fecha publicacion: {document.publication_date or 'sin fecha'}")
        print("   Estado: disponible")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
