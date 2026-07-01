# Studio Architecture

DatosEnOrden Studio desarrolla motores de informacion configurables. La idea central es construir una base reutilizable que pueda adaptarse a distintos dominios sin crear un software nuevo para cada cliente.

## Studio Y Producto Publico

DatosEnOrden publico es la primera aplicacion demostrativa. Muestra como conectar fuentes, evidencia, expedientes, seguimiento, conocimiento estructurado y reportes ciudadanos.

DatosEnOrden Studio es la capa de motores y configuracion que permite llevar esas capacidades a otros contextos.

## Motores Configurables

Los motores actuales o en evolucion son:

- Knowledge Engine: estructura documentos, claims, preguntas y evidencia.
- TraceFlow / Tracking Engine: sigue eventos, estados, documentos y cambios.
- ThirdLifeEngine / Report Engine: genera reportes y materiales para distintas audiencias.
- Source Plugins: conectan fuentes publicas o fuentes de cliente.

Los motores no deben conocer el negocio especifico. Deben conocer abstracciones: entidades, documentos, evidencia, eventos, workflows, audiencias y formatos.

## Configuracion Por Dominio

Cada dominio define:

- vocabulario
- tipos de entidades
- relaciones
- workflows
- documentos
- evidencia
- audiencias
- templates
- branding
- features activas

Asi el mismo motor puede servir para casos distintos.

## Ejemplos De Adaptacion

Municipio siguiendo proyectos:

- proyectos comunales
- hitos
- documentos de respaldo
- reportes de avance

Universidad siguiendo investigaciones:

- proyectos academicos
- publicaciones
- investigadores
- evidencia documental

Empresa siguiendo documentos internos:

- proyectos internos
- responsables
- decisiones
- reportes ejecutivos

ONG siguiendo compromisos:

- compromisos publicos
- eventos de avance
- documentos asociados
- reportes para comunidades o donantes

## Que Existe Hoy

Existe una aplicacion publica/demo y motores locales read-only para:

- conocimiento estructurado
- seguimiento
- reportes ciudadanos HTML
- source plugins locales
- configuracion plataforma inicial

## Limites De Los Motores Actuales

Knowledge Engine:

- debe transformar documentos y datos en conocimiento estructurado.
- no debe conocer leyes, paises, industrias ni vocabulario especifico.
- debe tomar labels, audiencias y tipos desde configuracion cuando el dominio lo requiera.

TraceFlow / Tracking Engine:

- debe seguir eventos, estados, documentos y cambios.
- los estados actuales del demo son transitorios.
- el destino es leer workflow states desde `PlatformConfig`.

ThirdLifeEngine / Report Engine:

- debe convertir conocimiento estructurado en salidas para audiencias.
- audiencias y templates deben venir desde configuracion.
- HTML/PDF/publicaciones son formatos, no dominios.

Source Plugins:

- son adaptadores de fuente.
- conocen detalles de archivos, APIs, proveedores o clientes.
- no deben introducir reglas de fuente dentro de Platform Core.

## Que No Se Promete Todavia

No se promete todavia:

- login multiusuario
- pagos o donaciones
- APIs externas productivas
- scraping productivo
- automatizacion completa con LLM
- publicacion con datos reales de cliente sin revision legal y operacional

## Principio Comercial

Cada cliente debe dejar una mejora reusable:

- una configuracion nueva
- un adaptador de fuente
- una plantilla
- una validacion
- una mejora de motor

El objetivo comercial no es vender un sistema cerrado por industria, sino motores configurables que acumulen valor con cada implementacion.
