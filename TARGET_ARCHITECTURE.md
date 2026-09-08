# TARGET_ARCHITECTURE — Propuesta para NexoNova Factory

Fecha: 2026-09-06. Estado: propuesta pendiente de revisión humana. No crea estructura ni autoriza migración.

Documentos relacionados: [arquitectura actual](CURRENT_ARCHITECTURE.md) y [plan de migración](MIGRATION_PLAN.md).

## 1. Decisión propuesta

Conservar una **fábrica local modular en Python, con ejecución secuencial y responsabilidades explícitas**. El código de la fábrica coordina requisitos, generación determinista, herramientas controladas, validadores y evidencia. Los productos generados son aplicaciones independientes con el stack NexoNova definido en AGENTS.md.

No trasladar el núcleo a Next.js: ese stack corresponde al producto generado. No introducir microservicios, un servidor de control, colas, base de datos de fábrica, framework multiagente ni directorios vacíos. Añadir infraestructura solo si aparece una necesidad operativa comprobada. La revisión humana conserva la autoridad sobre arquitectura, seguridad y despliegue.

El primer resultado útil debe ser un proyecto corporativo generable y verificable desde una plantilla versionada. Después se incorpora una plataforma de negocio con autenticación y datos; el ERP legado es un candidato de ejemplo avanzado, no el tamaño adecuado para validar la primera entrega.

## 2. Límites y responsabilidades

| Área | Responsabilidad y contrato | No debe asumir |
|---|---|---|
| CLI / entrada | Recibir WorkOrder estructurado, seleccionar proyecto y presentar resultados/códigos correctos | Convertir silenciosamente todo trabajo en bootstrap |
| Orquestador | Ejecutar pasos y transiciones, detener ante bloqueos, conservar checkpoint | Inventar resultados, aprobar arquitectura, ejecutar shell directamente |
| Harness | Aplicar contexto, permisos, presupuesto y validación a cada invocación | Dar acceso irrestricto a disco o red a una función |
| Roles developer/reviewer | Proponer cambios o evaluar evidencia con alcance explícito | Sustituir herramientas deterministas, certificarse a sí mismos |
| Generadores | Materializar templates/modules/config/documentación en workspace de forma reproducible | Decidir reglas de negocio que no están en los requisitos |
| Tools / executor | Ejecutar capacidades concretas con argumentos validados y capturar ToolResult | Interpretar un comando libre enviado por modelo |
| Validadores | Determinar cumplimiento desde archivos, hashes y resultados reales | Aprobar por presencia de un texto “pass” o por confianza del agente |
| Policy | Autorizar/denegar acciones concretas y reconocer aprobaciones humanas vigentes | Confundir permiso declarado con aislamiento de ejecución |
| Contexto | Resolver fuentes autorizadas y evidencia por proyecto/ciclo | Elevar briefs o memoria a instrucciones de sistema |
| Estado | Guardar transiciones, resultados y procedencia; gestionar concurrencia local | Mezclar datos de clientes con el código fuente de fábrica |
| Standards | Reglas normativas versionadas con controles verificables | Actuar como segunda implementación del motor de validación |
| Templates / modules | Código de producto reutilizable con contratos y versiones | Importar factory en la aplicación cliente |
| Documentación | Describir configuración, capacidades reales y operación | Atribuir aprobaciones humanas no registradas |

Dependencias permitidas: CLI → orquestador → harness/servicios → contratos y adaptadores. Generadores y validadores utilizan tools/almacenamiento mediante interfaces; tools no dependen de agentes. Standards y prompts son insumos versionados, no motores de ejecución. Las aplicaciones generadas no tienen dependencia runtime del paquete Python.

## 3. Estructura propuesta por evolución

Este árbol muestra destinos con responsabilidad prevista. Solo se materializan cuando la fase correspondiente incorpora archivos funcionales.

