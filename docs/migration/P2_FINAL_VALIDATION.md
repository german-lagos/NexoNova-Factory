# P2 — Corrección y validación final local

Fecha: 2026-09-09 (pruebas Docker entre el 9 de septiembre local y el 10 en UTC). **Estado de P2: PASS_WITH_LIMITATIONS.**

Los criterios técnicos obligatorios de P2 cuentan ahora con pruebas locales, incluidas pruebas reales del executor en Docker. Resultado final: **105 passed**, sin skips ni xfails en la ejecución con Docker habilitado. No se detectó un defecto del runtime que incumpla los criterios ensayados. La aprobación humana de arquitectura/seguridad sigue pendiente y este dictamen técnico no habilita P3.

Las limitaciones restantes son operativas y del modelo de amenaza: después de un crash abrupto la recuperación cierra metadata sin repetir herramientas, pero exige inspección/limpieza explícita; la redacción es heurística; se ha validado una sola combinación de host/imagen y la salida de unittest no certifica pruebas maliciosas. No se exige ni se atribuye captura de SIGKILL o recuperación automática de procesos. Por esas limitaciones se utiliza PASS_WITH_LIMITATIONS, no PASS. No quedan precondiciones técnicas externas que bloqueen los escenarios obligatorios ensayados.

## Historial y alcance

El 2026-09-08 la suite terminó con 71 passed y 2 failed: redacción parcial de un secreto sintético con espacios y SIGINT sin cierre. Ese FAIL era correcto para aquel estado. La presente revisión sustituye el dictamen anterior con evidencia nueva; no convierte las pruebas host en pruebas Docker.

En la corrección previa se modificaron `factory/executor.py` y `factory/cli.py`. Creados: `factory/execution_scope.py`, `factory/state_transfer.py`, `tests/test_p2_fixes.py`, `tests/test_p2_state.py`. Actualizados: este documento, P2.md, índice de migración, REFACTOR_REPORT.md y guías de arquitectura/mantenimiento de P2. No se movieron ni eliminaron fuentes/legado. No se añadieron dependencias, servicios, secretos, templates ni módulos web. En esta validación Docker se añadieron tests/test_p2_docker.py y los registros P2_DOCKER_RESULTS.json/P2_DOCKER_EVENTS.json; se fijó python_image en config/factory.json. No se modificó el runtime, las restricciones ni las regresiones anteriores. Se sincronizaron las referencias de estado P2 en README.md y las guías de arquitectura, seguridad, mantenimiento e índice de migración.

## P2-V01: redacción

El runtime consume el valor completo delimitado por comillas simples/dobles, incluyendo espacios, escapes, saltos de línea y colas sin cerrar por truncamiento. Mantiene filtrado de valores simples, bearer y claves privadas. La redacción ocurre antes de persistir ToolResult y checkpoint; los errores no incluyen el valor detectado.

Pruebas: regresión original sobre log persistido; nueve variantes de valores; proceso real cuya salida excede el límite y corta un valor entre comillas; evidencia parcial bajo SIGINT sin el secreto sintético. Solo se emplearon datos sintéticos.

**Sigue siendo una defensa heurística, no una garantía absoluta de eliminación de secretos.** No reconoce cualquier codificación, lenguaje, nombre de campo o secreto arbitrario. Una credencial nunca debe introducirse deliberadamente en fuentes/salida confiando en este filtro. Los tests no certifican ausencia universal de fugas.

## P2-V02: interrupción y limpieza

`_execute` conserva la salida parcial ya capturada, la redacta, intenta terminar/recolectar el proceso y limpiar su contenedor por nombre, y propaga `ExecutionInterrupted`, derivada de KeyboardInterrupt, con el resultado parcial. `run` persiste ToolResult y estado terminal antes de volver a propagar la interrupción. CLI devuelve **130** y un diagnóstico fijo. No se oculta KeyboardInterrupt como éxito.

