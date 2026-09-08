# MIGRATION_PLAN — Evolución incremental de NexoNova Factory

Fecha: 2026-09-06. **Estado: pendiente de aprobación explícita del usuario.**

Este documento no autoriza ninguna reestructuración. La auditoría termina con su entrega. No se ejecutará migración hasta que el usuario apruebe expresamente MIGRATION_PLAN.md. La eventual aprobación del plan no sustituye las revisiones humanas de arquitectura, seguridad, datos o despliegue exigidas por AGENTS.md.

Referencias: [CURRENT_ARCHITECTURE.md](CURRENT_ARCHITECTURE.md), [TARGET_ARCHITECTURE.md](TARGET_ARCHITECTURE.md).

## 1. Objetivo y criterio de éxito

Convertir el prototipo documental en una fábrica local que reciba requisitos, genere un producto NexoNova independiente, lo valide con herramientas reales y permita mantenerlo y preparar su entrega. Conservar el núcleo Python, contratos útiles, control secuencial, principios de política y trazabilidad; sustituir la simulación de capacidades por implementación comprobada.

El éxito no es completar un árbol de carpetas. Es demostrar en un piloto que:

- Un brief estructurado genera una aplicación con comportamiento verificable.
- El resultado no depende del runtime de la fábrica.
- Los fallos de pruebas, permisos, evidencia y configuración bloquean la aceptación.
- Los cambios de mantenimiento conservan personalizaciones del cliente.
- La preparación de despliegue entrega artefactos y procedimientos revisables, sin modificar producción.

No se fija una fecha ni coste de implementación: falta restaurar una línea base reproducible y acordar el alcance del primer producto. La estimación de reutilización de 40–50% del núcleo no es una estimación de calendario ni un porcentaje de producto completado.

## 2. Orden y dependencias

```text
Aprobación explícita de este plan
  → P0 Preservación y línea base
  → P1 Resultados y validación veraces
  → P2 Fronteras de ejecución, configuración y estado
  → P3 Primer generador corporate-site
  → P4 Business-platform y módulos iniciales
  → P5 Mantenimiento de productos
  → P6 Roles asistidos opcionales y evaluados
  → P7 Preparación de entrega y operación
```

P6 puede diferirse si el generador determinista ya resuelve el trabajo del piloto. Los contratos de mantenimiento se definen en P3, aunque la implementación completa de actualización llegue en P5. Los requisitos de contenedores y entrega se consideran al construir cada plantilla; P7 consolida y verifica la capacidad, sin dejar para el final decisiones que afecten el producto.

No se propone trabajo de subagentes ni ejecución paralela autónoma. Cada fase debe ser revisable y reversible en código, con cambios pequeños y pruebas relevantes.

## 3. P0 — Preservar y establecer una línea base

**Problema:** fuentes de diseño faltantes, metadatos Git no utilizables, tests no ejecutables en el entorno disponible e historial que no reproduce el estado actual.

Trabajo propuesto después de aprobar el plan:

1. Obtener o confirmar la copia completa y el repositorio Git real. No ejecutar `git init` sobre el árbol actual para ocultar la ausencia de historial. Si no existe repositorio recuperable, crear uno solo como decisión explícita, conservando procedencia del snapshot.
2. Preservar la ejecución histórica y el brief ERP con manifiesto de hashes, ubicación de archivo y notas de alcance. No duplicar secretos si una inspección previa encuentra alguno; su gestión corresponde al responsable humano.
3. Confirmar si las siete fuentes de DESIGN_DOCS se pueden recuperar. Si no, registrar ausencia y crear estándares nuevos revisados; no reconstruir supuestos originales desde fragmentos del run ni silenciar la exigencia de evidencia para obtener éxito.
4. Declarar versión Python soportada y dependencia de tests en empaquetado mínimo. Elegir mecanismo de bloqueo reproducible y documentar cualquier herramienta nueva. Instalar solo en un entorno aislado autorizado cuando se implemente.
5. Ejecutar los tests existentes fuera del árbol fuente y registrar salidas reales. Añadir caracterización de bloqueo actual y corrección del aislamiento de los tests para que no escriban memoria de fábrica en la raíz.
6. Preparar fixtures sanitizadas de casos completos y fallidos. No usar un run histórico de estado complete como oráculo de corrección de todos sus claims.

