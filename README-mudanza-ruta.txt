Este paquete contiene los archivos del proyecto preparados para vivir en:

E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl

Cambios aplicados:
- test-e2e-perfiles-subscriptions.ps1
  - Set-Location actualizado a ...\config\zenoytdl
  - rutas dentro del contenedor actualizadas a:
    /config/zenoytdl/config.generated.yaml
    /config/zenoytdl/subscriptions.runset.yaml
    /config/zenoytdl/beets.music-playlist.yaml
- validate-test-e2e-perfiles-subscriptions.ps1
  - Set-Location actualizado a ...\config\zenoytdl

No se han tocado:
- Los Python generadores, porque usan BASE_DIR = Path(__file__).resolve().parent
- Los YAML custom/generados
- Rutas de descargas /downloads/...
- Logs en /config/logs
- musiclibrary.db en /config/musiclibrary.db

Importante:
- Si quieres conservar el estado actual del runset inteligente, mueve también manualmente:
  .recent-items-state.json
  .recent-items-state.pending.json
  al nuevo directorio zenoytdl.
- No se incluyen logs históricos ni library.db en este ZIP.
