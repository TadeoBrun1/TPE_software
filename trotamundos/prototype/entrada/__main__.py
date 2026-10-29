"""`python -m entrada` levanta la entrada global con uvicorn."""
import os

import uvicorn

from entrada.app import desde_entorno

if __name__ == "__main__":
    uvicorn.run(desde_entorno().app, host="0.0.0.0", port=int(os.environ.get("PUERTO", "8000")), log_level="warning")
