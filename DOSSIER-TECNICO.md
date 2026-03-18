# dossier-tecnico.md

# Dossier técnico avanzado del proyecto

## 1. Resumen ejecutivo técnico

Este proyecto implementa una capa declarativa y orquestada sobre `ytdl-sub` para construir una biblioteca multimedia estructurada a partir de fuentes de YouTube, con estas propiedades clave:

- modelado funcional por perfiles;
- configuración humana compacta;
- generación automática de YAML reales compatibles con `ytdl-sub`;
- ejecución inteligente basada en estado previo y conteo local;
- postproceso especializado por dominio:
  - `music-playlist` -> limpieza + enriquecimiento con `beets`;
  - `ambience-video` / `ambience-audio` -> recorte posterior con `ffmpeg`;
- validación end-to-end con scripts PowerShell y shell embebido;
- persistencia operativa mediante logs, estado JSON y estructura estable de salida.

El sistema no se limita a “descargar vídeos”. En realidad actúa como una mini-plataforma de compilación y ejecución para colecciones multimedia tipadas.

---

## 2. Objetivo técnico real

El objetivo no es escribir YAML de `ytdl-sub` a mano para cada caso, sino disponer de:

1. un modelo declarativo de alto nivel;
2. un generador que traduzca ese modelo a sintaxis real válida;
3. una preparación inteligente de ejecución que evite trabajo redundante;
4. una capa de validación y postproceso dependiente del tipo de medio.

En otras palabras, el proyecto separa:

- **intención funcional** -> `profiles-custom.yml` + `subscription-custom.yml`
- **compilación** -> `generate-ytdl-config.py`
- **planificación** -> `prepare-subscriptions-runset.py`
- **ejecución** -> `ytdl-sub`
- **postproceso especializado** -> `clean-music-filenames.ps1`, `beets`, `trim-ambience-video.py`
- **validación** -> `test-e2e-perfiles-subscriptions.ps1`, `validate-test-e2e-perfiles-subscriptions.ps1`, `bloque1-test.ps1`, `bloque2-test.ps1`

---

## 3. Topología lógica del sistema

## 3.1. Entradas declarativas

### `profiles-custom.yml`
Define familias funcionales, defaults y semántica de perfil.

Ejemplos de perfiles observados:
- `Canales-youtube`
- `Podcast`
- `TV-Serie`
- `Music-Playlist`
- `Ambience-Video`
- `Ambience-Audio`

### `subscription-custom.yml`
Instancia perfiles concretos mediante:
- `custom_name`
- una o varias `sources`
- overrides por fuente como `url`, `max_items`, `quality`, `format`, `min_duration`, `max_duration`, etc.

---

## 3.2. Artefactos generados

### `config.generated.yaml`
Contiene:
- `configuration`
- `presets`

Cada preset está ya transformado al esquema que realmente entiende `ytdl-sub`.

### `subscriptions.generated.yaml`
Mapa final de suscripciones instanciadas por preset.

### `beets.music-playlist.yaml`
Se genera solo si el conjunto resultante incluye `music-playlist`.

### `subscriptions.runset.yaml`
Subconjunto ejecutable derivado del estado actual del sistema.

### `.recent-items-state.pending.json`
Estado provisional calculado durante la preparación.

### `.recent-items-state.json`
Estado consolidado y operativo tras una ejecución exitosa.

---

## 3.3. Salidas multimedia

Rutas observadas:
- `/downloads/Canales-youtube/{subscription_root}`
- `/downloads/Podcast/{subscription_root}/{source_target}`
- `/downloads/TV-Serie/{subscription_root}`
- `/downloads/Music-Playlist/{subscription_root}`
- `/downloads/Ambience-Video/{subscription_root}`
- `/downloads/Ambience-Audio/{subscription_root}`

En host Windows, el proyecto se ha validado sobre:

```text
E:\Docker_folders\ydtl-custom-downloads
```

---

## 4. Modelo de datos funcional

## 4.1. Perfil vs suscripción vs fuente

### Perfil
Es la clase funcional:
- define defaults;
- define el comportamiento semántico esperado;
- controla cómo se construye el preset de `ytdl-sub`.

### Suscripción
Es una entidad lógica agrupadora:
- tiene un `custom_name`;
- puede tener una o múltiples fuentes;
- comparte raíz de salida.

### Fuente
Es la unidad concreta de entrada:
- una URL de canal;
- una playlist;
- un single video;
- con overrides específicos.

---

## 4.2. Parámetros observados

