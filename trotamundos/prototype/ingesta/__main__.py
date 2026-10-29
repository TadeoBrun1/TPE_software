"""`python -m ingesta` levanta la ingesta de una región con uvicorn."""
import os

import uvicorn

from ingesta.app import desde_entorno

if __name__ == "__main__":
    ingesta = desde_entorno()
    uvicorn.run(ingesta.app, host="0.0.0.0", port=int(os.environ.get("PUERTO", "8000")), log_level="warning")