**Componentes:** KEEP AGENTS.md, pruebas negativas concretas; MODIFY empaquetado de tests/aislamiento; preservar para futuro MOVE historial y ejemplo. No mover aún interfaces del núcleo.

**Criterios de salida:** inventario confirmado; copia recuperable; pruebas ejecutables con comando documentado; comportamiento actual completo/fallido descrito sin falsos éxitos; autorización y procedencia de fuentes explícitas. Esta fase no exige hacer pasar el bootstrap actual desactivando controles.

**Riesgo:** bajo para inventario, medio para entorno, alto si se manipula historial. **Revisión humana:** procedencia, derechos de reutilización y estrategia de preservación. **Reversión:** volver a la línea base o revertir solo cambios propios, conservando snapshots y cambios del usuario; sin reset destructivo.

## 4. P1 — Hacer veraces los resultados y gates

**Problema:** F01, F02, F05, F07, F09, F10, F14. La fábrica puede presentar éxito no demostrado.

Trabajo:

1. Cambiar informes estáticos de tests/coverage/security/QA para representar no ejecutado, bloqueado o resultado real. Eliminar porcentajes constantes y aprobaciones atribuidas al usuario sin registro. Conservar los renderizadores útiles como plantillas de informe, no como verificadores.
2. Derivar matriz de trazabilidad y cierre desde resultados y referencias reales. `ready_for_first_project` no debe significar “aplicación lista”; sustituirlo o precisar su alcance en schema versionado.
3. Resolver referencias de evidencia contra el registro, fuente y hash; impedir que IDs arbitrarios certifiquen claims. Separar comprobación automática de existencia/integridad de la evaluación semántica humana o asistida.
4. Garantizar ejecución de todos los gates requeridos o bloqueo por implementación/herramienta ausente. Retirar de catálogo activo capacidades no implementadas, conservando las necesarias como backlog documentado.
5. Validar AgentResult desde el harness; verificar formato final después de producir el cierre, sin depender de un flag optativo del mismo productor. Usar un manifiesto de salidas por workflow en lugar de listas divergentes entre CLI, orquestador y prompts.
6. Hacer que CLI refleje outcome mediante código de salida; capturar errores esperados y persistir un cierre coherente también en abortos. No sustituir un error por un mensaje “sin errores”.
7. Distinguir estimación, no medido y uso real de tokens/coste. Contabilizar ejecución real de herramientas, no la allowlist. Documentar límites de presupuesto pendientes de enforcement hasta P2.

**Componentes:** MODIFY harness, orchestrator, cli, schemas, validators, observability; REPLACE verificadores documentales estáticos y chequeos ficticios; KEEP estados/IDs mediante compatibilidad explícita.

**Pruebas de aceptación:**

| Caso | Resultado requerido |
|---|---|
| Faltan fuentes obligatorias | Bloqueo explicado, nunca éxito genérico |
| ID de evidencia inexistente o hash cambiado | Gate de evidencia falla |
| No se ejecutó pytest/escáner obligatorio | Resultado no aprobado, cobertura no inventada |
| Prueba ejecutada falla | Run y código de salida indican fallo |
| Se altera final-report para decir complete | Verificación detecta inconsistencia con resultados requeridos |
| Artefacto obligatorio falta o está mal formado | Verificación falla |
| Un paso intermedio falla | Cierre conserva causa y pasos no ejecutados; matriz no marca todo completo |
| Documento de decisión carece de aprobación | Estado pendiente, sin atribución ficticia al usuario |

**Salida:** reportes confiables sobre lo que realmente se ejecutó; límites pendientes visibles. **Riesgo:** alto por cambio de semántica de aceptación. **Revisión:** humana sobre criterios de calidad y seguridad. **Reversión:** conservar formato legado de lectura; no regresar a un verificador que presente falsos éxitos para lograr compatibilidad.

## 5. P2 — Separar configuración, ejecución y estado

**Problema:** F03, F04, F06, F08, F10, F11, F12, F15. Una policy declarativa no controla efectos ni protege clientes.

Trabajo:

