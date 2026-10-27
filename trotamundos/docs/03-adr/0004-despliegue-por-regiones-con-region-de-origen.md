---
status: "proposed"
date: 2026-10-27
decision-makers: "Tadeo Brun, Tomas Lateana"
consulted: ""
informed: ""
---

# Despliegue por regiones con región de origen por usuario

## Context and Problem Statement

El sistema es global, debe cumplir 800 ms y 1,4 s para usuarios de todo el mundo, tolerar 5 minutos de inactividad por
mes y tratar los datos personales según la normativa de cada región. Hay que decidir la estrategia general de
despliegue y cómo se reparten los datos entre regiones.

## Decision Drivers

* QA-4 Disponibilidad: una sola instancia, zona o región no puede ser un punto único de falla.
* QA-5 Escalabilidad: escalar el almacenamiento para 15 millones de cuentas.
* CON-3: los datos personales dependen de la región del usuario.
* Considerados, pero no drivers de esta iteración: la latencia global (QA-2 y QA-3, iteración 3) y la atención desde la región más cercana (QA-10, iteración 4).

## Considered Options

* A. Una región con varias zonas de fallo
* B. Varias zonas más una región pasiva de recuperación
* C. Región primaria con réplicas de lectura en todas las regiones
* D. Región de origen por usuario, con varias zonas por región y recuperación en otra región

## Decision Outcome

Chosen option: "D. Región de origen por usuario", because acota las fallas a una región (QA-4), reparte los datos
por usuario (QA-5) y cumple CON-3 sin conflictos de escritura: cada usuario escribe siempre en una sola región.
Además deja preparada la latencia global y QA-10.

Reglas:

* Cada usuario tiene una región de origen que guarda sus datos y atiende su tráfico.
* Dentro de cada región hay varias instancias del núcleo repartidas en zonas de fallo distintas, con almacenamiento y
  mensajería redundantes.
* Cada región tiene recuperación en otra región (inicialmente pasiva para escrituras).
* La entrada de tráfico es redundante y enruta por región de origen.
* La región de origen forma parte de la clave de partición de datos.

**Qué queda sin resolver:** usuarios que viajan, itinerarios compartidos con personas de otra región (RF-08) y la
atención regional completa de QA-10 (idiomas y formatos). Se tratan en las iteraciones 3 y 4. QA-10 **no** se marca
como resuelto en esta iteración. Si el equipo decide no asumir el costo de D, la alternativa es B, y habrá que
registrar que QA-2, QA-3 y QA-10 no se cumplen para usuarios lejanos.

### Consequences

* Good, because una falla queda acotada a una región.
* Good, because cumple CON-3 y reduce la latencia sin replicar datos personales en todas partes.
* Good, because resuelve la partición de datos por usuario (QA-5).
* Bad, because aumenta mucho la operación: replicar datos, detectar fallas y conmutar.
* Bad, because la conmutación debe ser automática y tardar bastante menos de 5 minutos para no consumir el
  presupuesto mensual de QA-4.
* Bad, because el prototipo local no puede demostrar disponibilidad global.

### Confirmation

Revisión de la vista de despliegue y prueba en el prototipo: dos regiones locales simuladas, un usuario atendido por su
región de origen y la caída de una instancia sin interrumpir la consulta.

## Pros and Cons of the Options

### A. Una región con varias zonas de fallo

* Good, because es la más simple.
* Bad, because una falla regional deja el sistema caído y los usuarios lejanos no cumplen la latencia.

### B. Varias zonas más una región pasiva de recuperación

* Good, because cubre fallas de región con poco costo.
* Bad, because los usuarios lejanos de la región activa no cumplen QA-2, QA-3 ni QA-10.
* Bad, because una conmutación lenta consume el presupuesto de QA-4.

### C. Región primaria con réplicas de lectura en todas las regiones

* Good, because mejora la latencia de lectura.
* Bad, because las escrituras siguen siendo remotas y los datos personales se replican en todas las regiones (CON-3).

### D. Región de origen por usuario

* Good, because satisface los cinco drivers.
* Bad, because es la opción más compleja de construir y operar.

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 1, [iteration-1-structure](../01-add/iteration-1-structure.md) |
| Drivers | QA-4, QA-5, CON-3 (considerados: QA-2, QA-3, QA-10) |
| Vistas afectadas | [deployment-view](../02-views/deployment-view.md) |
| Specs | `specs/openapi/` |
| ADRs relacionadas | [0001](0001-nucleo-modular-con-procesos-separados.md), [0003](0003-almacen-analitico-separado.md) |
| Código del prototipo | `prototype/` |
