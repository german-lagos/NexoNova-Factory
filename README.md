# NexoNova Factory

Núcleo local en Python para evolucionar hacia una fábrica de software de NexoNova. **Estado actual: migración parcial y experimental. No genera todavía aplicaciones web ni está aprobado para producción.**

P0 estableció la línea base y P1 eliminó la aceptación del bootstrap documental como trabajo real. P2 incorpora almacenamiento privado, validación y un adaptador de pruebas preparado, pero su aislamiento Docker sigue pendiente de validación. P3 espera el brief concreto elegido por el usuario. Consulte [el informe de cambios](REFACTOR_REPORT.md) y [el estado de las fases](docs/migration/README.md).

## Requisitos

- Linux y Python 3.11 o superior; esta entrega se probó con Python 3.14.4. El lock usa flock y el adaptador asume un socket Docker local de Linux.
- Runtime sin dependencias Python externas. pytest se usa solo para desarrollo; setuptools es el backend de empaquetado.
- Docker local e imagen oficial Python fijada por digest **solo para el adaptador experimental de procesos**. La imagen no se descarga automáticamente. No se implementa un fallback de ejecución en host.
- Los productos futuros seguirán el stack de [AGENTS.md](AGENTS.md). No se han creado templates Next.js, autenticación, BD ni infraestructura de clientes en esta entrega.

## Desarrollo y pruebas

En un equipo con soporte de `venv` y `pip`:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-test.lock
.venv/bin/python -m pip install --no-build-isolation --no-deps -e .
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -B -m pytest -q -p no:cacheprovider
python3 -B scripts/validate_repository.py
```

El entorno de esta sesión no incluía pip/ensurepip: se utilizó `/tmp/nexonova-migration-venv` con descargas oficiales autorizadas. Al reiniciarse el entorno el 2026-09-07 se perdió esa ubicación y se recrearon las mismas dependencias en .venv, con pip oficial en .migration-tools (ambos ignorados). Esas ubicaciones auxiliares no son requisitos del runtime. Si falta ensurepip en tu equipo, prepara el soporte de entorno virtual antes de seguir los comandos. El lock fija versiones del entorno de desarrollo; aún no contiene hashes ni acredita compatibilidad multiplataforma.

## Operación local disponible

Crear un workspace **fuera del checkout**; el comando solo prepara estado y directorios:

```bash
python3 -B -m factory.cli init-workspace --root /tmp/nexonova-workspaces --client demo --project-id piloto
python3 -B -m factory.cli list
```

Vista previa del adaptador de pruebas, sin ejecutar procesos ni consumir aprobaciones:

```bash
python3 -B -m factory.cli run-tool --root /tmp/nexonova-workspaces --client demo --project-id piloto --tool python.unittest --config config/factory.json --dry-run
```

La vista previa devuelve `needs_user_input` y código 1 porque no acredita una prueba ejecutada. Sin Docker o imagen aprobada, la ejecución devuelve `not_answerable`. Ninguno de esos estados significa un test aprobado.

Para evaluar el adaptador más adelante, un operador deberá disponer de Docker local, revisar una imagen `python@sha256:<digest real de 64 caracteres hexadecimales>` y guardarla en una configuración privada basada en `config/factory.json`. `approve-tool` requiere esa misma configuración y un actor host; la autorización se consume una vez y caduca. Véase [seguridad y límites](docs/security.md). No sustituir el digest por el ejemplo literal ni ejecutar clientes antes de cerrar las pruebas de aislamiento.

Los comandos `run` e `init-project` permanecen como compatibilidad diagnóstica. `run --project <directorio externo> --objective <texto>` devuelve un cierre bloqueado: los 13 agentes académicos no ejecutan sus reportes estáticos. `verify --run <directorio de run>` comprueba formato/integridad y no modifica evidencia. Un run académico sin manifiesto nuevo no se certifica como actual.

## Responsabilidades

- `factory/`: CLI, orquestador, contratos, políticas, validación, contexto, estado y executor.
- `config/factory.json`: configuración explícita sin secretos; memoria desactivada y sin imagen de ejecución preaprobada.
- `tests/`: regresiones del núcleo, evidencia y fronteras de almacenamiento/ejecución.
- `docs/migration/`: decisiones, resultados y bloqueos por fase.
- `project/`: snapshot académico preservado; no utilizarlo para nuevos clientes.

No se movieron ni eliminaron archivos legados. La ausencia de historial Git está documentada; no se ejecutó `git init`. Los tres documentos de auditoría de la raíz son snapshots previos aprobados, no descripciones del estado implementado. La descripción actual está en [docs/architecture.md](docs/architecture.md).

## Próximo paso

Validar P2 con Docker local y revisión humana de seguridad, y recibir el brief de P3. Después podrán comenzar la generación corporativa, plataforma de negocio, mantenimiento y preparación de entrega en el orden del plan aprobado. No se han realizado despliegues, cambios de servicios externos ni migraciones de datos.
