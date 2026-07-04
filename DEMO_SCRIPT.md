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
8. Abrir `/tracking` para mostrar seguimiento de una propuesta/documento conectado al expediente.
9. Abrir `/reports` para mostrar el reporte ciudadano conectado al expediente y seguimiento.
10. Volver a `/demo` y tocar `Ver ecosistema de fuentes`.
11. Tocar `Exportar reporte HTML` para mostrar salida reutilizable.

## Que decir en 60 segundos

DatosEnOrden convierte registros publicos dispersos en un expediente ciudadano entendible. En vez de pedirle a una persona que revise compras, presupuestos, lobby, publicaciones o procedimientos por separado, el sistema reune fuentes, evidencias, relaciones y entidades conectadas en una sola vista. Tambien permite seguir la historia publica de documentos, propuestas y expedientes conectados por evidencia, y generar reportes ciudadanos reutilizables. Este demo usa datos locales de prueba; no afirma causalidad, irregularidad ni responsabilidad.

## Botones que tocar

- `/demo`: `Abrir expediente de ejemplo`.
- `/investigation`: `Exportar expediente`.
- `/tracking`: `Abrir expediente`, `Ver demo`, revisar timeline y documentos.
- `/reports`: `Abrir expediente`, `Ver seguimiento`, `Abrir HTML exportado`.
- `/demo`: `Ver ecosistema de fuentes`.
- Header: usar `Buscar` solo como accion global si alguien quiere probar busqueda directa.

## URLs exactas

```text
http://localhost:3000/demo
http://localhost:3000/
http://localhost:3000/ecosystem
http://localhost:3000/discover
http://localhost:3000/tracking
http://localhost:3000/reports
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

## C?mo presentar la transici?n

Esta versi?n muestra el formato de la experiencia p?blica: expediente, documento oficial, lectura documentada, seguimiento, reportes y actualidad documentada trabajando sobre datos locales de prueba.

El siguiente paso es publicar la primera Lectura Documentada real, usando un documento oficial peque?o, verificable y separado de los datos demo.

Los datos demo est?n separados de los datos p?blicos reales. Sirven para mostrar la experiencia, validar la trazabilidad y probar el recorrido sin afirmar hechos oficiales.

DatosEnOrden no reemplaza fuentes oficiales. Su funci?n es facilitar la lectura, mantener referencias visibles y ayudar a que cualquier persona pueda volver al documento original para verificar la informaci?n.

## Reset y verificacion

```powershell
python scripts/reset_and_load_mvp_demo.py
python scripts/run_demo_check.py
python scripts/demo_ready_check.py
python scripts/tracking_demo_summary.py
python scripts/export_tracking_demo_report.py
python scripts/export_citizen_report.py
python -m pytest -q --basetemp .pytest-tmp-demo-next
python -m reflex compile --dry --no-rich
```
