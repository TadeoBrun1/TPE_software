"""`python -m notificador` levanta el notificador de una región con uvicorn."""
import os

import uvicorn

from notificador.app import desde_entorno

if __name__ == "__main__":
    notificador = desde_entorno()
    uvicorn.run(notificador.app, host="0.0.0.0", port=int(os.environ.get("PUERTO", "8000")), log_level="warning")
