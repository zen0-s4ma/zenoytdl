# Dossier técnico actualizado — ZenoYTDL

## 1. Resumen técnico

ZenoYTDL implementa una mini-plataforma declarativa para construir colecciones multimedia tipadas a partir de YouTube usando `ytdl-sub`, PowerShell, Python y postprocesos específicos por dominio.

El sistema queda dividido en cinco capas:

1. **Modelo declarativo**: `profiles-custom.yml` y `subscription-custom.yml`
2. **Compilación**: `generate-ytdl-config.py`
3. **Planificación inteligente**: `prepare-subscriptions-runset.py`
4. **Ejecución**: `ytdl-sub` en Docker
5. **Postproceso y validación**: `beets`, `trim-ambience-video.py`, PowerShell de tests

---

## 2. Objetivo de diseño

El objetivo real no es descargar “vídeos sueltos”, sino expresar comportamientos de biblioteca.

Ejemplos:

- un canal como serie ordenada por fecha;
- una playlist como biblioteca de audio con metadatos enriquecidos;
- un vídeo de ambience como activo recortado a una duración operativa máxima.

Por eso el proyecto no trabaja directamente con YAML manual de `ytdl-sub`, sino con un modelo más compacto que luego compila.

---

## 3. Entradas declarativas

## 3.1 `profiles-custom.yml`

Contiene una lista `profiles:` donde cada entrada define:

- `profile_name`
- `profile_type`
- `defaults`

Los defaults actuales observables incluyen:

- `max_items`
- `quality`
- `format`
- `min_duration`
- `max_duration`
- `date_range`
- `embed_thumbnail`
- `audio_quality`

El código normaliza los perfiles y los indexa por `profile_name`.

## 3.2 `subscription-custom.yml`

Contiene una lista `subscriptions:` donde cada entrada define:

- `profile_name`
- `custom_name`
- `sources[]`

Cada `source` debe tener al menos `url` y puede sobrescribir parámetros heredados.

---

## 4. Compilador: `generate-ytdl-config.py`

## 4.1 Responsabilidades

- cargar YAML fuente;
- validar estructura mínima;
- fusionar defaults del perfil con overrides por fuente;
- detectar estrategia de descarga a partir de la URL;
- generar presets y suscripciones reales;
- construir `beets.music-playlist.yaml` cuando aplica.

## 4.2 Artefactos generados

- `config.generated.yaml`
- `subscriptions.generated.yaml`
- `beets.music-playlist.yaml`

## 4.3 Normalización clave

### `slugify()`
Se usa extensivamente para:

- nombres de preset;
- nombres de suscripción;
- `subscription_root`;
- `source_target` extraído de URL.

### `extract_source_target_from_url()`
Soporta detección desde:

- `watch?v=`
- `playlist?list=`
- `/@handle`
- `/channel/...`
- `/user/...`
- `/c/...`
- URLs cortas `youtu.be/...`

### `detect_download_strategy()`
Distingue entre:

- `single_video`
- `playlist`
- `channel`

---

## 5. Traducción funcional por perfil

## 5.1 Canales-youtube

Preset generado:

- `Jellyfin TV Show by Date`
- opcional `Max 720p` / `Max 1080p`
- opcional `Only Recent`

Overrides principales:

- `tv_show_directory = /downloads/Canales-youtube`
- `enable_throttle_protection`

Semántica:

- colección tratada como serie por fecha;
- `tv_show_name = subscription_root`.

## 5.2 Podcast

Preset generado:

- `Filter Duration`
- `Max MP3 Quality`
- opcional `Only Recent`

Salida:

```text
/downloads/Podcast/{subscription_root_sanitized}/{source_target_sanitized}
```

Audio extract:

- `enable: true`
- `codec: mp3`
- `quality: 0`

## 5.3 TV-Serie

Preset generado:

- `Jellyfin TV Show by Date`
- opcional `Max 720p` / `Max 1080p`
- opcional `Only Recent`
- `Filter Duration`

