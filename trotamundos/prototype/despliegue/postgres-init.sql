-- Bases de una región (se ejecuta una vez, al crear el volumen de PostgreSQL).
-- Dos bases para el núcleo emulan dos nodos de la base particionada (ADR-0042): 256 particiones lógicas repartidas
-- entre ellos. Registro de auditoría, ingesta, identidad y push tienen su propio almacenamiento.
CREATE DATABASE nodo0;
CREATE DATABASE nodo1;
CREATE DATABASE auditoria;
CREATE DATABASE ingesta;
CREATE DATABASE identidad;
CREATE DATABASE push;
