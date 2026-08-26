# Runtime OCR local

Esta capacidad extrae texto de imágenes de documentos oficiales escaneados. No
es una fuente, evidencia autónoma ni una corrección del documento.

La autoridad siempre es el archivo oficial original y su SHA-256. Un resultado
OCR debe conservar documento, hash, página, parámetros de render, motor,
versión, idioma y texto raw. Los datos materiales comienzan como `UNVERIFIED`.

## Provisionar

```powershell
.\scripts\provision_ocr.ps1
```

El runtime queda aislado en `data/tmp/ocr_runtime/tesseract`, ignorado por Git.
Utiliza Tesseract en CPU y el modelo español oficial `spa`. No modifica `.venv`,
PostgreSQL, el PATH del sistema ni datos de producción.

El provisionador verifica SHA-256 tanto del binario Windows como del modelo. Una
vez descargados, ambos quedan locales; la extracción posterior opera sin Internet.

## Limpieza

Se puede eliminar `data/tmp/ocr_runtime` para reconstruir el runtime. Nunca se
deben borrar los originales adquiridos ni sus manifiestos de provenance.
