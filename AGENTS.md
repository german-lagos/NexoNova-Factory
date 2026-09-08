# AGENTS.md — NexoNova Factory

## Project purpose

This repository contains NexoNova Factory, an AI-assisted software factory
intended to generate, validate and maintain web platforms for small and
medium-sized business clients.

The repository originated from an academic software factory and is currently
being adapted for professional use.

The goal is NOT to preserve the academic structure when it conflicts with
maintainability, security, modularity or NexoNova standards.

## General working rules

1. Never make destructive changes without explaining why they are necessary.
2. Preserve existing working functionality whenever possible.
3. Prefer incremental refactoring over complete rewrites.
4. Do not introduce new frameworks, libraries or infrastructure without
   documenting the reason.
5. Do not modify production infrastructure or external services.
6. Never expose, duplicate or commit secrets, credentials or private keys.
7. Keep human review as a required step for architectural, security and
   deployment decisions.
8. Run the relevant tests and validations after structural changes.
9. Document significant architectural decisions.
10. When uncertain, prefer the simplest maintainable solution.

## Target role of the factory

NexoNova Factory must eventually support:

- receiving structured client requirements;
- generating web projects from reusable templates;
- applying NexoNova engineering standards;
- integrating reusable modules;
- using AI agents for software engineering tasks;
- validating generated projects;
- generating documentation;
- preparing projects for version control and deployment;
- supporting maintenance and future updates.

The factory itself must remain independent from any individual client's
generated project.

## Target stack for generated NexoNova web products

Frontend / application:
- Next.js App Router
- TypeScript

UI:
- CSS Modules
- NexoNova design tokens
- reusable React components owned by NexoNova

Backend / API:
- Next.js Route Handlers
- domain service layer
- Better Auth

Database:
- PostgreSQL 16

ORM:
- Prisma 7
- Prisma Migrate

Containers:
- Docker
- Docker Compose for application and database

Reverse proxy:
- Nginx
- HTTPS / TLS

Version control and delivery:
- Git
- GitLab
- GitLab CI/CD

Initial server environment:
- Ubuntu Server LTS
- VPS

AI-assisted engineering:
- Codex
- AGENTS.md project instructions
- restricted permissions
- mandatory human review for significant changes

## Architecture principles

The factory and generated products must favor:

- modularity;
- maintainability;
- separation of concerns;
- reproducibility;
- traceability;
- testability;
- explicit configuration;
- secure defaults;
- reusable components;
- clear documentation.

Avoid unnecessary complexity and premature multi-agent architectures.

## Human responsibility

Codex assists with analysis, implementation, refactoring and validation.

Codex does not have final authority over:

- architecture approval;
- security approval;
- production deployment;
- credential management;
- destructive migrations;
- customer data decisions.

These require human review.