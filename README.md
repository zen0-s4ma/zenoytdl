# Zenoytdl

## Introducción
Zenoytdl es una capa superior sobre `ytdl-sub` orientada a simplificar la experiencia de configuración, validación, orquestación y operación de flujos de descarga y postprocesado declarativos.

## Objetivo del proyecto
Construir una herramienta robusta, extensible y operable que permita definir entradas, perfiles, colas, caché, persistencia y automatización mediante configuración clara, con una API propia y una evolución posterior hacia interfaces más avanzadas.

## Problema que resuelve
`ytdl-sub` es potente, pero su modelo de uso y su superficie de configuración requieren conocimiento técnico elevado. Zenoytdl persigue encapsular esa complejidad, añadir validación temprana, control de estado, persistencia y una semántica operativa más estable.

## Contexto y motivación
El proyecto nace para ofrecer una capa de dominio con mejor UX operativa, contrato de configuración propio, trazabilidad, control de errores, caché y colas persistentes, sin reimplementar el motor subyacente.

## Alcance
Incluye configuración declarativa, validación, resolución de perfiles/suscripciones, traducción hacia la capa inferior, ejecución de jobs, caché, colas, persistencia SQLite, observabilidad y API interna. La TUI/GUI/Web UI quedan planificadas para fases posteriores.

## Estado actual del proyecto
Estado documental y de planificación. La implementación debe avanzar por hitos cerrados con pruebas y regresión acumulada.

> Política obligatoria de actualización: este README **solo** se actualiza cuando un hito queda realmente cerrado. Un hito se considera cerrado únicamente cuando: 
> 1. están implementados sus entregables,
> 2. pasan sus pruebas específicas,
> 3. pasa la batería de regresión acumulada hasta ese hito,
> 4. no quedan defectos bloqueantes abiertos.
>
> Mientras un hito está “en progreso”, este README no debe reflejarlo como completado. Solo podrá actualizarse el apartado **Estado actual del proyecto**, **Roadmap**, y las secciones que dependan de funcionalidad ya verificada.

---

## Descripción de la herramienta

### Qué es la herramienta
Una capa de orquestación declarativa y operativa sobre `ytdl-sub`.

### Para qué sirve
Para centralizar configuración, validar entradas, traducir contratos, ejecutar descargas y postprocesos, persistir estado y exponer automatización y observabilidad.

### Qué tipo de usuarios la utilizarán
Usuarios técnicos, operadores self-hosted, desarrolladores de herramientas multimedia y, a futuro, usuarios con menos experiencia mediante UI más amigables.

### Casos de uso principales
- Descarga organizada basada en suscripciones y perfiles.
- Aplicación de postprocesado consistente.
- Evitar redescargas mediante historial y caché.
- Operación continua por colas.
- Integración futura con interfaces y API.

### Qué no pretende cubrir
- Sustituir internamente a `ytdl-sub`.
- Reimplementar su ecosistema completo.
- Resolver inicialmente UX visual avanzada.

---

## Arquitectura

### Visión general
Zenoytdl separa entrada, validación, orquestación, lógica de negocio, integración, persistencia, observabilidad e interfaces.

### Principios de diseño
- Separación estricta de responsabilidades.
- Validación temprana y explícita.
- Contratos documentados.
- Persistencia como fuente de verdad operativa.
- Observabilidad desde el diseño.
- README gobernado por hitos verificados.

### Capas del proyecto
#### Capa de entrada
CLI, API y futuras interfaces.

#### Capa de validación
Parsing, validación estructural y validación semántica.

#### Capa de orquestación
Coordinación de jobs, reintentos, prioridades y flujo del sistema.

#### Capa de lógica de negocio
Resolución de perfiles, suscripciones, políticas de caché y ciclo de vida.

#### Capa de integración con dependencias externas
Traducción y acoplamiento controlado con `ytdl-sub` y otras dependencias.

#### Capa de persistencia
SQLite para jobs, items conocidos, métricas y eventos.

#### Capa de observabilidad y logging
Logs estructurados, métricas y trazabilidad por ejecución.

#### Capa de interfaz de usuario
CLI inicial y API; TUI/GUI/Web planificadas.

### Flujo principal
#### Inicio del sistema
Carga bootstrap, rutas y entorno.

#### Carga de configuración
Lectura de YAMLs requeridos.

