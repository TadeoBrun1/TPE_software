# Imagen única del prototipo: cada servicio la usa con otro comando (`python -m nucleo`, `python -m puerta`, ...).
# El contexto de construcción es `trotamundos/`, para copiar también `specs/`: los contratos se leen de ahí.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app/prototype

COPY prototype/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY specs /app/specs
COPY prototype /app/prototype

RUN useradd --create-home trotamundos && mkdir -p /datos && chown trotamundos /datos
USER trotamundos
