Este paquete de documentación está actualizado para la ubicación actual del proyecto:

E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl

Archivos documentados en esta actualización:
- README.md
- DOSSIER-TECNICO.md
- EJEMPLOS.md
- test-zenoytdl\GUIA-USO.md

Puntos relevantes confirmados con el código actual:
- Los scripts Python usan BASE_DIR = Path(__file__).resolve().parent.
- La carpeta zenoytdl es la unidad real de despliegue del proyecto.
- La suite nueva de pruebas vive en test-zenoytdl.
- La suite nueva usa además estos ficheros filtrados:
  - subscriptions.runset.filtered.yaml
  - .recent-items-state.pending.filtered.json
- El contenedor ytdl-sub se invoca contra rutas dentro de /config/zenoytdl.
- beets usa /config/zenoytdl/beets.music-playlist.yaml.

Dónde copiar los docs:
- E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl\README.md
- E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl\DOSSIER-TECNICO.md
- E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl\EJEMPLOS.md
- E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl\README-mudanza-ruta.txt
- E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl\test-zenoytdl\GUIA-USO.md

Importante:
- No he tocado el código en este paquete, solo la documentación.
- Si quieres conservar estado e histórico operativo, conserva también:
  - .recent-items-state.json
  - .recent-items-state.pending.json
  - .recent-items-state.pending.filtered.json
  - logs históricos si te interesan
