# Vista de módulos

**Tipo:** Módulos (estática)
**Actualizada en la iteración:** 2 (refinamiento propuesto)
**Mantiene:** Ambos
**Estado:** propuesta de refinamiento de ingesta y asistencia, para revisión con iteración 3.

## 1. Propósito

Mostrar cómo se organiza el código en módulos y qué módulo puede usar a cuál. Sirve para razonar sobre
modificabilidad y para repartir el trabajo.

## 2. Presentación primaria

```mermaid
flowchart TD
    subgraph Nucleo["Núcleo"]
        API["api<br/>(controladores REST)"]
        VIA["viajes<br/>(agrupación y ciclo de vida)"]
        RES["reservas"]
        USR["usuarios<br/>(región, idioma, correos, remitentes)"]
        COM["comparticion"]
        SUS["suscriptor-novedades"]
        PUB["publicador-eventos"]
        ASI["asistencia saliente"]
        AGE["adaptador de agencia"]
    end

    subgraph Ingesta["Ingesta"]
        PLA["planificador"]
        COO["coordinador"]
        GES["gestor de vinculaciones"]
        ADA["adaptadores de acceso"]
        REC["receptor de avisos"]
        REG["registro de sincronización"]
        PRO["procesador por etapas"]
        PNV["publicador de novedades"]
    end

    RRG["resolución regional en entrada global"]

    CON["contratos<br/>(generados desde specs/)"]

    API --> VIA
    API --> RES
    API --> USR
    API --> COM
    SUS --> RES
    RES --> VIA
    VIA --> PUB
    RES --> PUB
    COM --> VIA

    API --> ASI
    ASI --> AGE
    ASI --> PUB
    ASI --> CON
    PLA --> COO
    COO --> GES
    COO --> ADA
    COO --> REG
    ADA --> PRO
    PRO --> REG
    REC --> REG
    REC --> GES
    PNV --> REG
    RRG --> CON

    SUS --> CON
    PUB --> CON
    PNV --> CON
```

Leyenda: la flecha significa "puede usar".

## 3. Catálogo de elementos

| Módulo | Responsabilidad | Directorio en `prototype/` |
|---|---|---|
| núcleo/api | Expone la API de itinerarios definida en `specs/openapi/` | `nucleo/api` |
| núcleo/viajes | Agrupa reservas por viaje; tarea programada que archiva viajes completados (RF-05) | `nucleo/viajes` |
| núcleo/reservas | Alta, cambio y baja de reservas; reservas pendientes de resolución | `nucleo/reservas` |
| núcleo/usuarios | Región de origen, idioma, cuentas de correo vinculadas y remitentes permitidos | `nucleo/usuarios` |
| núcleo/comparticion | Personas designadas por viaje (iteración 4) | `nucleo/comparticion` |
| núcleo/suscriptor-novedades | Recibe novedades del broker y las pasa a reservas | `nucleo/mensajeria` |
| núcleo/publicador-eventos | Publica los eventos de dominio de cada cambio confirmado | `nucleo/mensajeria` |
| núcleo/asistencia | Autoriza asistencia, conserva seguimiento y limita trabajadores salientes | `nucleo/asistencia` |
| núcleo/adaptador-agencia | Implementa el puerto de agencia, con resultado incierto e idempotencia | `nucleo/asistencia/adaptadores` |
| ingesta/planificador | Reconciliación por prioridad y cuota; agenda renovación de suscripciones | `ingesta/planificacion` |
| ingesta/coordinador | Ejecuta trabajo con exclusión por vinculación | `ingesta/coordinacion` |
| ingesta/gestor-vinculaciones | Vigencia de autorizaciones y estado técnico de suscripciones | `ingesta/vinculaciones` |
| ingesta/adaptadores-acceso | APIs, paginación y contratos externos por proveedor | `ingesta/adaptadores` |
| ingesta/receptor-avisos | Persiste trabajo antes de confirmar recepción | `ingesta/avisos` |
| ingesta/procesador | Selección, extracción, modelo canónico y validación | `ingesta/procesamiento` |
| ingesta/registro-sincronizacion | Cursores, resultados, casos pendientes y outbox | `ingesta/persistencia` |
| ingesta/publicador-novedades | Publica novedades con identidad estable y confirma envío | `ingesta/mensajeria` |
| entrada/resolucion-regional | Directorio mínimo que resuelve suscripción y región antes del Gateway | `entrada/enrutamiento` |
| contratos | Tipos generados a partir de `specs/`; único código que comparten núcleo e ingesta | `contratos/` |

## 4. Reglas de dependencia

* El núcleo y la ingesta **solo comparten** el módulo `contratos`. Ninguno importa código del otro.
* Un adaptador no depende de otro adaptador: agregar trenes es agregar un adaptador y un valor al tipo de reserva.
* Los módulos de dominio del núcleo (viajes, reservas, usuarios, comparticion) no dependen de `api` ni de la
  mensajería.
* Los adaptadores de mensajería (publicadores y consumidores) conocen el broker; los módulos de dominio usan puertos.
* Resolución regional pertenece a entrada global, no al dominio ni al procesador de ingesta.
* Asistencia invoca su puerto saliente con recursos acotados y no importa código de ingesta.
* Los directorios de la tabla son organización propuesta; no afirman código ya implementado.

## 5. Rationale

| Decisión | ADR |
|---|---|
| Núcleo modular separado de la ingesta | [0001](../03-adr/0001-nucleo-modular-con-procesos-separados.md) |
| Adaptador por proveedor y modelo canónico | [0001](../03-adr/0001-nucleo-modular-con-procesos-separados.md) |
| Comunicación por mensajes con contrato | [0002](../03-adr/0002-mensajeria-persistente-con-publicacion-suscripcion.md) |

## 6. Drivers que sustenta

| Driver | Cómo lo sustenta |
|---|---|
| QA-9 Evolucionabilidad | Un medio de transporte nuevo se agrega con un adaptador nuevo, sin tocar los existentes (táctica *restringir dependencias*) |
| RF-05 | El ciclo de vida del viaje vive en un solo módulo del núcleo |

## 7. Vistas relacionadas

[Componentes y conectores](cc-view.md) · [Despliegue](deployment-view.md)
