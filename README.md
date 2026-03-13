# Nombre del proyecto

**Zenoytdl**

---

## Estado verificado actual del roadmap

- **Hito 0**: base de arranque y validación mínima del core.
- **Hito 1**: preparación de runtime objetivo container-first cerrada.
- **Hito 2**: modelado del dominio interno cerrado (sin parseo YAML ni infraestructura real).
- **Hitos 3+**: en roadmap, no deben interpretarse como capacidades cerradas hasta su validación formal.

> Regla de gobierno: este README no sustituye a `hitos-and-test.md`; ante conflicto, manda `hitos-and-test.md`.

# Introducción

Zenoytdl es una herramienta de alto nivel concebida como una capa de orquestación, validación, modelado y control situada por encima de `ytdl-sub`, con el objetivo de simplificar su uso, centralizar la configuración, imponer contratos claros y proporcionar una base sólida para automatización, ejecución controlada, observabilidad, persistencia y futura evolución de interfaces.

El proyecto nace con una orientación claramente técnica y arquitectónica: no pretende limitarse a envolver comandos ni a exponer una interfaz superficial, sino construir un núcleo coherente que permita gobernar de forma consistente la ingestión de configuraciones, su validación, la resolución de perfiles y suscripciones, la traducción hacia la capa inferior, la ejecución de trabajos, la persistencia del estado y la trazabilidad completa del sistema.

Zenoytdl debe entenderse como una plataforma especializada para gestionar flujos de descarga y procesamiento declarativos, reproducibles, observables y extensibles, apoyándose en contratos YAML propios y en un modelo interno que abstrae las particularidades de la herramienta subyacente.

# Objetivo del proyecto

El objetivo principal del proyecto es construir una herramienta robusta, extensible y bien estructurada que permita operar `ytdl-sub` de forma mucho más controlada, comprensible y mantenible, reduciendo la complejidad expuesta al usuario final y añadiendo capacidades que no pertenecen al núcleo de la herramienta inferior o que no están resueltas con el nivel de gobernanza deseado.

De forma más concreta, Zenoytdl busca:

- centralizar la configuración del sistema mediante archivos YAML más claros y con mejor semántica;
- validar de forma temprana y estricta todos los datos de entrada antes de ejecutar trabajo real;
- modelar internamente perfiles, suscripciones, jobs, colas, caché, resultados y estado;
- traducir de forma controlada la configuración efectiva a un contrato ejecutable para `ytdl-sub`;
- registrar el estado operativo en una base de datos SQLite que actúe como fuente de verdad;
- facilitar la automatización y la futura exposición mediante API, CLI avanzada, TUI y GUI web;
- mejorar la fluidez operativa mediante caché, deduplicación, colas, reintentos y diseño orientado a rendimiento;
- permitir una evolución por hitos con pruebas acumulativas y fuerte control de regresiones.

# Problema que resuelve

`ytdl-sub` es una herramienta potente, pero su utilización directa puede resultar compleja cuando se pretende construir un sistema más amplio, coherente y mantenible alrededor de ella. El problema no se reduce únicamente a la sintaxis de configuración, sino a la ausencia de una capa superior que unifique:

- validación fuerte de entradas;
- semántica de negocio propia;
- modelado explícito del dominio;
- gestión de estado persistente;
- control de ejecución de trabajos;
- observabilidad estructurada;
- mecanismos de caché e invalidación;
- políticas de reintento y recuperación;
- una experiencia de uso más clara y evolutiva.

Zenoytdl resuelve, por tanto, la fragmentación entre configuración, ejecución, estado y trazabilidad, ofreciendo una arquitectura donde cada responsabilidad queda delimitada y donde el sistema puede crecer sin depender de atajos ni de automatizaciones opacas.

# Contexto y motivación

La motivación del proyecto surge de la necesidad de construir una solución de uso real sobre una base existente, pero sin heredar de forma descontrolada toda su complejidad interna. La herramienta inferior resuelve bien una parte del problema —la descarga y ciertos flujos de postprocesado—, pero no está diseñada como una plataforma integral de orquestación de suscripciones, perfiles, validaciones, colas, estado persistente y gobierno operativo.

En este contexto, Zenoytdl se plantea como una capa superior con identidad propia. No intenta competir con `ytdl-sub`, sino encapsularla, traducir sus capacidades a un lenguaje interno más coherente y hacer que el sistema completo sea más legible, más predecible y más controlable.

La motivación adicional incluye:

- reducir deuda técnica futura desde el inicio;
- favorecer un desarrollo incremental por hitos cerrables;
- dejar una base preparada para API e interfaces futuras;
- mejorar la reproducibilidad de despliegue en contenedor;
- construir una herramienta que pueda operar con disciplina de producto y no sólo como script o wrapper informal.

# Alcance

Zenoytdl cubre el núcleo técnico necesario para gestionar configuraciones, resolver perfiles y suscripciones, validarlas, transformarlas en ejecuciones concretas sobre `ytdl-sub`, operar jobs, mantener caché y colas, persistir el estado y exponer una capa programática para futuras interfaces.

Dentro del alcance del proyecto se encuentran:

- configuración declarativa del sistema mediante YAML;
- validación estructural y semántica de configuraciones;
- herencia y resolución perfil → suscripción;
- contrato de integración con `ytdl-sub`;
- compilación y traducción de artefactos de configuración;
- ejecución controlada de trabajos;
- persistencia en SQLite;
- caché, anti-redescarga y políticas de purga;
- colas y workers;
- logging, métricas, trazabilidad y diagnóstico;
- API interna propia;
- dockerización y despliegue reproducible;
- pruebas unitarias, de integración, funcionales, e2e y de regresión.