### A nivel de defaults
- `max_items`
- `quality`
- `format`
- `min_duration`
- `max_duration`
- `date_range`
- `embed_thumbnail`
- `audio_quality`

### A nivel de source
- `url`
- overrides puntuales de los mismos parámetros

---

## 4.3. Semántica diferenciada por perfil

### `Canales-youtube`
- estructura tipo Jellyfin TV Show by Date;
- resolución acotada;
- normalmente usa top reciente con `max_items > 0`.

### `Podcast`
- descarga audio, no vídeo;
- activa `audio_extract`;
- usa `output_directory` que incluye raíz y `source_target`.

### `TV-Serie`
- varias fuentes pueden converger sobre una serie lógica única;
- estructura pensada para Jellyfin;
- usa `tv_show_name`.

### `Music-Playlist`
- salida plana por carpeta;
- habitualmente `max_items = 0` para colección completa;
- enriquecimiento posterior con beets.

### `ambience-video`
- `max_duration` no es filtro de entrada;
- se convierte en `postprocess_trim_max_s`;
- recorte posterior tras descarga.

### `ambience-audio`
- mismo enfoque conceptual que `ambience-video`, pero en audio.

---

## 5. Anatomía interna de `generate-ytdl-config.py`

## 5.1. Responsabilidad principal

Este script actúa como compilador del modelo declarativo a artefactos concretos de ejecución.

Sus salidas principales son:
- `config.generated.yaml`
- `subscriptions.generated.yaml`
- opcionalmente `beets.music-playlist.yaml`

---

## 5.2. Decisiones de diseño detectables

### Base directory autorreferenciada
Usa:

```python
BASE_DIR = Path(__file__).resolve().parent
```

Con ello desacopla las rutas del cwd siempre que los ficheros estén en la misma carpeta.

### IO YAML segura
- valida existencia;
- usa `yaml.safe_load`;
- serializa con `safe_dump`;
- mantiene `allow_unicode=True`, `sort_keys=False`, `width=1000`.

### `slugify`
Normaliza:
- minúsculas;
- NFKD;
- ASCII;
- guiones;
- colapsado de separadores.

Esto afecta a:
- nombres de preset;
- nombres de suscripción;
- nombres de raíz;
- `source_target`.

---

## 5.3. Detección de tipo de fuente

La extracción de `source_target` se basa en parseo de URL:
- `watch?v=...`
- `list=...`
- `youtube.com/@...`
- `youtube.com/channel/...`
- `youtube.com/user/...`
- `youtube.com/c/...`
- `youtu.be/...`
- último segmento de path como fallback

Esto resuelve un problema clave: poder construir identificadores estables y directorios consistentes sin depender de naming arbitrario.

---

## 5.4. Separación entre `preset_name` y `subscription_name`

El generador construye:
- `preset_name = "{profile_key}-{subscription_root}-{source_target}"`
- `subscription_name = "{subscription_root}-{source_target}"`

Este detalle es importante:
- evita colisiones;
- mantiene unicidad global de preset;
- permite conservar una raíz lógica (`subscription_root`) y una diferenciación por fuente.

---

## 5.5. Mapeo semántico de duración

El generador distingue dos usos de `max_duration`:

### Perfiles normales
Se transforma en:
- `filter_duration_max_s`

### Perfiles ambience
Se transforma en:
- `postprocess_trim_max_s`

Esa separación evita el error conceptual de usar un filtro de entrada donde realmente se desea un recorte posterior del fichero final.

---

## 5.6. Inclusión condicional de `beets.music-playlist.yaml`

La variable `includes_music_playlist` se activa al detectar el profile slug `music-playlist`.

Esto demuestra una decisión de diseño interesante:
- el postproceso musical es tratado como capacidad adicional;
- no contamina el resto de perfiles.

---

## 5.7. Estructura base de configuración

`config.generated.yaml` incorpora:

```yaml
configuration:
  working_directory: /tmp/ytdl-sub-working-directory
  file_name_max_bytes: 255
  persist_logs:
    keep_successful_logs: true
    logs_directory: /config/logs
  lock_directory: /tmp
```

Implicaciones:
- los logs viven de forma persistente;
- el workdir es efímero y limpiable;
- los locks se centralizan en `/tmp`;
- hay control explícito del largo máximo del nombre de fichero.

---

## 5.8. Presets construidos por tipo

El script fabrica presets reales, no abstractos. Ejemplos observados:
- `Jellyfin TV Show by Date`
- `Max 720p`
- `Only Recent`
- `Filter Duration`
- `Max MP3 Quality`

