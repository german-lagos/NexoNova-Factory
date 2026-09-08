# Preparación de despliegue — pendiente

No hay aplicación web generada, pipeline de producto, Docker Compose, Nginx ni procedimiento de despliegue implementado. No se desplegó ningún sistema ni se modificaron servicios externos.

Docker en P2 tiene un propósito distinto: aislar una prueba local experimental de código. No es infraestructura de entrega de una aplicación. Su presencia/configuración aún debe validarse antes de promover P2.

P7 conserva el objetivo de generar artefactos para Docker/Compose, PostgreSQL donde corresponda, Nginx/TLS y GitLab CI/CD con el stack de AGENTS.md. Depende de un producto funcional y validado. No se crearán recetas vacías para simular cumplimiento; producción, credenciales y migraciones destructivas requieren decisiones humanas aparte.
