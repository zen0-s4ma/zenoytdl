# Dossier técnico exhaustivo sobre ytdl-sub

## Descripción general y alcance del dossier

**ytdl-sub** es una herramienta de línea de comandos (CLI) que “orquesta” **yt-dlp** para descargar media desde servicios online (incluyendo entity["company","YouTube","video platform"]) y después **reformatear archivos y metadatos** para que se integren correctamente en bibliotecas y reproductores/servidores como entity["organization","Jellyfin","media server software"], entity["company","Plex","media server platform"], entity["company","Emby","media server platform"] o entity["organization","Kodi","media player software"], evitando depender de “scrapers” externos o plugins del reproductor para reconocer contenido descargado. citeturn39search3turn15view0turn13search16

En términos de modelo mental, **ytdl-sub separa “qué descargar” (subscriptions) de “cómo debe quedar” (presets)**. Los presets se construyen como composición de “plugins” (módulos funcionales) y se aplican a cada subscription, con un sistema de herencia y sobreescrituras (overrides) para reducir repetición. citeturn13search22turn13search8turn15view0

Este dossier se centra en:

- Describir **arquitectura**, **componentes**, **flujo de ejecución** y **capacidades** de ytdl-sub. citeturn13search22turn39search3turn13search8  
- Enumerar de forma estructurada **todas las opciones CLI**, **todas las claves principales de configuración**, **los plugins y sus campos documentados**, **presets preconstruidos** y **mecanismos de scripting/variables** según documentación oficial y ejemplos oficiales. citeturn44view0turn39search1turn10view2turn41view2turn42view6turn44view4turn43view3turn38view0turn43view5  
- Proporcionar un apartado final con **ejemplos completos y realistas** (sintéticos pero fieles al esquema) de **todos los tipos de ficheros de configuración** y de la herramienta (comandos). citeturn44view1turn43view0turn30view0turn27view1turn20search0turn36view0turn35view0  

La documentación oficial consultada (base primaria) está publicada en entity["organization","Read the Docs","documentation hosting"] y el repositorio/mantenimiento principal se realiza en entity["company","GitHub","code hosting platform"] (autor principal: entity["people","Jesse Bannon","ytdl-sub maintainer"]). citeturn39search3turn15view0turn13search12

## Arquitectura, flujo de ejecución y decisiones de diseño

El flujo descrito por la guía oficial se resume así:

1) El usuario ejecuta `ytdl-sub sub` (o `dl`) para procesar una o varias **subscription files**. citeturn13search22turn43view0turn44view1  
2) Cada subscription **selecciona presets** (prebuilt o custom). citeturn13search22turn15view0  
3) Un preset es, esencialmente, una **composición de configuraciones de plugins**, con **herencia** (base presets) y precedencia “el último gana” cuando hay claves superpuestas. citeturn13search22turn13search8  
4) Los plugins gobiernan:  
   - cómo invoca ytdl-sub a yt-dlp (formatos, match-filters, opciones internas),  
   - qué entradas se descargan o se filtran,  
   - cómo se reescriben nombres/rutas,  
   - qué metadatos se generan/embeben (NFO, tags, thumbnails, chapters/subtitles),  
   - y cómo se gestionan historiales y retención (download archive / keep rules). citeturn13search22turn41view8turn41view9turn42view12turn44view6  

### Capas lógicas

- **Capa declarativa (YAML)**: define presets, plugins y overrides con expresiones/formatters. citeturn39search3turn13search22turn10view2  
- **Capa de orquestación**: valida subscriptions, resuelve herencia de presets, materializa configuraciones efectivas por subscription, ejecuta dry-run si aplica. citeturn13search22turn44view0  
- **Capa de descarga (yt-dlp)**: descarga metadatos y media, aplicando `format`, `match_filters`, `ytdl_options`, etc. citeturn39search3turn44view4turn44view5turn42view15  
- **Capa de post-procesado**: embedding/conversión con ffmpeg (según plugins), escritura de NFO, tags, thumbnails, retención. citeturn39search1turn41view8turn44view3turn42view12turn44view6  

### Propiedades relevantes para diseñar una “capa por encima” (wrapper)

- **Determinismo por “config efectiva”**: ytdl-sub tiende a comportarse como un “compilador” de YAML: a partir de presets + overrides genera una configuración final por subscription, que luego ejecuta. Esto facilita construir un wrapper que genere YAML o `dl`-args de forma programática. citeturn13search22turn44view1turn44view0  
- **Escalabilidad operativa**: hay mecanismos explícitos para cron/automatización (throttle_protection, chunk downloads, locks, logs persistentes), diseñados para reducir fallos cuando se archivan canales grandes o se ejecuta frecuentemente. citeturn39search6turn44view6turn13search12  
- **Separación del “modelo de la biblioteca”**: prebuilt presets por “player” (Plex/Jellyfin/Emby/Kodi) aplican transformaciones específicas (p.ej. sanitización de números para Plex; NFO kodi_safe para caracteres). Esta es una capa clave de compatibilidad que un wrapper debería exponer como “perfil de destino”. citeturn39search0turn10view1turn15view0  

