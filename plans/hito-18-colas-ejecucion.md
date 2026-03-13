# ExecPlan — Hito 18: Colas de ejecución continua

## Objetivo
Completar workers continuos con concurrencia limitada y parada limpia, respetando el modelo oficial de estados de job: `pending`, `running`, `success`, `retry`, `dead_letter`, `cancelled`.

## Pasos
1. Definir modelo de worker.
2. Implementar selección segura de jobs.
3. Registrar estados y logs.
4. Probar estrés e interrupciones.
5. Ejecutar regresión acumulada.
6. Actualizar README solo tras cierre real del hito.


## Contrato de estados y transiciones
Transiciones permitidas durante Hito 18:
- `pending -> running|cancelled`
- `running -> success|retry|cancelled|dead_letter`
- `retry -> pending|cancelled|dead_letter`

Estados terminales no reabribles: `success`, `dead_letter`, `cancelled`.

## Escenarios mínimos de regresión del hito
1. éxito de punta a punta,
2. reintento recuperable,
3. dead-letter por agotamiento de intentos,
4. cancelación controlada,
5. deduplicación sin creación de jobs activos duplicados.