#### Validación previa
Verificación sintáctica, estructural y semántica.

#### Resolución del flujo solicitado
Construcción del modelo efectivo por suscripción.

#### Ejecución de tareas
Encolado, deduplicación, traducción y ejecución.

#### Gestión de resultados
Registro de éxito, error, artefactos y métricas.

#### Registro de eventos y errores
Persistencia y logging estructurado.

### Flujos secundarios relevantes
#### Flujo de inicialización
Preparación de workspace, DB y defaults.

#### Flujo de actualización
Cambio de configuración con invalidación controlada.

#### Flujo de recuperación ante errores
Reintentos, diagnóstico y reanudación segura.

#### Flujo de parada segura
Cierre limpio de cola y persistencia de estado.

### Esquema ASCII
```text
[ Usuario / API / UI ]
          |
          v
[ Capa de entrada ]
          |
          v
[ Validación y normalización ]
          |
          v
[ Orquestación ]
          |
          v
[ Lógica de negocio ]
     |         |         |
     v         v         v
[ Config ] [ Cache ] [ Colas ]
     |         |         |
     +-----> [ Integraciones ] <-----+
                    |
                    v
            [ Resultados / Estado ]
                    |
                    v
         [ Logs / Métricas / Eventos ]
```

---

## Capacidades

### Capacidades principales
Validación, resolución de configuración, traducción y ejecución.

### Capacidades avanzadas
Caché persistente, colas, deduplicación, reintentos, purga.

### Capacidades de integración
Acoplamiento documentado con `ytdl-sub`.

### Capacidades de automatización
Procesamiento continuo y API.

### Capacidades de observabilidad
Logs, métricas, estados y eventos.

### Capacidades de extensibilidad
Perfiles, integraciones, skills, planes y módulos por capa.

---

## Funcionalidades

### Funcionalidades nucleares
Cargar, validar, resolver, traducir, ejecutar y persistir.

### Funcionalidades operativas
Colas, reintentos, historial, purga, mantenimiento.

### Funcionalidades de administración
Inspección de estado, configuración y jobs.

### Funcionalidades de monitorización
Métricas de caché, cola, ejecución y errores.

### Funcionalidades de mantenimiento
Migraciones, limpieza, recomputación de caché.

### Funcionalidades futuras previstas
TUI, GUI web, mejores integraciones y automatización ampliada.

---

## Orquestación

### Explicación teórica
La orquestación gobierna el ciclo completo desde entrada válida hasta resultado persistido.

### Responsabilidades de la orquestación
Encapsular la secuencia operativa, coordinar módulos y asegurar consistencia.

### Coordinación entre módulos
Entrada → validación → dominio → integración → ejecución → persistencia → observabilidad.

### Gestión del ciclo de vida de tareas
Creación, encolado, ejecución, finalización, reintento, cancelación.

### Priorización y planificación de ejecuciones
Por política configurable y límites de concurrencia.

### Gestión de dependencias internas
Respeto estricto a contratos y capas.

### Control de errores y reintentos
Reintentos acotados, clasificación de fallos y parada segura.

### Trazabilidad de las operaciones
Cada decisión relevante debe dejar evidencia operativa.

---

## Fluidez y rendimiento

### Objetivos de rendimiento
Reducir trabajo redundante, minimizar bloqueos y mantener throughput estable.

### Principios de diseño orientados a fluidez
Validación previa, caché efectiva, cola persistente y acoplamiento controlado.

### Estrategias para reducir bloqueos
Separación por etapas, reintentos acotados y observabilidad rica.

### Gestión eficiente de recursos
Límites de concurrencia, uso de disco controlado y políticas de purga.

### Paralelismo y concurrencia
Configurable, con protección ante duplicados y condiciones de carrera.

### Uso de cache
Historial, firmas y cache persistente.

### Gestión de colas
Modelo básico y posterior ejecución continua.

### Optimización de operaciones de entrada y salida
Normalización de rutas, escritura agrupada y persistencia incremental.

### Minimización de latencia percibida
Estados intermedios, logs claros y procesamiento continuo.

### Escalabilidad prevista
Escalado por workers, colas y partición lógica.

### Cuellos de botella conocidos o potenciales
I/O de disco, red, límites de la capa inferior y contención SQLite.

---