Además aplica overrides específicos como:
- `enable_throttle_protection: false`
- `tv_show_directory`
- `output_options`
- `audio_extract`
- `merge_output_format`

La presencia de estas piezas confirma que el generador traduce del modelo conceptual al dialecto real de `ytdl-sub`, corrigiendo incompatibilidades históricas ya resueltas.

---

## 6. Anatomía interna de `prepare-subscriptions-runset.py`

## 6.1. Responsabilidad principal

Este script no descarga nada. Su función es preparar el plan de ejecución mínimo necesario para esa pasada.

Produce:
- `subscriptions.runset.yaml`
- `.recent-items-state.pending.json`

---

## 6.2. Idea arquitectónica clave

No todas las suscripciones generadas deben ejecutarse cada vez.

El script compara:
- estado previo (`.recent-items-state.json`);
- contenido resoluble remoto (IDs recientes o completos);
- conteo local real de ficheros;
- estrategia de descarga de la URL.

Con eso decide:
- `RUN`
- `SKIP`

---

## 6.3. `MEDIA_RULES`

Define por perfil:
- directorio esperado;
- extensiones válidas

Esto permite:
- conteo local de ficheros;
- verificación física de existencia;
- razonamiento homogéneo por familia.

Es un pivot estructural del sistema.

---

## 6.4. Estrategias de descarga

La lógica trabaja con al menos estas estrategias:
- `channel`
- `playlist`
- `single_video`

Consecuencias:

### Canal / playlist con `max_items > 0`
Se obtienen los IDs recientes top N y se compara:
- contra conteo local esperado;
- contra el estado previo.

### Canal / playlist con `max_items = 0`
Se resuelve la fuente completa, y se detecta:
- descarga inicial completa;
- consolidación sin reejecución;
- fuente completa intacta;
- fuente completa cambiada.

### Single video
Se usa una lista de un único `selected_id`.

---

## 6.5. Heurística de decisión

### Caso A — faltan ficheros locales
`RUN`

### Caso B — top reciente intacto
`SKIP`

### Caso C — cambió top reciente
`RUN`

### Caso D — no hay estado previo pero ya hay local
Consolidación sin reejecución en algunos flujos.

### Caso E — no se pudieron resolver IDs
`RUN` conservador.

Este diseño prioriza:
- evitar redescarga redundante;
- no dejar pasar faltantes reales;
- no bloquearse por incapacidad temporal de resolver la fuente.

---

## 6.6. Estado pendiente y commit diferido

El script escribe un estado **pending** en vez de tocar directamente el estado estable.

Eso es una excelente decisión de robustez:
- si la ejecución falla, no “miente” sobre el sistema;
- solo se consolida a `.recent-items-state.json` tras una pasada satisfactoria.

---

## 7. Postproceso musical

## 7.1. `clean-music-filenames.ps1`

Este script limpia nombres antes de la importación en beets.

### Qué hace
- normaliza espacios;
- reemplaza variantes Unicode de guiones;
- elimina marcadores como:
  - `[Official Video]`
  - `[Official Audio]`
  - `(Remastered 2011)`
  - `(Lyric Video)`
  - `(HD)`
  - etc.
- simplifica versiones “cover”;
- evita nombres vacíos;
- detecta colisiones;
- renombra solo si el resultado cambió.

### Por qué existe
Los títulos de YouTube suelen ser ruidosos y reducen drásticamente el matching con bases de datos musicales. La limpieza previa aumenta la calidad de emparejamiento de beets.

---

## 7.2. `beets.music-playlist.yaml`

### Configuración observada
- `directory: /downloads/Music-Playlist`
- `library: /config/musiclibrary.db`
- plugins:
  - `fromfilename`
  - `chroma`
  - `discogs`
  - `lastgenre`
  - `scrub`
  - `fetchart`
  - `embedart`

### Política de import
- `write: true`
- `move: false`
- `copy: false`
- `resume: false`
- `incremental: false`
- `singletons: true`
- `group_albums: false`
- `default_action: apply`
- `none_rec_action: skip`
- log persistido en `/config/logs/beets-import.log`

### Implicación operativa
El pipeline musical no intenta forzar álbumes ni mover ficheros. Se centra en:
- enriquecer singles/temas;
- escribir metadata cuando hay match razonable;
- saltar limpiamente cuando no lo hay.

---

## 7.3. Contenedor beets separado

La ejecución real se hace en `beets-streaming2`, no en `ytdl-sub`.

Ventajas:
- aislamiento de responsabilidad;
- posibilidad de tener librería db separada;
- toolchain acústica y plugins encapsulados.

---

## 8. Postproceso ambience

