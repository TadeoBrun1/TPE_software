"""`python -m identidad` levanta el proveedor de identidad de una región con uvicorn."""
import os

import uvicorn

from identidad.app import desde_entorno

if __name__ == "__main__":
    proveedor = desde_entorno()
    uvicorn.run(proveedor.app, host="0.0.0.0", port=int(os.environ.get("PUERTO", "8000")), log_level="warning")