Contrato compatible: `status=error` con `termination=interrupted`, `signal=SIGINT` y `reason=interrupted` (puede incluir una advertencia de limpieza). Se distingue del éxito (`complete`), del fallo ordinario y del timeout (`reason=timeout`). `exit_code` conserva el retorno observado del proceso hijo; el código CLI 130 representa la señal recibida por la fábrica, no el código del hijo. `lifecycle=finished` y referencia relativa `tool-result.json` quedan persistidos.

La prueba real de SIGINT usa un driver aislado y un hijo de confianza: verifica CLI 130, evidencia pública parcial, ausencia del secreto sintético, PID del hijo inexistente, HOME temporal eliminado y staging vacío. La regresión original también pasa sin cambios. La validación Docker posterior confirma código CLI 130, resultado terminal, evidencia parcial redactada, proceso hijo terminado, directorio HOME temporal eliminado y contenedor ausente.

Se estudió SIGTERM: no se instala un handler global en el paquete embebible para cambiar señales de aplicaciones anfitrionas. SIGTERM no tiene cierre inmediato garantizado; corresponde a la recuperación explícita posterior de runs abandonados. **No se implementa ni se atribuye soporte de captura de SIGKILL.** Señales repetidas durante persistencia/limpieza, caída del SO o fallo de disco pueden impedir el cierre inmediato; la recuperación conserva incertidumbre y exige inspección. El test de recuperación usa una salida abrupta real con `os._exit`, no demuestra manejo de todas las señales ni cortes eléctricos.

## Pendientes internos implementados: decisión respecto al plan

### Punto 5: restricciones WorkOrder

Son obligatorias en P2. Se reutiliza WORK_ORDER_SCHEMA y se ofrece `--work-order` en approve-tool y run-tool; el objeto se copia, valida y vincula entero al hash de política/aprobación. El adaptador acepta únicamente work_type=test y salida tool-result.json. No implementa órdenes de generación.

- El alcance usa rutas relativas exactas o directorios; `.` significa todo el workspace. Sin globs. Si el workspace contiene archivos fuera de include o dentro de exclude, se rechaza la operación completa antes del proceso; no se amplía el montaje ni se omiten exclusiones silenciosamente.
- Inputs no autorizados, ausentes, externos o con hash distinto bloquean. Rutas y enlaces siguen sujetos a safe_path.
- dry_run del WorkOrder obliga a preview; latencia efectiva es el mínimo entre política global y WorkOrder. No hay retries automáticos, por lo que max_retries no puede habilitarlos.
- no_web=false o sandbox_required=false jamás relajan red desactivada/Docker obligatorio. Aprobación del operador siempre requerida. Los límites de coste se validan; no hay proveedor de modelos ni llamadas facturables, y model_usage sigue not_applicable.
- El uso directo sin WorkOrder sigue siendo la API manual del operador, con política global y aprobación obligatorias; no se transforma una orden inválida en llamada manual. Una futura integración del harness debe pasar la orden explícitamente.

### Punto 6: checkpoints y cierre recuperable

Es obligatorio en P2; no exige reiniciar automáticamente efectos desconocidos. El checkpoint `nexonova.checkpoint.v1` se escribe atómicamente antes de preparar/lanzar el proceso y se actualiza con evidencia parcial redactada. Contiene fase, policy_hash, nombre de contenedor y staging relativo. Cada run mantiene su propio checkpoint; no se sobrescribe evidencia de otros ciclos.

`recover-run` adquiere el lock del proyecto. Si ToolResult ya quedó persistido pero faltó actualizar state, conserva sus bytes y completa el cierre. Si no existe resultado terminal, recupera evidencia del checkpoint y registra error/interrupted con executed desconocido y cleanup=operator_inspection_required. No ejecuta procesos ni consume otra aprobación. Un segundo recovery es idempotente. El operador debe inspeccionar los recursos identificados antes de autorizar un nuevo run.

