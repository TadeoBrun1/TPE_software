# Prototipo

Demuestra que la arquitectura es viable. Tiene que ser **acotado** (el enunciado pide gestionar bien el tiempo y el
alcance), **trazable** a las ADRs y **consistente** con los contratos de [`specs/`](../specs/).

## Alcance

Elegir pocos escenarios y hacerlos bien. Completar esta tabla en la iteración 1.

| Escenario o driver | ¿Se implementa? | Cómo se demuestra |
|---|---|---|
| QA-1: correo de reserva visible en menos de 5 min | `<sí/no>` | `<prueba, script o demo>` |
| QA-2: consulta del panel en 800 ms | `<sí/no>` |  |
| QA-4: caída de una instancia sin cortar el servicio | `<sí/no>` |  |
| QA-6: cancelación de un tercero procesada | `<sí/no>` |  |
| QA-7: acceso no designado rechazado | `<sí/no>` |  |

## Estructura sugerida

```
prototype/
├── README.md
├── docker-compose.yml        # para levantar todo en local
├── <servicio-ingesta>/       # iteración 2
├── <servicio-consulta>/      # iteración 3
├── <simulador-terceros>/     # simula aerolíneas y proveedores de correo
└── tests/
    └── contract/             # pruebas contra specs/
```

Cada servicio tiene su propio README con: qué spec implementa, qué ADRs materializa, cómo se corre y cómo se prueba.

## Trazabilidad

| Servicio o módulo | Spec | ADRs | Vista | Iteración |
|---|---|---|---|---|
|  |  |  |  |  |

## Cómo correrlo

```bash
# Completar cuando exista el docker-compose
docker compose up
```

## Reglas

- No se implementa nada que no esté contemplado en una spec o una ADR. Si hace falta, primero se documenta.
- Las pruebas de contrato validan que los servicios cumplen `specs/`.
- No se suben credenciales ni datos reales de correo: se usan simuladores.