## Modelo de configuración, ficheros y sintaxis

ytdl-sub se configura principalmente con dos “familias” de ficheros YAML:

- `config.yaml`: configuración global del runtime + definición de presets custom (opcional, pero recomendado en usos avanzados). citeturn39search1turn13search12  
- Fichero(s) de subscriptions (por defecto `subscriptions.yaml`): define el árbol de subscriptions y los presets/overrides aplicados. citeturn10view2turn44view1turn30view0  

### Estructura de config.yaml

El `config.yaml` tiene dos secciones principales:

- `configuration`: opciones globales del programa (paths, locks, logs, aliases). citeturn39search1turn13search12  
- `presets`: presets custom definidos por el usuario (además de los prebuilt). citeturn39search1turn36view0  

Detalle completo de claves en `configuration`:

- `dl_aliases`: define alias para abreviar argumentos del subcomando `dl` (expande a cadenas de flags). citeturn39search1  
- `experimental.enable_update_with_info_json`: habilita `--update-with-info-json` (documentación advierte riesgo y recomienda backup). citeturn39search1turn44view1  
- `ffmpeg_path`, `ffprobe_path`: rutas a ejecutables; por defecto se asumen rutas típicas (Linux) o ejecutables junto a ytdl-sub en Windows. citeturn39search1  
- `file_name_max_bytes`: límite de tamaño de nombre de fichero (bytes). citeturn39search1  
- `lock_directory`: directorio temporal para locks que previenen ejecuciones paralelas; la doc avisa de problemas en montajes de red (debe residir en host). citeturn39search1  
- `persist_logs.keep_successful_logs`, `persist_logs.logs_directory`: persistencia de logs (por defecto no persistidos). citeturn39search1  
- `umask`: umask octal global aplicado a ficheros creados. citeturn39search1turn36view0  
- `working_directory`: staging/working dir para descargas antes de mover a destino final. citeturn39search1turn36view0  

### Estructura del subscription file

La “subscription file” define un árbol YAML de suscripciones. Conceptos clave:

- `__preset__`: bloque especial para definir configuración global (presets y/o overrides) aplicable a todo el fichero. citeturn10view2turn30view0turn27view1  
- **Agrupación por indentación**: las claves ancestro “heredan” a las claves descendientes; la subscription “real” suele ser el nodo más profundo que contiene URL(s). citeturn13search22turn10view2  
- **Pipes (`|`)** para aplicar múltiples presets/valores compartidos en una misma línea de grupo; ytdl-sub lo recomienda para componer presets sin repetición. citeturn14view2turn39search5  
- **Modo tilda (`~`)**: prefijo en el nombre de una subscription para permitir declarar override variables directamente debajo (especialmente útil para listas). citeturn39search6turn30view0turn35view0  
- **Multi-URL**: una subscription puede ser un string URL, una lista de URLs, o estructuras más ricas según plugin/preset (p.ej. `download.urls` con `variables` por URL). citeturn41view4turn44view3turn27view1turn30view0  

## Referencia exhaustiva de opciones y capacidades

### Opciones CLI

La invocación general es:

`ytdl-sub [GENERAL OPTIONS] {sub,dl,view} [COMMAND OPTIONS]` (en Windows: `ytdl-sub.exe`). citeturn43view0turn44view1  

#### General Options

Opciones comunes a todos los subcomandos (deben ir **antes** del subcomando): citeturn44view0turn43view0  

- `-h, --help`: muestra ayuda. citeturn44view0  
- `-v, --version`: versión del programa. citeturn44view0  
- `-c CONFIGPATH, --config CONFIGPATH`: ruta a config YAML; si no, usa `config.yaml`. citeturn44view0turn44view1  
- `-d, --dry-run`: previsualiza sin descargas y sin escribir en output dirs. citeturn44view0  
- `-l quiet|info|verbose|debug, --log-level quiet|info|verbose|debug`: nivel de logs en consola; default “verbose”. citeturn44view0  
- `-t TRANSACTIONPATH, --transaction-log TRANSACTIONPATH`: ruta para guardar transaction log de cambios (add/modify/delete). citeturn44view0  
- `-st, --suppress-transaction-log`: no imprime transaction logs. citeturn44view0  
- `-nc, --suppress-colors`: desactiva colores en salida. citeturn44view0  
- `-m MATCH [MATCH ...], --match MATCH [MATCH ...]`: selector para ejecutar solo subscriptions que coincidan (útil para “subset runs”). citeturn44view0  

#### Subscriptions Options (`sub`)

Ejecuta descargas definidas en uno o varios ficheros de subscriptions: `ytdl-sub [GENERAL OPTIONS] sub [SUBPATH ...]`. citeturn44view1turn42view1  

