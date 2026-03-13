# Roadmap de desarrollo por hitos

> **Prioridad documental (orden de autoridad):**
> 1. `hitos-and-test.md`
> 2. `AGENTS.md`
> 3. resto de documentación.

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
**Objetivo:** dejar listo todo lo necesario para empezar desde cero sin deuda inicial.
**Foco:** Este hito no construye todavía funcionalidad de negocio, pero es crítico porque fija el terreno donde se apoyará todo lo demás. El documento deja claro que Zenoytdl no es un script puntual, sino una herramienta con arquitectura propia, capas bien separadas y proyección a futuro. Eso significa que empezar “rápido” pero sin estructura sería contraproducente: rompería la coherencia del modelo, haría más difícil la validación y comprometería la estabilidad del core. Aquí se prepara el repo, las convenciones, el entorno y la base mínima para que los siguientes hitos se implementen sin improvisación.
**Dependencias:** ninguno.

## Hito 1 — Preparación de contenedorización y runtime objetivo
**Objetivo:** dejar decididos desde el principio los condicionantes técnicos necesarios para que el core pueda terminar como herramienta desplegable en contenedor Docker, sin contaminar todavía la implementación del núcleo.
**Foco:** Este hito existe para evitar un error clásico: desarrollar todo el core pensando implícitamente en un entorno local arbitrario y solo al final intentar “meterlo en Docker”. En este proyecto eso sería especialmente mala idea porque el documento ya presupone rutas persistentes, SQLite, caché, artefactos compilados y ejecución por subprocess sobre ytdl-sub. Por tanto, aquí no se dockeriza todavía, pero sí se fijan las reglas del juego del runtime objetivo: filesystem esperado, resolución de binarios, política de volúmenes, logs y persistencia. Eso permite que todos los hitos posteriores nazcan con compatibilidad container-first, aunque el empaquetado real llegue al final.
**Dependencias:** hito 0.

## Hito 2 — Modelado del dominio interno
**Objetivo:** definir el lenguaje interno real de Zenoytdl.
**Foco:** Este es el primer hito verdaderamente “de producto”. Aquí se decide cómo piensa Zenoytdl el problema. El documento insiste en que el valor principal de la herramienta está en ofrecer una semántica más clara que ytdl-sub: perfiles, suscripciones, postprocesados, overrides, estado, caché, colas y control de ejecución. Por eso el dominio no puede ser una traducción pobre de ytdl-sub, sino un modelo propio, estable y expresivo. Si este hito queda bien hecho, los siguientes módulos se apoyarán sobre conceptos nítidos; si queda mal hecho, toda la herramienta se volverá ambigua.
**Dependencias:** hito 1.

## Hito 3 — Diseño del contrato de configuración YAML
**Objetivo:** convertir el dominio en un contrato declarativo claro y mantenible.
**Foco:** Aquí el dominio deja de ser algo solo interno y se convierte en contrato externo. El esquema y el documento son muy claros: la herramienta debe estructurarse en torno a `general.yaml`, `profiles.yaml`, `subscriptions.yaml` y `ytdl-sub-conf.yaml`. Estos ficheros no son meros detalles técnicos; son la forma en que el usuario y, en el futuro, otras capas del sistema, expresarán la intención funcional. Por eso este hito no consiste solo en “aceptar YAML”, sino en diseñar una configuración de alto nivel, estable, legible y con semántica propia.
**Dependencias:** hito 2.

## Hito 4 — Parseo y carga de configuración
**Objetivo:** cargar todos los YAML obligatorios en memoria y convertirlos a modelo interno.
**Foco:** Una vez diseñado el contrato, este hito construye la frontera de entrada real del sistema. No basta con parsear YAML sintácticamente: hay que convertirlo en objetos internos correctos, tipados y aptos para validación posterior. Este paso es especialmente importante porque define el primer punto donde la herramienta transforma input externo en estructura semántica. También prepara la base para firmas, hashes, caché y trazabilidad de configuración.
**Dependencias:** hito 3.

