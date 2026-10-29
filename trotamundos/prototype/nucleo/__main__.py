"""`python -m nucleo` levanta el núcleo de una región con uvicorn (configuración por variables de entorno)."""
import os

import uvicorn

from nucleo.app import desde_entorno

if __name__ == "__main__":
    nucleo = desde_entorno()
    uvicorn.run(nucleo.app, host="0.0.0.0", port=int(os.environ.get("PUERTO", "8000")), log_level="warning")