Fuera del alcance inmediato inicial quedan:

- interfaces visuales avanzadas completas como producto final pulido desde el día uno;
- soporte universal para cualquier proveedor o plataforma imaginable;
- lógica de producto final centrada en UX avanzada antes de estabilizar el core;
- optimizaciones extremas prematuras no justificadas por necesidades reales;
- reimplementación total de las capacidades internas de `ytdl-sub`.

# Estado actual del proyecto

Este README está concebido como documento base de referencia para el proyecto. Debe utilizarse como marco estructural sobre el que se irá reflejando el avance real del sistema.

La regla de gobierno del proyecto es la siguiente:

- el `README.md` debe representar el **estado verificado** del proyecto;
- cada sección debe actualizarse **solo** cuando el hito correspondiente esté realmente completado;
- un hito se considera completado únicamente cuando pasa sus pruebas asociadas y la batería de regresión acumulada;
- no debe adelantarse en el README trabajo que todavía esté en curso, en revisión o pendiente de validación.

Por tanto, este documento puede contener una base extensa y estructurada, pero el contenido operativo marcado como implementado debe mantenerse alineado con la realidad del repositorio en cada momento.

---

# Descripción de la herramienta

## Qué es la herramienta

Zenoytdl es una herramienta de orquestación y control que envuelve `ytdl-sub` con una capa de dominio propia, una configuración declarativa más clara, mecanismos de validación, traducción, persistencia y ejecución, y una arquitectura preparada para crecimiento modular.

No es simplemente un lanzador de comandos ni un conjunto de scripts auxiliares. Es un sistema estructurado cuya finalidad es transformar intención declarativa en trabajo ejecutable y trazable.

## Para qué sirve

Sirve para definir, validar y ejecutar suscripciones y flujos de ingestión de medios de forma controlada, utilizando contratos YAML propios y una arquitectura que gestiona:

- perfiles reutilizables;
- suscripciones parametrizadas;
- traducción a la configuración ejecutable de `ytdl-sub`;
- ejecución de jobs con control de estado;
- prevención de trabajo redundante;
- persistencia del histórico y del estado;
- observabilidad y diagnóstico;
- base preparada para automatización y futuras interfaces.

## Qué tipo de usuarios la utilizarán

Zenoytdl está orientado principalmente a usuarios técnicos o semitécnicos que necesiten una solución más gobernable que la ejecución manual o ad hoc de herramientas de descarga.

Entre los perfiles de usuario esperables se encuentran:

- desarrolladores o mantenedores de pipelines de ingestión de contenido;
- operadores que necesiten automatización y visibilidad del estado del sistema;
- usuarios avanzados que quieran trabajar con configuraciones versionables y reproducibles;
- administradores que necesiten una base preparada para contenedores, persistencia y crecimiento funcional;
- futuros consumidores de la API o de interfaces superiores como TUI o GUI web.

## Casos de uso principales

Los casos de uso principales incluyen:

- definir suscripciones reutilizables a partir de perfiles y entradas declarativas;
- cargar una configuración completa y validarla antes de ejecutar trabajo real;
- traducir la configuración efectiva a un contrato ejecutable por `ytdl-sub`;
- lanzar trabajos de descarga y postprocesado con trazabilidad completa;
- evitar redescargas innecesarias mediante caché e historial;
- operar colas de ejecución con reintentos y control de concurrencia;
- exponer el estado del sistema por API o por CLI avanzada;
- desplegar el sistema dentro de contenedores con persistencia reproducible.

## Qué no pretende cubrir

Zenoytdl no pretende cubrir, al menos en su primera fase estable:

- edición multimedia avanzada como responsabilidad propia;
- reemplazar completamente el motor funcional de `ytdl-sub`;
- soportar cualquier workflow arbitrario sin contrato ni validación;
- convertirse inicialmente en una suite visual orientada al usuario no técnico absoluto;
- resolver problemas ajenos al núcleo de ingestión, traducción, ejecución, estado y observabilidad.

---

# Arquitectura

## Visión general

La arquitectura de Zenoytdl se basa en una separación estricta de responsabilidades. Cada capa del sistema existe para resolver un problema concreto y evitar acoplamientos innecesarios entre configuración, reglas de negocio, persistencia, ejecución y exposición externa.

La visión general puede resumirse así:

1. el usuario o consumidor externo expresa una intención a través de archivos de configuración, API o futura interfaz;
2. el sistema ingiere y normaliza esa entrada;
3. valida y resuelve perfiles, suscripciones y contratos;
4. genera un modelo interno consistente;
5. lo traduce hacia la capa inferior de integración;
6. orquesta jobs, colas, caché y persistencia;
7. ejecuta el trabajo real;
8. registra resultados, errores, métricas y eventos;
9. expone el estado del sistema de forma trazable.

## Principios de diseño

Los principios de diseño del proyecto son los siguientes:

- **separación de responsabilidades**: cada capa debe tener una función clara;
- **validación temprana**: ningún trabajo real debe lanzarse si la configuración no es válida;
- **contratos explícitos**: las reglas deben documentarse y no quedar implícitas;
- **persistencia como fuente de verdad**: el estado operativo debe quedar registrado;
- **traducción controlada**: la integración con `ytdl-sub` debe estar gobernada por contrato;
- **fluidez por diseño**: caché, colas y concurrencia se consideran desde el núcleo;
- **trazabilidad completa**: cada operación relevante debe poder auditarse;
- **extensibilidad**: la arquitectura debe permitir crecimiento sin rehacer el core;
- **contenedorización reproducible**: el sistema debe poder desplegarse con bajo nivel de sorpresa;
- **desarrollo por hitos verificables**: no se avanza de forma legítima sin pruebas y regresión verde.