- `SUBPATH`: rutas a subscription files; por defecto `./subscriptions.yaml`. Usa config por `--config` o `./config.yaml`. citeturn44view1turn42view1  
- `-u, --update-with-info-json`: “actualiza” subscriptions con config actual usando `info.json`. citeturn44view1turn39search1  
- `-o DL_OVERRIDE, --dl-override DL_OVERRIDE`: sobreescribe valores usando sintaxis `dl` (ej. `--dl-override='--ytdl_options.max_downloads 3'`). citeturn44view1  

#### Download Options (`dl`)

Permite describir una subscription “en línea” con flags, equivalente al YAML pero usando puntos en vez de indentación. citeturn44view1turn43view2turn39search1  

Ejemplo conceptual: lo que en YAML sería `overrides: tv_show_name: ...` se pasa como `--overrides.tv_show_name ...`. citeturn44view1turn43view2turn39search1  

Además, `dl_aliases` permite crear flags cortos que expanden a flags largos. citeturn39search1  

### Opciones de config.yaml

Sección `configuration` (todas las claves documentadas): citeturn39search1turn13search12  

- `dl_aliases` *(map)*: alias de flags para `dl`. citeturn39search1  
- `experimental.enable_update_with_info_json` *(bool)*: habilita actualización con info.json (experimental). citeturn39search1turn44view1  
- `ffmpeg_path` *(string path)*: ruta a ffmpeg. citeturn39search1  
- `ffprobe_path` *(string path)*: ruta a ffprobe. citeturn39search1  
- `file_name_max_bytes` *(int)*: límite de tamaño de nombre. citeturn39search1  
- `lock_directory` *(string path)*: directorio de locks; evitar FS remotos. citeturn39search1  
- `persist_logs.keep_successful_logs` *(bool)* y `persist_logs.logs_directory` *(path requerido si persist_logs existe)*. citeturn39search1  
- `umask` *(string octal)*: permisos por defecto de ficheros. citeturn39search1turn36view0  
- `working_directory` *(path)*: staging dir. citeturn39search1turn36view0  

### Plugins y campos documentados

La documentación oficial lista los plugins y su propósito; algunos plugins son booleanos simples y otros son estructuras con campos. citeturn41view1turn7view0  

A continuación se detallan **todos los plugins listados en la referencia oficial** y **los campos que la documentación muestra explícitamente**.

#### audio_extract

Extrae audio de un fichero de vídeo. citeturn41view2  

- `codec` *(String)*: codec de salida; soporta `aac`, `flac`, `mp3`, `m4a`, `opus`, `vorbis`, `wav`, `best`. citeturn41view2  
- `quality` *(Float)*: calidad ffmpeg; VBR 0–9 o bitrate (p.ej. 128). citeturn41view2  
- `enable` *(Optional[OverridesFormatter])*: activación condicional vía override variable. citeturn41view2  

#### chapters

Embebe capítulos; puede añadir capítulos de SponsorBlock y eliminar capítulos por regex o por categorías SponsorBlock. citeturn42view5turn41view3  

- `embed_chapters` *(según ejemplo, bool)*: embebe capítulos. citeturn42view5  
- `allow_chapters_from_comments` *(Optional[Boolean])*: si no hay capítulos, intenta extraerlos de comentarios; default False. citeturn42view6  
- `remove_chapters_regex` *(Optional[List[RegexString]])*: lista de regex contra títulos de capítulo para eliminar. citeturn41view3turn42view5  
- `sponsorblock_categories` *(Optional[List[String]])*: categorías a embebir como capítulos; soporta lista (o “all”) con categorías como `"sponsor"`, `"intro"`, `"outro"`, `"selfpromo"`, `"preview"`, `"filler"`, `"interaction"`, `"music_offtopic"`, `"poi_highlight"`. citeturn41view3turn42view6  
- `remove_sponsorblock_categories` *(Optional[List[String]] o “all” según doc)*: categorías SponsorBlock a remover del output; restringido a las incluidas en `sponsorblock_categories` o “all”. citeturn41view3turn42view6  
- `force_key_frames` *(bool según ejemplo)*: forzar keyframes en cortes (más lento, potencialmente menos artefactos). citeturn42view6turn41view3  

#### date_range

Restringe por rango temporal de metadatos para decidir qué descargar; acepta expresiones como `now-2weeks` o fechas como `20200101`. citeturn42view7turn41view4  

- `before` *(según ejemplo: string)*: límite superior (p.ej. `"now"`). citeturn42view7  
- `after` *(expected type documentado)*: límite inferior (p.ej. `"today-2weeks"`). citeturn42view7  
- `breaks` *(según ejemplo: bool)*: control de “break early” (documentado en ejemplo). citeturn42view7  
- `type` *(Optional[OverridesFormatter])*: tipo de fecha, `upload_date` o `release_date`; default `upload_date`. citeturn41view4  
- `enable` *(Optional[OverridesFormatter])*: activación condicional. citeturn41view4  

#### download

