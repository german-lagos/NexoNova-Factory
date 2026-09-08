# P2 — Validación final local

Fecha: 2026-09-08. **Estado de P2: FAIL.**

La validación detectó dos incumplimientos reproducibles, además de la imposibilidad de probar Docker. La suite completa termina con **71 passed, 2 failed** (73 casos, código 1). No se promueve P2 ni se inicia P3. La falta de Docker por sí sola sería un bloqueo; los defectos comprobados justifican FAIL como único estado global.

## Alcance y cambios

Se revisaron AGENTS.md, los documentos de arquitectura aprobados, MIGRATION_PLAN.md, REFACTOR_REPORT.md y las implementaciones/tests de P2. Se añadieron 15 casos en `tests/test_p2_validation.py`. No se modificaron tests anteriores, código runtime, configuración, secretos, dependencias ni infraestructura. No se movieron ni eliminaron archivos. Documentos actualizados: este registro, P2.md, el índice de migración y REFACTOR_REPORT.md. Los registros anteriores de 58 pruebas siguen siendo evidencia histórica, no el resultado vigente.

Se mantuvieron los dos tests de regresión como fallos ordinarios: sin xfail, skip ni aserciones relajadas. Corregir la implementación queda como siguiente trabajo de P2, fuera de esta entrega limitada a validación.

## Entorno y comandos ejecutados

Desde la raíz del repositorio, con el entorno Python `.venv` existente, sin instalar paquetes:

```bash
command -v docker
ls -l /var/run/docker.sock .venv/bin/python
python3 -c 'import shutil,pathlib,json; print(json.dumps({"docker_binary":shutil.which("docker"),"local_socket_exists":pathlib.Path("/var/run/docker.sock").exists(),"rootless_socket_exists":pathlib.Path("/run/user/"+str(__import__("os").getuid())+"/docker.sock").exists()}))'
docker --version
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_p2_validation.py -q -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q -p no:cacheprovider --tb=short
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/validate_repository.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m factory.cli --help
```

Resultados:

- Docker: ejecutable `null`, socket local y socket rootless convencional inexistentes. `docker --version`: `command not found`, código 127. No se puede consultar un daemon operativo desde este entorno. El adaptador solo admite `/var/run/docker.sock`; no se buscaron servicios remotos ni credenciales. No se instaló Docker ni se arrancó un servicio.
- `config/factory.json`: `python_image=null`; tampoco hay imagen por digest configurada y aprobada. No se intentó descargar imágenes.
- Suite anterior: **58 passed en 1.43 s**, código 0.
- Primera ampliación, antes de añadir éxito unittest real y comprobación de PID tras timeout: **11 passed, 2 failed en 0.51 s**, código 1.
- Suite completa ampliada: **71 passed, 2 failed en 2.89 s**, código 1.
- Validador de estructura/imports/enlaces y hashes protegidos: `structural_validation=complete`, código 0. CLI `--help`: inicia y devuelve código 0.

Los procesos de prueba son Python local de confianza, con datos sintéticos en temporales de pytest. El helper `host_adapter` sustituye deliberadamente descubrimiento/comando Docker por Python local; conserva aprobación, snapshot, lector y persistencia reales. `/usr/bin/true` sustituye únicamente la llamada de limpieza: **no demuestra que se cree o elimine un contenedor**. Esto solo existe en tests; no introduce un fallback en producción. stdout y stderr se capturan combinados por diseño.

## Fallos reproducidos

### P2-V01 — Redacción incompleta de secretos con espacios

`test_quoted_secret_with_spaces_is_fully_redacted_in_logs` inicia un proceso real que imprime un valor sintético entre comillas, con dos palabras, bajo la clave JSON `password`. Inspecciona el `tool-result.json` realmente persistido. La segunda palabra sobrevive: el patrón de `redact` termina al primer espacio. El caso de una palabra sí pasa. No se utilizaron credenciales reales.

Impacto: incumple la aceptación de logs sin secretos sintéticos; la redacción actual no debe tratarse como frontera suficiente. Corrección propuesta: tratar valores delimitados completos y escapes antes del patrón simple; cubrir delimitadores, valores multilínea y truncamiento por presupuesto sin reintroducir el secreto en diagnósticos. Incluso corregido, el filtrado seguirá siendo heurístico y exigirá revisión de seguridad.

### P2-V02 — SIGINT deja una ejecución abierta

`test_sigint_leaves_recoverable_finished_run` lanza un driver Python aislado. Su hijo envía SIGINT al driver y espera; no se envían señales al proceso pytest. `_execute` entra en su `finally`, pero `KeyboardInterrupt` atraviesa `run`, que solo captura OSError/ValueError. El driver termina con error; el workspace permanece intacto y staging se limpia, pero `state.json` conserva `lifecycle=running` y falta `tool-result.json`.

