# Dossier técnico — ZenoYTDL

## 1. Resumen técnico

ZenoYTDL implementa una mini-plataforma declarativa para construir colecciones multimedia tipadas a partir de YouTube usando `ytdl-sub`, Python y postprocesos específicos por dominio.

El sistema queda dividido en cinco capas:

1. **Modelo declarativo**: `profiles-custom.yml` y `subscription-custom.yml`
2. **Compilación**: `generate-ytdl-config.py`
3. **Planificación inteligente**: `prepare-subscriptions-runset.py`
4. **Ejecución**: `ytdl-sub` en Docker
5. **Postproceso y pruebas**: `beets`, `trim-ambience-video.py`, `test-zenoytdl/run_tests.py`

---

## 2. Objetivo de diseño

El objetivo real no es descargar vídeos sueltos, sino expresar comportamientos de biblioteca.

Ejemplos:

- un canal como serie ordenada por fecha;
- una playlist como biblioteca de audio con metadatos enriquecidos;
- un vídeo de ambience como activo recortado a una duración operativa máxima.

Por eso el proyecto no trabaja directamente con YAML manual de `ytdl-sub`, sino con un modelo compacto que luego compila.

---

## 3. Entradas declarativas

### 3.1 `profiles-custom.yml`

Contiene una lista `profiles:` donde cada entrada define:

- `profile_name`
- `profile_type`
- `defaults`

Defaults observables actuales:

- `max_items`
- `quality`
- `format`
- `min_duration`
- `max_duration`
- `date_range`
- `embed_thumbnail`
- `audio_quality`

### 3.2 `subscription-custom.yml`

Contiene una lista `subscriptions:` donde cada entrada define:

- `profile_name`
- `custom_name`
- `sources[]`

Cada `source` debe tener al menos `url` y puede sobrescribir parámetros heredados.

---

## 4. Compilador: `generate-ytdl-config.py`

### 4.1 Responsabilidades

- cargar YAML fuente;
- validar estructura mínima;
- fusionar defaults del perfil con overrides por fuente;
- detectar estrategia de descarga a partir de la URL;
- generar presets y suscripciones reales;
- construir `beets.music-playlist.yaml` cuando aplica.

### 4.2 Artefactos generados

- `config.generated.yaml`
- `subscriptions.generated.yaml`
- `beets.music-playlist.yaml`

### 4.3 Normalización clave

#### `slugify()`

Se usa para:

- nombres de preset;
- nombres de suscripción;
- `subscription_root`;
- `source_target` extraído de URL.

#### `extract_source_target_from_url()`

Soporta detección desde:

- `watch?v=`
- `playlist?list=`
- `/@handle`
- `/channel/...`
- `/user/...`
- `/c/...`
- `youtu.be/...`

#### `detect_download_strategy()`

Distingue entre:

- `single_video`
- `playlist`
- `channel`

---

## 5. Planificador: `prepare-subscriptions-runset.py`

### 5.1 Responsabilidades

- cargar perfiles y suscripciones originales;
- cargar `subscriptions.generated.yaml`;
- leer estado anterior;
- inspeccionar ficheros ya existentes dentro del contenedor `ytdl-sub`;
- consultar IDs recientes remotos;
- seleccionar qué entradas deben ir al runset.

### 5.2 Artefactos generados

- `subscriptions.runset.yaml`
- `.recent-items-state.pending.json`

### 5.3 Comportamiento operativo

Para cada fuente:

1. detecta estrategia (`channel`, `playlist`, `single_video`);
2. calcula directorio de salida esperado;
3. cuenta ficheros locales compatibles;
4. resuelve IDs remotos con `yt-dlp` dentro del contenedor;
5. compara con `.recent-items-state.json`;
6. decide si esa fuente entra o no en el runset.

---

## 6. Suite nueva de pruebas: `test-zenoytdl/run_tests.py`

### 6.1 Objetivo

Sustituir la orquestación de pruebas en PowerShell por una suite Python única, más simple y con un solo log por ejecución.

### 6.2 Parámetros

- `--profile "<PERFIL>"`
- `--all-profiles`
- `--dry-run`
- `--clean`
- `--keep-logs`

### 6.3 Flujo interno de la suite

#### 6.3.1 Limpieza opcional

Si se usa `--clean`:

- reinicia `.recent-items-state.json` a vacío;
- borra runsets y estados pendientes locales;
- purga descargas del alcance pedido en `ytdl-sub` y `beets-streaming2`;
- limpia working dirs y locks;
- reinicia ambos contenedores;
- limpia `test-zenoytdl/logs` salvo que se indique `--keep-logs`.

#### 6.3.2 Ejecución por perfil

Para cada perfil:

1. llama a `generate-ytdl-config.py --only-profile ...`;
2. llama a `prepare-subscriptions-runset.py --profile-name ...`;
3. comprueba si `subscriptions.runset.yaml` contiene entradas reales;
4. si no es dry-run, ejecuta:

```text
docker exec ytdl-sub ytdl-sub --config /config/zenoytdl/config.generated.yaml sub /config/zenoytdl/subscriptions.runset.yaml
```

5. promueve `.recent-items-state.pending.json` a `.recent-items-state.json`;
6. lanza postproceso cuando aplica.

#### 6.3.3 Postproceso automático

- `Music-Playlist` → `beet import`
- `Ambience-Video` → trim de vídeo
- `Ambience-Audio` → trim de audio

#### 6.3.4 Logging

Toda la ejecución se concentra en un único fichero dentro de:

```text
test-zenoytdl\logs\zenoytdl-test-suite-YYYYMMDD-HHMMSS.log
```

Ese log contiene tanto stdout/stderr de subprocess como resumen final por perfil.

---

## 7. Decisiones de diseño de la nueva suite

### 7.1 Un log único por ejecución

Se ha priorizado un único log para facilitar:

- revisión rápida;
- compartir resultados completos;
- comparar perfiles dentro de la misma tanda;
- evitar dispersión en subcarpetas por script.

### 7.2 Scope de limpieza ligado al scope de ejecución

- si pruebas un perfil, se limpia solo ese alcance;
- si ejecutas `--all-profiles`, la limpieza es global.

### 7.3 Sin dependencia de PS1 para la batería principal

La documentación operativa queda centrada exclusivamente en Python para la batería principal de pruebas.
