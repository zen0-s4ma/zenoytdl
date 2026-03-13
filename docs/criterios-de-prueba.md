# Criterios de prueba en Zenoytdl

## Tipos de prueba
- Unitarias
- Integración
- Funcionales / E2E
- Regresión
- Rendimiento
- Resiliencia
- Validación de configuración

## Comandos mínimos operativos (Hito 0 en curso)
- Lint: `python -m ruff check src tests`
- Unitarias: `python -m pytest tests/unit -m unit`
- Integración: `python -m pytest tests/integration -m integration`
- E2E: `python -m pytest tests/e2e -m e2e`
- Regresión acumulada: `python -m pytest tests/regression -m regression`

Detalle operativo ampliado: `docs/operacion-comandos.md`.

## Regla de cierre de hito
Un hito no está cerrado hasta pasar:
1. pruebas específicas del hito,
2. regresión acumulada desde Hito 0,
3. validaciones de configuración relevantes,
4. controles de resiliencia aplicables.

## Regla de README
Solo después del cierre real del hito se actualiza el `README.md`. No antes.

## Datos de prueba
Usar `tests/fixtures/valid`, `tests/fixtures/invalid` y snapshots controlados.


## Criterios específicos para colas y caché (Hitos 17-18)
Estados oficiales a validar en pruebas: `pending`, `running`, `success`, `retry`, `dead_letter`, `cancelled`.

Cobertura mínima obligatoria de regresión:
1. flujo de éxito (`pending -> running -> success`),
2. flujo con reintento (`running -> retry -> pending`),
3. agotamiento de reintentos y paso a `dead_letter`,
4. cancelación en `pending` y en `running`,
5. deduplicación por clave de item/firma y por existencia de job activo.

Criterios de aceptación de estas pruebas:
- no hay transiciones inválidas ni reapertura de estados terminales;
- `attempts` incrementa de forma consistente por ejecución real;
- los casos de deduplicación no crean jobs duplicados en `pending|running|retry`.