## Capas del proyecto

### Capa de entrada

La capa de entrada recibe la intención del usuario o del sistema externo. Inicialmente, esta entrada será mayoritariamente declarativa mediante archivos YAML y CLI, pero el diseño contempla su futura ampliación a API HTTP, TUI y GUI.

Su responsabilidad es aceptar datos de entrada, identificarlos, enrutar el flujo inicial y convertirlos a una forma apta para la normalización posterior.

### Capa de validación

Esta capa comprueba la integridad estructural y semántica de los datos de entrada. Debe detectar:

- errores de sintaxis;
- campos desconocidos;
- tipos inválidos;
- referencias rotas entre ficheros;
- incoherencias entre perfiles, suscripciones e integraciones;
- valores fuera de rango o incompatibles.

Su misión es fallar pronto, fallar de forma clara y evitar que el sistema ejecute trabajo con estado inconsistente.

### Capa de orquestación

La capa de orquestación coordina el ciclo de vida de las operaciones. Es responsable de decidir el orden de ejecución, administrar jobs, interactuar con la cola, aplicar políticas de reintento, controlar los pasos del flujo y mantener una visión operativa del sistema.

No debe contener detalles bajos de integración ni lógica de persistencia dispersa; debe operar a un nivel de coordinación.

### Capa de lógica de negocio

Aquí vive el modelo interno real de Zenoytdl: perfiles, suscripciones, configuración efectiva, jobs, resultados, estados, reglas de resolución e invariantes del dominio.

Esta capa define qué significa cada concepto dentro del sistema y cómo deben combinarse los distintos elementos para formar una operación válida.

### Capa de integración con dependencias externas

Esta capa encapsula la interacción con herramientas externas, siendo `ytdl-sub` el caso central. Debe transformar el modelo interno en llamadas, argumentos, artefactos o configuraciones compatibles con el sistema integrado.

También puede incluir integración con FFmpeg, sistema de archivos, runtime de contenedor y servicios auxiliares según evolucione el producto.

### Capa de persistencia

La capa de persistencia almacena el estado duradero del sistema. SQLite actúa como fuente de verdad para:

- suscripciones conocidas;
- jobs;
- ejecuciones;
- artefactos;
- caché;
- métricas;
- histórico de resultados;
- eventos y errores relevantes.

### Capa de observabilidad y logging

Esta capa proporciona visibilidad. Debe registrar logs estructurados, métricas, trazas y eventos operativos que permitan entender qué hizo el sistema, cuándo, por qué y con qué resultado.

### Capa de interfaz de usuario

Esta capa representa la interacción hacia fuera. En etapas tempranas puede ser principalmente CLI y API interna; en etapas posteriores puede ampliarse a TUI y GUI web. Debe consumir el core sin duplicar lógica de negocio.

## Flujo principal

### Inicio del sistema

El sistema arranca cargando su contexto base: variables de entorno, rutas de trabajo, configuración general, dependencias necesarias y estado persistente mínimo.

### Carga de configuración

Se leen los ficheros declarativos obligatorios y opcionales del proyecto, se resuelven rutas, se normalizan datos y se preparan estructuras internas temporales.

### Validación previa

Antes de ejecutar cualquier trabajo, el sistema valida sintaxis, estructura, relaciones, invariantes, contratos de integración y consistencia de los perfiles y suscripciones.

### Resolución del flujo solicitado

Una vez validada la entrada, el sistema resuelve herencias, overrides, defaults y dependencias internas para construir una configuración efectiva lista para traducción y ejecución.

### Ejecución de tareas

La orquestación convierte el trabajo solicitado en jobs, los encola o ejecuta según corresponda, aplica políticas de concurrencia, caché, deduplicación y reintentos, y delega la ejecución real a la capa de integración.

### Gestión de resultados

Los resultados de ejecución se clasifican, persisten y reflejan en el estado del sistema. El sistema debe distinguir entre éxito, fallo recuperable, fallo definitivo, omisión por caché y otros estados operativos relevantes.

### Registro de eventos y errores

Cada operación significativa debe generar trazabilidad suficiente para diagnóstico posterior, auditoría y soporte operativo.

## Flujos secundarios relevantes

### Flujo de inicialización

Este flujo cubre bootstrap del entorno, creación de directorios, preparación de base de datos, carga de configuración mínima y comprobaciones de salud del sistema.

### Flujo de actualización

Incluye recarga de configuración, invalidación selectiva de caché, sincronización de nuevas suscripciones, incorporación de nuevos jobs y adaptación del estado existente a una nueva configuración válida.

### Flujo de recuperación ante errores

Ante errores de ejecución, validación o integración, el sistema debe registrar el contexto, aplicar políticas de reintento cuando proceda, evitar corrupción del estado y dejar evidencia clara del motivo y del punto de fallo.

### Flujo de parada segura

La parada debe ser ordenada: finalización de jobs en curso según política definida, persistencia de estado, cierre de recursos, vaciado seguro de buffers de log y liberación limpia de locks o workers.

## Esquema ASCII

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

# Capacidades

## Capacidades principales

Las capacidades principales del sistema son:

- carga declarativa de configuraciones;
- validación estructural y semántica;
- modelado interno del dominio;
- resolución de perfiles y suscripciones;
- traducción controlada a `ytdl-sub`;
- ejecución de jobs;
- persistencia del estado;
- observabilidad y diagnóstico.

## Capacidades avanzadas

Entre las capacidades avanzadas previstas o necesarias se incluyen:

- invalidación selectiva de caché;
- deduplicación de jobs;
- reintentos con política configurable;
- control de concurrencia;
- compilación de configuraciones efectivas;
- auditoría de resultados;
- trazabilidad de cambios de configuración;
- evolución del core hacia servicios expuestos por API.

