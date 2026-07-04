# Legislative Document Flow

Fase: Legislative Document Experience V1.

Este documento describe el flujo futuro. No implementa adapters, no crea motores y no modifica componentes existentes.

## Flujo objetivo

```text
Boletin
  |
  v
Documento
  |
  v
Reading Pipeline
  |
  v
Knowledge
  |
  v
Publication
  |
  v
Lectura Documentada
  |
  v
Expediente enriquecido
```

## Version expandida

```text
cl-congreso-boletin-<boletin_completo>
  |
  | resolver fuente oficial
  v
Senado tramitacion.php?boletin=<correlativo>
  |
  | validar <boletin> completo
  v
Indice documental oficial
  |
  | seleccionar documento
  v
getDocto?iddocto=<iddocto>&tipodoc=<tipo>
  |
  | registrar metadata, hash, formato y fecha de recuperacion
  v
Official Document Workflow
  |
  | preparar documento local compatible
  v
Reading Pipeline
  |
  | extraer fragmentos, evidencia y estructura
  v
Knowledge Engine
  |
  | generar lectura documentada con trazabilidad
  v
Publication Engine
  |
  | publicar salida ciudadana
  v
Expediente legislativo enriquecido
```

## Responsabilidades por etapa

### Boletin

Entrada canonica:

```text
cl-congreso-boletin-<boletin_completo_normalizado>
```

Ejemplo:

```text
cl-congreso-boletin-8575-05
```

Responsabilidad:

- Identificar el proyecto legislativo.
- Preservar el boletin completo como canonico.
- Mantener aliases tecnicos como `8575` solo para consulta cuando una fuente lo exija.

### Documento

Fuente primaria V1:

```text
Senado
```

Resolucion:

```text
tramitacion.php -> lista documentos asociados -> getDocto
```

Tipos esperados:

- mensaje/mocion
- informe
- comparado
- oficio
- otros documentos que aparezcan en el XML oficial

Metadata minima:

```text
bill_id
display_boletin
source_organization
source_project_url
source_document_url
iddocto
tipodoc
document_type
content_type
retrieval_date
content_hash
```

### Reading Pipeline

Entrada esperada:

```text
Documento oficial ya descargado o preparado localmente
Metadata oficial asociada
```

No debe:

- consultar Senado;
- consultar Camara;
- resolver boletines;
- conocer `iddocto` o `tipodoc`;
- decidir que documentos descargar.

### Knowledge

Entrada esperada:

```text
Fragmentos y evidencia producidos por Reading Pipeline.
```

No debe:

- llamar endpoints legislativos;
- inferir cobertura que la fuente no entregue;
- mezclar texto de proyecto con texto de ley publicada sin explicitarlo.

### Publication

Entrada esperada:

```text
Lectura documentada validada.
```

Debe mostrar:

- boletin;
- organismo;
- URL oficial;
- tipo documental;
- fecha de recuperacion;
- formato original;
- limitaciones conocidas.

### Lectura Documentada

Salida ciudadana:

```text
Una lectura comprensible, trazable y anclada en el documento oficial.
```

Debe distinguir:

- texto inicial del proyecto;
- informes;
- comparados;
- oficios;
- votaciones;
- texto de ley publicada;
- historia consolidada.

### Expediente enriquecido

Resultado:

```text
El expediente del boletin deja de ser solo una entidad con votaciones y pasa a tener documentos oficiales seleccionados, leidos y trazables.
```

## Flujo por organismo

### Ruta primaria: Senado

```text
Boletin completo
  -> correlativo Senado
  -> tramitacion.php
  -> link_mensaje_mocion / informes / comparados / oficios
  -> getDocto
  -> documento oficial
```

Uso:

```text
Texto del proyecto y documentos asociados.
```

### Ruta complementaria: Camara

```text
Boletin completo
  -> getVotaciones_Boletin
  -> Votacion.ID / Sesion.ID
  -> getSesionBoletinXML
  -> documento de sesion
```

Uso:

```text
Votaciones, detalle parlamentario y boletines de sesion.
```

### Ruta posterior: LeyChile

```text
Proyecto publicado
  -> numero de ley / identificador de norma
  -> LeyChile
  -> texto normativo vigente o versionado
```

Uso:

```text
Texto final de norma publicada.
```

### Ruta posterior: BCN Historia de la Ley

```text
Proyecto publicado o historia disponible
  -> identificador BCN Historia de la Ley
  -> HTML/PDF consolidado
```

Uso:

```text
Historia legislativa consolidada.
```

## Politica V1

La V1 debe ser manual, acotada y auditable:

```text
1 boletin explicito
1 indice documental oficial
1 documento seleccionado
0 crawling
0 descarga masiva
0 publicacion automatica
```

## Contrato conceptual

```text
LegislativeDocumentCandidate
  bill_id
  display_boletin
  source
  source_url
  document_url
  document_type
  source_document_id
  source_document_kind
  title
  date
  chamber
  content_type
  retrieval_status
```

Este contrato es conceptual. No se crea todavia en codigo.

## Caso 8575-05

Entrada:

```text
cl-congreso-boletin-8575-05
```

Consulta Senado verificada:

```text
https://tramitacion.senado.cl/wspublico/tramitacion.php?boletin=8575
```

Validacion:

```text
<boletin>8575-05</boletin>
```

Documento inicial:

```text
iddocto=9000
tipodoc=mensaje_mocion
Content-Type observado: application/msword
```

Documento oficial:

```text
https://www.senado.cl/appsenado/index.php?mo=tramitacion&ac=getDocto&iddocto=9000&tipodoc=mensaje_mocion
```

## Recomendacion de implementacion siguiente

Crear una pieza pequena de descubrimiento documental, separada del adapter actual y sin tocar engines:

```text
resolve_legislative_documents(bill_id)
  -> consulta Senado
  -> valida boletin completo
  -> devuelve candidatos documentales
```

Luego una segunda accion explicita:

```text
fetch_legislative_document(candidate_id)
  -> descarga un getDocto seleccionado
  -> registra metadata/hash
  -> deja el archivo listo para Official Document Workflow
```

No pasar automaticamente al Reading Pipeline hasta que exista seleccion y metadata revisable.
