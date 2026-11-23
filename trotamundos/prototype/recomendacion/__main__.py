"""`python -m recomendacion` levanta el proceso de recomendación de una región con uvicorn."""
import os

import uvicorn

from recomendacion.app import desde_entorno

if __name__ == "__main__":
    recomendacion = desde_entorno()
    uvicorn.run(recomendacion.app, host="0.0.0.0", port=int(os.environ.get("PUERTO", "8000")), log_level="warning")
