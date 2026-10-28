# Trotamundos — Arquitectura de software con ADD

Trabajo Práctico Especial · Diseño de Sistemas de Software · UNICEN

> Panel de gestión de viajes en línea: un único punto de verdad para hoteles, autos, vuelos, trenes y autobuses,
> organizado por viaje, desde web o móvil.

**Equipo:** Tadeo Brun · Tomas Lateana

---

## Por dónde empezar a leer

| Quiero ver… | Ir a |
|---|---|
| El documento central de la arquitectura (resumen e índice de todo) | [docs/architecture.md](docs/architecture.md) |
| Requerimientos, QAs, restricciones y drivers | [docs/00-requirements/](docs/00-requirements/) |
| El proceso ADD: plan e iteraciones | [docs/01-add/](docs/01-add/) |
| Las vistas arquitectónicas | [docs/02-views/](docs/02-views/) |
| Las decisiones (ADRs, formato MADR) | [docs/03-adr/](docs/03-adr/) |
| Los contratos (spec-driven) | [specs/](specs/) |
| El prototipo | [prototype/](prototype/) |
| Quién hizo qué | [TEAM-LOG.md](TEAM-LOG.md) |

## Estado de las iteraciones ADD

| # | Objetivo | Responsable | Estado | Documento |
|---|---|---|---|---|
| 1 | Estructura general del sistema | Ambos | En revisión (ADRs propuestas) | [iteration-1](docs/01-add/iteration-1-structure.md) |
| 2 | Ingesta de reservas (correo + terceros) | Tomas | Pasos 2–7 revisados; viabilidad de QA-1 pendiente | [iteration-2](docs/01-add/iteration-2-ingestion.md) |
| 3 | Consulta, latencia, disponibilidad y escala | Tadeo | Pasos 2–7 documentados; decisiones confirmadas | [iteration-3](docs/01-add/iteration-3-query-scale.md) |
| 4 | Seguridad, compartición, i18n y analítica | Ambos | Pasos 2–7 documentados y auditados | [iteration-4](docs/01-add/iteration-4-security-evolvability.md) |

Las iteraciones adicionales (opción avanzada A/B de la 2da entrega, refinamientos) se agregan a
[iteration-plan.md](docs/01-add/iteration-plan.md).

## Estructura del repositorio

```
.
├── README.md
├── CONTRIBUTING.md          # reglas de trabajo en paralelo
├── TEAM-LOG.md              # registro de aportes por integrante
├── docs/
│   ├── README.md            # mapa del proceso y herramientas
│   ├── architecture.md      # documento central
│   ├── 00-requirements/     # contexto, RF, QAs (SEI), árbol de utilidad, drivers
│   ├── 01-add/              # ADD.md, plan, iteraciones, registro de impactos
│   ├── 02-views/            # una vista por archivo
│   ├── 03-adr/              # ADRs en formato MADR
│   └── images/
├── specs/                   # OpenAPI / AsyncAPI (el contrato manda)
├── prototype/               # código que demuestra la arquitectura
├── ai/                      # persona y prompts usados con IA
└── wiki/                    # Home y Sidebar para publicar en la Wiki de GitHub
```

Sobre la Wiki de GitHub, ver [docs/WIKI.md](docs/WIKI.md).