Define URL(s) de descarga; soporta formas “single URL”, “multi URL” y un modo estructurado con variables por URL y thumbnails por playlist/canal. citeturn41view4turn41view4turn42view8turn44view3  

Formas documentadas:

- `download: "https://..."` (string). citeturn41view4  
- `download: [ "https://...", "https://..." ]` (lista). citeturn41view4  
- Estructura con `download.urls` (según ejemplo): citeturn42view8turn44view3  
  - `urls` *(requerido en este modo)*: lista de entradas. citeturn42view8  
  - Por elemento de `urls`:  
    - `url`: URL a descargar. citeturn42view8turn44view3  
    - `variables`: mapa de variables por URL (p.ej. `season_index`, `season_name`). citeturn42view8turn44view3  
    - `ytdl_options`: opciones específicas de yt-dlp por URL (ej. `break_on_existing`). citeturn44view3turn42view15  
    - `playlist_thumbnails`: lista de objetos `{name, uid}` para extraer arte (avatar/banner/etc). citeturn42view8turn44view3  

#### embed_thumbnail

Controla si se embeben thumbnails dentro del archivo audio/vídeo. citeturn44view3  

- `embed_thumbnail` *(Boolean, plugin booleano)*: `True`/`False`. citeturn44view3  

#### file_convert

Convierte ficheros a otra extensión; soporta conversión interna con yt-dlp o conversión custom con ffmpeg y args. citeturn44view3turn41view5  

- `convert_to` *(String)*: extensión destino; listas de soportados para vídeo (`avi`, `flv`, `mkv`, `mov`, `mp4`, `webm`) y audio (`aac`, `flac`, `mp3`, `m4a`, `opus`, `vorbis`, `wav`). citeturn44view3  
- `convert_with` *(Optional[String])*: `yt-dlp` o `ffmpeg`; default `yt-dlp`. citeturn41view5turn44view3  
- `ffmpeg_post_process_args` *(Optional[OverridesFormatter])*: args para `ffmpeg -i input ... output`. citeturn41view5turn44view3  
- `enable` *(Optional[OverridesFormatter])*: activación condicional. citeturn41view5turn44view3  

#### filter_exclude

Excluye una entrada si **cualquier** filtro evalúa True (OR). citeturn44view4  

- `filter_exclude` *(Array de expresiones/formatters)*: lista de filtros (variables o scripts). citeturn44view4  

#### filter_include

Incluye una entrada solo si **todos** los filtros evalúan True (AND). citeturn42view11turn44view4  

- `filter_include` *(Array de expresiones/formatters)*: lista de filtros. citeturn42view11turn44view4  

#### format

Define `--format` de yt-dlp (misma sintaxis que yt-dlp) para seleccionar calidad/streams. citeturn44view4  

- `format` *(String)*: expresión de formato (ej. `(bv*[height<=1080]+bestaudio/best[height<=1080])`). citeturn44view4  

#### match_filters

Define `--match-filters` de yt-dlp (misma sintaxis), con lista de filtros; una entrada se descarga si **cualquier** filtro se cumple; AND dentro de una misma expresión con `&`. citeturn44view5  

- `match_filters.filters` *(List[String])*: lista de expresiones match-filter. citeturn44view5  

#### music_tags

Añade tags a archivos de audio usando MediaFile (misma lib que beets). La clave es un **mapa de tags**; los nombres de tags dependen del tipo de fichero y de la librería. citeturn41view6turn44view5  

- `music_tags` *(Map)*: claves = tags (`title`, `album`, `artist`, `albumartist`, etc) y valores = formatters/string/listas (multi-tags). citeturn41view6turn44view5  
- Nota importante de fecha: `date` y `original_date` esperan `YYYY-MM-DD`, y `upload_date_standardized` es compatible. citeturn41view6  

#### nfo_tags

Genera un `.nfo` (XML) por cada fichero descargado; soporta tags, atributos XML, claves duplicadas, y modo `kodi_safe`. citeturn42view12turn41view11turn41view7  

Campos documentados:

- `enable` *(Optional[OverridesFormatter])*: activación condicional. citeturn42view12  
- `nfo_name` *(EntryFormatter)*: nombre del NFO. citeturn41view11turn42view12  
- `nfo_root` *(EntryFormatter)*: tag raíz XML. citeturn41view11turn42view12  
- `tags` *(NfoTags)*: mapa de tags; soporta atributos y listas (claves duplicadas). citeturn41view7turn41view11turn42view12  
- `kodi_safe` *(OverridesBooleanFormatterValidator)*: reemplaza caracteres unicode >3 bytes por `□`; default False. citeturn41view11turn39search0  

#### output_options

Define directorio/nombres de salida una vez finalizado el post-procesado e integra el **download archive** y políticas de retención. citeturn41view8turn41view9turn44view0  

Claves visibles en la referencia y ejemplos:

- `output_directory` *(requerido; OverridesFormatter en la práctica)*: carpeta destino. citeturn41view8  
- `file_name` *(requerido)*: nombre de fichero final (usa EntryFormatter). citeturn41view8  
- `thumbnail_name` *(opcional)*: nombre de thumbnail (EntryFormatter). citeturn41view8  
- `info_json_name` *(opcional)*: nombre de `info.json` (EntryFormatter). citeturn41view8  
- `download_archive_name` *(opcional)*: nombre del archivo de “download archive”. citeturn41view8  
- `keep_files_after` *(opcional)*: retiene sólo elementos “después” de una fecha; combina con `keep_max_files`. citeturn41view9  
- `keep_files_before` *(opcional)*: retiene sólo “antes” de una fecha; requiere `maintain_download_archive` True; usa sintaxis date_range. citeturn41view9  
- `keep_files_date_eval` *(str)*: fecha estándar `YYYY-MM-DD` usada para registrar y evaluar retención; default `upload_date_standardized`. citeturn41view9  

*(Nota práctica)*: En configuraciones reales se usa `maintain_download_archive: True` para evitar redescargas y habilitar retención basada en archive. citeturn40search4turn41view9  

#### split_by_chapters

Divide un fichero por capítulos en múltiples ficheros; cada uno se convierte en “entry” con variables derivadas. citeturn41view10  

- Variables nuevas por entry al dividir: `chapter_title`, `chapter_index`, `chapter_index_padded`, `chapter_count`. citeturn41view10  
- `when_no_chapters` *(String)*: comportamiento cuando no hay capítulos (en ejemplo: `"pass"`). citeturn41view10  

#### square_thumbnail

Convierte thumbnails a formato cuadrado; útil para representar álbumes de audio; soporta thumbnails “file” y “embedded”. citeturn42view14  

- `square_thumbnail` *(Boolean, plugin booleano)*: `True`/`False`. citeturn42view14  

#### subtitles

Descarga/embebe subtítulos; controla tipos, idiomas, auto-generados, requisitos y naming. citeturn41view12turn7view3  

- `enable` *(Optional[OverridesFormatter])*: activación condicional. citeturn7view3  
- `allow_auto_generated_subtitles` *(Optional[Boolean])*: permite auto-generados. citeturn7view3  
- `embed_subtitles` *(Optional[Boolean])*: embebe subtítulos en el fichero. citeturn7view3  
- `languages` *(Optional[List[String]] o String)*: idiomas a descargar; default “en”. citeturn7view3turn41view12  
- `languages_required` *(Optional[List[String]])*: idiomas obligatorios; si faltan, error (nota: en doc, el check es para subtítulos “file-based”). citeturn41view12  
- `subtitles_name` *(Optional[EntryFormatter])*: nombre del fichero de subtítulos; `lang` y `subtitles_ext` son variables dinámicas. citeturn41view12turn7view3  
- `subtitles_type` *(Optional[String])*: tipo: `srt` (default), `vtt`, `ass`, `lrc`. citeturn41view12turn7view3  

#### throttle_protection

Introduce pausas aleatorias y límites para reducir throttling, con rangos `min/max`. citeturn44view6turn41view13  

- `enable` *(Optional[OverridesFormatter])*: activación condicional. citeturn44view6  
- `max_downloads_per_subscription` *(Optional[Range])*: número de descargas por subscription. citeturn44view6  
- `sleep_per_download_s` *(Optional[Range])*: sleep entre descargas. citeturn44view6  
- `sleep_per_request_s` *(Optional[Range])*: sleep entre requests de metadatos; yt-dlp usa el máximo. citeturn44view6turn41view13  
- `sleep_per_subscription_s` *(Optional[Range])*: sleep entre subscriptions. citeturn41view13  
- `subscription_download_probability` *(Optional[Float])*: probabilidad de descargar una subscription (útil en cron; estadísticamente descarga “a largo plazo”). citeturn41view13  

#### ytdl_options

Permite pasar opciones al API de yt-dlp (no necesariamente idénticas a flags CLI; la doc indica pequeñas diferencias) y se recomienda consultar el docstring de yt-dlp para detalles. citeturn7view2turn42view15  

Ejemplos documentados de claves en `ytdl_options`:

- `ignoreerrors`, `break_on_existing`, `cookiefile`, `max_downloads`. citeturn42view15turn40search4  

### Scripting: variables, tipos, funciones

#### Tipos soportados

El sistema de scripting/formatting documenta tipos base y “type-hints” utilizados en firmas de funciones (relevante si tu wrapper quiere validar expresiones):

Tipos: `String`, `Integer`, `Float`, `Boolean`, `Array`, `Map`, `Null`. citeturn43view4  
Type-hints: `AnyArgument`, `Numeric`, `Optional`, `Lambda`, `LambdaReduce`, `ReturnableArguments`. citeturn43view4  

#### Static variables (variables de suscripción)

La doc lista estas variables estáticas (disponibles en contexto de subscription):