## 8.1. `trim-ambience-video.py`

Pese al nombre, el script sirve tanto para vídeo como para audio.

### Capacidades
- parsea duraciones tipo `3h3m3s` o `HH:MM:SS`;
- distingue extensiones de vídeo y audio;
- recorta desde el inicio;
- usa `ffmpeg -c copy` para máxima velocidad;
- valida con `ffprobe`;
- gestiona reemplazo atómico del original;
- soporta `--faststart`;
- soporta `--skip-output-probe`.

---

## 8.2. Estrategia de recorte

### Filosofía
No se filtra la entrada por duración máxima en perfiles ambience. Primero se descarga el activo y luego se recorta al máximo deseado.

### Beneficios
- mejor control del fichero final;
- independencia de metadatos de duración remotos;
- coherencia con el caso “single_video ambience muy largo”.

---

## 8.3. Tolerancia de “ya recortado”

La constante:

```python
ALREADY_TRIMMED_TOLERANCE_SECONDS = 2.0
```

permite idempotencia práctica:
- si el fichero ya está dentro del límite + tolerancia, no se re-recorta.

---

## 8.4. Reemplazo robusto

El recorte:
1. genera temporal `.trimmed`;
2. mueve original a `.bak`;
3. sustituye;
4. limpia backup.

Si algo falla durante el replace, intenta restaurar el original.

Es una implementación razonablemente segura para automatización.

---

## 9. Scripts de prueba y validación

## 9.1. `test-e2e-perfiles-subscriptions.ps1`

Es el orquestador real de la prueba integral.

### Etapas observadas
1. preparar contexto sin borrar descargas existentes;
2. regenerar YAML;
3. preparar runset;
4. copiar script de trim al contenedor;
5. ejecutar ytdl-sub real;
6. consolidar estado pending -> estable;
7. limpieza musical;
8. importación beets;
9. recorte ambience-video;
10. recorte ambience-audio.

### Valor técnico
Es más que un test. Es una receta operacional reproducible.

---

## 9.2. `validate-test-e2e-perfiles-subscriptions.ps1`

Es el verificador posterior.

### Inspecciones que realiza
- cabeceras y tamaños de YAML generados;
- árboles de salida;
- conteos por tipo;
- duraciones y tamaño de medios;
- inspección de streams con ffprobe;
- comprobación de duración final del trim;
- búsqueda de residuos `.bak`, `.tmp`, `.part`, `.trimmed`;
- revisión de logs;
- estado de `/tmp` y del working_directory.

### Valor técnico
Cubre tanto consistencia lógica como integridad física del sistema.

---

## 9.3. `bloque1-test.ps1` y `bloque2-test.ps1`

Están orientados a comprobar `music-playlist` en dos fases:

### Bloque 1
- reset de directorio de salida;
- limpieza de workdir;
- borrado de logs asociados;
- reset de db/log de beets;
- ejecución e2e;
- conteo de MP3;
- localización de log final.

### Bloque 2
- nueva pasada sobre estado ya existente;
- conteo final;
- comprobación de entradas “already been recorded in the archive”;
- revisión de últimas líneas del log de beets.

### Valor técnico
Permiten demostrar no solo “descarga”, sino también comportamiento incremental y ausencia de trabajo redundante.

---

## 10. Contratos implícitos del sistema

## 10.1. Contrato de directorio común

Todos los scripts asumen que:
- los YAML custom;
- los generados;
- los scripts Python/PS1

coexisten en el mismo directorio de configuración.

---

## 10.2. Contrato de nombres de perfil

`profile_name` y `profile_type` deben estar alineados funcionalmente. El generador usa `profile_type` como referencia semántica real.

---

## 10.3. Contrato de volumen Docker

El sistema asume:
- `/config` persistente;
- `/downloads` persistente;
- contenedor `ytdl-sub` con `yt-dlp`, `ffmpeg`, shell;
- contenedor `beets-streaming2` con beets operativo.

---

## 10.4. Contrato de extensiones por familia

El conteo y la verificación dependen de extensiones definidas en `MEDIA_RULES`. Si introduces nuevos formatos, conviene ampliar esa tabla o el runset tomará decisiones erróneas sobre existencia local.

---

## 11. Flujo técnico completo

## 11.1. Cadena de procesamiento

1. se editan `profiles-custom.yml` y/o `subscription-custom.yml`;
2. `generate-ytdl-config.py` compila el modelo;
3. `prepare-subscriptions-runset.py` decide qué ejecutar;
4. `ytdl-sub` consume `config.generated.yaml` + `subscriptions.runset.yaml`;
5. se consolida el estado;
6. si hay música:
   - limpieza de nombres;
   - beets import;
