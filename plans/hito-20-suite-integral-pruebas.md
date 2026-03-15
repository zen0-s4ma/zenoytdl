# ExecPlan — Hito 20 Suite de pruebas integral

## 1. Título y objetivo
Consolidar la batería histórica 0–19 en una suite integral verificable para Hito 20, sin introducir semántica de negocio nueva.

## 2. Contexto
El roadmap define Hito 20 como red de seguridad transversal antes de priorizar UX.

## 3. Supuestos
- Hitos 0–19 están implementados y con pruebas existentes.
- El entorno de CI/local puede ejecutar pytest por capas y por marcador.

## 4. Restricciones
- No cambiar semántica de dominio.
- Mantener compatibilidad con `test-zenoytdl.ps1`.
- Mantener reproducibilidad (E2E controlado con comprobación real opcional).

## 5. Diseño propuesto
- Añadir una pirámide específica H20 (`unit/integration/e2e/regression`) enfocada a consistencia de suite y contratos cruzados.
- Actualizar documentación de criterios y comandos para incorporar la batería H20.
- Extender script operativo PowerShell y Makefile con ejecución focalizada H20.

## 6. Pasos de implementación
1. Auditar cobertura actual 0–19 y huecos de consolidación.
2. Implementar pruebas H20 por nivel.
3. Actualizar comandos operativos/documentación.
4. Ejecutar batería focalizada y regresión acumulada.

## 7. Pruebas previstas
- `python -m ruff check src tests`
- `python -m pytest tests/unit/test_hito20_integral_suite.py`
- `python -m pytest tests/integration/test_hito20_integral_integration.py`
- `python -m pytest tests/e2e/test_hito20_integral_flow.py`
- `python -m pytest tests/regression/test_hito20_integral_suite_regression.py`
- `python -m pytest tests/regression -m regression`

## 8. Riesgos y mitigaciones
- Riesgo: dependencia de binario real `ytdl-sub` no disponible en todos los entornos.
  - Mitigación: prueba real opcional con `skip` explícito.

## 9. Log de progreso
- [x] Auditoría inicial de suite.
- [x] Pruebas H20 añadidas.
- [x] Documentación/comandos actualizados.
- [x] Ejecución final completa acumulada.

## 10. Decisiones tomadas
- Se reforzó cobertura de integración transversal vía API + persistencia + cola + caché.
- Se mantuvo enfoque determinista usando entorno controlado para E2E.

## 11. Criterio de cierre
Hito cerrado solo con batería H20 y regresión acumulada 0–20 en verde.
