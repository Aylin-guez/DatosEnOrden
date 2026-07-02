from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from datosenorden.adapters.legislature import LegislativeDocumentResolver  # noqa: E402

INCOMING_DIR = ROOT / "data" / "official_documents" / "incoming"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Download one official legislative document into incoming documents."
    )
    parser.add_argument("bulletin", help="Complete bulletin id, for example 8575-05.")
    parser.add_argument("--type", required=True, dest="document_type", help="Document type to download.")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    document_path, metadata_path, selected = LegislativeDocumentResolver().download_selected(
        args.bulletin,
        args.document_type,
        INCOMING_DIR,
    )
    print("legislative_document_download: OK")
    print(f"  boletin={args.bulletin}")
    print(f"  type={selected.type}")
    print(f"  document_id={selected.document_id}")
    print(f"  document={document_path}")
    print(f"  metadata={metadata_path}")
    print("  next_step=manual review: incoming -> processing -> reading pipeline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