Pruebas: salida abrupta real después de checkpoint, recuperación idempotente, error inyectado entre persistencia de resultado y estado, ausencia de replay, respeto al lock y rechazo de run_id externo. No se promete reanudación de una herramienta a mitad de ejecución, limpieza Docker tras crash ni durabilidad frente a todo fallo físico.

### Punto 10: referencias versionadas al legado

Es obligatorio en P2; el plan permite referencias, no obliga a copiar contenido. `import-legacy-reference` crea un manifiesto privado `nexonova.legacy-reference.v1` con nombres relativos y hashes, sin copiar textos/JSON legados ni sus rutas absolutas internas. Los claims del legado quedan marcados unverified_legacy_claims. No se modifica su contenido ni se importan aprobaciones antiguas como autorizaciones.

`resolve_reference` recibe explícitamente la raíz fuente, valida versión/hash de árbol y archivos, y permite resolver la misma referencia contra una copia trasladada. Rechaza referencias externas, enlaces y fuentes cambiadas; la inspección rechaza nombres de archivos de credenciales y aplica presupuestos. La fuente debe conservarse por separado: una referencia no es un backup.

Además de fixtures, se importó/resolvió una referencia al `project/` real en un almacén temporal: **128 archivos**, hash del original sin cambios. El almacén temporal se descartó al terminar; no se eligió una nueva ubicación definitiva para datos del usuario. El importador queda disponible para esa operación posterior explícita.

## Entorno Docker e imagen

- Cliente y servidor Docker: **29.8.0**, cliente build **88096ef**.
- Host informado por daemon: Ubuntu 26.04.1 LTS, kernel 7.0.0-31-generic, x86_64; cgroup v2, driver systemd; AppArmor, seccomp y cgroup namespaces disponibles.
- Socket: **unix:///var/run/docker.sock**, el mismo que fuerza el executor. El sandbox de la sesión denegó inicialmente acceso; los comandos y tests Docker se ejecutaron fuera de ese sandbox con aprobación explícita. No se usaron contextos ni daemon remotos, ni se modificaron permisos del socket.
- Docker Compose **v5.5.1**, consultado solo para inventario: no es necesario para este adaptador de un contenedor.
- Imagen oficial seleccionada durante preparación: **python:3.12-slim**, Python **3.12.14** según metadata de la imagen.
- Referencia fijada en config/factory.json: **python@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea**.
- image ID informado: sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea. Se verificó presencia local por digest antes de ejecutar.
- Variables incorporadas revisadas: PATH, LANG=C.UTF-8, GPG_KEY (huella pública, no clave privada), PYTHON_VERSION y PYTHON_SHA256. El runtime añade HOME=/tmp y PYTHONDONTWRITEBYTECODE=1; Docker añade HOSTNAME. La prueba comprueba que no aparezcan variables adicionales ni la variable privada sintética del operador.

El digest fija los bytes; no equivale a auditoría de vulnerabilidades ni a aprobación de producción. La imagen queda local para reproducir pruebas. Cada ejecución sigue requiriendo aprobación vinculada a configuración/contenido. Las aprobaciones anteriores a este cambio de configuración no son válidas.

## Preparación, comandos y resultados

Preparación separada de la ejecución restringida:

```bash
docker --version
docker --host unix:///var/run/docker.sock info --format '{{json .ServerVersion}}'
ls -l /var/run/docker.sock
docker --host unix:///var/run/docker.sock image ls --digests --format '{{.Repository}} {{.Tag}} {{.Digest}}'
docker --host unix:///var/run/docker.sock info --format 'server={{.ServerVersion}} os={{.OperatingSystem}} kernel={{.KernelVersion}} arch={{.Architecture}} cgroup={{.CgroupVersion}} driver={{.CgroupDriver}} security={{json .SecurityOptions}}'
docker compose version
docker --host unix:///var/run/docker.sock pull python:3.12-slim
docker --host unix:///var/run/docker.sock image inspect python@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea --format '{{json .RepoDigests}} {{.Id}} {{json .Config.Env}}'
```

