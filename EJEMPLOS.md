# Ejemplos actualizados — ZenoYTDL

Este documento reúne ejemplos realistas basados en el comportamiento actual del código y de la suite de tests.

Ruta base asumida:

```powershell
cd E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl
```

---

## 1. Regenerar solo los YAML de salida

Útil para validar que la capa declarativa compila bien.

```powershell
python .\generate-ytdl-config.py
```

Resultado esperado:

- `config.generated.yaml`
- `subscriptions.generated.yaml`
- `beets.music-playlist.yaml` si existe `Music-Playlist`

---

## 2. Regenerar solo un perfil

### Solo música

```powershell
python .\generate-ytdl-config.py --only-profile music-playlist
```

### Solo podcast

```powershell
python .\generate-ytdl-config.py --only-profile podcast
```

### Solo serie TV

```powershell
python .\generate-ytdl-config.py --only-profile tv-serie
```

---

## 3. Preparar runset inteligente

```powershell
python .\prepare-subscriptions-runset.py
```

Genera:

- `subscriptions.runset.yaml`
- `.recent-items-state.pending.json`

---

## 4. Ejecutar `ytdl-sub` manualmente con el runset

```powershell
docker cp .\trim-ambience-video.py ytdl-sub:/tmp/trim-ambience-video.py
docker exec ytdl-sub ytdl-sub --config /config/zenoytdl/config.generated.yaml sub /config/zenoytdl/subscriptions.runset.yaml
```

---

## 5. Probar un solo perfil con la suite nueva

## 5.1 Canales-youtube

### Dry-run

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-profile-test.ps1 -ProfileName "Canales-youtube" -ClearDownloads:$false -DryRun:$true
```

### Ejecución real

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-profile-test.ps1 -ProfileName "Canales-youtube" -ClearDownloads:$false -DryRun:$false
```

## 5.2 Podcast

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-profile-test.ps1 -ProfileName "Podcast" -ClearDownloads:$false -DryRun:$false
```

## 5.3 TV-Serie

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-profile-test.ps1 -ProfileName "TV-Serie" -ClearDownloads:$false -DryRun:$false
```

## 5.4 Music-Playlist

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-profile-test.ps1 -ProfileName "Music-Playlist" -ClearDownloads:$false -DryRun:$false
```

## 5.5 Ambience-Video

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-profile-test.ps1 -ProfileName "Ambience-Video" -ClearDownloads:$false -DryRun:$false
```

## 5.6 Ambience-Audio

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-profile-test.ps1 -ProfileName "Ambience-Audio" -ClearDownloads:$false -DryRun:$false
```

---

## 6. Lanzar todo el E2E nuevo

### Sin borrar descargas

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-e2e.ps1 -ClearDownloads:$false -DryRun:$false
```

### Forzando limpieza de descargas por perfil

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-e2e.ps1 -ClearDownloads:$true -DryRun:$false
```

---

## 7. Validar inventario completo de descargas

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\validate-downloads.ps1 -DryRun:$false
```

Esto hace inventario de:

- ficheros de control del proyecto;
- rutas de salida por perfil;
- conteos por extensión;
- `ffprobe` sobre medios;
- logs recientes de contenedores.

---

## 8. Limpiar entorno antes de una regresión seria

### Todo el entorno

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\clean-windows-environment.ps1 -CleanLogs
```

### Solo un perfil

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\clean-windows-environment.ps1 -ProfileName "Music-Playlist" -CleanLogs
```

---

## 9. Test aislado de beets

### Dry-run

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\test-beets-only.ps1 -DryRun:$true
```

### Real

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\test-beets-only.ps1 -DryRun:$false
```

Caso de uso:

- comprobar que `beets` importa;
- comprobar que escribe metadatos;
- comprobar que genera log de importación.

---

## 10. Test aislado de trim

### Dry-run

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\test-trim-only.ps1 -DryRun:$true
```

### Real

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\test-trim-only.ps1 -DryRun:$false
```

Caso de uso:

- validar el script `trim-ambience-video.py` sin depender de descargas reales.

---

## 11. Batería completa nueva

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\_run-all-test.ps1
```

---

## 12. Batería maestra legacy en ventanas nuevas

```powershell
powershell -ExecutionPolicy Bypass -File .\run-master-tests.ps1
```

Esta secuencia lanza, entre otros:

- limpieza de entorno;
- test aislado de beets;
- test aislado de trim;
- dos pasadas por cada perfil.

---

## 13. Ejemplo realista de iteración para Music-Playlist

1. Editas `subscription-custom.yml` y cambias una playlist.
2. Regeneras:

```powershell
python .\generate-ytdl-config.py --only-profile music-playlist
python .\prepare-subscriptions-runset.py
```

3. Pruebas solo música:

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-profile-test.ps1 -ProfileName "Music-Playlist" -ClearDownloads:$false -DryRun:$false
```

4. Validas:

```powershell
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\validate-downloads.ps1 -DryRun:$false
```

---

## 14. Ejemplo realista de iteración para ambience

### Ambience-Video

```powershell
python .\generate-ytdl-config.py --only-profile ambience-video
python .\prepare-subscriptions-runset.py
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-profile-test.ps1 -ProfileName "Ambience-Video" -ClearDownloads:$false -DryRun:$false
```

### Ambience-Audio

```powershell
python .\generate-ytdl-config.py --only-profile ambience-audio
python .\prepare-subscriptions-runset.py
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-profile-test.ps1 -ProfileName "Ambience-Audio" -ClearDownloads:$false -DryRun:$false
```

---

## 15. Ejemplo de depuración cuando sospechas que el runset no está entrando

```powershell
python .\prepare-subscriptions-runset.py
Get-Content .\subscriptions.runset.yaml
Get-Content .\.recent-items-state.pending.json
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-profile-test.ps1 -ProfileName "Podcast" -ClearDownloads:$false -DryRun:$true
```

Mira después la carpeta de logs creada por el test para confirmar:

- si el perfil fue filtrado correctamente;
- si el runset quedó vacío;
- si se omitió postproceso por falta de entradas.

---

## 16. Ejemplo de cambio de ruta del proyecto

Todos estos docs asumen esta ruta final:

```text
E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl
```

Si el proyecto se mueve completo ahí y mantienes la carpeta `zenoytdl` como unidad de despliegue, los scripts Python siguen funcionando porque resuelven rutas relativas a `__file__`.

---

## 17. Checklist rápida después de tocar código o tests

```powershell
python .\generate-ytdl-config.py
python .\prepare-subscriptions-runset.py
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\test-beets-only.ps1 -DryRun:$false
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\test-trim-only.ps1 -DryRun:$false
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-e2e.ps1 -ClearDownloads:$false -DryRun:$false
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\validate-downloads.ps1 -DryRun:$false
```

---

## 18. Ejemplo maestro recomendado para cierre de una tanda grande

```powershell
cd E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\clean-windows-environment.ps1 -CleanLogs
python .\generate-ytdl-config.py
python .\prepare-subscriptions-runset.py
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\test-beets-only.ps1 -DryRun:$false
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\test-trim-only.ps1 -DryRun:$false
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\run-e2e.ps1 -ClearDownloads:$false -DryRun:$false
powershell -ExecutionPolicy Bypass -File .\test-zenoytdl\validate-downloads.ps1 -DryRun:$false
```
