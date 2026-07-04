# DatosEnOrden Platform

DatosEnOrden publico es la experiencia ciudadana: permite leer documentos oficiales, entenderlos con contexto, revisar referencias y navegar hacia expediente, seguimiento, reportes y actualidad documentada.

DatosEnOrden Studio es la capa reutilizable de motores, flujos y componentes que permite producir esas experiencias de manera consistente. Studio no es una pagina publica; es la base para construir productos de lectura, publicacion y trazabilidad documental.

## Componentes principales

- **Platform Core:** reglas comunes, contratos internos y servicios compartidos.
- **Reading Pipeline:** transforma un documento estructurado en una experiencia de lectura con paginas, fragmentos, anclas y referencias.
- **Knowledge Engine:** organiza conocimiento documentado: resumen ciudadano, puntos importantes, preguntas, claims y evidencia.
- **Publication Engine:** decide que superficies publicas deben actualizarse cuando cambia una fuente documental.
- **Actualidad Documentada:** construye temas publicos basados en documentacion oficial ya analizada.
- **Entity Resolution:** ayuda a reconocer cuando organismos, personas, empresas o registros apuntan a la misma entidad.
- **Dataset Registry:** describe fuentes disponibles, estado, cobertura y rol dentro de la plataforma.
- **Data Pipeline:** carga y normaliza datos locales o reales segun contratos definidos.

## Como se conectan

```text
Fuentes oficiales / documentos
          |
          v
   Data Pipeline ---- Dataset Registry
          |
          v
   Platform Core ---- Entity Resolution
          |
          v
   Reading Pipeline
          |
          v
   Knowledge Engine
          |
          v
   Publication Engine
          |
          v
Actualidad Documentada + Biblioteca + Documento Oficial
          |
          v
Expedientes + Seguimiento + Reportes + Buscador
```

## Relacion publico / Studio

El sitio publico usa los motores de Studio para publicar contenido comprensible y verificable. Studio contiene capacidades reutilizables; el sitio publico presenta resultados ciudadanos sin exponer configuraciones privadas, datos sensibles ni logica comercial de clientes.