## Dockerización

### Objetivo de la contenerización
Entorno reproducible, portable y aislado.

### Estrategia general de Dockerización
Runtime Linux con layout fijo en `/data`.

### Estructura de contenedores
Inicialmente un contenedor principal; ampliable.

### Servicios implicados
Core, SQLite local y dependencias de sistema necesarias.

### Redes
Red interna simple o compose dedicada.

### Volúmenes
Config, cache y output persistentes.

### Variables de entorno
Rutas, niveles de log y parámetros operativos.

### Persistencia de datos
Mediante volúmenes para DB, caché y artefactos.

### Arranque del sistema
Bootstrap, validación y arranque de cola.

### Parada y recreación de servicios
Con parada segura e idempotencia.

### Healthchecks
Lectura de estado interno y disponibilidad mínima.

### Logs en entorno Docker
A stdout/stderr y, si procede, en archivos estructurados.

### Consideraciones para desarrollo
Bind mounts y herramientas de depuración.

### Consideraciones para producción
Imagen mínima, usuario no root y persistencia estable.

---

## Configuración

### Filosofía general de configuración
Configuración declarativa, explícita y validable.

### Objetivos del sistema de configuración
Claridad, trazabilidad, seguridad y overrides controlados.

### Jerarquía de configuración
General → perfiles → suscripciones → integraciones → runtime.

### Orden de precedencia
Valor explícito de suscripción sobre perfil y global, salvo reglas específicas documentadas.

### Validación de configuración
Sintáctica, estructural y semántica.

### Configuración por entornos
Desarrollo, test y producción.

### Configuración por perfiles
Perfiles reutilizables por tipo de flujo.

### Configuración sensible y secretos
Fuera de repositorio, preferiblemente vía entorno o ficheros excluidos.

### Explicación detallada de las diferentes configuraciones
#### Configuración general
Workspace, defaults y comportamiento global.

#### Configuración de perfiles
Presets semánticos reutilizables.

#### Configuración de suscripciones o entradas
Definición concreta de items o fuentes.

#### Configuración de integraciones externas
Mapeos y límites con `ytdl-sub`.

#### Configuración de cache
Firmas, invalidación y retención.

#### Configuración de colas
Concurrencia, prioridad y reintentos.

#### Configuración de logging
Formato, nivel y destino.

#### Configuración de rendimiento
Paralelismo, límites y timeouts.

#### Configuración de red
Opciones de conectividad y resolución.

#### Configuración de Docker
Rutas, usuario y volúmenes.

### Ficheros de configuración
#### configuracion-general.yaml
**Propósito:** parámetros globales.  
**Cuándo se usa:** siempre.  
**Campos principales:** `workspace`, `default_profile`, `log_level`.  
**Ejemplo esperado:** ver `examples/config-minima/general.yaml`.

#### profiles.yaml
**Propósito:** perfiles reutilizables.  
**Cuándo se usa:** al resolver suscripciones.  
**Campos principales:** `name`, `platform`, `ytdl_options`.  
**Ejemplo esperado:** ver `examples/config-minima/profiles.yaml`.

#### subscriptions.yaml
**Propósito:** entradas concretas.  
**Cuándo se usa:** al encolar y resolver jobs.  
**Campos principales:** `name`, `profile`, `items`, `enabled`.  
**Ejemplo esperado:** ver `examples/config-minima/subscriptions.yaml`.

#### integrations.yaml
**Propósito:** contrato de integración externo.  
**Cuándo se usa:** antes de traducir a la capa inferior.  
**Campos principales:** mappings, límites, fallbacks.  
**Ejemplo esperado:** ver `examples/config-minima/integrations.yaml`.

#### cache.yaml
**Propósito:** política de caché.  
**Cuándo se usa:** en validación operativa y ejecución.  
**Campos principales:** hashes, invalidación, TTL lógico.  
**Ejemplo esperado:** ver `examples/config-minima/cache.yaml`.

#### queues.yaml
**Propósito:** política de cola.  
**Cuándo se usa:** en planificación y ejecución.  
**Campos principales:** concurrencia, prioridad, reintentos.  
**Ejemplo esperado:** ver `examples/config-minima/queues.yaml`.

