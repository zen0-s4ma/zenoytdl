# Compilación de artefactos ejecutables (Hito 11)

## Alcance
Este módulo materializa la salida traducida del Hito 10 en artefactos finales en disco, listos para ser consumidos por la siguiente capa (Hito 12+) sin ejecutar `ytdl-sub`.

## Entrada y salida
- Entrada: `TranslatedYtdlSubModel` válido (Hito 10).
- Salida: layout compilado estable bajo un directorio raíz:
  - `<subscription_id_normalized>--<translation_signature[:12]>/artifact.yaml`
  - `<subscription_id_normalized>--<translation_signature[:12]>/metadata.json`
  - `index.json` de lote.

## Contratos de compilación
1. **Validación de invocabilidad**: sólo se compila si existe `subscription.invocation` con `binary` y `mode` válido (`sub|dl`).
2. **Asociación de firma**:
   - `translation_signature` (Hito 10),
   - `effective_signature` (meta del modelo),
   - `compilation_signature` (hash estable del payload compilado).
3. **Naming determinista**: el directorio de salida depende de `subscription_id` + `translation_signature`.
4. **Recompilación estable**: si el contenido no cambia, no se reescriben `artifact.yaml` ni `metadata.json` y se marca `reused_previous=true`.
5. **Limpieza controlada**: en compilación de lote, pueden eliminarse directorios obsoletos no presentes en el conjunto compilado (`clean_stale=true`).

## Artefactos producidos
- `artifact.yaml`: representación materializable del modelo ytdl-sub traducido.
- `metadata.json`: metadatos de trazabilidad y firma por unidad compilada.
- `index.json`: índice de lote con todas las unidades compiladas y firma agregada.

## Separación con Hito 12+
- No hay subprocess, no se invocan binarios reales.
- No hay scheduler, colas ni persistencia avanzada.
- La responsabilidad termina cuando los artefactos quedan inspeccionables, trazables y listos para consumo.