## Hito 5 — Validación estructural y semántica
**Objetivo:** detectar cuanto antes configuraciones inválidas.
**Foco:** Este hito materializa uno de los principios rectores del esquema: **validación fuerte antes de ejecutar**. La herramienta no debe descubrir errores tarde, cuando ya haya compilado o invocado ytdl-sub, sino lo antes posible y con mensajes claros. Aquí se fijan reglas estructurales, relaciones cruzadas y restricciones semánticas. Este bloque es uno de los más sensibles, porque de su robustez depende la confianza del sistema y la calidad de la UX futura, aunque la UX visual todavía no exista.
**Dependencias:** hito 4.

## Hito 6 — Sistema de herencia y resolución perfil → suscripción
**Objetivo:** obtener configuración efectiva real antes de traducir nada.
**Foco:** El documento separa claramente niveles: perfil, suscripción, postprocesado, configuración general y conectividad con ytdl-sub. En la práctica eso exige un resolvedor que combine capas y produzca una configuración efectiva determinista. Este hito es el puente entre el mundo declarativo y el mundo operativo: aquí se decide qué valores quedan finalmente activos, de dónde vienen y con qué precedencia. También se prepara la base para caché y deduplicación, porque sin una firma estable de la configuración efectiva no puede haber reutilización fiable.
**Dependencias:** hito 5.

## Hito 7 — Sistema de overrides controlados
**Objetivo:** permitir flexibilidad sin romper la semántica del perfil.
**Foco:** Los overrides son un punto delicado: añaden potencia, pero también pueden destruir la coherencia del modelo si se dejan libres. El documento propone control explícito con políticas como `allowed`, `restricted` y `forbidden`, y da ejemplos concretos. Por tanto, este hito debe blindar el sistema para que las suscripciones puedan personalizarse sin desnaturalizar el perfil asignado. Conceptualmente, aquí se protege la semántica de negocio frente a configuraciones oportunistas o erróneas.
**Dependencias:** hito 6.

## Hito 8 — Modelado de postprocesados
**Objetivo:** tratar los postprocesados como parte formal del core.
**Foco:** El documento no trata el postprocesado como un extra, sino como parte del comportamiento estructural del sistema. Eso obliga a modelarlo formalmente: herencia, activación, compatibilidad, parámetros y relación con perfiles y suscripciones. Aquí el objetivo no es ejecutar todavía todos los efectos finales, sino garantizar que el sistema sabe describirlos y resolverlos como parte de su configuración efectiva. Esto prepara la compilación e integración posterior.
**Dependencias:** hito 7.

## Hito 9 — Contrato de integración con ytdl-sub
**Objetivo:** convertir `ytdl-sub-conf.yaml` en la fuente de verdad del acoplamiento.
**Foco:** Este hito es la formalización del acoplamiento con la capa inferior. El documento insiste en que Zenoytdl **no reemplaza** ytdl-sub: lo encapsula y lo usa como motor. Eso significa que la traducción no puede quedar dispersa en código arbitrario, sino centralizada en un contrato explícito. `ytdl-sub-conf.yaml` debe gobernar mappings, compatibilidad, reglas de traducción, validación y modo de invocación. Si este contrato queda bien resuelto, el sistema será adaptable y mantenible; si queda mal resuelto, la integración se volverá frágil y opaca.
**Dependencias:** hito 8.

## Hito 10 — Traducción a modelo ytdl-sub
**Objetivo:** transformar la configuración efectiva Zenoytdl en configuración ejecutable por la capa inferior.
**Foco:** Una cosa es tener un contrato de integración; otra es aplicar ese contrato para traducir configuraciones reales. Este hito implementa el traductor propiamente dicho. Debe transformar una semántica de alto nivel, más rica y abstracta, en una estructura compatible con ytdl-sub, sin perder coherencia ni dejar estados ambiguos. El esquema ASCII separa claramente el modelo interno de la validación/compilación/traducción a ytdl-sub, y este hito materializa esa frontera.
**Dependencias:** hito 9.

