# Ajustes y límites de ejecución del plan aprobado

La aprobación explícita del usuario del 2026-09-06 prevalece sobre los encabezados históricos «pendiente de aprobación» de los documentos de auditoría, que se conservan íntegros.

## A01 — Copia sin historial ni fuentes recuperables

P0 no pudo recuperar Git ni siete fuentes antiguas en el espacio visible. Se detienen recuperación/importación/traslado y operaciones Git; se conserva el material in situ con hashes. Corrección propuesta: trabajar sobre este snapshot para corregir comportamiento local, sin declarar recuperada la procedencia ni crear un Git artificial. El usuario deberá aportar o identificar el repositorio original antes de publicar. Las nuevas normas no se presentarán como reconstrucciones académicas.

## A02 — Entorno de pruebas

Python disponible no incluye pip/ensurepip. Se prepara un entorno temporal con pip oficial, pytest existente y backend de empaquetado fijado. Esto habilita las pruebas sin modificar el Python del sistema. Un lock de versiones de desarrollo no certifica todas las plataformas.

## A03 — Aislamiento del ejecutor

Bubblewrap existe y funciona fuera del sandbox del asistente; dentro no puede crear namespaces. No se sustituirá aislamiento real por shell local sin contención. Los tests de procesos aislados deben ejecutarse en un entorno que permita namespaces; una tool requerida se bloquea si el backend no está disponible.

## A04 — Brief elegido por el usuario

El usuario respondió que enviará un brief concreto para P3. No se usa el piloto ficticio alternativo. Se detiene la selección/materialización de plantilla del cliente hasta recibir ese brief. Continúan solo trabajos independientes de P1/P2 y documentación.

## A05 — Docker no disponible

Docker, backend del stack aprobado elegido para P2, no está disponible y falta una imagen local fijada por digest. Se prepara el adaptador y se prueban sus controles sin afirmar aislamiento real. No se incorporó Bubblewrap como tecnología de producto. Corrección de ejecución: mantener P2 sin promoción hasta validar Docker local; P3 también espera A04. P4–P7 conservan sus dependencias; no se rellenan carpetas para aparentar avance.

## A06 — Reinicio del entorno y pérdida de /tmp (2026-09-07)

La continuación ya no conserva /tmp/nexonova-migration-baseline, /tmp/nexonova-migration-venv ni el wheel temporal. El repositorio y baseline-sha256.json sí permanecen. Se detiene la generación del diff contra los originales: hashes no permiten reconstruir contenido y no se fabricará un patch a partir de memoria.

Corrección: herramientas en .migration-tools/ y .venv/ ignorados, checkpoint del estado actual en .migration-checkpoints/ ignorado, e inventario persistente de cambios por hashes. Este checkpoint no sustituye el baseline inicial perdido ni un repositorio Git. El material académico y las instrucciones se comprueban contra sus hashes originales. Para recuperar exactamente el código fuente previo debe obtenerse Git/originales del usuario. P0 queda con esta limitación de reversión explícita; no se iniciarán movimientos/eliminaciones que dependan de esa recuperación.
