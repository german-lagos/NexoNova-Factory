# REFACTOR_REPORT — Entrega incremental parcial

Inicio: 2026-09-06. Actualización: 2026-09-08. Versión de trabajo: 0.1.0 experimental. **La migración completa no ha terminado. P2: FAIL.** La validación local reproduce fuga parcial de un secreto sintético con espacios y falta de cierre tras SIGINT. Docker no está disponible. No se inicia P3.

## Resultado

P0 estableció una línea base reproducible de tests y preservación del material académico. P1 impide presentar reportes constantes como ejecución válida. P2 prepara estado privado, aprobaciones vinculadas y un adaptador restringido; su [validación final](docs/migration/P2_FINAL_VALIDATION.md) termina con 71 pruebas aprobadas y 2 fallidas. Deben corregirse ambos defectos y verificar Docker real antes de promoverla, con revisión humana. P3–P7 no se ejecutaron y tienen registros explícitos de pendientes en [docs/migration](docs/migration/README.md).

No se cambiaron secretos, infraestructura externa o datos productivos; no se desplegó ni se ejecutaron migraciones de BD. No se inicializó Git ni se movió el historial/ERP. AGENTS.md y los tres documentos aprobados permanecen íntegros.

## Qué se reutilizó

- Paquete Python y CLI, secuencia OrchestratorGraph → HarnessRunner.
- Contratos WorkOrder/CycleState/AgentResult y dataclasses de registros.
- Decisiones de PolicyEngine, cadena de validadores y pruebas negativas útiles.
- Recuperación léxica, fuentes explícitas, hashing y logs JSONL.
- Material académico como referencia preservada, sin elevarlo a capacidad productiva.

## Qué se modificó

- tests/test_factory.py: aislamiento y comprobaciones semánticas; contexto sintético no vacío.
- factory/registry.py y harness.py: roles legacy bloqueados, rechazo de autorización pendiente y validación de resultados/rutas.
- factory/validators.py y schemas.py: evidencia resoluble, hashes del texto consumido, gates no implementados bloqueantes, límites numéricos e IDs seguros.
- factory/orchestrator.py y cli.py: cierre real, código de salida, estado externo al checkout, UUID y CLI de workspace/herramientas.
- factory/context.py: fuentes configurables y snapshots sin sobrescritura.
- factory/memory.py y policy.py: memoria desactivada; aprobación del productor insuficiente.
- factory/utils.py: escritura atómica, hashes de bytes, rechazo de NaN, eliminación del shell innecesario en env_hash.
- factory/observability.py: estimaciones locales identificadas, sin atribuirlas a modelos.
- factory/__init__.py y constants.py: identidad y versión del runtime coherentes con el empaquetado.

## Qué se reemplazó

- Cierre y matriz de trazabilidad estáticos por reports basado en resultados y manifiesto.
- verify basado solo en existencia por lectura de integridad/estado coherente; runs legados no certificables conservados.
- Aprobación implícita de controles de calidad por bloqueo si no existe verificación real.
- Detección que equiparaba comando presente con capacidad lista por disponibilidad no acreditada explícita.

Los cuerpos de agents.py **no fueron reescritos todavía**. Se impide ejecutarlos desde el harness; permanecen para revisión hasta que generadores reales sustituyan sus responsabilidades en P3. Esto evita una reescritura sin brief y no se presenta como generación implementada.

## Qué se eliminó

Ningún archivo fuente o legado. Se retiraron comportamientos de falsa aprobación, inicialización de memoria de fábrica al leer y contadores de allowlists como ejecución. Los cachés existentes permanecen ignorados; no se realizaron borrados cosméticos.

## Qué se creó

- Empaquetado: pyproject.toml, requirements-test.lock y exclusiones raíz.
- factory/reports.py: cierre y verificación de integridad.
- factory/storage.py: raíz privada por cliente, lock, UUID, aprobaciones y rutas acotadas.
- factory/config.py y config/factory.json: límites explícitos y ejecución desactivada sin imagen aprobada.
- factory/executor.py: adaptador experimental Docker local, snapshot filtrado, límites y resultados.
- tests/test_integrity.py y tests/test_storage.py: regresiones de evidencia y fronteras.
- tests/test_p2_validation.py: 15 comprobaciones adicionales de procesos, persistencia, escrituras y aprobaciones; dos regresiones fallidas conservadas, sin cambiar el runtime en esta entrega de validación.
- scripts/validate_repository.py: imports, estructura, enlaces, versiones y preservación de hashes.
- README.md, docs/architecture.md, docs/security.md, docs/maintenance.md, docs/deployment.md.
- Registros P0–P7, ajustes del plan, manifiesto de origen e inventario de cambios por hashes en docs/migration.

