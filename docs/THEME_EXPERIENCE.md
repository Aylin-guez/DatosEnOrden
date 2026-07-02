# Theme Experience

## Filosofia

Un tema reune todo el conocimiento relacionado con un asunto publico.

La vista de tema no reemplaza la lectura documentada, el documento oficial, el expediente ni el seguimiento. Los ordena en una experiencia principal para que una persona pueda entender primero el asunto y luego bajar a la evidencia.

## Topic View

`Topic View` es una experiencia de usuario, no una nueva arquitectura.

Para la primera version se usa el tema `Ley de Presupuestos del Sector Publico 2013`, derivado del boletin y del documento oficial ya cargados. La vista reutiliza:

- Lectura documentada existente.
- Documento oficial existente.
- Knowledge existente.
- Timeline existente del expediente.
- Resumen de expediente existente.
- Resumen de votaciones existente.
- Fragmentos y referencias existentes.

## Orden de lectura

La vista organiza el tema asi:

1. Hero: titulo, estado, tiempo estimado, documentos, ultima actualizacion y organismos.
2. Documento oficial.
3. Que propone.
4. Que cambia.
5. Que NO cambia.
6. Que sigue.
7. Evidencia.
8. Lecturas Documentadas.
9. Expediente.
10. Seguimiento.
11. Votaciones.
12. Documento original.

## Navegacion

La ruta principal es `/topic`.

La navegacion conceptual es:

`Tema -> Lectura -> Documento -> Fragmento`

En esta version:

- `Tema` apunta a `/topic`.
- `Lectura` apunta a la seccion de lecturas documentadas.
- `Documento` apunta a la seccion del documento oficial.
- `Fragmento` apunta a la seccion de evidencia.
- El documento completo se abre en `/official-document`.

## Restricciones

Esta version no crea motores, adapters, fuentes, APIs ni schema. Tampoco modifica Platform Core, Reading Pipeline, Knowledge Engine ni Publication Engine.

La vista solo reorganiza informacion disponible.
