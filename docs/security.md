# Seguridad y límites de la implementación parcial

Estado: preparado para revisión humana, no aprobado para producción ni ejecución de clientes.

## Fronteras

El operador host es de confianza; briefs, memoria, código del cliente y resultados de procesos no tienen autoridad para elevar permisos. La cuenta host y el daemon Docker deben ser administrados por una persona responsable. Una etiqueta actor en un registro no prueba identidad; no hay firma ni servicio de autenticación de aprobaciones.

La CLI no ofrece shell libre. El adaptador usa una tabla cerrada de comandos, una imagen Python oficial fijada por digest y el socket Docker local explícito. No hereda DOCKER_HOST, configuración del usuario ni credenciales de registro. No descarga imágenes. El único montaje de entrada es un snapshot filtrado de solo lectura; no monta la raíz host ni su socket dentro del contenedor. Una indisponibilidad bloquea ejecución.

La imagen y límites están incluidos en el hash de política asociado a la aprobación. Cambiar fuente, herramienta o configuración invalida esa aprobación. Consumirla requiere acceso al almacén host de aprobaciones, inaccesible desde el contenedor. La fuente aceptada tampoco se monta con escritura.

## Credenciales

No se modificaron secretos. .gitignore evita el agregado accidental de archivos comunes, pero no borra secretos previamente versionados. El snapshot rechaza nombres de credenciales conocidos, datos binarios y patrones sospechosos; logs se redactan antes de persistir. Son defensas conservadoras e incompletas, no un escáner especializado ni una certificación. No introducir datos reales de clientes en la prueba inicial.

## Cómo revisar una aprobación de herramienta

Después de preparar y revisar Docker local e imagen oficial por digest, crear una config privada basada en config/factory.json. La config no contiene secretos. Usar el mismo archivo al aprobar y ejecutar:

```bash
python3 -m factory.cli approve-tool --root /tmp/nexonova-workspaces --client demo --project-id piloto --tool python.unittest --actor operador --config /ruta/privada/factory.json
python3 -m factory.cli run-tool --root /tmp/nexonova-workspaces --client demo --project-id piloto --tool python.unittest --approval ID_DEVUELTO --config /ruta/privada/factory.json
```

Esos ejemplos no constituyen autorización para ejecutar clientes. El ID es de uso único y caduca a los diez minutos. Antes de uso real hay que revisar humanamente el resultado y las limitaciones de P2. No hay APIs de despliegue, gestión de credenciales ni DB write.

## Riesgos pendientes

- Docker local fue validado con datos sintéticos: aislamiento, límites, uid/gid, acceso cruzado y limpieza. Véase [el registro P2](migration/P2_FINAL_VALIDATION.md). Sigue pendiente revisión humana; un crash abrupto requiere inspección y limpieza explícita, no replay automático.
- El daemon Docker local es una capacidad privilegiada del host. No conectarlo a infraestructura productiva para validar este prototipo.
- Locks son cooperativos; no resisten un atacante con la misma cuenta host ni carreras provocadas por procesos host fuera de la fábrica. Debe existir un único operador/escritor controlado por workspace durante evaluación.
- Los reportes de tests son salida del proceso: no demuestran cobertura semántica ni seguridad de la aplicación. Hace falta evaluar los tests y validadores de producto en fases posteriores.
- Puede quedar un run en running o un snapshot temporal tras caída del proceso host. No hay recuperación automática; revisar manualmente antes de limpiar.
- El formato de integridad detecta alteración parcial, no manipulación conjunta de resultado/manifiesto.
- Funciones académicas siguen en agents.py para revisión; no deben invocarse directamente como generadores. El harness las bloquea.
