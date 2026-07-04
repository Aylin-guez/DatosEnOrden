# Document Template V1

Este documento define la estructura oficial permanente para todas las Lecturas Documentadas de DatosEnOrden.

La plantilla no genera conocimiento, no interpreta documentos y no reemplaza motores existentes. Define el orden visual y el contrato de datos que deben entregar los flujos previos para que cualquier documento futuro se presente con el mismo formato.

## Principios

- Todo contenido debe estar respaldado por evidencia documental.
- No se debe hardcodear contenido especifico de un documento.
- La misma estructura aplica a documentos demo, documentos reales, decretos, proyectos, licitaciones, informes y presupuestos.
- Si una seccion no tiene elementos, debe mostrar un mensaje explicito en vez de ocultarse.
- El documento oficial y sus referencias deben permanecer visibles y navegables.

## Orden visual obligatorio

### 1. Documento oficial

Mostrar:

- titulo
- organismo
- fecha
- tipo de documento
- estado
- enlace al documento oficial

Contrato esperado:

```json
{
  "document": {
    "title": "...",
    "organization": "...",
    "date": "YYYY-MM-DD",
    "document_type": "...",
    "status": "...",
    "official_url": "https://..."
  }
}
```

### 2. Que propone?

Resumen muy breve, basado solo en evidencia documental.

Contrato esperado:

```json
{
  "proposal_summary": {
    "text": "...",
    "evidence_ids": ["..."]
  }
}
```

### 3. Que cambia?

Mostrar unicamente cambios respaldados por el documento. Cada punto debe enlazar a su evidencia.

Contrato esperado:

```json
{
  "documented_changes": [
    {
      "id": "...",
      "text": "...",
      "evidence_ids": ["..."],
      "reference_label": "Pagina ..."
    }
  ]
}
```

### 4. Que NO dice el documento?

Esta seccion es obligatoria. Debe mostrar afirmaciones frecuentes que no estan respaldadas por el documento.

No inventar. Si no existen elementos, mostrar exactamente:

```text
No se identificaron afirmaciones relevantes fuera del documento.
```

Contrato esperado:

```json
{
  "unsupported_claims": [
    {
      "id": "...",
      "text": "...",
      "reason": "No aparece en el documento revisado."
    }
  ],
  "unsupported_claims_empty_message": "No se identificaron afirmaciones relevantes fuera del documento."
}
```

### 5. Que falta para que esto ocurra?

Explicar, segun el estado documental, en que etapa se encuentra:

- proyecto
- discusion
- aprobacion
- promulgacion
- reglamento
- entrada en vigencia

No interpretar. Solo informar el estado respaldado por el documento.

Contrato esperado:

```json
{
  "implementation_status": {
    "stage": "proyecto | discusion | aprobacion | promulgacion | reglamento | entrada_en_vigencia | no_determinado",
    "text": "...",
    "evidence_ids": ["..."]
  }
}
```

### 6. Preguntas frecuentes

Mostrar preguntas derivadas del Knowledge Engine. Cada respuesta debe enlazar a la evidencia.

Contrato esperado:

```json
{
  "frequent_questions": [
    {
      "id": "...",
      "question": "...",
      "answer": "...",
      "evidence_ids": ["..."],
      "reference_label": "Pagina ..."
    }
  ]
}
```

### 7. Evidencia

Mostrar:

- pagina
- fragmento
- boton `Ir al documento`

El documento debe abrir exactamente en el fragmento correspondiente cuando sea posible.

Contrato esperado:

```json
{
  "evidence": [
    {
      "id": "...",
      "page": 1,
      "fragment_id": "...",
      "quote": "...",
      "document_anchor": "...",
      "open_label": "Ir al documento"
    }
  ]
}
```

### 8. Documento oficial

Mostrar nuevamente metadata de origen:

- documento original
- version
- organismo
- fecha de publicacion
- fecha de recuperacion por DEO

Contrato esperado:

```json
{
  "official_source": {
    "original_document": "...",
    "version": 1,
    "organization": "...",
    "publication_date": "YYYY-MM-DD",
    "retrieval_date": "YYYY-MM-DD"
  }
}
```

### 9. Resumen en una frase

Cerrar siempre con una frase del tipo:

```text
Este documento propone ________, no establece ________ y actualmente se encuentra en ________.
```

Debe construirse unicamente con informacion del documento.

Contrato esperado:

```json
{
  "one_sentence_summary": {
    "text": "Este documento propone ..., no establece ... y actualmente se encuentra en ... .",
    "evidence_ids": ["..."]
  }
}
```

## Contrato completo esperado

```json
{
  "document": {},
  "proposal_summary": {},
  "documented_changes": [],
  "unsupported_claims": [],
  "unsupported_claims_empty_message": "No se identificaron afirmaciones relevantes fuera del documento.",
  "implementation_status": {},
  "frequent_questions": [],
  "evidence": [],
  "official_source": {},
  "one_sentence_summary": {}
}
```

## Relacion con motores existentes

- Reading Pipeline debe proveer paginas, fragmentos, anclas y referencias.
- Knowledge Engine debe proveer resumen, preguntas, puntos y claims documentales.
- Publication Engine debe publicar el contrato hacia las superficies correspondientes.
- La UI debe renderizar esta plantilla sin reconstruir contenido.

## Regla editorial

Si una afirmacion no puede vincularse a evidencia documental, no debe presentarse como hecho. Debe ir en `Que NO dice el documento?` solo si fue identificada como afirmacion frecuente no respaldada. Si no hay elementos, se usa el mensaje obligatorio de ausencia.