Además fuerza:

- `merge_output_format = format`
- `tv_show_name = subscription_root`

## 5.4 Music-Playlist

Preset generado:

- `Max MP3 Quality`
- opcional `Only Recent`

Salida:

```text
/downloads/Music-Playlist/{subscription_root_sanitized}
```

Archivo de descarga:

- `maintain_download_archive: true`

Postproceso esperado:

- importación singleton con `beets`
- limpieza previa de nombres si el workflow lo incluye

## 5.5 Ambience-Video

No usa `Only Recent`.

Salida:

```text
/downloads/Ambience-Video/{subscription_root_sanitized}
```

Comportamiento clave:

- descarga vídeo;
- el `max_duration` no se traduce a filtro de descarga, sino a `postprocess_trim_max_s`.

## 5.6 Ambience-Audio

Salida:

```text
/downloads/Ambience-Audio/{subscription_root_sanitized}
```

Comportamiento clave:

- extrae audio MP3;
- el `max_duration` se usa también como `postprocess_trim_max_s`.

---

## 6. Planificador: `prepare-subscriptions-runset.py`

## 6.1 Responsabilidades

- cargar perfiles y suscripciones originales;
- cargar `subscriptions.generated.yaml`;
- leer estado anterior;
- inspeccionar ficheros ya existentes dentro del contenedor `ytdl-sub`;
- consultar IDs recientes remotos;
- seleccionar qué entradas deben ir al runset.

## 6.2 Artefactos generados

- `subscriptions.runset.yaml`
- `.recent-items-state.pending.json`

## 6.3 Estado persistente

- estado consolidado: `.recent-items-state.json`
- estado pendiente: `.recent-items-state.pending.json`

La suite nueva añade además una variante filtrada por perfil:

- `subscriptions.runset.filtered.yaml`
- `.recent-items-state.pending.filtered.json`

## 6.4 Reglas de medios observables

`MEDIA_RULES` codifica carpetas y extensiones por perfil:

- `Canales-youtube` → vídeo
- `Podcast` → mp3
- `TV-Serie` → vídeo
- `Music-Playlist` → mp3
- `Ambience-Video` → vídeo
- `Ambience-Audio` → audio multiformato

## 6.5 Lógica de selección

A alto nivel, el planificador compara:

- IDs recientes detectados en la fuente remota;
- número esperado según `max_items`;
- número real de ficheros presentes;
- snapshot previo almacenado.

Resultado práctico:

- si una fuente ya está satisfecha, puede quedar fuera del runset;
- si hay novedad, falta material o cambió el conjunto esperado, entra en el runset.

---

## 7. Suite de pruebas nueva: `test-zenoytdl`

## 7.1 Motivo

La carpeta `test-zenoytdl` reemplaza la necesidad de depender solo del script E2E legacy y aporta:

- contextos de ejecución por prueba;
- logs por timestamp;
- filtrado de runset por perfil;
- postprocesos invocables de forma homogénea;
- tests aislados de `beets` y `trim`.

## 7.2 Fichero base `_shared.ps1`

Define utilidades para:

- localizar raíz del proyecto;
- localizar carpeta de logs;
- ejecutar expresiones con logging;
- ejecutar scripts shell dentro de Docker;
- filtrar el runset a uno o varios perfiles;
- copiar el script de trim al contenedor;
- promover el estado pendiente a definitivo;
- capturar logs relevantes de `ytdl-sub` y `beets-streaming2`.

## 7.3 `run-profile-test.ps1`

Pipeline general:

1. validar nombre de perfil;
2. limpieza opcional de descargas del perfil;
3. reset de estado temporal;
4. regeneración del YAML;
5. preparación del runset;
6. filtrado a un solo perfil;
7. ejecución real o dry-run;
8. promoción del estado si procede;
9. postproceso específico;
10. captura de logs.

## 7.4 `run-e2e.ps1`