El pull se invocó desde Python subprocess con HOME y DOCKER_CONFIG en TemporaryDirectory vacío y PATH=/usr/bin:/bin, sin credenciales. El primer intento falló porque el DNS del daemon no resolvió registry-1.docker.io. El segundo funcionó sin cambiar DNS ni servicios. Esa descarga fue la única preparación de imagen; todos los docker run del executor conservaron **--pull=never**, **--network=none**, sin puertos, sin --privileged y sin filesystem host completo.

Pruebas finales desde la raíz del repositorio, con acceso autorizado al socket local:

```bash
NEXONOVA_TEST_DOCKER=1 PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_p2_docker.py -q -p no:cacheprovider --tb=short
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_p2_validation.py -q -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_p2_fixes.py tests/test_p2_state.py -q -p no:cacheprovider
NEXONOVA_TEST_DOCKER=1 PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q -p no:cacheprovider --tb=short
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/validate_repository.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m factory.cli --help
docker --host unix:///var/run/docker.sock ps -a --filter name=nexonova-test- --format '{{.ID}} {{.Names}} {{.Status}}'
```

| Comprobación | Resultado final |
|---|---|
| tests/test_p2_docker.py | 10 passed, 9.60 s |
| tests/test_p2_validation.py | 15 passed, 1.50 s |
| tests/test_p2_fixes.py + tests/test_p2_state.py | 22 passed, 0.62 s |
| Suite completa, Docker incluido | 105 passed, 12.37 s; código 0; cero skips/xfails |
| Estructura/imports/hashes/enlaces/config | structural_validation=complete, código 0 |
| CLI --help | Inicia, código 0 |
| Contenedores nexonova-test-* restantes | 0 |
| Directorios /tmp/nexonova-docker-client-* restantes | 0 |

Los tests Docker son opt-in para no usar el daemon implícitamente en una suite local ordinaria. Sin NEXONOVA_TEST_DOCKER=1 se marcan NOT_EXECUTED mediante skip; **la ejecución reportada sí estableció esa variable y ejecutó todos los casos**.

## Escenarios reales, contenedores y limpieza

Los tests usan exclusivamente clientes A/B sintéticos fuera del checkout. No sustituyen command, Popen ni el transporte del executor. Los nombres y resultados por escenario se conservan en [P2_DOCKER_RESULTS.json](P2_DOCKER_RESULTS.json), y los eventos sanitizados del daemon en [P2_DOCKER_EVENTS.json](P2_DOCKER_EVENTS.json).

Se crearon **30 contenedores** entre diagnóstico y repeticiones finales. Para los 30 existe evento create y destroy; ninguno quedó listado al final. La captura de eventos usa docker events sobre el socket local, desde 2026-09-10T02:35:00Z hasta la hora de cierre, filtra type=container y conserva únicamente atributos mínimos de nombres nexonova-test-*. El registro de resultados incluye las 24 ejecuciones de contenedor de las cuatro iteraciones totalmente aprobadas; los eventos incluyen también los seis del primer diagnóstico.

