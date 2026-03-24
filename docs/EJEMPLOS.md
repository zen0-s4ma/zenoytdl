# Ejemplos de uso — ZenoYTDL

## 1. Ruta base

Ejecutar siempre desde:

```text
E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl
```

---

## 2. Generación manual de artefactos

### Generar todo

```powershell
python .\generate-ytdl-config.py
```

### Generar solo un perfil

```powershell
python .\generate-ytdl-config.py --only-profile music-playlist
```

### Preparar runset de todos los perfiles

```powershell
python .\prepare-subscriptions-runset.py
```

### Preparar runset de un perfil concreto

```powershell
python .\prepare-subscriptions-runset.py --profile-name "Music-Playlist"
```

---

## 3. Nueva suite de pruebas Python

## 3.1 Probar un único perfil

### `Canales-youtube`

```powershell
python .\test-zenoytdl\run_tests.py --profile "Canales-youtube" --clean
```

### `Podcast`

```powershell
python .\test-zenoytdl\run_tests.py --profile "Podcast" --clean
```

### `TV-Serie`

```powershell
python .\test-zenoytdl\run_tests.py --profile "TV-Serie" --clean
```

### `Music-Playlist`

```powershell
python .\test-zenoytdl\run_tests.py --profile "Music-Playlist" --clean
```

### `Ambience-Video`

```powershell
python .\test-zenoytdl\run_tests.py --profile "Ambience-Video" --clean
```

### `Ambience-Audio`

```powershell
python .\test-zenoytdl\run_tests.py --profile "Ambience-Audio" --clean
```

---

## 3.2 Probar un perfil en dry-run

```powershell
python .\test-zenoytdl\run_tests.py --profile "Podcast" --clean --dry-run
```

En este modo sí se generan:

- `config.generated.yaml`
- `subscriptions.runset.yaml`
- `.recent-items-state.pending.json`

Pero no se ejecuta descarga real ni postproceso.

---

## 3.3 Lanzar toda la batería

### Completa con limpieza previa general

```powershell
python .\test-zenoytdl\run_tests.py --all-profiles --clean
```

### Completa con limpieza previa pero conservando logs anteriores

```powershell
python .\test-zenoytdl\run_tests.py --all-profiles --clean --keep-logs
```

### Completa en dry-run

```powershell
python .\test-zenoytdl\run_tests.py --all-profiles --clean --dry-run
```

---

## 4. Casos de uso típicos

### 4.1 Cambio en una playlist de música

1. Editas `subscription-custom.yml`.
2. Lanzas:

```powershell
python .\test-zenoytdl\run_tests.py --profile "Music-Playlist" --clean
```

3. Revisas el log único de la ejecución.

### 4.2 Regresión completa antes de dar por buena una tanda

```powershell
python .\test-zenoytdl\run_tests.py --all-profiles --clean
```

### 4.3 Solo comprobar generación y selección de runset

```powershell
python .\test-zenoytdl\run_tests.py --all-profiles --clean --dry-run
```

---

## 5. Logs

Ruta:

```text
E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl\test-zenoytdl\logs
```

Ejemplo de fichero:

```text
zenoytdl-test-suite-20260322-170000.log
```

Ese log reúne en un solo sitio:

- limpieza inicial;
- generación;
- planificación de runset;
- descarga real si aplica;
- postproceso;
- resumen final.