## Hito 11 — Compilación de artefactos ejecutables
**Objetivo:** producir artefactos finales consumibles por ytdl-sub.
**Foco:** Tras traducir, hace falta una fase estable y reproducible de compilación. El documento habla de artefactos compilados para ytdl-sub y de un directorio específico para ellos. Eso significa que Zenoytdl no debe ejecutar “sobre la marcha” sin rastro, sino producir una salida materializable, inspeccionable y trazable. Este hito fija el contrato entre la capa de traducción y la de ejecución.
**Dependencias:** hito 10.

## Hito 12 — Módulo de ejecución controlada de ytdl-sub
**Objetivo:** invocar ytdl-sub como motor subyacente de forma controlada y trazable.
**Foco:** Aquí Zenoytdl deja de ser solo “modelado y compilación” y pasa a operar de verdad. El documento especifica invocación por subprocess y deja claro que ytdl-sub es motor subyacente, no interfaz. Este hito implementa una ejecución encapsulada, trazable y gobernada por el core. Debe ser robusta ante errores, tiempos de espera, logs y clasificación de fallos. Además, prepara el terreno para colas, estado y API.
**Dependencias:** hito 11.

## Hito 13 — Persistencia y estado operativo en SQLite
**Objetivo:** convertir la base de datos en la fuente de verdad operativa.
**Foco:** El esquema lo formula como principio rector: la persistencia debe ser la fuente de verdad operativa. Este hito fija que el sistema ya no dependerá solo del runtime actual o de memoria temporal, sino de un estado consolidado. Aquí se modelan ejecuciones, elementos conocidos, resultados, purgas, descargas, timestamps y firmas de configuración. Todo lo que venga después —anti-redescarga, colas, caché, API— necesita este cimiento.
**Dependencias:** hito 12.

## Hito 14 — Anti-redescarga, historial y trazabilidad
**Objetivo:** usar el estado para evitar repeticiones indebidas y poder explicar qué pasó.
**Foco:** Una vez existe estado persistente, ya es posible tomar decisiones operativas inteligentes. Este hito aprovecha esa base para que el sistema no reprocesse indefinidamente el mismo contenido y para que todas las decisiones relevantes queden trazadas. Este bloque es muy importante para que Zenoytdl se perciba como sistema maduro: no solo hace cosas, sino que sabe qué hizo, por qué y qué debe evitar repetir.
**Dependencias:** hito 13.

## Hito 15 — Retención, purga y limpieza
**Objetivo:** aplicar políticas de conservación reales sobre artefactos y estado.
**Foco:** Este bloque materializa la parte de “políticas de retención” que el documento considera parte central de la semántica del sistema. No se trata solo de borrar archivos antiguos, sino de aplicar reglas coherentes según publicación, límites de `max_items`, consistencia entre disco y base de datos, y trazabilidad de purgas. Este hito aporta sostenibilidad operativa y prepara el terreno para escenarios de larga duración.
**Dependencias:** hito 14.

## Hito 16 — Sistema de caché
**Objetivo:** reducir recomputaciones y mejorar fluidez operativa desde el core.
**Foco:** El documento es muy explícito: la caché no es un accesorio, sino parte central de la fluidez percibida. Aquí se introducen caches de validación, traducción, compilación y metadatos, con invalidación coherente. Este hito existe para que la herramienta responda de forma ágil sin sacrificar corrección. Para agentes IA, la regla clave es esta: la caché acelera, pero nunca puede convertirse en fuente de verdad por encima del estado o la configuración efectiva.
**Dependencias:** hito 15.

## Hito 17 — Gestor de colas: modelo y persistencia
**Objetivo:** introducir un modelo explícito de trabajo.
**Foco:** Al igual que la caché, el documento considera la cola parte esencial del comportamiento operativo. Este primer hito de colas define qué es un job, qué tipos existen, cómo se priorizan y cómo se persisten. No es todavía el momento de los workers completos, pero sí de dejar modelado el universo de trabajo. Esto ordena el sistema y evita que ejecución, validación y mantenimiento queden mezclados en llamadas ad hoc.
**Dependencias:** hito 16.

