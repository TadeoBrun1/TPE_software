---
status: "proposed"
date: 2026-10-27
decision-makers: "Tadeo Brun, Tomas Lateana"
consulted: ""
informed: ""
---

# Arquitectura de referencia: clientes ricos web y móvil sobre una aplicación de servicios con puerta de entrada única

## Context and Problem Statement

Los viajeros usan Trotamundos desde la web y desde el celular, y el enunciado pide una interfaz rica que aproveche
capacidades nativas como el GPS. En la primera iteración de ADD hay que elegir la arquitectura de referencia que da
la forma general del sistema: qué tipo de clientes hay, cómo se comunican con el backend y por dónde entra el
tráfico.

## Decision Drivers

* CRN-1: estructura inicial del sistema.
* QA-10: interfaz rica con capacidades nativas (GPS) y operación multirregión.
* QA-3: primer contenido en móvil en menos de 1,4 s.
* QA-4: el punto de entrada no puede ser un punto único de falla.
* QA-5: absorber picos y repartir carga entre instancias.

## Considered Options

* A. Aplicación web renderizada en el servidor, y una app móvil híbrida que la muestra dentro de una vista web
* B. Clientes ricos (aplicación web de una sola página y app móvil nativa) que consumen una API a través de una
  puerta de entrada única (*API Gateway*)
* C. Como B, pero con un backend específico por tipo de cliente (*Backend for Frontend*)
* D. Clientes que llaman directamente a cada proceso del backend

## Decision Outcome

Chosen option: "B. Clientes ricos con puerta de entrada única", because la app nativa da acceso al GPS y puede
mostrar contenido guardado en el dispositivo apenas se abre (QA-10, QA-3), y la puerta de entrada concentra en un solo
lugar el enrutamiento por región de origen y el balanceo entre instancias (ADR-0004).

Se combinan dos arquitecturas de referencia de la guía de Microsoft que usa el libro de ADD (Cervantes y Kazman):

* **Aplicación de cliente rico / aplicación móvil** en el lado del usuario: aplicación web de una sola página y app
  móvil nativa, con caché local del último itinerario.
* **Aplicación de servicios** en el backend: el núcleo expone una API de itinerarios (`specs/openapi/`) y no genera
  pantallas.

Responsabilidades de la **puerta de entrada**:

* Ser el único punto de entrada desde Internet; los procesos internos no quedan expuestos.
* Validar la identidad de quien llama (el mecanismo concreto de autenticación se decide en la iteración 4).
* Dirigir cada solicitud a la región de origen del usuario y repartir la carga entre instancias sanas.
* Limitar el tráfico excesivo por cliente.

La puerta de entrada se despliega con varias instancias en varias zonas (ADR-0004).

Patrones y tácticas que aplica:

| Patrón o táctica (Bass) | Cómo se aplica | Driver |
|---|---|---|
| Arquitecturas de referencia de cliente rico, aplicación móvil y aplicación de servicios | Forma general del sistema | CRN-1, QA-10 |
| Patrón *API Gateway* | Punto único de entrada con enrutamiento y validación | QA-4, QA-5, QA-10 |
| Táctica *mantener múltiples copias de los datos* (caché en el cliente) | La app muestra el último itinerario guardado mientras pide el actualizado | QA-3 |
| Táctica *redundancia activa* (disponibilidad) | Varias instancias de la puerta de entrada en varias zonas | QA-4 |
| Táctica *administrar las solicitudes de trabajo* (performance) | Límite de tráfico por cliente en la puerta de entrada | QA-5 |

### Consequences

* Good, because la app móvil puede usar GPS y mostrar contenido sin esperar al servidor.
* Good, because los clientes no conocen la estructura interna: el backend puede cambiar sin cambiar los clientes.
* Good, because el enrutamiento por región y el balanceo quedan en un solo lugar.
* Bad, because hay que mantener dos clientes (web y móvil nativa).
* Bad, because la puerta de entrada es un salto más en cada solicitud y debe ser redundante.

### Confirmation

Revisión de las vistas [C&C](../02-views/cc-view.md) y de [despliegue](../02-views/deployment-view.md): ningún cliente
accede a un proceso interno sin pasar por la puerta de entrada. La API de itinerarios está definida en
`specs/openapi/`.

## Pros and Cons of the Options

### A. Web renderizada en el servidor y app híbrida

* Good, because hay un solo código de interfaz.
* Bad, because la vista web dentro de la app limita el acceso a capacidades nativas como el GPS (QA-10).
* Bad, because cada apertura necesita al servidor para mostrar algo, lo que dificulta QA-3.

### B. Clientes ricos con puerta de entrada única

* Good, because cumple QA-3 y QA-10 y centraliza el acceso.
* Bad, because hay dos clientes que mantener.

### C. Clientes ricos con un *Backend for Frontend* por cliente

* Good, because cada cliente recibe exactamente los datos que necesita, lo que puede ayudar a QA-2 y QA-3.
* Bad, because agrega un proceso por cliente sin que todavía haya evidencia de que la API común no alcance.
* Neutral, because puede incorporarse en la iteración 3 si el análisis de QA-2 o QA-3 lo justifica.

### D. Clientes que llaman directamente a cada proceso

* Good, because no agrega un salto intermedio.
* Bad, because expone la estructura interna, y cualquier cambio de backend rompe a los clientes.
* Bad, because no hay un lugar único para enrutar por región, autenticar ni limitar el tráfico.

## More Information

### Trazabilidad

| Elemento | Enlace |
|---|---|
| Iteración ADD | 1, [iteration-1-structure](../01-add/iteration-1-structure.md) |
| Drivers | CRN-1, QA-10, QA-3, QA-4, QA-5 |
| Vistas afectadas | [cc-view](../02-views/cc-view.md), [deployment-view](../02-views/deployment-view.md) |
| Specs | `specs/openapi/` |
| ADRs relacionadas | [0001](0001-nucleo-modular-con-procesos-separados.md), [0004](0004-despliegue-por-regiones-con-region-de-origen.md) |
| Código del prototipo | `prototype/` |
