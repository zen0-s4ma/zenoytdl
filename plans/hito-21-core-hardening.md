# ExecPlan — Hito 21 Core completo endurecido

## 1. Título y objetivo
Cerrar el core funcional de Zenoytdl endureciendo estabilidad operativa, ergonomía de errores y criterios de cierre, sin abrir superficies de TUI/GUI.

## 2. Contexto
Hito 21 es cierre del núcleo antes de Dockerización/empaquetado final. Debe consolidar módulos existentes (config, validación, traducción, compilación, ejecución, persistencia, caché, colas y API).

## 3. Supuestos
- Hito 20 está implementado y validado.
- El repositorio mantiene la separación por capas vigente.
- README solo se actualiza al cierre real verificado.

## 4. Restricciones
- Sin TUI/GUI web.
- Sin autenticación/multiusuario/frontend.
- Sin modificar lógica interna de ytdl-sub.

## 5. Diseño propuesto
1. Endurecer CLI con errores estructurados (`code` + `message`).
2. Añadir guard-rails en runtime de colas para rechazar configuraciones inválidas.
3. Añadir batería focalizada H21 (unit/integration/e2e/regression).
4. Sincronizar comandos operativos y runner PowerShell.
5. Dejar criterio explícito de “core completo” y límite con UX futura.

## 6. Pasos de implementación
1. Revisar warnings/deuda crítica en `src.api.cli` y runtime colas.
2. Aplicar cambios mínimos de robustez sin alterar semántica de negocio.
3. Crear tests H21 focalizados.
4. Actualizar `docs/criterios-de-prueba.md`, `docs/operacion-comandos.md`, `Makefile`, `test-zenoytdl.ps1`.
5. Ejecutar lint + batería H20 + H21 + regresión seleccionada.

## 7. Pruebas previstas
- `python -m ruff check src tests`
- `python -m pytest tests/unit/test_hito20_integral_suite.py tests/integration/test_hito20_integral_integration.py tests/e2e/test_hito20_integral_flow.py tests/regression/test_hito20_integral_suite_regression.py`
- `python -m pytest tests/unit/test_hito21_core_hardening.py tests/integration/test_hito21_core_hardening_integration.py tests/e2e/test_hito21_core_hardening_flow.py tests/regression/test_hito21_core_hardening_regression.py`
- `python -m pytest tests/regression -m regression`

## 8. Riesgos y mitigaciones
- Riesgo: romper contratos previos al endurecer runtime. Mitigación: mantener cambios acotados y cubrir con regresión.
- Riesgo: sobredocumentar cierre sin evidencia. Mitigación: listar comandos reales ejecutados y resultados.

## 9. Log de progreso
- [x] Auditoría inicial de deuda/warnings.
- [x] Cambios de endurecimiento en CLI y runtime.
- [x] Tests focalizados H21 añadidos.
- [x] Documentación y runner actualizados.
- [ ] Cierre final condicionado a batería completa verde 0–21.

## 10. Decisiones tomadas
- Se priorizó robustez y operabilidad (errores estructurados + validación de config runtime).
- No se amplió superficie de producto fuera del core.

## 11. Criterio de cierre
1. pruebas H21 en verde,
2. regresión acumulada 0–21 en verde,
3. sin bloqueantes core abiertos,
4. documentación sincronizada,
5. explicitación de frontera para proyecto separado TUI/GUI.
