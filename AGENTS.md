# Zenoytdl Agents Guide

## Propósito del repositorio
Zenoytdl encapsula `ytdl-sub` para ofrecer una capa más simple, validable y operable para configuración, orquestación, persistencia y automatización.

## Estado del proyecto (obligatorio para agentes)
- El core del repositorio está cerrado en su primera etapa funcional (hitos 0–21).
- El trabajo futuro se trata como **evolución/extensión/endurecimiento adicional**, no como rediseño arbitrario desde cero.
- La arquitectura por capas actual es contractual; cualquier cambio debe justificar compatibilidad y no romper contratos estabilizados.
- TUI/GUI web no forman parte de este repositorio; cualquier interfaz visual futura debe mantenerse desacoplada del core.

## Qué debe hacer siempre un agente
- Leer primero este archivo y la documentación enlazada relevante.
- Tomar como fuentes obligatorias de contexto `README.md`, `docs/`, `examples/` y `tests/` antes de modificar comportamiento documentado.
- Respetar la arquitectura por capas.
- No saltarse contratos ni validaciones.
- Mantener el repositorio consistente con pruebas y documentación.
- Tratar `README.md` como documento gobernado por estado verificado.

## Layout clave
- `README.md`: visión integral del proyecto y estado verificado.
- `docs/`: arquitectura, contratos, SQLite, colas, runtime, pruebas y roadmap.
- `plans/`: planes de ejecución complejos por hito o característica.
- `examples/`: configuraciones de referencia.
- `tests/`: pruebas y fixtures.
- `.agents/skills/`: workflows reutilizables.
- `src/`: módulos por capa.

## Comandos esperados del proyecto
Como mínimo, cualquier agente debe dejar documentado:
- comando de lint
- comando de tests unitarios
- comando de integración
- comando e2e
- comando de regresión acumulada
- alternativa operativa en Windows PowerShell cuando `make` no esté disponible

## Done means
Un cambio sólo está terminado cuando:
1. cumple el contrato y la arquitectura,
2. pasa sus pruebas específicas,
3. no rompe regresión acumulada,
4. actualiza documentación afectada,
5. si cierra un hito o un bloque funcional relevante, actualiza también `README.md`.

## Regla crítica sobre README
`README.md` sólo debe reflejar capacidades verificadas por pruebas y sin bloqueantes abiertos.

Mientras un cambio está en curso:
- no marcar capacidades como disponibles si aún no están verificadas,
- no presentar prototipos o hipótesis como estado operativo real.

## Regla sobre hitos
- El roadmap vive en `docs/roadmap-hitos.md`.
- La numeración debe ser secuencial y estable.
- Si se añaden hitos, justificarlo explícitamente.
- No se puede avanzar al siguiente hito con regresiones abiertas del actual o anteriores.

## ExecPlans
Para tareas complejas o refactors significativos, usar un ExecPlan siguiendo `PLANS.md` y los documentos en `plans/`.

## Límites y restricciones
- No modificar la lógica interna de `ytdl-sub`; usar el contrato de integración.
- No introducir secretos reales en el repositorio.
- No crear dependencias nuevas sin justificación técnica clara.
- Mantener separación entre dominio, integración, persistencia, API y observabilidad.
- No inventar funcionalidad no implementada ni alterar contratos estabilizados sin plan y validación explícitos.

## Documentación que debe mantenerse sincronizada
Si cambia:
- configuración → actualizar `docs/contrato-yaml.md`
- integración → actualizar `docs/contrato-ytdl-sub.md`
- persistencia → actualizar `docs/esquema-sqlite.md`
- colas/caché → actualizar `docs/cola-y-cache.md`
- criterios de cierre → actualizar `docs/criterios-de-prueba.md` y `README.md` cuando corresponda