1. Introducir configuración validada y un contexto explícito de cliente/proyecto/workspace. Usar JSON inicialmente para aprovechar biblioteca estándar; cualquier cambio a YAML incluye justificación de parser y manejo seguro.
2. Separar código, metadata no sensible, secretos y estado. Configuración de cliente permanece privada. Crear exclusiones raíz después de revisar el inventario.
3. Implementar el executor único de herramientas. Validar argumentos y rutas, impedir escapes por symlinks/traversal, establecer cwd/env/timeout y política de red/recursos. Herramientas de prueba ejecutan código del proyecto: su contención debe ser real.
4. Aplicar permisos antes de cada acción y detener ante autorización requerida. Definir un dry-run con significado preciso: genera propuestas en staging autorizado, no modifica el producto aceptado ni dispara efectos externos. La escritura de logs/metadatos también tiene una raíz autorizada.
5. Registrar aprobaciones vinculadas a acción/diff/alcance y separar permisos globales de restricciones del WorkOrder. No basta `approved=true` introducido en JSON por un agente.
6. Crear almacenamiento por run/ciclo con escrituras atómicas y un escritor por proyecto. IDs de run sin colisión práctica; snapshots de evidencia inmutables; checkpoints y cierre recuperable. No añadir BD de control en el MVP.
7. Eliminar inicialización implícita de memoria en factory_root. Mantener memoria automática desactivada o implementar propuestas aprobadas con origen, vigencia y alcance verificables. No permitir que la memoria cambie policy.
8. Actualizar contexto a fuentes explícitas por proyecto; persistir hashes del texto realmente consumido. No añadir vector DB ni caché hasta que exista una necesidad medida y política de invalidación.
9. Implementar límites de tiempo, llamadas y consumo antes/durante la ejecución, según la información realmente disponible. Evitar coste=0 por defecto cuando no se pueda medir un futuro proveedor.
10. Migrar solo copias o referencias de estado legado mediante importador versionado que no cambie sus bytes originales. Los punteros futuros usan rutas portables.

**Componentes:** MODIFY núcleo; CREATE executor, storage, config y tests de fronteras; MOVE historial y memoria legada a ubicación privada validada; REMOVE directorios vacíos y cachés del producto activo solo después de comprobar que son regenerables.

**Pruebas de aceptación:** traversal y symlink fuera del workspace denegados; cliente A no lee/modifica B; acción que requiere aprobación no ejecuta efectos; cambio de diff invalida aprobación previa; dry-run no cambia el producto aceptado; tool ausente/timeout produce ToolResult correcto; tokens/tiempo/calls se limitan según contrato; dos runs simultáneos no mezclan archivos; escritura interrumpida no corrompe último estado válido; evidencia de ciclo anterior mantiene significado; leer memoria no escribe en raíz del código; logs de diagnóstico no filtran un secreto sintético.

**Salida:** entorno controlado suficiente para ejecutar herramientas reales y crear productos. **Riesgo:** alto. **Revisión:** obligatoria de arquitectura y seguridad antes de habilitar generación asistida o procesos no confiables. **Reversión:** schemas/versiones separados y archivo legado intacto; cambios de código reversibles. No desactivar contención para resolver un fallo de compatibilidad.

## 6. P3 — Crear el primer generador útil

**Problema:** no existen aplicaciones generadas, template, módulos, entrada real de requisitos ni identidad del producto.

Trabajo:

1. Acordar un brief pequeño de sitio corporativo con criterios claros: identidad visual, servicios, contacto o FAQ según necesidad. Usar datos ficticios para la prueba inicial. No iniciar con las 40 pantallas del ERP.
2. Implementar WorkOrder de new-project: requisitos/criterios, template/version, configuración no sensible y módulos solicitados. Rechazar inputs incompletos antes de modificar el workspace.
3. Crear plantilla corporate-site con Next.js App Router, TypeScript, CSS Modules y tokens/componentes NexoNova. Fijar versiones y lockfile; validar compatibilidad antes de darla por aceptada. No añadir BD/auth si no hay función que las requiera.
4. Implementar generador determinista en staging. Validar parámetros, colisiones y archivos existentes; no interpolar texto del cliente en comandos. Producir diff/manifiesto para revisión.
5. Añadir `.nexonova/project.json` con procedencia, versiones y baseline; decidir desde ahora cómo distinguir archivos del generador y personalizaciones.
6. Ejecutar instalación reproducible, comprobación de tipos, build y pruebas apropiadas a las funciones reales. Registrar versiones, resultados y hashes. Validar estructura, documentación y ausencia de dependencia runtime hacia factory.
7. Crear README y guías concretas, y primer pipeline de validación de fábrica cuando exista un repositorio GitLab autorizado. Preparar configuración del pipeline es local; no crear servicios/remotos por implicación.