## Capacidades de integración

Zenoytdl debe integrarse de forma controlada con:

- `ytdl-sub`;
- FFmpeg y herramientas auxiliares de postprocesado cuando proceda;
- sistema de archivos y volúmenes persistentes;
- runtime de contenedor;
- SQLite;
- futuros consumidores vía API.

## Capacidades de automatización

La herramienta está diseñada para permitir:

- ejecución recurrente de flujos;
- bootstrap de entorno reproducible;
- procesos de cola automáticos;
- mantenimiento programado de caché y purgas;
- despliegues en contenedor;
- integración futura con schedulers externos.

## Capacidades de observabilidad

El sistema debe poder emitir:

- logs estructurados;
- métricas de rendimiento;
- información de estado de jobs;
- indicadores de uso de caché;
- eventos de error y recuperación;
- trazabilidad de ciclo de vida.

## Capacidades de extensibilidad

Zenoytdl debe permitir crecimiento mediante:

- incorporación de nuevos tipos de integración;
- ampliación del contrato YAML;
- nuevos perfiles y modos de suscripción;
- nuevas políticas de colas, reintentos y caché;
- nuevos endpoints o interfaces;
- separación modular por capas y submódulos.

---

# Funcionalidades

## Funcionalidades nucleares

- leer configuración desde YAML;
- validar configuración;
- resolver perfiles y suscripciones;
- construir modelo interno efectivo;
- traducir a contrato de integración;
- ejecutar jobs;
- registrar estado y resultados.

## Funcionalidades operativas

- colas de trabajo;
- workers;
- reintentos;
- deduplicación;
- caché persistente;
- invalidación;
- purga y retención;
- control de concurrencia;
- manejo de fallos.

## Funcionalidades de administración

- inspección del estado del sistema;
- consulta del histórico;
- revisión de errores;
- mantenimiento de base de datos y caché;
- actualización de configuración;
- arranque y parada controlados.

## Funcionalidades de monitorización

- exposición de métricas;
- consulta del estado de jobs;
- seguimiento de tiempos de ejecución;
- análisis de hit/miss de caché;
- identificación de cuellos de botella;
- observación de eventos relevantes.

## Funcionalidades de mantenimiento

- purga de registros antiguos;
- compactación o mantenimiento de almacenamiento;
- limpieza de temporales;
- reconstrucción de artefactos derivados si procede;
- revalidación de configuración;
- comprobaciones de salud del entorno.

## Funcionalidades futuras previstas

- API estable de administración y consulta;
- TUI operativa;
- GUI web;
- panel de estado y métricas;
- herramientas de diagnóstico ampliadas;
- más granularidad en scheduling, perfiles y políticas de ejecución.

---

# Orquestación

## Explicación teórica

La orquestación es la capa que convierte una intención declarativa validada en un flujo real de acciones coordinadas. No ejecuta simplemente tareas aisladas, sino que administra dependencias, estados, tiempos, orden, reintentos, prioridades y efectos colaterales.

En Zenoytdl, la orquestación debe actuar como eje entre entrada, modelo, integración, persistencia y observabilidad.

## Responsabilidades de la orquestación

Sus responsabilidades incluyen:

- transformar solicitudes en jobs ejecutables;
- decidir cuándo un job debe ejecutarse, aplazarse o descartarse;
- interactuar con la cola y con el sistema de caché;
- gobernar el ciclo de vida de ejecución;
- coordinar la persistencia del estado;
- notificar y registrar resultados.

## Coordinación entre módulos

La orquestación debe hablar con todas las capas sin mezclarlas. Debe recibir configuraciones ya validadas, consumir el modelo interno, solicitar traducciones a la integración, registrar estados en persistencia y emitir señales a la observabilidad.

## Gestión del ciclo de vida de tareas

Cada tarea debe atravesar estados bien definidos, como por ejemplo:

- creada;
- pendiente;
- bloqueada;
- en ejecución;
- completada;
- omitida por caché;
- reintentable;
- fallida;
- cancelada.

La orquestación es responsable de gobernar estas transiciones con reglas claras.

## Priorización y planificación de ejecuciones

El sistema debe permitir establecer políticas de prioridad y planificación, de modo que ciertos jobs puedan ejecutarse antes que otros o bajo restricciones de concurrencia específicas.

## Gestión de dependencias internas

Hay tareas que pueden depender de la resolución previa de configuración, del estado de caché, del acceso a recursos compartidos o de otros jobs relacionados. Estas dependencias deben resolverse antes de lanzar trabajo real.

## Control de errores y reintentos

La orquestación debe distinguir entre errores transitorios y errores definitivos, aplicar reintentos sólo donde proceda, evitar bucles improductivos y registrar siempre el contexto del fallo.

## Trazabilidad de las operaciones

Cada acción relevante debe quedar asociada a identificadores, timestamps, contexto, configuración efectiva usada, resultado y logs relacionados.

---

# Fluidez y rendimiento

## Objetivos de rendimiento

Los objetivos de rendimiento no deben entenderse sólo como velocidad máxima, sino como equilibrio entre:

- tiempo razonable de respuesta;
- consumo controlado de recursos;
- previsibilidad;
- ausencia de bloqueos evitables;
- aprovechamiento de caché;
- escalabilidad funcional y operativa.

## Principios de diseño orientados a fluidez

- validación temprana para evitar trabajo inútil;
- minimización de recomputación;
- persistencia eficiente;
- separación entre operaciones rápidas y operaciones pesadas;
- diseño asíncrono donde tenga sentido;
- observabilidad para detectar degradaciones.

