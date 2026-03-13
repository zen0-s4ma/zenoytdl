# ExecPlan — Hito 0: Preparación de base para arrancar

## 1. Título y objetivo
Fortalecer la base técnica mínima del core para arrancar sin deuda inicial, manteniendo alcance estricto de Hito 0.

## 2. Contexto
`hitos-and-test.md` define Hito 0 como preparación de stack, estructura, convenciones, tooling y smoke checks, sin funcionalidad de negocio.

## 3. Supuestos
- Se mantiene Python como stack inicial del core.
- No se avanza a decisiones de runtime container final (Hito 1+).
- No se cierra el hito sin pruebas y regresión acumulada en verde.

## 4. Restricciones
- No introducir lógica de negocio.
- No adelantar features de Hito 1 en adelante.
- No actualizar README como hito cerrado de forma prematura.

## 5. Diseño propuesto
- Añadir utilidades base de entorno para:
  - resolución de workspace/path,
  - nivel de logging,
  - carga mínima de variables de entorno.
- Mantener entrypoint de bootstrap como smoke operativo.
- Añadir prueba de estructura base del repositorio por capas.

## 6. Pasos de implementación
1. Crear módulo de utilidades base de entorno/paths/logging.
2. Añadir tests unitarios de esas utilidades.
3. Añadir prueba de estructura base para comprobar layout por capas.
4. Ejecutar lint + pruebas unitarias, integración, e2e y regresión Hito 0.

## 7. Pruebas previstas
- `python -m ruff check src tests`
- `python -m pytest tests/unit -m unit`
- `python -m pytest tests/integration -m integration`
- `python -m pytest tests/e2e -m e2e`
- `python -m pytest tests/regression -m regression`

## 8. Riesgos y mitigaciones
- Riesgo: ampliar alcance hacia Hito 1.
  - Mitigación: limitar cambios a bootstrap, utilidades base y pruebas de base.
- Riesgo: romper smoke existente.
  - Mitigación: mantener compatibilidad con CLI actual y reforzar tests.

## 9. Log de progreso
- [x] Diagnóstico inicial de cobertura Hito 0.
- [ ] Implementación y pruebas.
- [ ] Validación final y veredicto de cierre.

## 10. Decisiones tomadas
- Se crea este ExecPlan porque el trabajo es multietapa y transversal (src + tests + planes).
- Se prioriza cobertura de utilidades base faltantes detectadas en plan de pruebas de Hito 0.

## 11. Criterio de cierre
Para considerar Hito 0 cerrable:
1. Checklist de Hito 0 implementado sin deuda crítica.
2. Pruebas del hito en verde.
3. Regresión acumulada Hito 0 en verde.
4. Sin bloqueantes abiertos.
5. Recién entonces, evaluar actualización de README.
