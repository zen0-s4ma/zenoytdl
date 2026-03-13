# Criterios de prueba en Zenoytdl

## Tipos de prueba
- Unitarias
- Integración
- Funcionales / E2E
- Regresión
- Rendimiento
- Resiliencia
- Validación de configuración

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
