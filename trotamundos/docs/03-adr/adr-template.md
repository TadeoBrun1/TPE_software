---
status: "proposed"
date: YYYY-MM-DD
decision-makers: "<A>, <B>"
consulted: ""
informed: ""
---

# <Título corto: problema resuelto y solución elegida>

## Context and Problem Statement

<!-- Contexto y problema, en 2 a 3 frases o como pregunta. Qué driver lo motiva. -->

## Decision Drivers

* <driver 1, por ejemplo QA-1 Frescura de actualizaciones>
* <driver 2>

## Considered Options

* <opción 1>
* <opción 2>
* <opción 3>

## Decision Outcome

Chosen option: "<opción>", because <justificación: cumple el driver X y es la mejor entre las opciones considerando Y>.

### Consequences

* Good, because <consecuencia positiva>
* Bad, because <consecuencia negativa o costo>

### Confirmation

<!-- Cómo se verifica que la decisión se implementó y funciona (prueba de escenario, revisión de código, test de contrato). -->

## Pros and Cons of the Options

### <opción 1>

* Good, because <argumento>
* Neutral, because <argumento>
* Bad, because <argumento>

### <opción 2>

* Good, because <argumento>
* Bad, because <argumento>

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | `<N>`, [iteration-N-...](../01-add/) |
| Drivers | `<QA-x, RF-x>` |
| Vistas afectadas | `<enlaces>` |
| Specs | `<enlaces>` |
| ADRs relacionadas | `<enlaces>` (reemplaza a, depende de, relacionada con) |
| Código del prototipo | `<ruta>` |

<!--
Estados posibles: proposed | accepted | rejected | deprecated | superseded by ADR-XXXX
Nombre del archivo: NNNN-titulo-en-minusculas-con-guiones.md
-->