Recorre todos los perfiles definidos por `_shared.ps1` y al final lanza `validate-downloads.ps1`.

## 7.5 `validate-downloads.ps1`

Realiza:

- inventario de ficheros de control del proyecto;
- inventario de árboles de salida por perfil;
- conteo por extensiones relevantes;
- `ffprobe` sobre medios descargados;
- captura de logs.

## 7.6 `test-beets-only.ps1`

Test aislado de metadatos:

- crea un MP3 sintético con metadata “sucia”;
- lanza importación con `beets`;
- comprueba resultado de importación y logs.

## 7.7 `test-trim-only.ps1`

Test aislado de recorte:

- genera un MP4 sintético de prueba;
- copia `trim-ambience-video.py` al contenedor;
- recorta a 5 segundos;
- valida duración final con `ffprobe`.

## 7.8 `clean-windows-environment.ps1`

Limpia:

- logs locales si se pide;
- generados temporales locales;
- estado local;
- descargas, locks y working dirs en `ytdl-sub`;
- descargas, DB y logs en `beets-streaming2`.

## 7.9 `_run-all-test.ps1`

Ejecuta batería completa en orden lógico.

## 7.10 `run-master-tests.ps1`

Sigue existiendo en la raíz y abre pruebas en terminales nuevas usando un orquestador maestro. Es útil como secuencia exhaustiva, pero la carpeta `test-zenoytdl` concentra la suite nueva.

---

## 8. Scripts legacy en raíz

## 8.1 `test-e2e-perfiles-subscriptions.ps1`

Workflow más monolítico que:

- genera configuración;
- prepara runset;
- ejecuta `ytdl-sub`;
- limpia nombres de música;
- lanza `beets`;
- recorta ambience;
- valida resultado.

## 8.2 `validate-test-e2e-perfiles-subscriptions.ps1`

Validador asociado al E2E legacy.

Estos scripts no están mal, pero la estructura nueva es más modular y trazable.

---

## 9. Dependencias operativas

### Windows host

- PowerShell
- Python
- Docker

### Contenedor `ytdl-sub`

- `ytdl-sub`
- Python
- `ffmpeg`
- `ffprobe`

### Contenedor `beets-streaming2`

- `beet`
- acceso a `/config/zenoytdl`
- acceso a `/downloads/Music-Playlist`

---

## 10. Rutas clave del sistema

### Proyecto

```text
E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl
```

### Descargas host

```text
E:\Docker_folders\ydtl-custom-downloads
```

### Rutas internas más usadas

```text
/config/zenoytdl/config.generated.yaml
/config/zenoytdl/subscriptions.runset.yaml
/config/zenoytdl/subscriptions.runset.filtered.yaml
/config/zenoytdl/beets.music-playlist.yaml
/downloads/Canales-youtube
/downloads/Podcast
/downloads/TV-Serie
/downloads/Music-Playlist
/downloads/Ambience-Video
/downloads/Ambience-Audio
/config/logs
```

---

## 11. Riesgos y consideraciones reales

- `Music-Playlist` con `max_items: 0` equivale a no limitar por recencia.
- `Podcast` y `Music-Playlist` fuerzan MP3 aunque la fuente original sea vídeo.
- `Ambience-*` depende de recorte posterior; si no se lanza trim, el material puede quedar demasiado largo.
- El runset inteligente depende del estado JSON y del conteo real dentro de `/downloads`, así que borrar descargas sin resetear estado puede alterar el comportamiento esperado.
- La suite nueva reduce ese riesgo porque ofrece limpieza, filtrado y promoción controlada del estado.

---

## 12. Recomendación de operación

Para trabajo diario:

1. editar YAML fuente;
2. lanzar `run-profile-test.ps1` para el perfil que toque;
3. revisar logs en `test-zenoytdl\logs\...`;
4. usar `validate-downloads.ps1` cuando cierres una tanda importante;
5. reservar `_run-all-test.ps1` o `run-master-tests.ps1` para regresión completa.
