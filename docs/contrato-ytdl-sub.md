# Contrato de integración Zenoytdl ↔ ytdl-sub

## Finalidad
Documentar cómo el modelo interno de Zenoytdl se traduce hacia la configuración y ejecución de `ytdl-sub`.

## Principios
- La capa de integración no define negocio.
- Solo consume configuración ya validada.
- Todo fallback debe estar documentado.
- Todo mapping debe ser trazable.

## Comprobaciones mínimas de runtime (Hito 0)
Antes de cualquier traducción real, el core ejecuta detección de dependencias críticas:
- resolución de binario `ytdl-sub` en `PATH`,
- resolución de binario `ffmpeg` en `PATH`.

Estas comprobaciones son smoke checks de disponibilidad y no reemplazan validaciones semánticas del contrato de traducción.

## Componentes del contrato
- mappings de campos Zenoytdl → capa inferior
- normalización previa
- límites de formatos y parámetros
- fallbacks compatibles
- errores traducibles a mensajes operativos claros

## Regla de cambios
Si cambia este contrato, deben actualizarse pruebas de integración y ejemplos. El README no se modifica hasta que el hito responsable del cambio esté cerrado formalmente.
