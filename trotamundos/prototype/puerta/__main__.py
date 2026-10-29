"""`python -m puerta` levanta la puerta de entrada de una región con uvicorn."""
import os
import time

import uvicorn

from puerta.app import desde_entorno

if __name__ == "__main__":
    for intento in range(30):  # espera a que los proveedores de identidad publiquen sus claves
        try:
            puerta = desde_entorno()
            break
        except OSError:
            time.sleep(2)
    else:
        raise SystemExit("no se pudieron cargar las claves de los emisores")
    uvicorn.run(puerta.app, host="0.0.0.0", port=int(os.environ.get("PUERTO", "8000")), log_level="warning")
