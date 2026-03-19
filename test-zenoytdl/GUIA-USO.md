# Guía de uso actualizada — `test-zenoytdl`

Esta carpeta contiene la suite de pruebas nueva del proyecto y es la forma recomendada de validar cambios en perfiles, generación, runset, postprocesos y descargas.

---

## Ubicación esperada

```text
E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl\test-zenoytdl
```

Su carpeta padre debe ser la raíz real del proyecto:

```text
E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl
```

---

## Qué hay en esta carpeta

- `_shared.ps1`: funciones comunes de logging, Docker, filtrado y postproceso.
- `run-profile-test.ps1`: prueba un único perfil.
- `run-e2e.ps1`: recorre todos los perfiles.
- `validate-downloads.ps1`: inventario y validación final.
- `test-beets-only.ps1`: prueba aislada de importación con beets.
- `test-trim-only.ps1`: prueba aislada del trim.
- `clean-windows-environment.ps1`: limpieza del entorno.
- `_run-all-test.ps1`: batería completa.
- `listado-comandos-lanzar-ps1.txt`: chuleta de comandos.
- `logs\`: árbol de logs por timestamp.

---

## Requisitos

### Host Windows

- PowerShell
- Python
- Docker funcionando

### Contenedores

- `ytdl-sub`
- `beets-streaming2`

### Herramientas internas esperadas

En `ytdl-sub`:

- `ytdl-sub`
- `python`
- `ffmpeg`
- `ffprobe`

En `beets-streaming2`:

- `beet`

---

## Convención de perfiles válidos

Perfiles aceptados por la suite:

- `Canales-youtube`
- `Podcast`
- `TV-Serie`
- `Music-Playlist`
- `Ambience-Video`
- `Ambience-Audio`

---

## 1. `run-profile-test.ps1`

Sirve para probar un único perfil de forma controlada.

### Sintaxis

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-profile-test.ps1 -ProfileName "<PERFIL>" -ClearDownloads:$false -DryRun:$false
```

### Parámetros

- `-ProfileName`: nombre exacto del perfil
- `-ClearDownloads:$true/$false`: si limpia las descargas del perfil antes de ejecutar
- `-DryRun:$true/$false`: si ejecuta de verdad o solo deja preparado el flujo

### Qué hace

1. crea contexto de logs;
2. valida el nombre del perfil;
3. resetea estado temporal y working dirs;
4. genera YAML (`generate-ytdl-config.py`);
5. prepara runset inteligente (`prepare-subscriptions-runset.py`);
6. filtra el runset al perfil pedido;
7. si no es dry-run, ejecuta `ytdl-sub` sobre `subscriptions.runset.filtered.yaml`;
8. promueve `.recent-items-state.pending.filtered.json` a estado definitivo si corresponde;
9. lanza postproceso específico según perfil;
10. captura logs relevantes.

### Postproceso automático por perfil

- `Music-Playlist` → `beets`
- `Ambience-Video` → trim
- `Ambience-Audio` → trim
- resto → sin postproceso específico

### Ejemplos

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-profile-test.ps1 -ProfileName "Podcast" -ClearDownloads:$false -DryRun:$false
```

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-profile-test.ps1 -ProfileName "Ambience-Video" -ClearDownloads:$true -DryRun:$false
```

---

## 2. `run-e2e.ps1`

Ejecuta todos los perfiles en secuencia y al final dispara `validate-downloads.ps1`.

### Sintaxis

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-e2e.ps1 -ClearDownloads:$false -DryRun:$false
```

### Parámetros

- `-ClearDownloads:$true/$false`
- `-DryRun:$true/$false`

### Ejemplo

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-e2e.ps1 -ClearDownloads:$false -DryRun:$false
```

---

## 3. `validate-downloads.ps1`

Hace una validación amplia sin modificar el contenido.

### Sintaxis

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\validate-downloads.ps1 -DryRun:$false
```

### Qué revisa

- ficheros de control del proyecto;
- árboles de salida de cada perfil;
- conteos de medios por extensión;
- `ffprobe` sobre audio y vídeo;
- logs recientes de contenedores.

---

## 4. `test-beets-only.ps1`

Prueba aislada del pipeline de metadatos.

### Qué hace

- limpia un directorio de prueba;
- genera un MP3 sintético con metadata basura;
- ejecuta importación de `beets`;
- deja rastro en logs para comprobar el comportamiento.

### Ejemplo

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\test-beets-only.ps1 -DryRun:$false
```

---

## 5. `test-trim-only.ps1`

Prueba aislada del script `trim-ambience-video.py`.

### Qué hace

- crea un MP4 sintético de prueba;
- copia el script real de trim al contenedor;
- recorta a 5 segundos;
- valida duración final.

### Ejemplo

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\test-trim-only.ps1 -DryRun:$false
```

---

## 6. `clean-windows-environment.ps1`

Limpia el entorno antes de una tanda de tests.

### Sintaxis general

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\clean-windows-environment.ps1 -CleanLogs
```

### Con perfil concreto

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\clean-windows-environment.ps1 -ProfileName "Music-Playlist" -CleanLogs
```

### Qué limpia

En local:

- `subscriptions.runset.yaml`
- `subscriptions.runset.filtered.yaml`
- `.recent-items-state.pending.json`
- `.recent-items-state.pending.filtered.json`
- resetea `.recent-items-state.json`
- opcionalmente limpia `test-zenoytdl\logs`

En `ytdl-sub`:

- descargas del perfil o de todos
- working dirs
- locks
- runsets temporales
- estados pendientes

En `beets-streaming2`:

- descargas del perfil o de todos
- `musiclibrary.db`
- `beets-import.log`

---

## 7. `_run-all-test.ps1`

Lanza toda la batería nueva en orden lógico.

### Ejemplo

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\_run-all-test.ps1
```

---

## 8. Logs y trazabilidad

Cada ejecución crea su propio contexto de logs dentro de `test-zenoytdl\logs\...`.

Al final de los scripts se muestran normalmente:

- `Main log`
- `Transcript`
- carpeta completa de ejecución

Esto hace mucho más fácil localizar:

- comandos realmente lanzados;
- salida de Docker;
- errores del perfil;
- resultado de `beets` o `trim`.

---

## 9. Flujo recomendado de trabajo

### Cuando tocas un perfil concreto

1. editas YAML o código;
2. pruebas `test-beets-only.ps1` o `test-trim-only.ps1` si aplica;
3. lanzas `run-profile-test.ps1` para ese perfil;
4. revisas logs;
5. rematas con `validate-downloads.ps1`.

### Cuando tocas partes transversales

1. `clean-windows-environment.ps1 -CleanLogs`
2. `_run-all-test.ps1`
3. `validate-downloads.ps1`

---

## 10. Ficheros filtrados que usa esta suite

La suite nueva no trabaja solo con el runset general; además crea y usa:

- `subscriptions.runset.filtered.yaml`
- `.recent-items-state.pending.filtered.json`

Eso permite probar un solo perfil sin romper la lógica general del planificador.

---

## 11. Ruta donde debe ir esta guía

```text
E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl\test-zenoytdl\GUIA-USO.md
```