Impacto: no existe cierre recuperable para esta interrupción normal. Corrección propuesta: definir y persistir un resultado terminal de interrupción, conservar evidencia parcial ya redactada y restaurar la semántica de salida/señal; verificar limpieza real en Docker. SIGTERM, SIGKILL y recuperación tras caída requieren pruebas separadas. No se equipara una escritura atómica con recuperación de un job.

## Matriz de capacidades y evidencia

PASS en esta tabla se limita a la comprobación indicada, nunca al aislamiento completo.

| Capacidad | Resultado | Evidencia y límite |
|---|---|---|
| Docker local operativo | BLOCKED | Binario y socket ausentes; imagen no configurada |
| Ejecución real del executor en contenedor | NOT_EXECUTED | Depende de Docker y digest aprobado; cero contenedores lanzados |
| Workspace aislado del host y metadata | NOT_EXECUTED | Se revisó argv/montaje; no se verificó contención del kernel |
| Traversal, rutas externas y symlinks | PASS, API local | Tests anteriores de rutas/enlaces y nuevos intentos reales de escritura denegados; directorio externo sin cambios. No acredita resistencia a carreras de un atacante host |
| Hardlinks y sustitución de directorio runs | PASS, API local | Rechazo con enlaces reales y ausencia de escritura externa |
| cwd y entorno permitidos | PASS, proceso host | Proceso observa workspace y PATH/HOME/DOCKER_CONFIG controlados; variable sintética del operador ausente. Python puede añadir LC_CTYPE. cwd/env del contenedor: NOT_EXECUTED |
| Timeout y límite de salida | PASS, proceso host | Timeout real; PID del hijo ya no existe; duración menor a 5 s para límite de 1 s. Salida acotada en test anterior. Timeout/recursos de contenedor: NOT_EXECUTED |
| Códigos de salida y stdout/stderr | PASS, proceso host | Código 7 conservado, stdout JSON y stderr visibles en stream combinado; ToolResult persistido. Unittest real: código 0 y un test ejecutado |
| Herramienta ausente | PASS, control local | Docker ausente no habilita fallback; ejecutable inexistente real devuelve error persistido y limpia staging. Python ausente dentro de imagen: NOT_EXECUTED |
| Fallo de proceso | PASS, proceso host | Código 7 produce error, no complete |
| Interrupción SIGINT | FAIL | P2-V02; estado abierto sin resultado terminal |
| SIGTERM, SIGKILL, caída del daemon y reinicio | NOT_EXECUTED | Sin prueba específica de recuperación; daemon no disponible |
| Limpieza de temporales host | PASS, casos probados | Staging vacío tras error de arranque, fallo y SIGINT; HOME temporal desaparece tras finalización ordinaria |
| Limpieza de contenedores en éxito/error/timeout/interrupción | NOT_EXECUTED | El sustituto `/usr/bin/true` no acredita limpieza Docker |
| Dry-run | PASS | Popen prohibido por test, hash de producto intacto y aprobación sin consumir; genera metadata local autorizada |
| Separación cliente A / B | PASS parcial, API | Escritura y aprobación cruzadas rechazadas. Lectura/escritura desde contenedor de A hacia B: NOT_EXECUTED. Ambos almacenes comparten usuario host; no hay aislamiento frente a esa cuenta |
| Aprobación antes de proceso | PASS | Nuevos guards hacen fallar el test si Popen arranca con aprobación ausente o de otro cliente |
| Cambio de contenido/alcance/política | PASS | Cambiar archivo o policy_hash impide cualquier proceso. Tests previos cubren acción distinta, caducidad y uso único |
| Logs sin secretos sintéticos | FAIL | Valor simple redactado en log real; valor entre comillas con espacios filtra sufijo (P2-V01) |
| Escritor único y evidencia | PASS acotado | Un segundo proceso real no adquiere lock ni crea run; lock reutilizable al salir. UUID/snapshots anteriores verificados por suite |
| Atomicidad | PASS acotado | Fallo inyectado en os.replace conserva estado anterior y limpia temporal; corte eléctrico/SIGKILL durante escritura: NOT_EXECUTED |
| Red, CPU, memoria, pids, readonly, usuario y capabilities Docker | NOT_EXECUTED | Flags revisados; enforcement necesita contenedor real |

## Calidad de los tests existentes