7. si hay ambience:
   - recorte posterior;
8. validación con scripts e inspecciones.

---

## 11.2. Principio de idempotencia aproximada

No es una idempotencia matemática perfecta, pero el diseño la busca mediante:
- `maintain_download_archive: true`;
- comparación de IDs recientes;
- uso de estado estable/pending;
- saltos en runset;
- tolerancia de trim;
- comportamiento no destructivo de beets para no-match.

---

## 12. Riesgos y puntos delicados

## 12.1. Dependencia del naming remoto
YouTube puede cambiar nombres, disponibilidad o estructura de entradas.

## 12.2. Matching imperfecto en música
Beets depende de la calidad del nombre y de la existencia de candidatos razonables.

## 12.3. Fragilidad ante cambios en formatos remotos
Si cambia el comportamiento de `yt-dlp` o de la fuente, el modelo puede seguir siendo correcto pero fallar operativamente.

## 12.4. Estado incoherente si se omite el commit
Si no se mueve `.recent-items-state.pending.json` a `.recent-items-state.json`, el runset inteligente perderá parte de su sentido incremental.

## 12.5. Extensiones no contempladas
El conteo local y las decisiones del runset dependen de conjuntos de extensiones conocidas.

---

## 13. Mejores prácticas técnicas recomendadas

## 13.1. Mantener custom y generated separados
Nunca edites a mano los generados como fuente de verdad.

## 13.2. Regenerar antes de preparar runset
Evita planes de ejecución basados en artefactos obsoletos.

## 13.3. Consolidar estado solo tras éxito
Mantiene la honestidad del sistema.

## 13.4. Ejecutar limpieza musical antes de beets
Mejora notablemente el matching.

## 13.5. Validar con ffprobe
Especialmente en ambience, donde importa el medio final real, no solo que “el comando terminó”.

---

## 14. Posibles extensiones futuras

## 14.1. Generalizar postprocesos por tipo
Pasar de scripts ad hoc a una tabla declarativa de postprocesos.

## 14.2. Motor de selección por políticas
Ejemplo:
- latest N
- latest by date range
- full sync
- rolling window

## 14.3. Estado por hash o manifest local
Además de selected IDs, guardar inventario local más rico.

## 14.4. Validación estructural previa
Añadir schema validation explícita para custom YAML antes de compilar.

## 14.5. Reporting HTML/Markdown automático
Generar un informe de cada ejecución con:
- runset;
- tiempos;
- ficheros añadidos;
- errores;
- métricas por perfil.

---

## 15. Lectura técnica de los ficheros del proyecto

### `profiles-custom.yml`
Declaración de defaults por tipo.

### `subscription-custom.yml`
Instanciación operativa real.

### `generate-ytdl-config.py`
Compilador principal.

### `prepare-subscriptions-runset.py`
Planificador incremental.

### `config.generated.yaml`
Configuración final consumible por `ytdl-sub`.

### `subscriptions.generated.yaml`
Mapa completo de trabajo.

### `subscriptions.runset.yaml`
Subconjunto ejecutable de la pasada.

### `beets.music-playlist.yaml`
Política de enriquecimiento musical.

### `clean-music-filenames.ps1`
Pre-normalización heurística de títulos.

### `trim-ambience-video.py`
Postproceso de recorte con ffmpeg/ffprobe.

### `test-e2e-perfiles-subscriptions.ps1`
Workflow integral real.

### `validate-test-e2e-perfiles-subscriptions.ps1`
Validación técnica exhaustiva.

### `bloque1-test.ps1`
Prueba inicial intensiva de music-playlist.

### `bloque2-test.ps1`
Prueba incremental de segunda pasada.

### `estado_perfiles_ytdl_sub_actualizado_v4.md`
Histórico técnico-funcional y estado de cierre de perfiles.

---

## 16. Conclusión técnica

El proyecto ya no es simplemente una colección de scripts, sino una arquitectura ligera de ingestión multimedia declarativa con:

- compilación de configuración;
- planificación incremental;
- tratamiento semántico por tipo de contenido;
- postproceso especializado;
- observabilidad suficiente para operar y depurar;
- validación reproducible.

La pieza más importante conceptualmente no es la descarga, sino la **traducción estable entre el modelo funcional deseado y el comportamiento real del stack**. Esa traducción es la que hace viable escalar perfiles, variar fuentes, probar cambios y conservar coherencia operativa sin rehacer manualmente YAML complejos en cada iteración.