No se crearon carpetas vacías para templates, modules, prompts ni deployment. No hay nuevas dependencias runtime Python. pytest ya estaba requerido por las pruebas; setuptools se añadió únicamente para empaquetar. No se incorporó Bubblewrap como tecnología del producto.

## Validación

- P0 original: 9 pruebas aprobadas en copia temporal; 9 con aislamiento corregido.
- P1: 24 pruebas aprobadas.
- P2/cierre anterior: 58 pruebas aprobadas; evidencia histórica en [registro de cierre](docs/migration/FINAL_VALIDATION.md).
- P2/validación actual: 71 passed, 2 failed; código 1. Fallan redacción de secreto entre comillas con espacios y cierre recuperable tras SIGINT. Imports/estructura/hashes protegidos y arranque CLI pasan. Comandos y límites en [P2_FINAL_VALIDATION](docs/migration/P2_FINAL_VALIDATION.md).
- CLI sigue iniciando; bootstrap legado devuelve fallo explícito, no éxito artificial.
- Empaquetado wheel probado sin dependencias runtime; comprobación instalada y validación estructural registradas al cierre.
- Los tests de lector de procesos usan subprocess sintéticos confiables: **no prueban aislamiento Docker**.
- No hay tests de aplicaciones web, E2E, BD ni despliegue porque esas capacidades no existen aún.

## Deuda técnica restante

Contratos aún contienen nombres y campos académicos; funciones legadas inactivas permanecen. Falta migrar datos antiguos mediante lector/importador con versión, reanudar ejecuciones, definir retención/backup y soportar más herramientas reales. El lock de tests fija versiones pero no hashes ni todas las plataformas. Falta una matriz de Python y CI. No se ha recuperado Git ni confirmado procedencia completa. Tras reiniciar el entorno se perdió el baseline temporal de código: existe inventario de hashes, pero la reversión exacta al código inicial exige recuperar originales. Se creó un checkpoint local del estado actual, sin presentarlo como baseline histórico.

## Riesgos pendientes

P2 tiene dos defectos demostrados: el log conserva parte de un secreto sintético con espacios y SIGINT deja estado running sin ToolResult terminal. Necesita además validación de Docker/imágenes/kernel y revisión de seguridad; binario/socket ausentes e imagen sin configurar impiden ejecutar contenedores aquí. Las comprobaciones de rutas y locks no resisten un atacante con la misma cuenta host. El escaneo/redacción es heurístico; no es una certificación. Un crash puede dejar temporales o contenedores cuya limpieza debe revisar el operador. Manifiestos sin firma no resisten reescritura conjunta del almacén. Un resultado de tests no sustituye revisión de los propios tests ni aprobación humana.

## Funcionalidades todavía no implementadas

Generación Next.js, templates corporativa/business-platform, módulos, Better Auth/Prisma/PostgreSQL, actualización de proyectos, bug-fix automatizado, agentes con modelos, pipelines de producto, contenedores de entrega/Nginx/TLS, preparación de despliegue y operación/restauración de productos. No se atribuye avance funcional a P3–P7 por tener documentos de estado.

## Pasos recomendados hacia v0.2

1. Corregir las dos regresiones P2, completar recuperación/importación pendientes y validar Docker local con revisión humana. Mantener P3 detenido hasta cierre P2; el brief concreto sigue pendiente.
2. Recuperar el repositorio Git real y resolver procedencia antes de publicar.
3. Implementar corporate-site con manifest, versiones y build/tests independientes de la fábrica.
4. Continuar business-platform y módulos con consumidor real, luego mantenimiento; integrar IA solo donde aporte valor.
5. Preparar entrega únicamente cuando exista producto validado, respetando los gates humanos del plan.

Esta entrega se detiene para revisión de lo construido y resolución de precondiciones. No se declara completado MIGRATION_PLAN.md ni se solicita volver a aprobar la autorización general ya concedida.
