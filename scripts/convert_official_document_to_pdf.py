from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DOCUMENT_ID = "senado-docto-9000-mensaje_mocion"
DEFAULT_SOURCE = ROOT / "data" / "official_documents" / "incoming" / DEFAULT_DOCUMENT_ID / "document.doc"
DEFAULT_OUTPUT = ROOT / "data" / "official_documents" / "published" / DEFAULT_DOCUMENT_ID / "document.pdf"
DEFAULT_PUBLIC_COPY = ROOT / "assets" / "official_documents" / DEFAULT_DOCUMENT_ID / "document.pdf"
WINDOWS_SOFFICE_CANDIDATES = (
    Path("C:/Program Files/LibreOffice/program/soffice.exe"),
    Path("C:/Program Files (x86)/LibreOffice/program/soffice.exe"),
)


@dataclass(frozen=True)
class ConversionResult:
    ok: bool
    source: Path
    output: Path
    message: str
    public_copy: Path | None = None
    soffice: Path | None = None
    returncode: int = 0


def find_soffice() -> Path | None:
    found = shutil.which("soffice")
    if found:
        return Path(found)
    for candidate in WINDOWS_SOFFICE_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def convert_document_to_pdf(
    source: Path = DEFAULT_SOURCE,
    output: Path = DEFAULT_OUTPUT,
    public_copy: Path | None = DEFAULT_PUBLIC_COPY,
    soffice: Path | None = None,
) -> ConversionResult:
    source = source.resolve()
    output = output.resolve()
    public_copy = public_copy.resolve() if public_copy is not None else None
    soffice = soffice or find_soffice()

    if not source.exists():
        return ConversionResult(False, source, output, f"No existe el documento oficial de entrada: {source}")
    if soffice is None:
        return ConversionResult(
            False,
            source,
            output,
            "LibreOffice Headless no esta disponible. Instala LibreOffice y asegura que 'soffice' este en PATH.",
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(soffice),
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        str(output.parent),
        str(source),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "conversion failed").strip()
        return ConversionResult(False, source, output, detail, soffice=soffice, returncode=completed.returncode)
    if not output.exists():
        return ConversionResult(False, source, output, f"LibreOffice termino sin crear el PDF esperado: {output}", soffice=soffice)
    if public_copy is not None:
        public_copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(output, public_copy)
    return ConversionResult(True, source, output, f"PDF publicado: {output}", public_copy=public_copy, soffice=soffice)


def main() -> int:
    result = convert_document_to_pdf()
    status = "OK" if result.ok else "ERROR"
    print(f"official_document_pdf: {status}")
    print(f"  source={result.source}")
    print(f"  output={result.output}")
    if result.public_copy is not None:
        print(f"  public_copy={result.public_copy}")
    if result.soffice is not None:
        print(f"  soffice={result.soffice}")
    print(f"  message={result.message}")
    if not result.ok and result.soffice is None:
        print("  install=Instala LibreOffice y verifica: soffice --headless --version")
    return 0 if result.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())