## Estrategias para reducir bloqueos

- desacoplar carga/validación de ejecución pesada;
- uso de colas;
- workers independientes;
- reintentos controlados;
- locks mínimos y bien definidos;
- acceso optimizado a base de datos y sistema de archivos.

## Gestión eficiente de recursos

El sistema debe administrar CPU, memoria, disco, red y procesos externos con criterios explícitos, evitando tanto infrautilización extrema como sobrecarga descontrolada.

## Paralelismo y concurrencia

Debe soportarse concurrencia configurable, con límites seguros y controlados, evitando que múltiples trabajos idénticos compitan por los mismos recursos.

## Uso de cache

La caché es una pieza central para evitar trabajo redundante. Debe utilizarse para identificar elementos ya procesados, resultados ya conocidos o configuraciones ya resueltas cuya reutilización sea válida.

## Gestión de colas

Las colas permiten absorber carga, ordenar trabajo, priorizar tareas y desacoplar el ritmo de entrada del ritmo de ejecución real.

## Optimización de operaciones de entrada y salida

La arquitectura debe reducir accesos innecesarios a disco, relecturas de configuración no justificadas, escrituras redundantes y operaciones que puedan agruparse o diferirse.

## Minimización de latencia percibida

La latencia percibida puede reducirse proporcionando feedback temprano, registrando progreso, desacoplando procesos costosos y resolviendo rápidamente las fases de validación e inspección.

## Escalabilidad prevista

Aunque SQLite y un único runtime pueden ser suficientes para etapas tempranas, la arquitectura debe permitir crecer en complejidad modular y en volumen de uso sin rehacer los conceptos nucleares.

## Cuellos de botella conocidos o potenciales

Entre los cuellos de botella potenciales se encuentran:

- ejecución de procesos externos;
- operaciones intensivas de disco;
- sobreuso de la base de datos en estados de alta concurrencia;
- traducción o compilación repetitiva innecesaria;
- ausencia de invalidación de caché precisa;
- serialización excesiva del flujo.

---

# Dockerización

## Objetivo de la contenerización

La contenerización persigue lograr despliegue reproducible, aislamiento del runtime, simplificación operativa y una base consistente para desarrollo, pruebas y producción.

## Estrategia general de Dockerización

La estrategia general consiste en encapsular Zenoytdl y sus dependencias necesarias dentro de uno o varios contenedores, usando bind mount de configuración en `/config` y persistencia en rutas `/data/...` definidas por contrato de runtime.

## Estructura de contenedores

La estructura concreta puede variar según fase del proyecto, pero conceptualmente debe incluir:

- contenedor principal del core;
- persistencia mediante volúmenes montados;
- posible separación futura de componentes auxiliares si el sistema crece.

## Servicios implicados

Como mínimo, puede existir un servicio principal de Zenoytdl. En fases posteriores pueden añadirse servicios complementarios para UI, métricas u otras necesidades.

## Redes

La configuración de red debe ser simple, explícita y segura. Debe evitar exposición innecesaria y permitir comunicación interna entre servicios cuando sea necesario.

## Volúmenes

Los volúmenes deben persistir:

- configuración;
- estado SQLite;
- caché;
- artefactos descargados;
- logs si se decide persistirlos en disco.

## Variables de entorno

Las variables de entorno deben usarse para parametrizar entorno, rutas, secretos, ajustes de logging y otras opciones no deseables de hardcodear.

## Persistencia de datos

La persistencia debe sobrevivir a recreaciones del contenedor y preservar coherencia entre base de datos, caché, configuración y resultados.

## Arranque del sistema

El arranque debe ser determinista: comprobación de entorno, carga de configuración, preparación de recursos, migraciones necesarias y puesta en marcha del servicio principal.

## Parada y recreación de servicios

La parada debe ser limpia y la recreación no debe corromper estado ni duplicar trabajo. Deben contemplarse políticas de reinicio seguras.

## Healthchecks

Los healthchecks deben verificar no sólo que el proceso vive, sino que el sistema está realmente en un estado operativo mínimo aceptable.

## Logs en entorno Docker

Los logs deben poder consumirse tanto desde stdout/stderr como, si se requiere, desde directorios persistentes o integraciones externas.

## Consideraciones para desarrollo

En desarrollo interesa:

- facilidad de rebuild;
- montaje de código y configuración;
- visibilidad de logs;
- rapidez de iteración;
- separación clara entre datos temporales y datos persistentes.

## Consideraciones para producción

En producción interesa:

- imagen reproducible y limpia;
- usuario no privilegiado cuando sea viable;
- mínimos privilegios y exposición;
- persistencia robusta;
- control de recursos;
- observabilidad;
- políticas de reinicio y mantenimiento.

---

# Configuración

## Filosofía general de configuración

La configuración de Zenoytdl debe ser declarativa, legible, versionable, separable por responsabilidades y fácil de validar. El sistema no debe depender de defaults opacos difíciles de auditar.

## Objetivos del sistema de configuración

- claridad semántica;
- separación por ámbitos;
- validación estricta;
- reusabilidad mediante perfiles;
- facilidad para overrides controlados;
- adaptación a distintos entornos;
- mínima ambigüedad.

## Jerarquía de configuración

La jerarquía debe organizarse en ficheros especializados, cada uno con responsabilidad acotada. La combinación entre ellos debe estar gobernada por reglas explícitas.

## Orden de precedencia

Debe existir un orden de precedencia claro entre:

- valores por defecto del sistema;
- configuración general;
- perfiles;
- suscripciones;
- integraciones;
- variables de entorno cuando proceda;
- overrides explícitos por operación.

## Validación de configuración