```text
nexonova-factory/
├── AGENTS.md
├── README.md
├── pyproject.toml                  paquete y dependencias de desarrollo
├── .gitignore
├── .gitlab-ci.yml                  validación de la fábrica, cuando haya GitLab
├── docs/
│   ├── architecture.md
│   ├── factory-overview.md
│   ├── agent-design.md
│   ├── workflows.md
│   ├── security.md
│   ├── deployment.md
│   ├── maintenance.md
│   └── decisions/                 decisiones significativas aprobadas
├── config/
│   ├── factory.json               inicial: biblioteca estándar, sin parser nuevo
│   └── agents.json                solo al existir roles configurables reales
├── factory/                       conservar paquete e imports base
│   ├── cli.py
│   ├── constants.py
│   ├── schemas.py
│   ├── registry.py
│   ├── orchestrator.py
│   ├── harness.py
│   ├── policy.py
│   ├── context.py
│   ├── memory.py
│   ├── observability.py
│   ├── storage.py                 extraer al implementar atomicidad/aislamiento
│   ├── utils.py
│   ├── workflows/                código de new/update/bugfix/prepare-deployment
│   ├── agents/                   adaptadores de roles developer/reviewer
│   ├── tools/                    filesystem, procesos, Git, testing
│   ├── generators/               proyecto, módulos, configuración, docs
│   └── validators/               evidencia, estructura, seguridad, calidad, docs
├── prompts/                      cuando se conecte razonamiento asistido
│   ├── system/
│   ├── tasks/
│   └── shared/
├── standards/                    documentos concretos, no taxonomía vacía
├── templates/
│   ├── corporate-site/           primera plantilla funcional
│   └── business-platform/        después de validar generación base
├── modules/                      incorporar uno por uno con contratos y tests
├── tests/                        unitarios y pruebas de integración relevantes
├── examples/erp/                  opcional: brief legado revisado/sanitizado
└── scripts/                      solo tareas de desarrollo/operación reales
```

Fuera del código versionado, en una raíz de trabajo explícita:

```text
<workspace-root>/
└── <client-id>/<project-id>/
    ├── workspace/                checkout independiente del producto
    ├── temporary/                staging por operación
    ├── runs/<run-id>/
    │   ├── manifest.json
    │   ├── work-order.json
    │   ├── state.json
    │   ├── cycles/<cycle-id>/    contexto/evidencia/resultados inmutables
    │   ├── artifacts/
    │   └── logs/
    └── memory/                   registros aprobados del proyecto, si se usan
```

La fábrica puede admitir `projects/` ignorado como ubicación local opcional, pero no debe exigirlo dentro de su checkout. Para empezar, el workspace es también el repositorio independiente del producto; no hace falta duplicarlo en `generated/`. Una exportación generada solo debe existir si hay un flujo real que la consuma, con estado claro de borrador o versión aceptada.

## 4. Comparación completa con el árbol conceptual solicitado