## Hito 18 — Gestor de colas: ejecución, reintentos y concurrencia
**Objetivo:** hacer que la cola no sea solo una tabla, sino un sistema operativo real del core.
**Foco:** Este hito convierte el modelo de trabajos en una maquinaria operativa. Aquí aparecen workers, deduplicación efectiva, backoff, dead-letter y reglas de concurrencia. El documento subraya que la cola aporta orden, control y priorización, y que junto con la caché mejora la percepción de rapidez y robustez. Por tanto, este bloque es esencial para que Zenoytdl funcione bien bajo carga, no solo en demos simples.
**Dependencias:** hito 17.

## Hito 19 — API propia del core
**Objetivo:** exponer una frontera estable y programable para operar Zenoytdl.
**Foco:** La API es una consecuencia natural del enfoque del documento: Zenoytdl debe ofrecer una interfaz programática consistente y servir de base a futuras interfaces desacopladas. Por eso la API no es un añadido ornamental, sino la frontera formal del núcleo. Aquí se exponen operaciones de consulta, validación, resolución, control de cola, sincronización e historial. Todo lo visual queda fuera; lo que se construye aquí es una interfaz estable y automatizable.
**Dependencias:** hito 18.

## Hito 20 — Suite de pruebas integral
**Objetivo:** demostrar que el sistema no solo existe, sino que funciona con garantías.
**Foco:** Este hito consolida todo el esfuerzo anterior en una red de seguridad técnica. El documento pide explícitamente una test suite completa antes de dar prioridad práctica a la UX. Aquí se integran todas las baterías: dominio, parseo, validación, traducción, compilación, persistencia, anti-redescarga, retención, caché, colas y API. Este hito no introduce nueva semántica, pero sí convierte el proyecto en una base confiable para evolución posterior.
**Dependencias:** hito 19.

## Hito 21 — Aplicación completa, endurecida y probada
**Objetivo:** cierre del proyecto core con el sistema completo y listo para servir de base a UX futura.
**Foco:** Este hito es el cierre funcional del núcleo antes del empaquetado final. Aquí ya no se trata de abrir nuevos bloques, sino de endurecer el conjunto: revisar arquitectura, afinar rendimiento, asegurar compatibilidad con ytdl-sub, pulir errores y dejar documentación técnica suficiente. Es el momento de convertir un conjunto de módulos correctos en un core realmente maduro. La UX sigue fuera, pero este hito prepara precisamente el terreno para que esa UX futura pueda construirse sobre una base estable.
**Dependencias:** hito 20.

## Hito 22 — Dockerización del core
**Objetivo:** empaquetar el core ya estabilizado como imagen Docker operable, sin alterar su contrato funcional ni su arquitectura principal.
**Foco:** Este hito transforma el core estable en un artefacto desplegable real. No debe rediseñar el sistema, sino empaquetarlo respetando su arquitectura: configuración externa, volúmenes persistentes, binarios de sistema, ytdl-sub, SQLite, caché, artefactos compilados y logs. El objetivo es que el contenedor sea una forma oficial de ejecutar Zenoytdl, no un experimento paralelo. Este hito conecta directamente con las decisiones tomadas al principio en el runtime objetivo.
**Dependencias:** hito 21.

## Coherencia cruzada con `plans/*.md`
- `plans/hito-03-contrato-yaml.md` mantiene el mismo foco de contrato YAML y secuencia dependiente del Hito 3.
- `plans/hito-09-integracion-ytdl-sub.md` mantiene el mismo foco de contrato de traducción e integración del Hito 9.
- `plans/hito-18-colas-ejecucion.md` mantiene el mismo foco de ejecución continua, concurrencia y parada limpia del Hito 18.
