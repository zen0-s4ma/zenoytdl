# Modelo de Colas y Caché en Zenoytdl

## Jobs y estados
Estados sugeridos:
- pending
- running
- success
- failure
- skipped
- cancelled

## Colas
- cola simple inicial
- procesamiento continuo posterior
- deduplicación obligatoria
- parada segura

## Caché
- firma por item y configuración efectiva
- cache persistente
- invalidación selectiva
- métricas de hit/miss

## Regla de validación por hito
Cada avance en cola o caché debe venir con pruebas específicas y regresión acumulada. Solo al cerrar el hito correspondiente puede reflejarse en el README como capacidad confirmada.
