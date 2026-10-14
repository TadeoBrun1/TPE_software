# Modelo de dominio

**Tipo:** Soporte (vocabulario)
**Actualizada en la iteración:** Preparación
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
        region
    }
    class Viaje {
        id
        nombre
        estado
        fechaInicio
        fechaFin
    }
    class Reserva {
        id
        tipo
        proveedor
        estado
        origen
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
| Usuario | Viajero con cuenta en la plataforma |
| Viaje | Agrupación de reservas; se archiva al completarse |
| Reserva | Hotel, auto, vuelo, tren o autobús; puede venir de correo, de un tercero o de carga manual |
| CuentaDeCorreo | Buzón vinculado con autorización del usuario |
| Remitente | Remitente de una whitelist |
| Comparticion | Permiso de un viaje para una persona designada |
| Proveedor | Aerolínea, hotel, rentadora u otro |

## 4. Preguntas abiertas

- ¿La persona con quien se comparte tiene cuenta propia?
- ¿"Origen" de la reserva (correo, tercero, manual) se modela como atributo o como entidad?
