# Mantenimiento de esta entrega parcial

Ejecutar la suite y scripts/validate_repository.py después de cambios. El segundo comando verifica imports relativos, enlaces de documentación actual, versiones y hashes del material académico preservado.

El repositorio visible carece de historial Git utilizable. No se creó uno artificial. docs/migration/change-inventory.json identifica cambios por hashes; baseline-sha256.json conserva hashes de origen. La copia temporal del código inicial se perdió al reiniciar el entorno: no se generó un diff reconstruido ni puede revertirse exactamente mediante hashes. .migration-checkpoints/ conserva solo un checkpoint posterior del estado actual. No aplicar una reversión automáticamente sobre trabajo posterior del usuario. Recuperar el Git original y aclarar procedencia antes de publicar.

Actualizar requirements-test.lock mediante un entorno aislado y probar la suite; el runtime sigue sin dependencias externas. La configuración privada necesita validación y revisión si cambian límites o imagen. Una nueva configuración invalida aprobaciones anteriores.

Respaldar fuentes y estado privado bajo responsabilidad del operador. No se implementa exportación/restauración automática: antes de borrar un run o un snapshot, confirmar que no hay escritor ni contenedor activo y que el contenido no es único. No se definió retención de datos de clientes; requiere decisión humana.

Los proyectos web todavía no existen; update-project y bug-fix permanecen pendientes de P3/P4/P5. No regenerar ni sobrescribir un proyecto ajeno con las funciones documentales académicas.
