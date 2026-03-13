# Zenoytdl Agents Guide

## Propósito del repositorio
Zenoytdl encapsula `ytdl-sub` para ofrecer una capa más simple, validable y operable para configuración, orquestación, persistencia y automatización.

## Qué debe hacer siempre un agente
- Leer primero este archivo y la documentación enlazada relevante.
- Respetar la arquitectura por capas.
- No saltarse contratos ni validaciones.
- Mantener el repositorio consistente con pruebas y documentación.
- Tratar `README.md` como documento gobernado por hitos cerrados.

## Layout clave
- `README.md`: visión integral del proyecto y estado verificado.
- `docs/`: arquitectura, contratos, SQLite, colas, runtime, pruebas y roadmap.
- `plans/`: planes de ejecución complejos por hito o característica.
- `examples/`: configuraciones de referencia.
- `tests/`: pruebas y fixtures.
- `.agents/skills/`: workflows reutilizables.
- `src/`: módulos por capa.

## Comandos esperados del proyecto
Los comandos definitivos se fijarán al cerrar Hito 0. Como mínimo, cualquier agente debe dejar documentado:
- comando de lint
- comando de tests unitarios
- comando de integración
- comando e2e
- comando de regresión acumulada

## Done means
Un cambio sólo está terminado cuando:
1. cumple el contrato y la arquitectura,
2. pasa sus pruebas específicas,
3. no rompe regresión acumulada,
4. actualiza documentación afectada,
5. si cierra un hito, actualiza también `README.md`.

## Regla crítica sobre README
`README.md` **no se actualiza durante la ejecución parcial de un hito**.

Solo se permite su actualización cuando el hito queda formalmente cerrado, lo que exige:
- entregables implementados,
- pruebas del hito en verde,
- batería de regresión acumulada en verde,
- ausencia de defectos bloqueantes abiertos.

Mientras un hito está en curso:
- no marcarlo como completado,
- no mover estado del roadmap a “hecho”,
- no documentar funcionalidades como disponibles si aún no están verificadas.

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

## Documentación que debe mantenerse sincronizada
Si cambia:
- configuración → actualizar `docs/contrato-yaml.md`
- integración → actualizar `docs/contrato-ytdl-sub.md`
- persistencia → actualizar `docs/esquema-sqlite.md`
- colas/caché → actualizar `docs/cola-y-cache.md`
- criterios de cierre → actualizar `docs/criterios-de-prueba.md` y `README.md` cuando corresponda