| Área conceptual | Decisión / ajuste | Justificación |
|---|---|---|
| README.md | Crear manual raíz | Instalación, límites, CLI y ejemplo reproducible |
| docs/architecture.md | Crear | Límites de fábrica/productos y dependencias permitidas |
| docs/factory-overview.md | Crear | Corregir el escape accidental del nombre conceptual; visión funcional |
| docs/agent-design.md | Crear al definir roles | Contratos, evaluación y límites; no catálogo académico |
| docs/workflows.md | Crear | Transiciones, entradas, salidas y condiciones de bloqueo |
| docs/security.md | Crear | Modelo de confianza, permisos y manejo de datos |
| docs/deployment.md | Crear | Preparación de entrega y responsabilidades humanas |
| docs/maintenance.md | Crear | Actualizaciones, recuperación, compatibilidad y soporte |
| config/factory.yaml | Preferir inicialmente factory.json | Mismo propósito con biblioteca estándar y schemas existentes; YAML requeriría justificar parser adicional |
| config/agents.yaml | agents.json solo si agrega configuración real | Evitar duplicar campos del registry; permisos máximos permanecen en política de código |
| config/environments/ | Diferir carpetas | Usar perfiles concretos de ejecución cuando cambien capacidades; no mezclar entornos de productos |
| config/clients/ | Metadata privada en workspace, fuera del repo | Configuración de cliente no es código compartible; versionar solo ejemplos sanitizados |
| agents/developer, reviewer | factory/agents + prompts separados | Código dentro del paquete; roles secuenciales y revisión humana final |
| prompts/system, tasks, shared | Adoptar cuando exista integración real | Fuente versionada, composición trazable y jerarquía de confianza |
| workflows/new-project | factory/workflows/new_project | Implementación Python junto al núcleo y documentación en docs |
| workflows/update-project | factory/workflows/update_project | Actualización controlada desde manifiesto y diff |
| workflows/bug-fix | factory/workflows/bug_fix | Reproducción, corrección mínima y regresión |
| workflows/deployment | prepare_deployment en factory/workflows | Preparar artefactos; no desplegar automáticamente |
| standards/architecture, coding, security | Adoptar contenidos desde primera plantilla | Reglas con ID y validador asociado cuando sean automatizables |
| standards/ui | Adoptar tokens, componentes propios, accesibilidad | No heredar Tailwind/shadcn ni restricciones de dashboard para todos los sitios |
| standards/testing, documentation, deployment | Adoptar al crear controles reales | Sin duplicar manuales: standards indica qué exigir; docs explica cómo operar |
| templates/corporate-site | Primera plantilla | Producto pequeño que valida valor empresarial y reproducibilidad |
| templates/business-platform | Segunda plantilla | Integra autenticación, permisos, persistencia y administración |
| modules/* | Incorporación gradual | Módulo requiere consumidor, contrato y prueba; no crear ocho esqueletos |
| tools/filesystem, git, terminal, testing | factory/tools | Executor controlado; terminal significa procesos allowlisted, no shell libre |
| tools/documentation | Combinar con generators/documentation | Renderizar documentos es generación; filesystem realiza la escritura |
| tools/deployment | Diferir acceso externo; preparación local en tools existentes | Docker/Git pueden producir evidencia local sin administrar servidores |
| validators/project, security, structure, documentation, quality | factory/validators cuando crezca | Estructura puede ser parte de project; evidencia merece comprobación explícita |
| generators/project, modules, config, documentation | factory/generators | Separar según lógica real, no carpetas vacías por cada nombre |
| projects/workspace, generated, temporary | Raíz externa por cliente/proyecto | Evitar duplicar árboles y mezclar datos con fábrica |
| tests/agents, workflows, generators, validators, integration | Adoptar gradualmente | Empezar por pruebas del núcleo y fronteras; crear subdirectorios por volumen |
| scripts/ | Solo scripts concretos | No crear segunda CLI ni duplicar lógica de Python |
| logs/ | Integrar en runs/<run-id>/logs | Correlación, aislamiento y retención; logs globales solo si hay un servicio real |
| deployment/environments, containers, scripts, documentation | No crear raíz de fábrica inicialmente | Compose/Docker/Nginx del producto viven en plantilla y repositorio generado; manual común en docs/deployment.md |

Esta separación conserva una solución existente mejor que la dispersión conceptual: **un paquete Python único y un directorio de artefactos por run**. Se modifica el contenido y la ubicación privada del estado, no el principio de agrupar evidencia por ejecución.

## 5. Contratos que hacen concreta la arquitectura

### WorkOrder

Debe identificar cliente y proyecto, tipo de trabajo, objetivo, requisitos estructurados con criterios de aceptación, fuentes autorizadas, alcance incluido/excluido, template/version, módulos, restricciones y salidas esperadas. Las rutas se resuelven desde el contexto autorizado, no desde texto libre. Restricciones de la entrada pueden reducir permisos, no elevar los límites globales. Identificadores, rangos, campos requeridos y relaciones entre campos se validan antes de escribir.

El texto libre puede iniciar una propuesta de requisitos; si faltan datos esenciales, el flujo marca bloqueo específico y presenta una aclaración. No producir una spec genérica y declararla completa. Para nuevo proyecto, limitar inicialmente la entrada a un esquema pequeño y verificable.

### Run y transiciones

Distinguir lifecycle operativo (`pending`, `running`, `waiting_approval`, `finished`) de outcome (`complete`, `needs_user_input`, `not_answerable`, `error`) o documentar una evolución equivalente del schema. Preservar lectura de estados heredados con una versión explícita. Cada transición guarda paso, causa, resultado y referencia de evidencia.

Run IDs sin colisión práctica; escritura atómica y un escritor por proyecto en el MVP. Checkpoints solo después de cerrar un paso. Reanudar exige verificar hashes del workspace, configuración, inputs y aprobaciones; nunca repetir ciegamente una acción con efectos. No promover resultados parciales a entregables aceptados.

### ToolRequest / ToolResult

ToolRequest identifica operación, workspace, argumentos permitidos, entradas y decisión de autorización. ToolResult registra herramienta y versión real, comando/argumentos sanitizados cuando corresponda, cwd, inicio/fin, exit code, estado, artefactos, hashes, logs y modalidad simulada/real. Capturar timeout o ausencia de herramienta como resultados distintos de un test aprobado.

Los chequeos de política y las ejecuciones se registran como eventos separados. Gates obligatorios sin herramienta disponible quedan bloqueados; controles opcionales pueden quedar skipped con razón. Solo complete si los controles requeridos del workflow se cumplieron con evidencia.

### Aprobación

Registro humano asociado a acción y diff/hash, cliente/proyecto, entorno, permisos y vigencia. Arquitectura y seguridad requieren revisión incluso si la implementación es local. Un cambio de alcance o artefacto invalida una aprobación vinculada a otra propuesta. Las tareas locales reversibles autorizadas no deben exigir una aprobación por cada archivo: se trabaja bajo alcance explícito; las decisiones significativas y despliegues conservan su gate humano.

### Manifiesto del producto

Guardar en el repositorio cliente un manifiesto no sensible, por ejemplo `.nexonova/project.json`: versión de la fábrica/generador, template, módulos, estándares, configuración no secreta, baseline de archivos generados y procedencia de requisitos. Distinguir propiedad del generador y personalizaciones del cliente. No incluir copia del runtime Python ni memoria privada. Este contrato permite mantenimiento sin regenerar a ciegas.

### Evidencia y reportes

IDs inmutables por contenido/ciclo; registrar hash del contenido realmente consumido y origen autorizado. Cada claim técnico relevante referencia evidencia resoluble. Distinguir observación, inferencia y no comprobado; un validador no puede demostrar automáticamente toda afirmación de arquitectura. El reviewer y la persona responsable cubren lo que no es automatizable.

Documentación de pruebas consume ToolResults; cobertura no medida se representa como tal. Decisiones contienen aprobador real o estado pendiente. Los reportes históricos se preservan y etiquetan como legados desde un manifiesto externo, sin modificar sus bytes.

## 6. Workflows propuestos

| Flujo | Entrada | Secuencia mínima | Salida y condición de aceptación |
|---|---|---|---|
| new-project | WorkOrder aprobado y template/version | Validar → plan → revisión de decisiones → generar en staging → validar → revisión de diff → aceptar workspace | Proyecto independiente, manifiesto y evidencia; criterios requeridos satisfechos |
| update-project | Repo cliente, manifiesto y cambio solicitado | Verificar árbol/base → plan de actualización → detectar personalizaciones → producir diff → tests y revisión | Actualización rastreable; conflictos requieren resolución explícita, sin sobrescritura silenciosa |
| bug-fix | Defecto y entorno reproducible | Reproducir → prueba de regresión → cambio mínimo → validación y revisión | Evidencia del fallo previo y corrección; sin actualización amplia de plantilla salvo necesidad |
| prepare-deployment | Versión aceptada del producto | Build → verificar configuración de ejemplo → empaquetar contenedores/config → controles → checklist humano | Artefactos y procedimiento revisables; no conexión ni modificación productiva |

Un workflow es una secuencia parametrizada pequeña. No exigir el mismo número de pasos a una corrección documental y a una plataforma con BD. Validaciones de riesgo y decisiones humanas pueden añadirse sin convertir cada responsabilidad en un agente.

## 7. Plantillas, módulos y stack de productos

El stack objetivo se adopta de AGENTS.md: Next.js App Router y TypeScript; CSS Modules, tokens y componentes React propios; Route Handlers y capa de servicios de dominio; Better Auth; PostgreSQL 16; Prisma 7 y Prisma Migrate; Docker/Compose; Nginx y TLS; Git/GitLab CI/CD; Ubuntu Server LTS en VPS. Esto no valida combinaciones específicas: cada plantilla tendrá versiones fijadas y una matriz de compatibilidad comprobada antes de aceptarse.

Propuesta de responsabilidades internas del producto generado:

```text
producto-cliente/
├── src/app/                       rutas, layouts y Route Handlers
├── src/components/                componentes NexoNova y CSS Modules
├── src/styles/                    tokens y estilos globales mínimos
├── src/modules/<capacidad>/       servicios de dominio y lógica del módulo
├── src/lib/                       infraestructura compartida acotada
├── prisma/                        schema y migraciones cuando usa BD
├── tests/                         unitarios, integración y E2E pertinentes
├── public/
├── docs/                          instalación, operación y mantenimiento
├── deployment/                    configuración de contenedores/proxy si se agrupa aquí
├── .nexonova/project.json          procedencia y baseline no sensible
├── package.json y lockfile
├── .env.example                   placeholders únicamente
├── .gitlab-ci.yml                  pipeline del producto
└── AGENTS.md                       instrucciones del producto y revisión humana
```

Un sitio corporativo informativo no necesita activar autenticación, Prisma o una BD sin una función que lo requiera. No se cambia el stack aprobado: se activan sus capacidades según alcance. La plantilla business-platform sí debe demostrar integración de autenticación, autorización por recurso, servicios y persistencia. No imponer un backend Python al producto porque la fábrica esté escrita en Python.

| Módulo conceptual | Alcance y dependencia | Categoría | Destino y momento | Riesgo de creación |
|---|---|---|---|---|
| authentication | Identidad/sesiones; Better Auth y persistencia aprobada. Autorización de negocio separada | CREATE | modules/authentication, con business-platform | alto |
| contact | Validar formulario y transporte configurable; envío real solo bajo contrato autorizado | CREATE | modules/contact, primer piloto si lo requiere | medio |
| blog | Contenido, publicación y permisos según alcance | CREATE | modules/blog, tras necesidad de cliente | medio |
| gallery | Presentación de imágenes; cargas y almacenamiento son decisiones adicionales | CREATE | modules/gallery, tras consumidor real | medio |
| services | Contenido de servicios y componentes UI | CREATE | modules/services, candidato al sitio corporativo | bajo |
| testimonials | Contenido y presentación; gestión editorial opcional | CREATE | modules/testimonials, según cliente | bajo |
| admin | Superficie administrativa protegida y permisos; no paquete de identidad duplicado | CREATE | modules/admin, con business-platform | alto |
| faq | Contenido de preguntas/respuestas y UI accesible | CREATE | modules/faq, candidato al sitio corporativo | bajo |

CREATE indica inexistencia actual y necesidad condicionada; no autoriza crear todos los módulos en la primera fase. En cada uno: manifiesto con versión, dependencias/compatibilidad, archivos/servicios aportados, variables no secretas requeridas, migraciones cuando corresponda, tests y procedimiento de actualización. Primero composición local sencilla; no un sistema de plugins dinámicos propio.

## 8. Seguridad, estado y mantenimiento

Fronteras de confianza: persona operadora → motor de fábrica → entradas del cliente no confiables → proveedor asistido si se habilita → herramientas y filesystem → repositorio de producto → entorno de despliegue. Modelos, memoria y documentos no autorizan efectos. La política y el aislamiento efectivo se aplican en el executor aunque un prompt diga lo contrario.

Aislamiento por cliente/proyecto también en índices, logs, memoria y archivos temporales. Denegar traversal y symlinks que salgan de raíces autorizadas. Procesos con cwd/env explícitos, timeout y comandos acotados; distinguir pruebas de código no confiable y contenedor con política real de recursos/red. Una allowlist de nombres por sí sola no es sandbox.

Mantener configuración de secretos fuera de repositorios y reportes, con ejemplos de variables. No hay que introducir un gestor externo hasta definir un entorno real. Retención, acceso y eliminación de datos de clientes requieren decisión humana; el software debe permitir aplicarlas por proyecto. El MVP puede desactivar memoria automática y reusar solo conocimiento aprobado explícitamente.

Para estado local: escrituras atómicas, bloqueo de un escritor, schemas versionados, exportación y restauración verificables. Respaldos y política de retención se documentan; no crear una BD de control solo por anticipación. Si aparecen múltiples operadores concurrentes, evaluar un almacén transaccional mediante ADR y migración propia.

Mantenimiento de productos: baseline del template, versiones de módulos/standards, cambios cliente preservados, actualizaciones mediante diff revisable, tests de regresión y rutas de rollback de código. Mantenimiento de fábrica: releases pequeñas, compatibilidad de manifests, fixtures de runs y matriz de plantillas. No prometer rollback automático de datos; migraciones de datos y producción son decisiones humanas.

## 9. Componentes nuevos — clasificación y dependencias

| Elemento ausente | Qué resuelve / problema actual | Categoría | Ubicación | Dependencias | Riesgo |
|---|---|---|---|---|---|
| README raíz y documentación operativa | Onboarding y capacidades verificables | CREATE | README.md, docs/* | CLI y contratos aprobados | bajo |
| ADR/procedencia/licencia | Decisiones y derechos de reutilización sin registro adecuado | CREATE | docs/decisions; metadata legal definida por responsable | revisión humana | medio |
| Empaquetado y lock/resolución reproducible | Entorno de tests no reproducible | CREATE | pyproject.toml y archivo de bloqueo según herramienta elegida | versión Python y pytest | medio |
| Exclusiones raíz | Evitar versionar estado/secretos/cachés | CREATE | .gitignore raíz | inventario y raíz privada de estado | medio |
| Configuración validada | Parámetros fuera de constantes sin elevación de permisos | CREATE | config/factory.json; loader interno | schemas y policy | medio |
| Identidad cliente/proyecto y registro privado | Separación real entre clientes | CREATE | storage y workspace externo | WorkOrder, paths y permisos | alto |
| Almacén transaccional local de runs | Atomicidad, concurrencia, recuperación y versiones | CREATE | factory/storage.py | utils y schemas | alto |
| Executor de herramientas | Efectos controlados y resultados verificables | CREATE | factory/tools | policy, storage y entorno | alto |
| Adaptador Git local | Diffs, estado y baseline, sin publicar por defecto | CREATE | factory/tools/git | Git, workspace y permisos | medio |
| Workflows de producto | Variantes new/update/bugfix/preparación | CREATE | factory/workflows | orquestador, tools y validators | alto |
| Generador de producto y manifiesto | Materializar aplicación independiente | CREATE | factory/generators | templates y configuración | alto |
| Generación de módulos/config/docs | Composición y documentación desde evidencia | CREATE | factory/generators | manifests, módulos y ToolResults | medio |
| Standards verificables | Reglas comunes alineadas con NexoNova | CREATE | standards | AGENTS.md, template y controles | medio |
| Plantilla corporate-site | Primer resultado empresarial | CREATE | templates/corporate-site | stack/frontend y CI de plantilla | medio |
| Plantilla business-platform | Producto con identidad, datos y administración | CREATE | templates/business-platform | auth, Prisma/PG y validación de seguridad | alto |
| Prompts y roles asistidos | Razonamiento delimitado, actualmente inexistente | CREATE | prompts y factory/agents | harness seguro, contratos y evaluación | alto |
| Tests de fronteras y productos | Probar efectos y aceptación, no solo archivos | CREATE | tests | fixtures, executor y templates | alto |
| CI de fábrica | Ejecutar validaciones reproducibles por cambio | CREATE | .gitlab-ci.yml raíz | empaquetado y suites | medio |
| Recetas de entrega del producto | Build/Compose/Nginx/pipeline y documentación | CREATE | templates y repo generado; docs/deployment.md | producto validado y revisión humana | alto |

No se propone instalar dependencias ni conectar servicios en esta auditoría. La elección de nuevas bibliotecas, parser YAML si se prefiere, herramientas de calidad y adaptador de IA debe documentarse en la fase que las necesite. La capacidad asistida puede comenzar con interacción humana sobre diff y contratos; no es obligatorio automatizar un proveedor para demostrar generación determinista.

## 10. Criterios de arquitectura aceptable

1. Un requisito del cliente cambia el producto generado de forma comprobable; no solo el ID de un reporte.
2. El proyecto generado se ejecuta y mantiene sin importar la fábrica.
3. Un test fallido, tool ausente obligatoria o evidencia inválida impide aceptar el trabajo.
4. Un agente no puede escribir fuera de su workspace ni autorizarse acciones sensibles.
5. El estado de un cliente no se filtra a otro; un run conserva evidencia interpretable después de cambios de fuentes.
6. Actualizaciones producen diffs revisables y preservan personalizaciones; conflictos bloquean la aceptación.
7. Preparar despliegue genera artefactos verificables, manteniendo la aprobación productiva en manos humanas.
8. Cada directorio creado tiene consumidores, pruebas o documentación concreta que justifiquen su existencia.

La aprobación de esta arquitectura y sus decisiones de seguridad corresponde a NexoNova. El siguiente paso autorizado depende de la aprobación explícita de MIGRATION_PLAN.md; esta propuesta por sí sola no inicia trabajo.
