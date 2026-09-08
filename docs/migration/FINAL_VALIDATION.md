# Validación de cierre de la entrega parcial

Inicio: 2026-09-06. Cierre: 2026-09-07. Alcance: P0/P1 y preparación parcial de P2.

Este registro se completa con resultados de comandos reales. No acredita ejecución de P3–P7 ni aislamiento Docker.

## Comprobaciones

Suite completa del núcleo, CLI, empaquetado e instalación aislada, validación estructural/imports, enlaces de documentación y hashes del material preservado. Resultados detallados se registran en validation-results.json al finalizar.

## Incidencia documental

La primera comprobación de enlaces detectó una referencia a este registro antes de su creación. Se creó el documento y se repite el control; no se trató un enlace roto como éxito.

## Límites

Docker no disponible; no se ejecutaron contenedores ni pruebas web/BD/producción. Pendiente brief concreto de P3. Los procesos usados para probar timeout/salida son fixtures confiables del núcleo, no procesos de clientes.

## Resultado final del 2026-09-07

| Comprobación | Resultado |
|---|---|
| Suite disponible completa | 58 passed, 1.33 s; exit 0 |
| Arranque CLI desde fuentes | --help, exit 0 |
| Imports, estructura, enlaces y hashes protegidos | structural_validation=complete |
| Construcción wheel sin dependencias runtime | exit 0 |
| Instalación del wheel en target aislado | exit 0 |
| Arranque CLI instalada | --help, exit 0 |
| Inicialización de workspace desde paquete instalado | exit 0 |
| Preview desde paquete instalado | needs_user_input, exit 1 esperado, sin proceso |
| Ejecución sin backend aprobado | not_answerable, exit 1 esperado, sin proceso |

Wheel: nexonova_factory-0.1.0-py3-none-any.whl; SHA-256: ff3c80d5d3678f103d6b2a41a6241f67aa96d25503adbb6e61a9da0acd7190de. Artefacto local ignorado en .migration-tools/wheels. La instalación se probó con imports desde .migration-tools/installed-20260907, no desde factory del checkout.

Los logs de cada comando están en [validation-results.json](validation-results.json). El warning de caché pip no escribible no impidió instalación; no se modificó Python del sistema.

El primer intento de cierre tras la continuación falló porque pip.pyz y el entorno de /tmp ya no existían. Se recrearon las mismas versiones fijadas en .venv/.migration-tools; véase A06. Se repitieron las validaciones completas sobre el estado actual. No se genera un diff falso contra el baseline perdido: [change-inventory.json](change-inventory.json) compara hashes y clasifica archivos.

Estos resultados validan el núcleo disponible. No completan P2, P3 ni fases posteriores y no constituyen aprobación humana de seguridad.