- **Éxito/aislamiento:** unittest real termina 0 y complete, con un test ejecutado; se valida salida, estado terminal, staging vacío y contenedor ausente.
- **Fallo ordinario:** unittest falla con código 1; conserva diagnóstico y error, elimina staging/contenedor.
- **Timeout:** proceso duerme 30 segundos y excede presupuesto de 3 segundos. ToolResult conserva reason=timeout, exit_code=-9 del cliente terminado; estado final finished y contenedor ausente.
- **Límite de salida:** salida superior al máximo produce error/output_limit y limpieza. En algunas iteraciones el intento rm encontró el contenedor ya eliminado por --rm: el runtime mantuvo la advertencia conservadora de inspección. La inspección posterior confirmó ausencia; no se eliminó ni silenció esa advertencia.
- **SIGINT:** se interrumpe la CLI solo cuando el checkpoint demuestra que el contenedor ya emitió evidencia. Código 130, termination=interrupted, signal=SIGINT, evidencia pública retenida y sufijo sintético privado ausente. Se verifica desaparición del PID del cliente Docker, del proceso del contenedor, HOME temporal, staging y contenedor.
- **Crash controlado:** SIGKILL termina solamente el driver de prueba. Queda el contenedor esperado; recover-run cierra metadata con executed desconocido y operator_inspection_required. El mismo ID y StartedAt siguen presentes y no aparece otro run: no hay replay. Se elimina explícitamente **ese** contenedor con rm -f, su staging y HOME de cliente, y se comprueba que los procesos terminaron. No se promete captura de SIGKILL ni limpieza automática tras él.
- **Rutas/enlaces:** cuatro casos adicionales comprueban traversal, ruta absoluta, symlink y hardlink hacia el cliente B; se rechazan antes del contenedor y no se consume aprobación ni cambia el sentinel B. Se compara el inventario de contenedores antes/después.

La primera ejecución tuvo un fallo de la nueva fixture: sustituyó un marcador también dentro del nombre de una variable y produjo Python inválido. Se corrigió la fixture, sin tocar runtime ni políticas. El resto de aquella ejecución pasó. Dos directorios vacíos del cliente Docker quedaron tras los primeros ensayos de crash; se identificaron por nombre y hora, se eliminaron con rmdir y se amplió la prueba para comprobar/limpiar también ese recurso. Todas las iteraciones posteriores pasan con esa comprobación. No se hizo prune ni se eliminaron imágenes, redes o recursos ajenos; no se crearon volúmenes persistentes ni redes/puertos de prueba.

## Controles demostrados y no demostrados

| Capacidad | Evidencia actual |
|---|---|
| Creación real y montaje | Executor sin mocks; container inspect y eventos create/start/die/destroy; un único bind a /workspace, readonly |
| Escritura autorizada | Escritura/lectura real en /tmp funciona; /workspace, /etc, /root y rutas privadas rechazan escritura |
| cwd y rutas | /workspace exacto; intento real /workspace/../forbidden denegado; API rechaza traversal/absolutas/enlaces |
| Cliente A/B | Proceso A no lee ni escribe sentinels de workspace, runs o approvals B; hash del árbol B intacto |
| Entorno | Solo variables revisadas de imagen/runtime/Docker; variable sintética privada ausente |
| Red | Solo interfaz lo; conexión a dirección de documentación 192.0.2.1:9 rechazada localmente, sin contactar un servidor; NetworkMode=none |
| CPU/memoria/PIDs | HostConfig y cgroup v2 dentro del contenedor: cuota CPU equivalente a 1 CPU, memory.max=536870912, pids.max=64 |
| Archivos/noexec | RLIMIT_FSIZE=(10485760,10485760); escritura que excede 10 MiB falla realmente; ejecutar archivo creado en /tmp falla PermissionError |
| Usuario/capabilities | UID/GID del operador coinciden; CapEff=0, NoNewPrivs=1, Seccomp=2; Privileged=false y CapDrop=ALL |
| Éxito, fallo, timeout, salida excesiva | Resultados y limpieza reales verificados |
| SIGINT y recuperación tras crash | Evidencia, estado/códigos, ausencia de replay y limpieza comprobados según escenario |
| Dry-run/WorkOrder/aprobaciones | Suite existente: rechazo antes de Popen, cambios de alcance invalidan aprobación, sin efectos en producto |
| Atomicidad, lock, memoria, contexto, referencias | Suite existente pasa; no se reconstruyeron claims ni se alteró el legado |

