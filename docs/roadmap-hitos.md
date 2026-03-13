# Roadmap de desarrollo por hitos

## Regla global de cierre de hito
Un hito **no se considera completado** hasta que:
1. están implementados sus entregables,
2. pasan las pruebas específicas del hito,
3. pasa la batería de regresión acumulada desde Hito 0 hasta el hito actual,
4. no hay defectos bloqueantes abiertos,
5. se actualiza `README.md` para reflejar únicamente el estado ya verificado.

## Regla global de README
Durante un hito en curso, `README.md` no debe marcar ese hito como completado ni documentar como disponibles capacidades que aún no han superado la validación final.

## Hito 0 — Preparación de base para arrancar
Objetivo: preparar estructura, stack, herramientas, convenciones y smoke tests.
Pruebas: bootstrap en limpio, scripts base, test runner operativo.
Cierre documental: actualizar `README.md` solo cuando Hito 0 pase sus pruebas y regresión acumulada aplicable.

## Hito 1 — Preparación de contenedor de desarrollo
Objetivo: runtime Linux, layout `/data`, usuario y volúmenes.
Pruebas: imagen construye, contenedor arranca y respeta rutas.
Cierre documental: sólo tras validación completa.

## Hito 2 — Modelado del dominio interno
Objetivo: definir entidades, invariantes y errores de dominio.
Pruebas: casos válidos e inválidos.

## Hito 3 — Diseño del contrato de configuración YAML
Objetivo: formalizar esquemas, relaciones y contrato.
Pruebas: fixtures válidos/ inválidos y sincronía entre archivos.

## Hito 4 — Parseo y carga de configuración
Objetivo: cargar YAMLs a modelo interno.
Pruebas: parseo correcto, errores claros y carga integrada.

## Hito 5 — Validación estructural y semántica
Objetivo: detectar configuraciones inconsistentes o ambiguas.
Pruebas: referencias faltantes, tipos, rangos y campos desconocidos.

## Hito 6 — Herencia y resolución perfil→suscripción
Objetivo: configuración efectiva por suscripción.
Pruebas: herencias, defaults y overrides básicos.

## Hito 7 — Overrides y flujos de anulación
Objetivo: mezcla avanzada y trazabilidad de procedencia.
Pruebas: conflictos y reglas de resolución.

## Hito 8 — Modelado de post-procesamiento
Objetivo: representar etapas posteriores a descarga.
Pruebas: inclusión correcta en jobs y contrato.

## Hito 9 — Contrato de integración con ytdl-sub
Objetivo: fuente de verdad del acoplamiento.
Pruebas: mappings, límites y fallbacks.

## Hito 10 — Traducción a modelo ytdl-sub
Objetivo: generar configuración ejecutable para la capa inferior.
Pruebas: salida exacta y ejecución controlada.

## Hito 11 — Compilación de artefactos
Objetivo: lanzar procesos reales y capturar resultados.
Pruebas: artefactos esperados, logs y gestión de errores.

## Hito 12 — Módulo de ejecución de jobs
Objetivo: planificar y controlar trabajos.
Pruebas: múltiples jobs, orden y reintentos.

## Hito 13 — Persistencia y estado en SQLite
Objetivo: registrar estado operativo.
Pruebas: tablas, escrituras y migraciones iniciales.

## Hito 14 — Anti-redescarga, historial y purga
Objetivo: evitar trabajo redundante y gestionar retención.
Pruebas: segunda ejecución no redescarga, purga correcta.

## Hito 15 — Retención, purga y caché persistente
Objetivo: consolidar política durable.
Pruebas: persistencia tras reinicio y mantenimiento.

## Hito 16 — Sistema de caché avanzado
Objetivo: invalidación selectiva y métricas.
Pruebas: invalidación correcta y mejora medible.

## Hito 17 — Gestor de colas: modelo simple
Objetivo: base de jobs en SQLite.
Pruebas: encolar, consultar y transicionar estados.

## Hito 18 — Gestor de colas: ejecución continua
Objetivo: procesamiento asíncrono continuo.
Pruebas: vaciado de cola, concurrencia y parada limpia.

## Hito 19 — API propia del core
Objetivo: exponer operaciones y estado.
Pruebas: endpoints válidos/ inválidos y workflows disparados.

## Hito 20 — Suite de pruebas integrales
Objetivo: consolidar cobertura y regresión.
Pruebas: ejecución completa de suites.

## Hito 21 — Aplicación completa
Objetivo: integrar CLI, core y ejemplos reales.
Pruebas: flujo end-to-end por ejemplo.

## Hito 22 — Dockerización del producto
Objetivo: contenedor listo para producción.
Pruebas: build final, despliegue reproducible y regresión acumulada en contenedor.
