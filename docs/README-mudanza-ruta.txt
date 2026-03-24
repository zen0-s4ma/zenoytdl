Este paquete de documentación y pruebas está actualizado para la ubicación actual del proyecto:

E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl

Archivos operativos relevantes en esta actualización:
- README.md
- DOSSIER-TECNICO.md
- EJEMPLOS.md
- test-zenoytdl\GUIA-USO.md
- test-zenoytdl\listado-comandos-python.txt
- test-zenoytdl\run_tests.py

Puntos confirmados con el código actual:
- Los scripts Python usan BASE_DIR = Path(__file__).resolve().parent o rutas equivalentes derivadas desde el propio fichero.
- La carpeta zenoytdl es la unidad real de despliegue del proyecto.
- La batería recomendada de pruebas vive en test-zenoytdl\run_tests.py.
- La suite nueva genera un único log por ejecución en test-zenoytdl\logs.
- El contenedor ytdl-sub se invoca contra rutas dentro de /config/zenoytdl.
- beets usa /config/zenoytdl/beets.music-playlist.yaml.

Dónde copiar estos ficheros:
- E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl\README.md
- E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl\DOSSIER-TECNICO.md
- E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl\EJEMPLOS.md
- E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl\README-mudanza-ruta.txt
- E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl\test-zenoytdl\GUIA-USO.md
- E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl\test-zenoytdl\listado-comandos-python.txt
- E:\Docker_folders\streaming2\ytdl-sub\config\zenoytdl\test-zenoytdl\run_tests.py

Importante:
- La documentación operativa de pruebas ya no usa PS1 como vía recomendada.
- La forma soportada y documentada de probar el proyecto es Python.