No se ejecutaron pruebas de estrés para provocar OOM, saturación de PIDs o medir throttling de CPU: se verificaron los límites instalados en el kernel, además de HostConfig, no benchmarking de esos mecanismos. No se certifica resistencia a vulnerabilidades del kernel/daemon, otras arquitecturas o imágenes. No se hizo escaneo de CVEs de la imagen. SIGTERM/cortes eléctricos/reinicio del daemon siguen sin validación específica; no son escenarios de cierre automático prometidos por el MVP. La herramienta ausente conserva cobertura host y bloqueo sin fallback; no se preparó otra imagen deliberadamente rota. Estas limitaciones no sustituyen ni contradicen el requisito P2 de aplicar límites/red/aislamiento al adaptador actual.

## Reevaluación literal de P2

| Punto del plan | Evaluación técnica |
|---|---|
| 1. Configuración JSON y contexto explícito | Cumplido: validación, cliente/proyecto y digest explícitos |
| 2. Separar código/metadata/secretos/estado | Cumplido en modelo host confiable: snapshot único, B inaccesible, metadata fuera del bind, env privado no heredado; redacción sintética pasa |
| 3. Executor y contención real | Cumplido: pruebas Docker reales de montaje, rutas, cwd/env, red, usuario/capabilities y límites de kernel |
| 4. Permisos, dry-run y raíces autorizadas | Cumplido para el adaptador disponible; no se inicia proceso con autorización inválida ni se altera producto en preview |
| 5. Aprobaciones y restricciones WorkOrder | Cumplido: acción/contenido/política/orden/cliente vinculados, caducidad/uso único y restricciones que no amplían permisos |
| 6. Atomicidad, escritor, UUID, evidencia y recuperación | Cumplido para cierre recuperable: estado ordinario/SIGINT, checkpoint y crash real sin replay; inspección/limpieza manual tras crash explícita |
| 7. Memoria sin escrituras implícitas | Cumplido: desactivada y cubierta por suite |
| 8. Fuentes explícitas y hashes consumidos | Cumplido por tests de contexto/integridad; sin DB/caché nueva |
| 9. Tiempo/llamadas/consumo según contrato | Cumplido: presupuestos host/WorkOrder, timeout real, límites Docker; modelo no aplicable, sin consumo inventado |
| 10. Referencias versionadas y bytes originales | Cumplido: importador/resolve, portabilidad/hash y preservación del legado ya probados; ubicación definitiva de archivo bajo decisión del operador |
| Salida: entorno controlado para herramientas reales/productos | Evidencia suficiente para el executor de pruebas P2; no afirma que exista generación P3 |
| Revisión humana obligatoria arquitectura/seguridad | PENDIENTE antes de habilitar generación asistida o procesos no confiables; no se concede mediante tests |

La clasificación describe aceptación **técnica con limitaciones**, no aprobación humana ni autorización para continuar. Los controles de cliente no resisten a un atacante con la misma cuenta host o acceso al daemon; ambos permanecen fuera del modelo de amenaza. Las aprobaciones/manifiestos no están firmados y la salida textual de unittest puede falsificarse por código malicioso: revisar también qué prueban los tests. Retención/backup y reanudación automática siguen como evolución operativa.

**P2: PASS_WITH_LIMITATIONS.** Se detiene después de esta validación para revisión humana. P3–P7 no se iniciaron; no hubo despliegues ni cambios de infraestructura externa.


## Aprobación posterior — 2026-09-11

El usuario aprobó P2 PASS_WITH_LIMITATIONS y autorizó la preparación P3. Las menciones anteriores de aprobación pendiente son históricas. La validación del renombrado detectó una carrera de limpieza Docker, corregida y documentada en [P3.md](P3.md). Suite actual: 133 aprobadas, incluidas las pruebas Docker originales intactas. Política actual docker-unittest.v3; límites operativos y prohibición de producción permanecen.