- `subscription_array`  
- `subscription_has_download_archive`  
- `subscription_indent_i`  
- `subscription_map`  
- `subscription_name`  
- `subscription_value`  
- `subscription_value_i` citeturn43view3  

#### Entry variables (variables por entry descargada)

La referencia oficial lista un conjunto amplio de “entry variables” (campo base, metadatos, playlist/source/upload/release, e índices internos de ytdl-sub). Un wrapper que genere plantillas de nombres/rutas debería tratar esto como el “catálogo oficial” de placeholders soportados. citeturn38view0turn39search8  

#### Scripting functions (catálogo de funciones)

La documentación lista funciones por categorías. A nivel de wrapper, las funciones son relevantes si vas a generar expresiones `{ ... }` con `%func(...)`. citeturn43view5turn43view6turn43view7turn44view2turn43view8  

Listado por categoría (nombres tal y como aparecen en la referencia):

- Array: `array`, `array_apply`, `array_apply_fixed`, `array_at`, `array_contains`, `array_enumerate`, `array_extend`, `array_first`, `array_flatten`, `array_index`, `array_overlay`, `array_product`, `array_reduce`, `array_reverse`, `array_size`, `array_slice`. citeturn43view5  
- Boolean: `and`, `bool`, `eq`, `gt`, `gte`, `is_array`, `is_bool`, `is_float`, `is_int`, `is_map`, `is_null`, `is_numeric`, `is_string`, `lt`, `lte`, `ne`, `not`, `or`, `xor`. citeturn43view5turn43view6  
- Conditional: `elif`, `if`, `if_passthrough`. citeturn43view6  
- Date: `datetime_strftime`. citeturn43view6  
- Error: `assert`, `assert_eq`, `assert_ne`, `assert_then`, `throw`. citeturn43view6  
- Json: `from_json`. citeturn43view7turn44view2  
- Map: `map`, `map_apply`, `map_contains`, `map_enumerate`, `map_extend`, `map_get`, `map_get_non_empty`, `map_size`. citeturn43view7turn44view2  
- Numeric: `add`, `div`, `float`, `int`, `max`, `min`, `mod`, `mul`, `pow`, `range`, `sub`. citeturn43view7turn44view2  
- Print: `print`, `print_if_false`, `print_if_true`. citeturn44view2  
- Regex: `regex_capture_groups`, `regex_capture_many`, `regex_capture_many_required`, `regex_capture_many_with_defaults`, `regex_fullmatch`, `regex_match`, `regex_search`, `regex_search_any`, `regex_sub`. citeturn44view2turn44view2  
- String: `capitalize`, `concat`, `contains`, `contains_all`, `contains_any`, `join`, `lower`, `pad`, `pad_zero`, `replace`, `slice`, `split`, `string`, `strip`, `titlecase`, `unescape`, `upper`. citeturn44view2turn43view8  
- Ytdl-sub: `legacy_bracket_safety`, `sanitize`, `sanitize_plex_episode`, `to_date_metadata`, `to_native_filepath`, `truncate_filepath_if_too_long`. citeturn43view8  

## Presets preconstruidos, variables de override y capacidades “listas para usar”

### TV Show Presets

La guía “TV Show Presets” documenta versiones específicas por reproductor con comportamientos distintos (p.ej. Plex sanitiza números y convierte a mp4; Kodi activa `kodi_safe`; Jellyfin/Emby generan NFO y gestionan poster art). citeturn39search0  

También documenta dos familias principales:

- **TV Show by Date**: temporadas/episodios basados en fecha de subida. Presets disponibles: `Kodi TV Show by Date`, `Jellyfin TV Show by Date`, `Emby TV Show by Date`, `Plex TV Show by Date`. citeturn39search0turn30view0  
- **TV Show Collection**: estructura por “seasons explícitas” con `s01_name`, `s01_url`, etc; permite separar playlists/canales por temporadas; existe en variantes equivalentes por player. citeturn39search0turn30view0  

Overrides documentados para reordenación por fecha (TV Show by Date):

- `tv_show_by_date_season_ordering`  
- `tv_show_by_date_episode_ordering` citeturn39search0  

### Media Quality Presets

Presets preconstruidos para especificar calidad de vídeo:

- `Max Video Quality`, `Max 2160p`, `Max 1440p`, `Max 1080p`, `Max 720p`, `Max 480p`. citeturn14view0  

Y para audio (asumiendo extracción de audio):

- `Max Audio Quality`, `Max MP3 Quality`, `Max Opus Quality`, `MP3 320k`, `MP3 128k`. citeturn14view0  

### Helper Presets

Incluyen presets orientados a operación y filtrado:

