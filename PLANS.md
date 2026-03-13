# Zenoytdl Execution Plans

## Finalidad
Este documento define el formato de ExecPlans del proyecto. Un ExecPlan es un documento vivo y autosuficiente para cambios complejos.

## Cuándo usarlo
Usar un ExecPlan cuando haya:
- una feature de varias etapas,
- un refactor significativo,
- incertidumbre técnica relevante,
- impacto transversal en varias capas,
- riesgo de regresión alto.

## Requisitos no negociables
- Debe ser autosuficiente para alguien sin contexto previo.
- Debe incluir pasos, pruebas, decisiones y riesgos.
- Debe actualizarse durante el trabajo.
- Debe dejar claro cuándo está terminado.
- Si el trabajo cierra un hito, debe incluir el paso final de validar regresión acumulada y actualizar el `README.md`.

## Plantilla mínima
### 1. Título y objetivo
### 2. Contexto
### 3. Supuestos
### 4. Restricciones
### 5. Diseño propuesto
### 6. Pasos de implementación
### 7. Pruebas previstas
### 8. Riesgos y mitigaciones
### 9. Log de progreso
### 10. Decisiones tomadas
### 11. Criterio de cierre

## Regla de README al cerrar un plan ligado a hito
Si el ExecPlan completa un hito, el paso final obligatorio es:
1. ejecutar pruebas del hito,
2. ejecutar regresión acumulada,
3. verificar ausencia de bloqueantes,
4. actualizar `README.md` para reflejar únicamente el estado ya verificado.
