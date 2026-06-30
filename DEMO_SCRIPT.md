# Demo Script

DatosEnOrden es un demo local de expediente ciudadano. Usa datos de prueba, no oficiales, marcados como `LOCAL_TEST_DATA` y `NOT_OFFICIAL_DATA`.

## Ruta recomendada para publico no tecnico

1. Abrir `http://localhost:3000/demo`.
2. Mostrar el checklist: fuentes cargadas, expediente disponible, reporte exportable.
3. Tocar `Abrir expediente de ejemplo`.
4. Mostrar `Resumen ciudadano`.
5. Mostrar `Como se conectan los datos`.
6. Mostrar `Cobertura de fuentes`.
7. Abrir detalles tecnicos solo si preguntan por trazabilidad.
8. Volver a `/demo` y tocar `Ver ecosistema de fuentes`.
9. Tocar `Exportar reporte HTML` para mostrar salida reutilizable.

## Que decir en 60 segundos

DatosEnOrden convierte registros publicos dispersos en un expediente ciudadano entendible. En vez de pedirle a una persona que revise compras, presupuestos, lobby, publicaciones o procedimientos por separado, el sistema reune fuentes, evidencias, relaciones y entidades conectadas en una sola vista. Este demo usa datos locales de prueba; no afirma causalidad, irregularidad ni responsabilidad. Sirve para mostrar como podria verse una herramienta publica de trazabilidad cuando se conecten fuentes reales con reglas claras.

## Botones que tocar

- `/demo`: `Abrir expediente de ejemplo`.
- `/investigation`: `Exportar expediente`.
- `/demo`: `Ver ecosistema de fuentes`.
- `/search?q=Servicio+de+Salud+Arauco`: `Abrir expediente` desde el resultado.

## URLs exactas

```text
http://localhost:3000/demo
http://localhost:3000/
http://localhost:3000/ecosystem
http://localhost:3000/discover
http://localhost:3000/search?q=Servicio+de+Salud+Arauco
http://localhost:3000/investigation
http://localhost:3000/investigation?id=SERVICIO+DE+SALUD+ARAUCO+HOSPITAL+DE+ARAUCO
http://localhost:3000/investigation?id=338d160c-8d5d-47e1-9c37-038ed5043ba1
```

## Aclaraciones sobre datos de prueba

- Son datos locales de demostracion.
- No son datos oficiales en vivo.
- No reemplazan una fuente publica original.
- No prueban delito, corrupcion, riesgo, irregularidad ni responsabilidad.
- Las conexiones muestran relaciones documentales del demo y deben revisarse contra la evidencia original cuando existan datos reales.

## Que queda por integrar con datos reales

- Conectores oficiales y permisos de uso por fuente.
- Actualizacion periodica.
- Validacion de calidad y deduplicacion avanzada.
- Busqueda publica endurecida para produccion.
- Gobierno de datos, auditoria y monitoreo.
- Despliegue con HTTPS, PostgreSQL administrado y controles de acceso si corresponde.

## Reset y verificacion

```powershell
python scripts/reset_and_load_mvp_demo.py
python scripts/run_demo_check.py
python scripts/demo_ready_check.py
python -m pytest -q --basetemp .pytest-tmp-demo-next
python -m reflex compile --dry --no-rich
```
