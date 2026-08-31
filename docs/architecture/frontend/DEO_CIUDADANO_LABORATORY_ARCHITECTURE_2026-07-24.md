# DEO Ciudadano - Laboratory Architecture

Fecha de ejecucion: 2026-07-24

## Proposito

`reflex_app/features/laboratory/` reserva la frontera modular para el futuro Laboratorio de Politicas Publicas. En Fase 13 no implementa funcionalidades, no registra rutas y no modifica `AppState`, navegacion, shell ni footer.

El objetivo es que Laboratory nazca como feature independiente y no tenga que extraerse despues desde `reflex_app/reflex_app.py`.

## Estructura Inicial

```text
reflex_app/features/laboratory/
├── __init__.py
├── pages.py
├── components.py
├── state.py
└── models.py
```

Estos archivos contienen solo la frontera del paquete. No contienen paginas Reflex, componentes reales, modelos de dominio ni state funcional.

## Responsabilidades Futuras

- `pages.py`: paginas futuras del Laboratorio y registro explicito de rutas cuando una fase lo autorice.
- `components.py`: componentes especificos de Laboratory, sin llamadas directas a clientes externos.
- `state.py`: state propio de Laboratory o adaptadores minimos de feature, sin agregar campos de dominio al `AppState` monolitico.
- `models.py`: modelos de Expediente, Hipotesis, Evidencia, Participacion e Indicador, o imports desde modelos compartidos ya justificados.
- `__init__.py`: frontera publica minima del paquete.

## Limites

- No se registra ninguna ruta en Fase 13.
- No se agrega ningun `@rx.page`.
- No se agrega navegacion.
- No se modifica shell ni footer.
- No se modifica `AppState`.
- No se importa `reflex_app.reflex_app` desde Laboratory.
- No se implementa UI, state, servicios, clientes ni flujo de Laboratorio.

## Dependencias Permitidas

Cuando se implemente una fase futura, Laboratory podra depender de:

- modulos ya extraidos de `reflex_app.constants`;
- modelos compartidos en `reflex_app.models` si el uso esta justificado;
- helpers puros en `reflex_app.helpers`;
- layouts compartidos seguros en `reflex_app.layouts`;
- componentes comunes presentacionales en `reflex_app.components.common`;
- clientes o casos de uso propios bajo `reflex_app/features/laboratory/`;
- configuracion externa para URLs publicas del backend.

## Dependencias Prohibidas

Laboratory no debe depender de:

- `reflex_app.reflex_app`;
- `AppState` monolitico para campos de dominio;
- DEO Core o modulos privados de backend desde el frontend;
- Bricks desde componentes;
- secretos, API keys, puertos internos o URLs internas hardcodeadas;
- clientes globales del frontend que mezclen dominios;
- modelos grandes definidos directamente dentro de una pagina;
- autodiscovery de rutas.

## Flujo Previsto

```text
Pagina Laboratory
v
Laboratory State o caso de uso de feature
v
Cliente/configuracion propia de Laboratory
v
API publica o Gateway configurado
v
View models para componentes Laboratory
```

Los componentes no llamaran servicios externos. Las paginas coordinaran UI y eventos; el State o los casos de uso haran la coordinacion de datos.

## Integracion Futura Con Expedientes

Laboratory podra enlazar a Expedientes existentes, pero no duplicarlos dentro de una pagina.

Reglas previstas:

- Reutilizar rutas publicas de expediente mediante helpers ya extraidos.
- Mantener modelos de Expediente/Hipotesis/Evidencia separados de los componentes.
- Si se requiere interoperar con `PUBLIC_RECORD_STATE`, hacerlo mediante un adaptador minimo documentado.
- No agregar cientos de campos Laboratory al `AppState` legacy.
- Mantener la navegacion declarativa como fuente de verdad cuando se agregue una entrada futura.
- Registrar rutas con imports explicitos, nunca por autodiscovery.

## Estado De Fase 13

- Paquete creado.
- Documentacion creada.
- Rutas no registradas.
- `@rx.page` no agregado.
- `AppState` no modificado.
- Navegacion no modificada.
- Shell y footer no modificados.
- Fase 14 no iniciada.