- `Only Recent` / `Only Recent Archive`: controlan retención por fecha y/o número máximo de ficheros; `Only Recent` puede eliminar automáticamente contenido “viejo” al salir de rango. citeturn39search6turn30view0  
- `Filter Keywords`: incluye/excluye por keywords en title/description, con `_eval` ANY/ALL; variables como `title_include_keywords`, `title_exclude_keywords`, `description_include_keywords`, `description_exclude_keywords` y sus `_eval`. citeturn39search6turn10view0  
- `Filter Duration`: filtra por duración con `filter_duration_min_s` y `filter_duration_max_s`. citeturn39search6  
- `Chunk Downloads`: descarga por lotes (default 20) para evitar el coste de “metadata newest-to-oldest” en canales grandes; usa `chunk_max_downloads`. citeturn39search6turn30view0  
- `_throttle_protection` y `_url`: helpers internos para throttling/URLs/metadata sibling/webpage, documentados como presets auxiliares. citeturn39search6  

### Music Presets y Music Video Presets

En los ejemplos oficiales de repo aparecen presets listos para música:

- `YouTube Releases`, `YouTube Full Albums`, `SoundCloud Discography`, `Bandcamp`. citeturn20search0turn16view0  

Para music videos se documentan (en ejemplos oficiales) presets por player:

- `"Plex Music Videos"`, y menciones a alternativas `Jellyfin Music Videos` y `Kodi Music Videos`. citeturn27view1turn16view0  

Además, el ejemplo de music videos muestra un **“map-mode”** (prefijo `+` en el nombre) que permite agrupar URLs por categorías (“Music Videos”, “Concerts”) y admitir objetos `title/year/date/url` para personalizar metadatos por URL. citeturn27view1turn40search2  

## Ejemplos completos y realistas de configuración y uso

Los siguientes ejemplos son **ficheros completos** (no “snippets”) diseñados para cubrir los patrones y opciones documentadas. Están inspirados en ejemplos oficiales y en el esquema descrito por la documentación (para evitar copiar literalmente ficheros del repo), y se acompañan de comandos reales de ejecución. citeturn30view0turn20search0turn27view1turn36view0turn44view1turn44view0  

### Ejemplo de config.yaml mínimo operativo

```yaml
configuration:
  working_directory: ".ytdl-sub-working-directory"
```

Este “mínimo” es útil cuando se usan solo presets prebuilt y no necesitas overrides/presets custom globales. citeturn39search1turn15view0  

### Ejemplo de config.yaml con logging, locks, umask y dl_aliases

```yaml
configuration:
  # Umask global aplicado a ficheros creados
  umask: "022"

  # Directorio de trabajo temporal (staging)
  working_directory: ".ytdl-sub-working-directory"

  # Locks para evitar ejecuciones paralelas (evitar FS remotos)
  lock_directory: "/tmp"

  # Límite de bytes en nombre de fichero
  file_name_max_bytes: 255

  # Persistencia de logs
  persist_logs:
    logs_directory: "/var/log/ytdl-sub"
    keep_successful_logs: false

  # Aliases para acortar `dl`
  dl_aliases:
    mv: "--preset \"Plex Music Videos\""
    u: "--download.url"
    q1080: "--format \"(bv*[height<=1080]+bestaudio/best[height<=1080])\""

  experimental:
    enable_update_with_info_json: false
```

Este ejemplo cubre claves y advertencias documentadas (locks en host, logs persistentes, aliases y experimental). citeturn39search1turn44view1turn44view4turn44view5  

### Ejemplo de config.yaml avanzado con presets custom (TV shows)

Este patrón refleja la idea documentada: presets custom compuestos por plugins, herencia y composición con presets prebuilt. citeturn13search22turn36view0turn39search0turn44view5  

```yaml
configuration:
  umask: "002"
  working_directory: ".ytdl-sub-working-directory"
  persist_logs:
    logs_directory: "/config/logs"
    keep_successful_logs: false

presets:
  # Preset para rutas base
  tv_show_paths:
    overrides:
      tv_show_directory: "/tv_shows"

  # Filtrar Shorts
  no_shorts:
    match_filters:
      filters:
        - "original_url!*=/shorts/"

  # SponsorBlock: eliminar categorías concretas
  sponsorblock_clean:
    chapters:
      sponsorblock_categories:
        - "intro"
        - "outro"
        - "sponsor"
        - "selfpromo"
        - "interaction"
        - "preview"
        - "music_offtopic"
      remove_sponsorblock_categories: "all"
      force_key_frames: false

  # Base “TV show”
  base_tv:
    preset:
      - "Kodi TV Show by Date"
      - "Max 1080p"
      - "tv_show_paths"
      - "sponsorblock_clean"
      - "no_shorts"
    chapters:
      embed_chapters: true
    subtitles:
      embed_subtitles: true
      languages:
        - "en"
      allow_auto_generated_subtitles: true
    throttle_protection:
      sleep_per_request_s: { min: 3.0, max: 8.0 }
      sleep_per_subscription_s: { min: 2.0, max: 6.0 }
      max_downloads_per_subscription: { min: 10, max: 25 }

  tv_full_archive:
    preset:
      - "base_tv"

  tv_only_recent:
    preset:
      - "base_tv"
      - "Only Recent"
    overrides:
      only_recent_date_range: "2months"
      only_recent_max_files: 30
```