Toda configuración debe pasar validación estructural y semántica antes de considerarse ejecutable. Los errores deben ser descriptivos, localizables y accionables.

## Configuración por entornos

El sistema debe poder adaptarse a desarrollo, pruebas y producción mediante configuración declarativa y variables de entorno, evitando bifurcaciones de código innecesarias.

## Configuración por perfiles

Los perfiles existen para agrupar parámetros comunes y evitar repetición. Deben permitir herencia y sobrescritura controlada desde las suscripciones.

## Configuración sensible y secretos

Los secretos no deben quedar hardcodeados en el repositorio. Deben gestionarse mediante variables de entorno, ficheros excluidos o mecanismos equivalentes de despliegue seguro.

## Explicación detallada de las diferentes configuraciones

### Configuración general

Define el contexto base del sistema: rutas, comportamiento global, defaults, niveles de logging, límites generales, modo de trabajo, parámetros del runtime y ajustes operativos globales.

### Configuración de perfiles

Define conjuntos reutilizables de parámetros de comportamiento para categorías de suscripciones o casos de uso comunes.

### Configuración de suscripciones o entradas

Contiene las suscripciones concretas, fuentes, elementos, activación, overrides y datos específicos de cada flujo real.

### Configuración de integración con ytdl-sub

Se define en `ytdl-sub-conf.yaml` y concentra mappings, reglas de traducción, compatibilidad, fallback e invocación hacia `ytdl-sub`.

### Configuración de cache

Controla políticas de deduplicación, persistencia de firmas, invalidación y retención relacionada con resultados y metadatos reutilizables.

### Configuración de colas

Define concurrencia, número de workers, políticas de prioridad, reintentos, backoff, polling y reglas de scheduling.

### Configuración de logging

Establece formato, nivel, destino, rotación, estructuración y granularidad de los registros.

### Configuración de rendimiento

Permite ajustar límites de concurrencia, buffers, timings, políticas de batching e intervalos de mantenimiento.

### Configuración de red

Incluye puertos, bindings, timeouts, proxies, límites de conexión y cualquier ajuste relacionado con comunicaciones externas.

### Configuración de Docker

Describe variables, montajes, servicios, healthchecks, límites y parámetros necesarios para ejecutar el sistema en contenedor.

## Ficheros de configuración

### general.yaml

#### Propósito

Define la base de comportamiento global del sistema.

#### Cuándo se usa

Se usa en cada arranque y en cada operación que requiera conocer el contexto general del runtime.

#### Campos principales

Ejemplos de campos esperables:

- `workspace`
- `data_dir`
- `default_profile`
- `log_level`
- `environment`
- `max_parallelism`
- `database_path`

#### Ejemplo esperado

```yaml
workspace: /data/library
environment: production
default_profile: default
log_level: INFO
database_path: /data/state.sqlite
cache_path: /data/cache.sqlite
compiled_config_dir: /data/compiled-ytdl-sub
max_parallelism: 2
```

### profiles.yaml

#### Propósito

Define perfiles reutilizables y parametrizables.

#### Cuándo se usa

Se usa al resolver cualquier suscripción que referencie un perfil.

#### Campos principales

- `name`
- `platform`
- `enabled`
- `defaults`
- `ytdl_options`
- `postprocessing`

#### Ejemplo esperado

```yaml
profiles:
  - name: default
    platform: generic
    enabled: true
    ytdl_options:
      quality: best
  - name: audio_only
    platform: podcast
    enabled: true
    ytdl_options:
      extract_audio: true
      quality: bestaudio
```

### subscriptions.yaml

#### Propósito

Define suscripciones concretas y entradas reales del sistema.

#### Cuándo se usa

Se usa al planificar trabajo real, generar jobs y resolver configuración efectiva.

#### Campos principales

- `name`
- `profile`
- `enabled`
- `items`
- `overrides`
- `tags`

#### Ejemplo esperado

```yaml
subscriptions:
  - name: canal-ejemplo
    profile: default
    enabled: true
    items:
      - https://www.youtube.com/@ejemplo
  - name: podcast-ejemplo
    profile: audio_only
    enabled: true
    items:
      - https://example.com/feed.xml
```

### ytdl-sub-conf.yaml

#### Propósito

Define el contrato de integración con `ytdl-sub` y es la fuente de verdad del acoplamiento.

#### Cuándo se usa

Se usa al validar la traducibilidad de perfiles/suscripciones y al preparar la traducción final al formato ejecutable por `ytdl-sub`.

#### Campos principales

- `integration_version`
- `preset_mapping`
- `field_mapping`
- `translation_rules`
- `compatibility`
- `fallback_policy`
- `validation`
- `invocation`

#### Ejemplo esperado

```yaml
integration_version: 1
preset_mapping:
  default: base_video
field_mapping:
  quality: format
  output_template: output
translation_rules:
  quality:
    best: "bv*+ba/b"
compatibility:
  min_ytdl_sub_version: "2024.01"
fallback_policy:
  on_missing_field: reject
validation:
  strict_unknown_fields: true
invocation:
  binary: ytdl-sub
```

### cache.yaml

#### Propósito

Gobierna la capa de caché del sistema.

#### Cuándo se usa

Se usa antes, durante y después de las ejecuciones para decidir reutilización, invalidación y mantenimiento.

#### Campos principales

- `enabled`
- `strategy`
- `hash_scope`
- `ttl`
- `invalidate_on_config_change`

#### Ejemplo esperado

```yaml
cache:
  enabled: true
  strategy: signature
  hash_scope: effective_config
  ttl: null
  invalidate_on_config_change: true
```

### queues.yaml

#### Propósito

Define el comportamiento del sistema de colas y workers.

#### Cuándo se usa

