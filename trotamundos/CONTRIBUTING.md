# Cómo trabajamos

Dos personas, iteraciones ADD en paralelo. Estas reglas existen para no pisarnos y para que la Wiki
muestre el trabajo de cada integrante.

## 1. Ramas y Pull Requests

- `main` siempre refleja lo que ya revisamos entre los dos.
- Una rama por tema: `iter-1/contexto`, `iter-2/ingesta`, `iter-3/consulta`, `adr/0021-cola-de-mensajes`, `proto/ingesta`.
- Todo cambio entra por Pull Request y lo revisa **la otra persona** (alcanza con 1 aprobación).
- Commits con el formato `tipo(alcance): descripción`, por ejemplo `docs(iter-2): agrega ADR-0021` o `feat(proto): consumer de correos`.
- Cada integrante hace sus commits con su propio usuario: es la evidencia de autoría que pide el enunciado.

## 2. Dueño de cada archivo

| Zona | Dueño | Regla |
|---|---|---|
| `docs/00-requirements/` | Ambos | Cambios solo por PR con revisión de ambos: son los drivers inmutables |
| `docs/01-add/iteration-1-*` | Ambos | Se hace en conjunto |
| `docs/01-add/iteration-2-*` | Integrante A | Solo A edita |
| `docs/01-add/iteration-3-*` | Integrante B | Solo B edita |
| `docs/01-add/iteration-4-*` | Ambos | Se hace en conjunto |
| `docs/02-views/*` y `docs/architecture.md` | **Compartido** | Ver la regla de elementos compartidos |
| `docs/03-adr/` | Quien crea la ADR | Respetar su bloque de numeración |
| `specs/` | Quien es dueño del servicio | Cambiar un contrato usado por el otro exige aviso (ver §4) |

## 3. Numeración de ADRs por bloques

Para que dos ramas paralelas no creen la misma ADR número 0007, cada iteración tiene su bloque:

| Iteración | Rango |
|---|---|
| 1 | 0001 – 0019 |
| 2 | 0020 – 0039 |
| 3 | 0040 – 0059 |
| 4 | 0060 – 0079 |
| Extra | 0080 en adelante |

Las ADRs se numeran en orden dentro de su bloque y **nunca se borran**: si una decisión cambia, la ADR vieja pasa a
`superseded by ADR-XXXX` y se crea una nueva.

## 4. Protocolo ante impactos entre iteraciones

El riesgo concreto: una decisión de la iteración 2 puede perjudicar lo que se está resolviendo en la 3, y al revés.

1. Si tu cambio toca un **elemento compartido** (contenedores de la iteración 1, modelo de dominio, un contrato en
   `specs/`, el bus de eventos, la base de datos común), antes de mergear anotá una fila en
   [docs/01-add/impact-log.md](docs/01-add/impact-log.md).
2. Avisá a la otra persona en el PR (mencionándola) y esperá su revisión.
3. Si el impacto es negativo, se resuelve con una ADR (que puede ser de cualquiera de los dos bloques) y se
   actualizan los documentos de las iteraciones afectadas.
4. Al cerrar cada iteración (paso 7 de ADD) se repasa el impact-log para confirmar que no quedó nada abierto.

Regla corta: **lo que es de una iteración se edita libre; lo que usa la otra persona se avisa.**

## 5. Spec-driven

1. Primero se escribe o actualiza el contrato en `specs/`. Si el contrato lo usan dos iteraciones, ambos acuerdan
   el formato antes de implementarlo.
2. Después se implementa en `prototype/`.
3. Cada servicio del prototipo indica en su README qué spec y qué ADRs implementa.

## 6. Uso de IA

Si usamos IA para producir un artefacto, se sigue el proceso de [ai/prompts.md](ai/prompts.md) (alternativas, decisión
humana, auditoría independiente y revisión cruzada), se agrega la etapa a su tabla de uso y el resultado se revisa a
mano antes del PR. Los dos integrantes entienden y pueden defender cada decisión: el paper mostró que la IA oscila
en decisiones críticas (por ejemplo monolito modular vs. microservicios), así que esas decisiones las confirma una
persona.
