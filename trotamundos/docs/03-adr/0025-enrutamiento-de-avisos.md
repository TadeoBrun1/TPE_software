---
status: "proposed"
date: 2026-10-28
decision-makers: "Tomas Lateana; revisión cruzada pendiente en PR #4"
consulted: "Revisión de Tadeo Brun y asistencia de ChatGPT/Codex"
---

# Resolver la región de los avisos mediante un directorio mínimo

## Context and Problem Statement

Una notificación de correo o proveedor puede identificar una suscripción sin incluir usuario ni región. La entrada
global necesita elegir la región antes de llegar al Gateway regional. Confiar en una región declarada por el
remitente permitiría desviar tráfico; difundir el aviso expondría metadatos y multiplicaría carga. El acceso debe
respetar la entrada global y el Gateway de ADR-0003 y ADR-0004.

## Decision Drivers

* RF-03 y QA-1: recibir y encaminar novedades a tiempo
* QA-6: conservar identidad y evitar duplicar aplicación
* QA-8: verificar origen y minimizar datos
* ADR-0003 y ADR-0004: región de origen y entrada regional

## Considered Options

* A. URL pública directa de ingesta por región
* B. Difusión del aviso a todas las regiones
* C. Directorio mínimo de suscripciones en la entrada global

## Decision Outcome

Chosen option: **C. Directorio mínimo de suscripciones en la entrada global**. Registrar antes de habilitar avisos una asociación
proveedor + identificador de suscripción → vinculación + región + versión + estado. El núcleo es autoridad de la
vinculación; el directorio mantiene una proyección de enrutamiento, sin cuerpos de correo ni tokens de acceso.
La entrada valida el origen conforme al protocolo externo; el Gateway y receptor comprueban vigencia y repeticiones.
El receptor persiste trabajo antes de confirmar recepción. Un identificador desconocido no se difunde: se responde
según protocolo, se limita tráfico y se registra el incidente mínimo. Un fallo temporal usa respuesta reintentable
y reconciliación posterior. Cambiar región requiere coordinar versión y renovación de suscripción.

### Consequences

* Good, because ubica una sola región sin confiar en una región no verificada ni exponer directamente ingesta.
* Bad, because agrega una dependencia compartida y metadatos protegidos; una caída puede consumir el presupuesto de frescura.
* Bad, because la autenticidad concreta depende del proveedor; conocer un identificador no autentica por sí solo el aviso.

### Confirmation

Probar suscripción válida, identificador desconocido, aviso repetido, firma inválida, región cambiada y directorio
indisponible. Confirmar recepción solo tras persistencia; comprobar recuperación por cursor sin difusión global.

## Pros and Cons of the Options

### A. URL pública directa de ingesta por región

* Good, because reduce un salto y permite seleccionar región al crear la URL.
* Bad, because expone ingesta fuera de la entrada acordada y complica controles y migración de región.

### B. Difusión del aviso a todas las regiones

* Good, because evita consultar un directorio previo.
* Bad, because multiplica tráfico y datos entre regiones y obliga a deduplicar en todos los destinos.

### C. Directorio mínimo de suscripciones en la entrada global

* Good, because resuelve un único destino con metadatos mínimos y control de vigencia.
* Bad, because requiere disponibilidad, actualización coordinada y protección del directorio.

## More Information

[Contrato detallado](../../specs/notification-routing.md) · [Vista](../02-views/ingestion-view.md).
