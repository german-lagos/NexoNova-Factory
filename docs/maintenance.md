# Mantenimiento de esta entrega parcial

Ejecutar la suite y scripts/validate_repository.py después de cambios. El segundo comando verifica imports relativos, enlaces de documentación actual, versiones y hashes del material académico preservado.

El repositorio visible carece de historial Git utilizable. No se creó uno artificial. docs/migration/change-inventory.json identifica cambios por hashes; baseline-sha256.json conserva hashes de origen. La copia temporal del código inicial se perdió al reiniciar el entorno: no se generó un diff reconstruido ni puede revertirse exactamente mediante hashes. .migration-checkpoints/ conserva solo un checkpoint posterior del estado actual. No aplicar una reversión automáticamente sobre trabajo posterior del usuario. Recuperar el Git original y aclarar procedencia antes de publicar.

Actualizar requirements-test.lock mediante un entorno aislado y probar la suite; el runtime sigue sin dependencias externas. La configuración privada necesita validación y revisión si cambian límites o imagen. Una nueva configuración invalida aprobaciones anteriores.

Respaldar fuentes y estado privado bajo responsabilidad del operador. No se implementa exportación/restauración automática: antes de borrar un run o un snapshot, confirmar que no hay escritor ni contenedor activo y que el contenido no es único. No se definió retención de datos de clientes; requiere decisión humana.

Los proyectos web todavía no existen; update-project y bug-fix permanecen pendientes de P3/P4/P5. No regenerar ni sobrescribir un proyecto ajeno con las funciones documentales académicas.

## Operación local P2: órdenes, referencias y recuperación

P2 tiene validación técnica PASS_WITH_LIMITATIONS con Docker; estas instrucciones no habilitan código no confiable sin revisión humana. Véase [la validación vigente](migration/P2_FINAL_VALIDATION.md).

approve-tool y run-tool aceptan `--work-order ruta.json`. Utilizar el mismo WorkOrder en ambos: todo su contenido forma parte del hash aprobado. El cambio de adaptador a política v2 invalida aprobaciones anteriores; emitir una nueva aprobación tras revisar el alcance. Solo se admite work_type=test, rutas relativas (sin globs), expected_outputs vacío o tool-result.json. Una exclusión que afecte a un archivo del workspace bloquea el montaje entero. Omitir la orden selecciona la API manual del operador, no permite omitir aprobación ni política global.

`import-legacy-reference --root /ruta/privada --client acme --project-id site --source /ruta/legado` crea un manifiesto de hashes y rutas relativas en imports/. No copia ni transforma el legado. Para resolverlo mediante la API `factory.state_transfer.resolve_reference`, proporcionar de nuevo la raíz fuente; así puede trasladarse la fuente sin incrustar rutas absolutas de otra máquina. Mantener su backup: el manifiesto no recupera archivos perdidos. No reutilizar aprobaciones ni claims complete del legado como evidencia actual.

Tras una caída, `recover-run --root /ruta/privada --client acme --project-id site --run-id RUN-...` cierra metadata bajo lock sin relanzar la herramienta. Preserva el resultado terminal existente o recupera evidencia del checkpoint con resultado desconocido/interrumpido. El código CLI es 1 si el run no terminó complete. Inspeccionar los recursos identificados en checkpoint/ToolResult cuando cleanup indica operator_inspection_required; recuperar metadata no demuestra que un contenedor haya terminado. No borrar recursos ni reejecutar automáticamente. SIGINT normal devuelve 130 tras persistir; SIGTERM/SIGKILL y fallos físicos no tienen cierre inmediato garantizado.

Los checkpoints contienen salida parcial redactada. La redacción es heurística y no garantiza eliminar secretos arbitrarios. Mantener privado el almacén y no introducir credenciales en el workspace o salida.