Se usa cuando el sistema programa y ejecuta jobs de forma asíncrona o continua.

#### Campos principales

- `enabled`
- `workers`
- `max_parallel_jobs`
- `retry_policy`
- `poll_interval_seconds`

#### Ejemplo esperado

```yaml
queues:
  enabled: true
  workers: 2
  max_parallel_jobs: 2
  poll_interval_seconds: 5
  retry_policy:
    max_attempts: 3
    backoff_seconds: 30
```

### logging.yaml

#### Propósito

Define el comportamiento del logging y de parte de la observabilidad base.

#### Cuándo se usa

Se usa en el arranque y durante toda la vida del sistema.

#### Campos principales

- `level`
- `format`
- `json`
- `output`
- `file_path`

#### Ejemplo esperado

```yaml
logging:
  level: INFO
  format: structured
  json: true
  output: stdout
```

### docker-compose.yml

#### Propósito

Orquesta el arranque de la solución en entorno Docker Compose.

#### Cuándo se usa

Se usa en desarrollo local, pruebas integradas o despliegues simples basados en Compose.

#### Servicios definidos

Como base mínima, puede incluir:

- `zenoytdl`

Y en el futuro puede ampliarse con servicios auxiliares.

#### Observaciones importantes

- debe reflejar rutas persistentes del contrato (`/data/library`, `/data/tmp`, `/data/logs`, `/data/state.sqlite`, `/data/cache.sqlite`, `/data/compiled-ytdl-sub`);
- debe exponer sólo lo necesario;
- debe definir variables de entorno relevantes;
- debe incluir healthchecks cuando proceda;
- no debe mezclar secretos sensibles dentro del propio fichero.

### .env

#### Propósito

Permite externalizar variables de entorno y separar configuración sensible del versionado principal.

#### Cuándo se usa

Se usa antes de arrancar el entorno, especialmente en Docker Compose y en despliegues locales.

#### Variables principales

Ejemplos esperables:

- `ZENOYTDL_ENV`
- `ZENOYTDL_CONFIG_DIR`
- `ZENOYTDL_DATA_DIR`
- `ZENOYTDL_LOG_LEVEL`
- `TZ`

#### Recomendaciones de seguridad

- no commitear secretos reales;
- proporcionar `.env.example` cuando proceda;
- documentar variables obligatorias y opcionales;
- usar valores por defecto seguros o neutros.

<!-- Repetir este bloque para cada fichero de configuración real del proyecto -->

---

# Test

## Estrategia general de testing

La estrategia de pruebas del proyecto debe cubrir el sistema desde varios niveles de profundidad, asegurando que tanto el comportamiento aislado de los módulos como los flujos completos del negocio quedan verificados.

## Objetivos de las pruebas

- detectar fallos temprano;
- proteger contratos e invariantes;
- validar integración entre capas;
- prevenir regresiones;
- verificar resiliencia y comportamiento operativo;
- dar confianza para avanzar por hitos.

## Tipos de pruebas

El sistema debe contemplar como mínimo pruebas:

- unitarias;
- de integración;
- end-to-end;
- de regresión;
- de rendimiento;
- de validación de configuración;
- de resiliencia.

## Tests unitarios

Deben verificar módulos aislados, como parser, validadores, resolutores, transformadores, utilidades de persistencia y componentes de orquestación con dependencias controladas.

## Tests de integración

Deben validar cómo colaboran entre sí varios módulos: por ejemplo, carga de configuración + validación + resolución + traducción + persistencia parcial.

## Tests end-to-end

Deben recorrer flujos completos, desde una entrada declarativa válida hasta la generación del resultado esperado y su registro en el sistema.

## Tests de regresión

Son obligatorios al cierre de cada hito. Deben ejecutarse de forma acumulada e impedir considerar completado un hito si rompen trabajo previo.

## Tests de rendimiento

Deben ayudar a detectar degradaciones, bloqueos, tiempos de espera excesivos o políticas de concurrencia ineficientes.

## Tests de validación de configuración

Deben cubrir casos válidos, inválidos, ambiguos, incompletos y contradictorios, garantizando que los errores se detectan con mensajes útiles.

## Tests de resiliencia

Deben simular fallos de integración, interrupciones, estados inconsistentes evitables, reinicios, reintentos y recuperación controlada.

## Cobertura esperada

La cobertura esperada debe ser suficiente para blindar contratos, invariantes, rutas críticas y flujos principales. La cifra exacta podrá definirse más adelante, pero la prioridad debe estar en cobertura significativa, no cosmética.

## Casos críticos a validar

- configuración inválida;
- referencias rotas entre perfiles y suscripciones;
- traducción incorrecta a integración;
- redescarga no deseada;
- pérdida de estado;
- ejecución duplicada de jobs;
- errores de reintento;
- corrupción de caché;
- fallo de parada limpia;
- inconsistencias entre resultado y persistencia.

## Datos de prueba

Debe existir un conjunto controlado de fixtures, ejemplos válidos e inválidos, snapshots y artefactos mínimos reproducibles.

## Entorno de pruebas

El entorno de pruebas debe ser reproducible, automatizable y lo más cercano posible al comportamiento real en las rutas críticas.

## Ejecución de tests

La suite de pruebas debe poder ejecutarse mediante comandos bien definidos y documentados.

## Automatización de tests

Las pruebas deben integrarse en el flujo de desarrollo y en la validación previa al cierre de hitos o merges.

## Criterios de aceptación

Una funcionalidad se considera aceptable cuando satisface su contrato, pasa sus pruebas específicas y no introduce regresiones sobre funcionalidad previa.

## Criterios de salida por hito

Un hito sólo puede marcarse como finalizado cuando:

- están implementados sus entregables comprometidos;
- pasan las pruebas específicas del hito;
- pasa la batería de regresión acumulada;
- la documentación afectada se actualiza en consecuencia;
- el README se actualiza sólo después de lo anterior.

---

# Observabilidad

## Logging

El sistema debe emitir logs consistentes, legibles y preferiblemente estructurados, con niveles adecuados y contexto suficiente para diagnóstico.

## Métricas

Debe ser posible registrar métricas como:

- duración de jobs;
- jobs completados/fallidos;
- reintentos;
- tasa de hit/miss de caché;
- tiempos por fase;
- tamaño de cola;
- latencias de integración.

## Trazas

Las trazas deben permitir reconstruir el recorrido de una operación desde la entrada hasta el resultado final, incluyendo decisiones de orquestación.

## Alertas

En fases más avanzadas, pueden definirse alertas sobre estados anómalos: exceso de fallos, cola bloqueada, crecimiento de latencia, incapacidad de persistencia o degradación sistemática.

## Diagnóstico de errores

El sistema debe facilitar diagnóstico mediante contexto, correlación de eventos, clasificación de fallos y acceso al estado asociado a la operación fallida.

---

# Seguridad

## Principios básicos de seguridad

- principio de mínimo privilegio;
- validación estricta de entradas;
- no exponer superficie innecesaria;
- no almacenar secretos en claro dentro del repositorio;
- uso prudente de ejecución de procesos externos.

## Gestión de secretos

Los secretos deben gestionarse fuera del código y de la configuración versionada, usando variables de entorno o mecanismos adecuados de despliegue.

## Superficie de exposición

Cualquier API, puerto, volumen compartido o mecanismo de administración debe justificarse y limitarse al mínimo necesario.

## Validación de entradas

Toda entrada del usuario o del sistema externo debe validarse antes de afectar al modelo interno o a la ejecución real.

## Permisos y aislamiento

El sistema debe favorecer ejecución como usuario no privilegiado, permisos mínimos sobre disco y aislamiento razonable en contenedor.

---

# Limitaciones conocidas

## Limitaciones funcionales

- dependencia del comportamiento real de `ytdl-sub` y herramientas asociadas;
- cobertura inicial potencialmente acotada a ciertos casos de uso y contratos;
- interfaces visuales avanzadas no prioritarias al inicio.

## Limitaciones técnicas

- SQLite tiene límites naturales para ciertos escenarios de altísima concurrencia;
- ejecución de procesos externos puede introducir variabilidad y puntos de fallo;
- la calidad de ciertos flujos dependerá del contrato de integración y de sus límites.

## Limitaciones operativas

- necesidad de una buena política de observabilidad para operar con confianza;
- complejidad creciente si se amplían demasiados modos sin reforzar contratos;
- necesidad de disciplina de pruebas para mantener coherencia entre hitos.

---

# Roadmap

## Prioridades actuales

Las prioridades actuales deben centrarse en consolidar el núcleo:

- estructura base del proyecto;
- contratos de configuración;
- modelo de dominio;
- validación;
- traducción e integración;
- ejecución controlada;
- persistencia;
- colas y caché;
- suite de pruebas sólida.

## Mejoras previstas a corto plazo

- cierre del core funcional;
- mejor cobertura de pruebas;
- documentación técnica más detallada;
- primeros endpoints o API interna utilizable;
- dockerización más madura.

## Mejoras previstas a medio plazo

- robustecimiento de observabilidad;
- TUI operativa;
- ampliación de capacidades de administración;
- mejores herramientas de diagnóstico;
- refinamiento de rendimiento.

## Mejoras previstas a largo plazo

- GUI web;
- capacidades operativas más avanzadas;
- extensibilidad más rica para nuevas integraciones;
- mayor sofisticación en scheduling, reporting y control de estado.

---

# FAQ

## Preguntas frecuentes técnicas

**¿Zenoytdl reemplaza a ytdl-sub?**  
No. Lo encapsula y lo gobierna desde una capa superior.

**¿La configuración se define directamente con la sintaxis nativa de ytdl-sub?**  
No necesariamente. La idea es disponer de contratos YAML propios y traducirlos de forma controlada.

**¿SQLite es la fuente de verdad del sistema?**  
Sí, para el estado operativo y persistente del core.

**¿La caché es opcional o central?**  
Es una parte central del diseño orientado a fluidez y anti-redescarga.

## Preguntas frecuentes de uso

**¿Puedo definir varias suscripciones con un mismo perfil?**  
Sí, ese es precisamente uno de los objetivos del sistema de perfiles.

**¿Se puede invalidar caché al cambiar configuración?**  
Sí, esa es una de las capacidades previstas del sistema.

**¿El README se puede ir adelantando según se planean cosas?**  
No. Debe reflejar sólo estado realmente verificado y cerrado por hito.

## Preguntas frecuentes de despliegue

**¿Se puede ejecutar en Docker?**  
Está planificado en el roadmap; su cierre formal corresponde a hitos posteriores.

**¿La persistencia sobrevive a recreaciones?**  
Debe hacerlo mediante volúmenes y una estrategia correcta de datos persistentes.

**¿Se puede usar en desarrollo y en producción?**  
Sí, con ajustes de configuración y endurecimiento progresivo según entorno.

---

# Licencia

Pendiente de definición explícita por parte del proyecto. Se recomienda elegir una licencia clara y documentarla de forma formal en el repositorio.

# Autoría y créditos

Proyecto conceptual y arquitectónico de Zenoytdl, con documentación base orientada a desarrollo guiado por hitos, pruebas acumulativas, contratos explícitos y encapsulación de `ytdl-sub` mediante una arquitectura propia extensible.
