# Prompts usados

Adaptación del flujo del paper "Better Together" a los nombres de archivo de este repo. Sirve de plantilla y de
**registro**: cada vez que se use IA para producir un artefacto, se agrega una fila a la tabla de abajo.

## Archivos que se le dan a la IA como contexto

| Archivo | Rol |
|---|---|
| `ai/architect-persona.md` | Persona fija |
| `docs/01-add/ADD.md` | Descripción del proceso |
| `docs/00-requirements/architectural-drivers.md` y los archivos que enlaza | Entradas priorizadas |
| `docs/architecture.md` | Documento central que se va modificando |
| `docs/01-add/iteration-plan.md` | Plan acordado |

## Prompts

**1. Revisar entradas**

```
Revisá docs/00-requirements/architectural-drivers.md y los documentos que enlaza.
Verificá que los requerimientos sean consistentes y que entiendas las prioridades.
Hacé preguntas de aclaración si hace falta.
```

**2. Modelo de dominio**

```
Considerá los drivers y creá un modelo de dominio en docs/02-views/domain-model.md.
Representalo con un diagrama de clases en Mermaid e incluí una tabla que describa cada elemento.
```

**3. Plan de iteraciones**

```
Considerá las prioridades de los requerimientos y el modelo de dominio. Creá un plan de iteraciones
siguiendo docs/01-add/ADD.md. Para cada iteración, indicá el objetivo principal. La primera debe estructurar
el sistema; las siguientes atacan los drivers de mayor prioridad, y los requerimientos que sostienen el
negocio van en las primeras. Presentalo como tabla con número, objetivo y drivers, en docs/01-add/iteration-plan.md.
```

**4. Ejecutar una iteración**

```
Vamos a ejecutar los pasos de ADD descritos en docs/01-add/ADD.md. Seguilos exactamente como están
descritos. Ejecutá un solo paso por vez y esperá mi devolución antes de continuar. Respondé en Markdown.
Esta es la iteración: N. Usá la plantilla docs/01-add/iteration-template.md.
```

**5. ADR de una decisión**

```
Redactá una ADR en formato MADR, usando docs/03-adr/adr-template.md, para la decisión <X> de la iteración N.
Incluí al menos dos alternativas descartadas con sus pros y contras y la trazabilidad a los drivers.
```

## Reglas de uso

1. **Una persona revisa todo lo que produce la IA** antes de abrir el PR. En el paper, los modelos cambiaron de
   opinión entre corridas en decisiones críticas (monolito modular o microservicios), así que esas las decide una
   persona.
2. Se corrige a mano lo que esté mal y se anota abajo qué se cambió.
3. Los números inventados por la IA se tratan como suposiciones hasta validarlos.

## Registro

| Fecha | Quién | Prompt (número o texto) | Artefacto generado | Qué se corrigió a mano |
|---|---|---|---|---|
|  |  |  |  |  |

## Registro de preparación — iteración 2

| Fecha | Herramienta | Solicitud resumida | Artefactos | Revisión humana |
|---|---|---|---|---|
| 2026-10-27 | ChatGPT/Codex | Continuar por pasos la iteración 2 y documentar vistas/ADRs (paso 6) | Iteración, vistas de ingesta, ADR-0020 a 0024 y contrato propuesto | Revisión cruzada y paso 7 pendientes |

Base inicial: `a5cf3ca379324426b493cee10a78953ab0a7ab30`; actualizada antes del PR a
`5e3c0c377280046e934fad1d1e13c0d31711c5c5` para conservar la primera iteración publicada por el otro integrante.
Se refinó el contrato con región de origen, clave de negocio y orden por reserva. No se atribuyen pruebas o
aprobaciones inexistentes.