#### logging.yaml
**Propósito:** logging y observabilidad.  
**Cuándo se usa:** al arranque y durante ejecución.  
**Campos principales:** level, format, sinks.  
**Ejemplo esperado:** ver `examples/config-minima/logging.yaml`.

#### docker-compose.yml
**Propósito:** orquestación local de servicios.  
**Cuándo se usa:** desarrollo o despliegue simple.  
**Servicios definidos:** core y almacenamiento asociado.  
**Observaciones importantes:** persistencia obligatoria en volúmenes.

#### .env
**Propósito:** variables sensibles o dependientes de entorno.  
**Cuándo se usa:** en runtime local o compose.  
**Variables principales:** rutas, log level, opciones de ejecución.  
**Recomendaciones de seguridad:** no versionar secretos reales.

---

## Test

### Estrategia general de testing
Testing incremental por capas y por hitos.

### Objetivos de las pruebas
Probar exactitud, resiliencia, regresión y operabilidad.

### Tipos de pruebas
#### Tests unitarios
Componentes aislados.

#### Tests de integración
Interacción entre módulos.

#### Tests end-to-end
Flujos completos.

#### Tests de regresión
Validación acumulada por hito.

#### Tests de rendimiento
Cola, caché, I/O y throughput.

#### Tests de validación de configuración
Contratos YAML y ejemplos.

#### Tests de resiliencia
Fallas temporales, reintentos y parada segura.

### Cobertura esperada
Suficiente para gobernar cierre de hitos.

### Casos críticos a validar
Parsing, herencia, traducción, ejecución, caché, cola y persistencia.

### Datos de prueba
Fixtures válidos e inválidos, snapshots y artefactos mínimos.

### Entorno de pruebas
Local, CI y contenedor.

### Ejecución de tests
Mediante scripts de proyecto y suites por capa.

### Automatización de tests
Obligatoria antes del cierre de hito.

### Criterios de aceptación
No cerrar un hito con fallos abiertos ni regresiones.

### Criterios de salida por hito
Un hito sólo sale de “en curso” a “completado” cuando pasa su suite específica y la regresión acumulada. **Sólo entonces se actualiza el README.**

---

## Observabilidad

### Logging
Estructurado, contextual y orientado a diagnóstico.

### Métricas
Duración, tasa de éxito, cola, caché y errores.

### Trazas
Correlación por job y ejecución.

### Alertas
Para fallos repetidos, cola atascada o degradación relevante.

### Diagnóstico de errores
Mensajes accionables y persistencia suficiente.

---

## Seguridad

### Principios básicos de seguridad
Mínimo privilegio, validación y aislamiento.

### Gestión de secretos
Nunca en repositorio.

### Superficie de exposición
Limitada, especialmente en API y contenedores.

### Validación de entradas
Obligatoria antes de ejecución.

### Permisos y aislamiento
Usuario no root y volúmenes con permisos controlados.

---

## Limitaciones conocidas

### Limitaciones funcionales
Dependencia del motor subyacente y cobertura progresiva de features.

### Limitaciones técnicas
SQLite, I/O local y restricciones de la capa inferior.

### Limitaciones operativas
Necesidad de definir bien contratos y ejemplos reales.

---

## Roadmap

### Prioridades actuales
Núcleo, contratos, validación, traducción, ejecución y persistencia.

### Mejoras previstas a corto plazo
Colas, caché avanzada y API.

### Mejoras previstas a medio plazo
Operación continua, observabilidad ampliada y mejores integraciones.

### Mejoras previstas a largo plazo
TUI, GUI web y experiencia de usuario avanzada.

---

## FAQ

### Preguntas frecuentes técnicas
**¿Zenoytdl sustituye a `ytdl-sub`?**  
No. Lo encapsula.

**¿Puede actualizarse el README durante un hito a medias?**  
No. Solo al cerrar el hito con pruebas y regresión verde.

### Preguntas frecuentes de uso
**¿Necesito configurar todos los YAML desde el principio?**  
No necesariamente, pero la configuración mínima obligatoria debe estar bien formada.

### Preguntas frecuentes de despliegue
**¿El contenedor debe arrancar ya la cola?**  
Sí, según el contrato de runtime, salvo modo explícito de mantenimiento o test.

---

## Licencia
Pendiente de definición.

## Autoría y créditos
Proyecto Zenoytdl. Documentación base orientada a agentes y desarrollo asistido.