**Componentes:** CREATE templates/corporate-site, generators, standards, manifiesto, pruebas de integración y documentación; MODIFY CLI/orquestador para new-project. No crear todavía ocho módulos vacíos.

**Criterios de salida:** dos configuraciones de cliente generan diferencias esperadas sin filtrarse datos; misma entrada/versiones produce mismo contenido estable salvo metadata temporal declarada; rechaza sobrescritura no acordada; producto construye y funciona desde su repo independiente; reportes prueban ejecución real; componentes UI cumplen criterios acordados; un fallo de build impide aceptación.

**Riesgo:** medio-alto. **Revisión:** arquitectura del template, identidad UI y resultado funcional por humano. **Reversión:** descartar staging identificado y conservar el workspace aceptado; nunca borrar un directorio que pueda contener trabajo del usuario. Sin datos productivos en esta fase.

## 7. P4 — Plataforma de negocio y módulos con consumidor real

**Problema:** la fábrica aún no demuestra productos con autenticación y persistencia.

Trabajo:

1. Crear business-platform como template versionado que reutiliza componentes UI; evitar copiar incoherentemente dos sistemas de diseño.
2. Integrar Better Auth, Route Handlers, servicios de dominio, Prisma 7, Prisma Migrate y PostgreSQL 16 conforme a AGENTS.md. Registrar combinaciones exactas y pruebas de compatibilidad.
3. Implementar autenticación y una capacidad administrativa acotada con autorización por recurso; no confundir identidad con permisos de negocio. Mantener decisiones de seguridad sujetas a revisión.
4. Definir el contrato de módulo: versión, dependencias, archivos/servicios, configuración, migraciones, tests y actualización. Incorporar contact/services/FAQ o administración según alcance aprobado, no todos por adelantado.
5. Añadir pruebas de integración con BD efímera y datos sintéticos, controles de sesión/autorización y un flujo E2E representativo. Aplicar migraciones solo en entornos locales de prueba.
6. Reubicar el brief ERP como ejemplo independiente si ya se aprobó su destino; conservar original y documentar las contradicciones a resolver antes de convertirlo en proyecto. No incorporar sus reglas al estándar global.

**Componentes:** CREATE business-platform y módulos seleccionados; MODIFY composición/generadores/validators; MOVE ejemplo legado. Todo módulo no solicitado continúa como backlog.

**Criterios de salida:** acceso denegado sin permiso aunque se manipule identificador; migraciones reproducibles en BD efímera; configuración sensible fuera del repo y logs; módulo instalable solo en combinaciones compatibles; regresión del sitio corporativo sin cambios no deseados; validación humana de arquitectura y seguridad.

**Riesgo:** alto. **Reversión:** versiones de plantilla/módulo anteriores en entornos de prueba; no prometer reversión automática de una migración de datos. Datos reales y migraciones destructivas están fuera del alcance de esta fase.

## 8. P5 — Actualizar y corregir proyectos existentes

**Problema:** generar una vez no basta para mantener plataformas de múltiples clientes.

Trabajo:

1. Implementar update-project desde manifiesto y baseline. Comprobar estado del árbol y preservar cambios preexistentes.
2. Producir diff de actualización de template/módulos/standards; reconocer conflicto con personalizaciones y detener aceptación hasta resolución. No regenerar todo sobre un repo cliente.
3. Implementar bug-fix con reproducción, prueba de regresión pertinente y cambio mínimo. Separar corrección de defecto de actualización general de dependencias.
4. Versionar compatibilidad del manifiesto y documentar soporte. Registrar requerimiento/ticket de origen sin copiar datos sensibles innecesarios.
5. Introducir preparación local para revisión Git: estado, diff y referencias. Publicación, merge o contacto externo no se infieren de una operación local.
6. Ejecutar pruebas del producto afectado y regresiones de generador por cambios compartidos. Evitar ampliar pruebas sin justificación cuando checks relevantes ya pasan.