Este ejemplo mezcla `match_filters`, `chapters`, `subtitles`, `throttle_protection`, herencia de presets y `Only Recent`. citeturn39search0turn39search6turn44view5turn42view6turn41view12turn44view6  

### Ejemplo de subscriptions.yaml para TV Show by Date y TV Show Collection

```yaml
__preset__:
  overrides:
    tv_show_directory: "/tv_shows"
    only_recent_date_range: "2months"
    only_recent_max_files: 30

# TV Show by Date (player específico)
Plex TV Show by Date:
  = Documentaries:
    "NOVA PBS": "https://www.youtube.com/@novapbs"
    "National Geographic": "https://www.youtube.com/@NatGeo"

  = News | Only Recent:
    "BBC News": "https://www.youtube.com/@BBCNews"

  = Music:
    "Rick Beato":
      - "https://www.youtube.com/@RickBeato"
      - "https://www.youtube.com/@rickbeato240"

# TV Show Collection: temporadas explícitas
Plex TV Show Collection:
  = Music:
    "~Beyond the Guitar":
      s01_name: "Videos"
      s01_url: "https://www.youtube.com/c/BeyondTheGuitar"
      s02_name: "Covers"
      s02_url: "https://www.youtube.com/playlist?list=PLE62gWlWZk5NWVAVuf0Lm9jdv_-_KXs0W"
```

Cubre: `__preset__`, pipes, tilda mode, multi-URL y presets TV Show by Date/Collection. citeturn30view0turn39search0turn39search6  

### Ejemplo de subscriptions.yaml para música

```yaml
__preset__:
  overrides:
    music_directory: "/music"

YouTube Releases:
  = Jazz:
    "Thelonious Monk": "https://www.youtube.com/@theloniousmonk3870/releases"

YouTube Full Albums:
  = Lofi:
    "Game Chops": "https://www.youtube.com/playlist?list=PLBsm_SagFMmdWnCnrNtLjA9kzfrRkto4i"

SoundCloud Discography:
  = Synthwave:
    "Lazerdiscs Records": "https://soundcloud.com/lazerdiscsrecords"

Bandcamp:
  = Lofi:
    "Emily Hopkins": "https://emilyharpist.bandcamp.com/"
```

Este patrón corresponde a los ejemplos oficiales de repo para música (nombres de presets y estructura). citeturn20search0turn16view0  

### Ejemplo de subscriptions.yaml para music videos (modo simple + map-mode)

```yaml
__preset__:
  overrides:
    music_video_directory: "/music_videos"

"Plex Music Videos":
  = Pop:
    "Rick Astley": "https://www.youtube.com/playlist?list=PLlaN88a7y2_plecYoJxvRFTLHVbIVAOoc"

  = Rock:
    "+ Guns N' Roses":
      Music Videos:
        - "https://www.youtube.com/playlist?list=PLOTK54q5K4INNXaHKtmXYr6J7CajWjqeJ"
      Concerts:
        - title: "Live at The Ritz - New York City"
          year: "1988"
          url: "https://www.youtube.com/watch?v=OldpIhHPsbs"
        - title: "Live at The Hollywood Bowl"
          date: "2023-01-11"
          url: "https://www.youtube.com/watch?v=Z7hutGlvq9I"
```

Cubre: preset `"Plex Music Videos"`, `+` map-mode, agrupación por categorías y objetos con `title/year/date/url`. citeturn27view1turn40search2  

### Ejemplos de comandos reales

#### Ejecutar subscriptions desde fichero

```bash
# Ejecuta subscriptions.yaml (por defecto) con config.yaml (por defecto)
ytdl-sub sub

# Ejecuta un fichero concreto
ytdl-sub sub ./subscriptions.yaml
```

La semántica de `SUBPATH` y defaults está documentada. citeturn44view1turn42view1  

#### Dry-run y filtrado por match

```bash
# Dry-run (no descarga, no escribe en output)
ytdl-sub --dry-run sub ./subscriptions.yaml

# Ejecutar solo subscriptions que coincidan con un match
ytdl-sub --match "BBC News" sub ./subscriptions.yaml
```

Ambas flags están en “General Options”. citeturn44view0turn44view1  

#### Descargar una subscription por CLI usando `dl`

```bash
ytdl-sub dl \
  --preset "Plex TV Show by Date" \
  --overrides.tv_show_directory "/tv_shows" \
  --download "https://www.youtube.com/@BBCNews"
```

La doc explica que `dl` usa puntos en lugar de indentación YAML y la equivalencia conceptual entre YAML y flags. citeturn44view1turn43view2  

#### Sobreescritura de ejecución (`--dl-override`)

```bash
ytdl-sub sub ./subscriptions.yaml \
  --dl-override="--ytdl_options.max_downloads 3"
```

Este mecanismo permite a un wrapper aplicar “overrides transitorios” sin editar YAML. citeturn44view1