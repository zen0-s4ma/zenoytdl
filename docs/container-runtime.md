# Entorno de ejecución en contenedor (Linux)

## Layout /data
- `/data/config`
- `/data/cache`
- `/data/output`
- `/data/logs`

## Requisitos
- usuario no root si es posible
- permisos correctos sobre `/data`
- herramientas del runtime instaladas

## Arranque
- carga de configuración
- validación inicial
- bootstrap de persistencia
- arranque del servicio principal o cola

## Observación sobre README
La disponibilidad efectiva del runtime en contenedor solo debe reflejarse en el README cuando el hito correspondiente haya pasado build, pruebas y regresión acumulada.