**Criterios de salida:** una personalización cliente sobrevive a una actualización compatible; un conflicto bloquea sobrescritura; repo sin manifiesto no se adopta silenciosamente; cambio solicitado produce trazabilidad y diff mínimo; bug reproducido deja de fallar tras corrección; versión incompatible exige un plan específico.

**Riesgo:** alto por posible pérdida de personalizaciones. **Revisión:** diff y decisiones de resolución por humano. **Reversión:** referencias de código y backup del workspace previos, sin sobrescribir modificaciones posteriores ajenas; plan independiente para datos.

## 9. P6 — Incorporar razonamiento asistido solo donde aporte valor

**Problema:** los nombres de agentes actuales no son capacidades reales de IA.

Trabajo condicionado a necesidad del piloto:

1. Definir developer y reviewer como roles con contratos de entrada/salida, alcance y evaluación. Usar secuencia simple; no crear roles OCR, SRE o billing permanentes.
2. Externalizar instrucciones de sistema/tarea/compartidas y versionarlas. Mantener normas, datos del cliente y memoria con fronteras de confianza claras.
3. Elegir el mecanismo de integración asistida y documentar permisos, privacidad, coste y dependencia nueva si la hay. No habilitar envío de fuentes a terceros sin el alcance autorizado correspondiente.
4. Conectar propuestas y ToolRequests al harness/executor existente. El modelo no accede directamente a filesystem ni declara gates aprobados por sí mismo.
5. Evaluar tareas representativas, cambios inválidos, instrucciones maliciosas en briefs y contexto insuficiente. Registrar qué verificó el reviewer y qué queda pendiente de persona revisora.
6. Medir uso si el proveedor lo permite y marcar estimaciones/faltantes con honestidad. No atribuir tokens del modelo cuando solo se procesó JSON local.

**Criterios de salida:** propuestas útiles sobre el producto piloto; entradas no confiables no elevan permisos; revisión detecta fallos de muestra; ejecuciones bloquean cuando falta autorización; coste/uso con origen explícito; no se reduce revisión humana significativa.

**Riesgo:** alto. **Revisión:** arquitectura, privacidad y seguridad humanas. **Reversión:** desactivar adaptador asistido y conservar los flujos deterministas; prompts/resultados quedan versionados según retención aprobada.

## 10. P7 — Preparar entrega, operación y mantenimiento

**Problema:** no existen contenedores, recetas de entrega, pipeline de producto ni runbooks verificados.

Trabajo:

1. Consolidar Docker/Compose para aplicación y PostgreSQL donde corresponda; Nginx y configuración TLS parametrizada para los productos. Certificados y credenciales reales quedan fuera del repo y de la fábrica.
2. Preparar pipeline GitLab CI/CD del producto con controles de build, tests y artefactos; distinguirlo del pipeline que valida factory. No conectar ni cambiar servidores productivos durante esta fase local.
3. Implementar prepare-deployment: comprobar artefacto/versiones, configuración requerida, migraciones a revisar, documentación y permisos. Separar package/prepared de deployed.
4. Documentar instalación local, preparación para Ubuntu Server LTS/VPS, backups/restauración, actualización de dependencias, rotación operativa de secretos bajo responsabilidad humana, logs y recuperación.
5. Probar recetas en entorno local/efímero autorizado, incluyendo arranque limpio, persistencia de prueba y restauración con datos sintéticos. Escáneres faltantes obligatorios bloquean certificación.
6. Definir retención y acceso a logs/estado por cliente y proceso de soporte. Revisar restore/export del estado de fábrica y compatibilidad entre releases.

**Criterios de salida:** paquete de entrega construible; configuración completa mediante placeholders documentados; Compose y proxy probados donde corresponda; backups/restauración de prueba demostrados; checklist humano de release; ninguna credencial ni dato productivo utilizado; no presentar preparación como despliegue realizado.

**Riesgo:** alto si se confunde con producción; medio para preparación local contenida. **Revisión:** responsable de arquitectura, seguridad y operación. **Reversión:** conservar artefactos/versiones previos y runbooks; una eventual reversión productiva exige aprobación y plan específico.

**Fuera del plan ejecutable:** desplegar en VPS real, modificar DNS/TLS productivo, crear recursos externos, enviar correos, hacer merge/publicación, gestionar credenciales reales o realizar migraciones destructivas. Cada uno requiere el alcance y la aprobación humana correspondientes; no queda autorizado por esta auditoría ni por la preparación local.