- Los tests de `safe_path`, symlinks/hardlinks y reemplazo de runs usan filesystem real, no solo valores inventados. Se añadieron intentos de escritura por `ProjectStore.write` para comprobar efectos.
- Las pruebas de aprobación anteriores verificaban excepciones/estados; los nuevos guards de Popen acreditan ausencia de ejecución para las variantes ensayadas. No autentican a una persona frente a otro proceso con la misma cuenta host.
- El test anterior de lock usaba dos context managers en un proceso; el nuevo caso compite desde un segundo proceso real. No prueba todos los sistemas de archivos ni escritores que ignoren flock.
- Los tests de argv Docker verifican intención de configuración. Los de subprocess anteriores verifican lector, límites y redacción simple: ninguno prueba Docker.
- Se añadió unittest real exitoso y proceso fallido con evidencia persistida. La interpretación de `Ran ... / OK` sigue dependiendo de texto que código no confiable puede falsificar; un resultado complete no certifica calidad ni integridad de los tests.
- El test anterior de atomicidad inyecta fallo en os.replace; no representa todas las caídas posibles. Los tests de snapshots sí comprueban preservación de evidencia anterior.
- La redacción simple daba cobertura insuficiente; la regresión nueva demuestra una fuga. No había cobertura SIGINT; ahora demuestra falta de cierre.

## Criterios de P2, punto por punto

Correspondencia con los diez puntos de trabajo y la salida de MIGRATION_PLAN.md:

| Punto | Evaluación |
|---|---|
| 1. Configuración validada y contexto explícito | Comprobado para JSON y cliente/proyecto del adaptador existente; configuración inválida rechazada |
| 2. Separación código, metadata, secretos y estado | Raíz externa y escrituras acotadas comprobadas; separación efectiva del proceso no confiable BLOCKED por Docker. Fuga en diagnóstico FAIL |
| 3. Executor, rutas, cwd/env, tiempo, red y recursos reales | Controles host parcialmente comprobados; contención Docker NOT_EXECUTED. No satisface el punto completo |
| 4. Permisos previos y dry-run con raíz autorizada | Comprobado en API actual, sin efectos de proceso en rechazos; no generalizable a herramientas futuras |
| 5. Aprobaciones vinculadas y restricciones de WorkOrder | Acción/contenido/policy/cliente/caducidad/uso único comprobados. No hay integración completa de restricciones WorkOrder con el adaptador; revisión humana pendiente |
| 6. Estado por run, atomicidad, escritor, evidencia y recuperación | Lock real y persistencia ordinaria comprobados; cierre SIGINT FAIL; reanudación/checkpoints operativos siguen pendientes |
| 7. Memoria desactivada y sin escritura implícita | Comprobado por tests y configuración; no se activa memoria automática |
| 8. Fuentes explícitas y hashes de texto consumido | Comprobado por tests de contexto/integridad; sin DB vectorial ni caché nueva |
| 9. Límites tiempo/llamadas/consumo | Tests de presupuestos, timeout y salida pasan para el contrato disponible. Recursos Docker NOT_EXECUTED; proveedor de modelos no existe, consumo declarado no aplicable |
| 10. Importador versionado de legado y referencias portables | NOT_EXECUTED: importador aún no implementado; original preservado según hashes. No confundir conservación con migración validada |
| Salida: entorno controlado para herramientas reales/productos | No cumplida: dos fallos reproducidos, Docker bloqueado y cierre recuperable/importación pendientes |
| Revisión obligatoria arquitectura/seguridad | Pendiente de revisión humana; esta validación no concede aprobación |

La aceptación adicional «dos runs simultáneos no mezclan archivos» tiene evidencia de exclusión del segundo escritor y IDs separados, no de dos herramientas concurrentes en Docker. Lectura cruzada A/B y contención efectiva permanecen sin verificar. No se reinterpretan esos criterios para aprobar P2.

## Riesgos pendientes y revisión humana

1. Corregir P2-V01 y P2-V02 y repetir toda la suite sin relajar sus regresiones.
2. Disponer de un host local de pruebas con Docker operativo e imagen Python oficial revisada, fijada por digest y disponible localmente. Mantener `--pull=never`, sin red, sin credenciales y sin puertos publicados.
3. Ejecutar pruebas reales de montaje readonly, lectura/escritura cruzada A/B, rutas/symlinks, cwd/env, recursos/red, herramienta ausente y limpieza por nombre tras éxito/error/timeout/interrupción. Inspeccionar que no queden contenedores temporales. Actualmente todas estas comprobaciones Docker están NOT_EXECUTED.
4. Acordar recuperación/checkpoints e importación versionada del legado, sin modificar sus bytes. Son pendientes del plan, no nuevas fases.
5. Revisar límites del modelo de amenaza: cuenta host/daemon confiables, carreras de filesystem, redacción heurística, aprobación no criptográfica y salida de tests potencialmente falsificable. La revisión debe decidir cuándo puede habilitarse código no confiable.

No se modificaron secretos, servicios ni políticas para obtener un resultado favorable. No hubo despliegues. P3–P7 permanecen detenidas; se entrega este diagnóstico para revisión humana.
