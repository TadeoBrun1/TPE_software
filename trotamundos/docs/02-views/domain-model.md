# Modelo de dominio

**Tipo:** Soporte (vocabulario)
**Actualizada en la iteración:** 2 (vocabulario refinado)
**Mantiene:** Ambos. **Estado:** BORRADOR (propuesta inicial a discutir)

## 1. Propósito

Fijar el vocabulario del dominio antes de las iteraciones, para que las dos personas hablen de las mismas cosas.

## 2. Diagrama

```mermaid
classDiagram
    class Usuario {
        id
        email
        idioma
        regionDeOrigen
    }
    class Viaje {
        id
        nombre
        estado : activo | archivado
        fechaInicio
        fechaFin
        archivadoEn
    }
    class Reserva {
        id
        tipo : vuelo | hotel | auto | tren | autobús
        codigoDelProveedor
        estado : confirmada | modificada | cancelada | pendiente
        origen : correo | tercero | manual
        camposEditadosPorUsuario
        version
    }
    class PanelDeUsuario {
        usuario
        version
        viajesActivos
    }
    class Remitente {
        direccion
        permitido
    }
    class CuentaDeCorreo {
        proveedor
        autorizacion
    }
    class Comparticion {
        permiso
    }
    class Proveedor {
        nombre
        tipoDeTransporte
    }

    class Vinculacion {
        id
        estadoAutorizacion
        version
        regionDeOrigen
    }
    class Suscripcion {
        idExterno
        proveedor
        vencimiento
        estado
    }
    class CursorSincronizacion {
        valorOpaco
        version
    }
    class CasoPendiente {
        id
        motivo
        estado
    }
    Usuario "1" --> "*" Vinculacion : autoriza
    Vinculacion "1" --> "0..1" CuentaDeCorreo : correo opcional
    Vinculacion "1" --> "0..*" Suscripcion : tiene avisos
    Vinculacion "1" --> "0..*" CursorSincronizacion : avance por flujo
    Vinculacion "1" --> "0..*" CasoPendiente : genera
    Usuario "1" --> "1" PanelDeUsuario : se lee mediante
    Usuario "1" --> "*" Viaje : tiene
    Viaje "1" --> "*" Reserva : agrupa
    Usuario "1" --> "*" CuentaDeCorreo : vincula
    Usuario "1" --> "*" Remitente : administra lista
    Reserva "*" --> "1" Proveedor : proviene de
    Viaje "1" --> "*" Comparticion : se comparte mediante
    Comparticion "*" --> "1" Usuario : con una persona designada
```

## 3. Elementos

| Elemento | Descripción |
|---|---|
| Usuario | Viajero con cuenta en la plataforma. Su región de origen decide dónde se guardan sus datos (ADR-0003) |
| Viaje | Agrupación de reservas. Está completo cuando pasó la fecha de su última reserva más 2 días; una tarea diaria lo archiva y lo elimina un año después (ADR-0045) |
| Reserva | Hotel, auto, vuelo, tren o autobús; puede venir de correo, de un tercero o de carga manual. Registra qué campos editó el usuario: las novedades cambian los del proveedor y conservan los del usuario (ADR-0044). Si no se puede asociar a un viaje, queda en estado `pendiente` de resolución. Agregar un medio de transporte es agregar un valor a `tipo` y un adaptador (QA-9) |
| PanelDeUsuario | Vista precalculada del panel (`panel_por_usuario`), con la versión del último cambio. No es una entidad de negocio: es una copia para leer, reconstruible desde viajes y reservas (ADR-0040) |
| CuentaDeCorreo | Buzón vinculado con autorización del usuario |
| Remitente | Remitente de una whitelist |
| Comparticion | Permiso de un viaje para una persona designada |
| Proveedor | Aerolínea, hotel, rentadora u otro |
| Vinculacion | Relación autorizada entre usuario y cuenta o proveedor. Estado y versión autoritativos en el núcleo; ingesta conserva referencias técnicas |
| Suscripcion | Registro técnico de avisos, con identificador externo, vencimiento y estado. Ingesta administra su ciclo; entrada global tiene una proyección mínima de región |
| CursorSincronizacion | Posición opaca por flujo o carpeta, confirmada junto con resultados y outbox en ingesta; no es una versión de reserva |
| CasoPendiente | Novedad o fallo que necesita resolución; conserva motivo y evidencia mínima. Una ambigüedad de dominio pertenece al núcleo y un fallo de extracción a ingesta |

Vinculación forma parte del vocabulario funcional; suscripción, cursor y caso técnico son conceptos de soporte de
integración, no nuevos agregados obligatorios del dominio de viajes. `eventId` identifica un mensaje y no sustituye
la identidad de reserva ni del caso. Ver [contrato de ingesta](../../specs/ingestion-contract.md).

## 4. Preguntas abiertas

- ¿La persona con quien se comparte tiene cuenta propia?
- ¿"Origen" de la reserva (correo, tercero, manual) se modela como atributo o como entidad? En la iteración 1 queda como atributo.