## 11. Matriz de dependencia entre hallazgos y fases

| Hallazgos de CURRENT | Fase que introduce corrección | Evidencia de cierre |
|---|---|---|
| F01 fuentes ausentes | P0/P1 | Corpus autorizado y test de ausencia que bloquea |
| F02 éxito/cobertura estáticos | P1 | Reportes derivados de ejecuciones y fallos reproducidos |
| F03 permiso sin detención | P2 | Acción denegada no produce efecto |
| F04 aislamiento/aprobación | P2 | Pruebas de rutas, clientes, procesos y aprobación vinculada |
| F05 gates ficticios | P1, integraciones P2/P3 | Todos los controles requeridos ejecutados o bloqueo explícito |
| F06 evidencia mutable | P2 | Resolución de referencias por ciclo tras cambiar fuentes |
| F07 tests débiles | P0/P1 y cada fase | Aserciones semánticas y escenarios negativos |
| F08 memoria parcial | P2 | Memoria desactivada o aprobada, sin escritura implícita en raíz |
| F09 CLI/cierre | P1 | Exit codes, errores y estado coherentes |
| F10 consumo/límites | P1/P2/P6 | Estimación honesta, límites ejecutables y uso medido si existe |
| F11 persistencia/concurrencia | P2 | Atomicidad, exclusión y recuperación |
| F12 dependencias/capacidades | P0/P2 | Entorno reproducible y health checks efectivos |
| F13 stack alternativo | P3/P4 | Templates aprobadas con stack NexoNova |
| F14 aprobación ficticia | P1/P2 | Registro humano verificable o pendiente |
| F15 mezcla de proyectos/rutas | P2/P4 | Estado privado y ejemplo separado, historial preservado |

## 12. Reglas para una migración revisable

- Ningún movimiento puramente cosmético antes de corregir responsabilidades y definir sus consumidores.
- Cambiar una interfaz a la vez y conservar lectura de estado legado cuando sea necesaria. No mover todos los módulos y alterar lógica en una única entrega.
- Una nueva dependencia necesita razón, versión compatible, declaración reproducible y prueba pertinente. No incorporar todo el catálogo de tools solo porque está escrito en registry.
- No importar reportes antiguos como “passed” del estado nuevo; son archivo histórico.
- Antes de REMOVE, explicar por qué es regenerable o sustituido y verificar que no contiene trabajo único. Los originales de evidencia y ERP se preservan.
- Hacer rollback de cambios propios mediante revisión de diferencias y versiones; no usar operaciones destructivas sobre trabajo ajeno.
- Detener la promoción de una fase si falla su criterio de salida. No debilitar validadores para avanzar.
- Los documentos de arquitectura se actualizan con decisiones aprobadas; la propuesta conceptual no se vuelve normativa por estar en una carpeta nueva.

## 13. Revisiones humanas necesarias, sin acciones pendientes en esta auditoría

Para iniciar: aprobación explícita de este MIGRATION_PLAN.md. Después, en el momento correspondiente, revisión del esquema de permisos/almacenamiento, alcance del primer piloto, plantilla de autenticación/datos, integración asistida si se habilita y receta de entrega. Las decisiones se presentan con implementación local, tests y diff listos para revisar siempre que el alcance ya permita prepararlos.

No se requiere elegir ahora entre herramientas de modelos, frameworks de agentes, formatos alternativos de configuración o infraestructura adicional para aceptar el diagnóstico. Las propuestas por defecto son: Python, un paquete, secuencia simple, configuración JSON inicial, estado privado por proyecto y generación determinista antes de automatización asistida.

## 14. Estado al entregar este plan

- Auditoría y tres documentos completados fuera del repositorio.
- Código y archivos del proyecto sin cambios; ninguna reestructuración ejecutada.
- Diagnósticos acotados ejecutados solo en copia temporal.
- Suite pytest no ejecutada por dependencia ausente; no se afirma cobertura ni aprobación de pruebas.
- No se instalaron dependencias ni se modificaron servicios externos o infraestructura.
- Trabajo detenido al entregar el análisis. La próxima implementación solo comienza tras aprobación explícita de este documento.
