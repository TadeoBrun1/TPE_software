# La Wiki de GitHub: qué es y cómo la usamos

## Qué es

Cada repositorio de GitHub puede tener una pestaña **Wiki**. Técnicamente es un segundo repositorio git, aparte del
principal, con la dirección `https://github.com/<usuario>/<repo>.wiki.git`. Contiene páginas en Markdown:

- `Home.md` es la portada.
- `_Sidebar.md` es el menú lateral que aparece en todas las páginas.
- Cada otro `.md` es una página.

Tiene su propio historial: cada edición queda registrada con autor y fecha. Eso sirve para mostrar la evolución del
trabajo y la labor de cada integrante, que es lo que pide el enunciado.

## Cómo activarla

1. En el repo: **Settings → Features → Wikis** (tildar).
2. Entrar a la pestaña **Wiki** y crear la primera página desde la web (`Create the first page`). El repositorio
   `.wiki.git` recién existe después de ese paso.
3. Desde ahí se puede editar en la web o clonar:
   ```bash
   git clone https://github.com/<usuario>/trotamundos.wiki.git
   ```

## Cómo la usamos

La Wiki está activa en https://github.com/TadeoBrun1/TPE_software/wiki.

- **La fuente de verdad es `docs/`**, dentro del repo principal: ahí está todo versionado junto a las specs y se
  revisa con Pull Requests.
- La Wiki es la portada e índice: `Home.md` (descripción breve e índices por sección) y `_Sidebar.md` (menú lateral).
  Sus links apuntan a la rama `main` del repo, así que muestran lo ya integrado.
- El proceso ADD está centralizado en una sola página, [01-add/ADD.md](01-add/ADD.md), con links a cada iteración.
- El estado del trabajo no va en la portada: se sigue en el [TEAM-LOG](../TEAM-LOG.md).
- La carpeta [`wiki/`](../wiki/) del repo guarda la versión vigente de `Home.md` y `_Sidebar.md`. Si cambian, se
  publican en la Wiki con:

```bash
git clone https://github.com/TadeoBrun1/TPE_software.wiki.git
cp TPE_software/trotamundos/wiki/Home.md TPE_software/trotamundos/wiki/_Sidebar.md TPE_software.wiki/
cd TPE_software.wiki
git add . && git commit -m "docs: actualiza portada y menú de la wiki" && git push
```
