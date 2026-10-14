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

## Lo que no está claro del enunciado

El texto dice "en formato de Wiki (por ej., Github)". Puede significar la pestaña Wiki o simplemente documentación
en Markdown dentro de GitHub. **Conviene preguntárselo a los docentes antes de la primera entrega.**

## Cómo está preparado este repo para ambas lecturas

- **La fuente de verdad es `docs/`**, dentro del repo principal. Ahí está todo versionado junto al código y las specs,
  y se revisa con Pull Requests.
- La carpeta [`wiki/`](../wiki/) contiene `Home.md` y `_Sidebar.md` listos para copiar a la Wiki. Esas páginas
  funcionan como portada e índice y apuntan a `docs/` en el repo.
- Si los docentes exigen que el contenido viva en la pestaña Wiki, se copian ahí también las páginas de `docs/`
  (los diagramas Mermaid se ven igual).

## Pasos para publicar la portada en la Wiki

```bash
git clone https://github.com/<usuario>/trotamundos.wiki.git
cp trotamundos/wiki/Home.md trotamundos/wiki/_Sidebar.md trotamundos.wiki/
cd trotamundos.wiki
git add . && git commit -m "docs: portada de la wiki" && git push
```

Antes de publicar, reemplazar `<usuario>` por el usuario u organización real en los links de esas dos páginas.
