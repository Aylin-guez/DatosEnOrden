# Runtime QA local

Para revisar DatosEnOrden Ciudadano después de encender o reiniciar el PC:

```powershell
.\scripts\qa.ps1 start
```

Para ver el estado sin iniciar ni detener procesos:

```powershell
.\scripts\qa.ps1 status
```

Para abrir la aplicación:

```powershell
.\scripts\qa.ps1 open
.\scripts\qa.ps1 open -ExpedientId EXP-REAL-DATA-PROTECTION-21719
```

Para detener el runtime QA certificado:

```powershell
.\scripts\qa.ps1 stop
```

El launcher sólo usa la base QA aislada y falla de forma segura si no puede
certificar el clúster, los puertos o la propiedad de los procesos.
