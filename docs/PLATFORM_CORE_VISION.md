# Platform Core Vision

## 1. Que Es DatosEnOrden Studio

DatosEnOrden Studio es el espacio donde se desarrollan motores de informacion configurables: piezas reutilizables para transformar documentos, registros, eventos y evidencia en conocimiento, seguimiento y reportes.

Studio no debe ser una coleccion de proyectos aislados. Cada proyecto nuevo debe fortalecer motores comunes o ampliar configuraciones reutilizables.

## 2. Que Es DatosEnOrden Publico

DatosEnOrden publico es la primera aplicacion demostrativa construida sobre esos motores. Su dominio actual usa informacion publica local de prueba y una narrativa ciudadana, pero no define el limite de la plataforma.

El producto publico demuestra:

- busqueda y expediente
- seguimiento
- conocimiento estructurado
- reportes ciudadanos
- fuentes conectadas

## 3. Que Son Los Motores

Los motores son componentes de Core que conocen abstracciones estables:

- entidades
- relaciones
- eventos
- documentos
- evidencia
- fuentes
- estados
- workflows
- plantillas
- audiencias
- formatos

Motores actuales o conceptuales:

- Knowledge Engine: convierte documentos o datos en claims, preguntas, evidencia, resumen y digest reutilizable.
- TraceFlow / Tracking Engine: sigue historia, eventos, estados, documentos y cambios en el tiempo.
- ThirdLifeEngine / Report Engine: convierte conocimiento estructurado en reportes, HTML, PDF, publicaciones y materiales para audiencias.
- Source Plugins: adaptadores que conectan fuentes publicas o fuentes de cliente.

## 4. Que Es Platform Core / Configuration Core

Platform Core es el conjunto de modelos, contratos y helpers que permite que los motores funcionen en distintos dominios sin cambiar codigo de negocio.

Configuration Core es la capa declarativa que aporta vocabulario, tipos, workflows, audiencias, plantillas, flags y branding para cada dominio o cliente.

El Core pregunta:

- que entidades existen?
- que relaciones se permiten?
- que estados tiene este workflow?
- que audiencias existen?
- que templates puede producir el motor?

La configuracion responde esas preguntas.

## 5. Por Que No Hardcodear Negocio

Hardcodear negocio crea motores duplicados:

- TraceFlow Fiscalia
- TraceFlow Clinica
- TraceFlow Municipalidad
- TraceFlow Minera

La meta es un solo TraceFlow Engine configurable por dominio. Lo mismo aplica a Knowledge Engine, Report Engine y motores futuros.

Si un motor conoce conceptos como pais, politica, pacientes, facturas, expedientes, empresas, contratos, productos o clientes, queda atrapado en un dominio. Esos conceptos deben vivir en configuracion o adaptadores.

## 6. Core, Configuracion, Adaptador Y Producto Final

Core:

- modelos abstractos
- contratos de datos
- validadores
- motores rule-based generales
- exportadores genericos
- helpers de workflow y evidencia

Configuracion:

- vocabulario de dominio
- entity types
- relationship types
- document types
- evidence types
- workflows
- audiencias
- templates
- branding
- feature flags

Adaptador de fuente:

- carga una fuente especifica
- normaliza datos externos al contrato del Core
- conoce detalles del proveedor, cliente, archivo o API
- no contamina el Core con reglas propias de la fuente

Producto final:

- experiencia visible
- rutas
- copy
- demo o aplicacion cliente
- configuracion seleccionada
- permisos, despliegue y branding

## 7. Principio De Evolucion

Cada proyecto de cliente debe mejorar el Core o ampliar configuracion, no crear un software aislado.

Un proyecto nuevo puede aportar:

- un nuevo Source Plugin
- una nueva configuracion de dominio
- una plantilla reusable
- una mejora del motor aplicable a otros dominios
- un bugfix o validacion general

No debe aportar:

- un fork completo del motor
- reglas de cliente incrustadas en el Core
- duplicacion de modelos existentes con otro nombre

## 8. Cuando Algo Entra Al Core

Entra al Core si:

- aplica a mas de un dominio
- describe una abstraccion estable
- mejora validacion o interoperabilidad
- reduce duplicacion real
- puede probarse sin datos de cliente
- no necesita vocabulario de negocio especifico

Ejemplos:

- validacion de workflows
- representacion de evidencia
- export HTML generico
- timeline de eventos
- resumen JSON-safe

## 9. Cuando Algo Queda Como Configuracion De Cliente

Queda como configuracion si:

- cambia por industria o cliente
- es vocabulario de negocio
- define estados propios del workflow
- define audiencias o templates particulares
- es branding o tono
- activa/desactiva features

Ejemplos:

- "Reporte ciudadano"
- "Reporte ejecutivo"
- "Hito aprobado"
- "Paciente"
- "Factura"
- "Proyecto interno"

## 10. Riesgos

Sobreconfigurar demasiado pronto:

- agregar capas declarativas antes de conocer patrones reales puede frenar el producto.
- regla: configurar solo lo que ya aparece en dos o mas contextos o tiene alta probabilidad de variar.

Hacer motores demasiado abstractos:

- abstracciones sin uso real se vuelven dificiles de explicar y probar.
- regla: cada abstraccion debe tener caso demo, test y salida visible.

Mezclar demo ciudadano con producto comercial:

- el demo publico tiene lenguaje ciudadano y fuentes publicas locales.
- el Core debe seguir siendo neutral y portable.
- regla: copy de producto no debe entrar al motor.

Meter reglas de cliente dentro del Core:

- una necesidad puntual puede parecer generica.
- regla: si menciona una industria, cliente o fuente concreta, primero va a configuracion o adaptador.
