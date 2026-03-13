# Contrato de archivos de configuración YAML

## Objetivos
- Expresar intención del usuario con semántica clara.
- Separar lo global, lo reutilizable y lo concreto.
- Permitir validación fuerte y mensajes de error útiles.

## configuracion-general.yaml
Propósito: parámetros globales.
Campos base:
- `workspace`: ruta base.
- `default_profile`: perfil por defecto.
- `log_level`: nivel de log.
- `environment`: entorno lógico.

## profiles.yaml
Propósito: perfiles reutilizables.
Campos base:
- `name`
- `platform`
- `ytdl_options`
- `postprocess`
- `output_policy`

Reglas:
- `name` único.
- Tipos estrictos.
- No se aceptan campos desconocidos salvo extensiones documentadas.

## subscriptions.yaml
Propósito: entradas concretas.
Campos base:
- `name`
- `profile`
- `items`
- `enabled`
- `overrides`

Reglas:
- `profile` debe existir.
- `name` único.
- `items` no vacío.

## integrations.yaml
Propósito: contrato con dependencias externas.
Campos base:
- mappings de opciones
- límites
- formatos permitidos
- fallbacks

## cache.yaml
Propósito: política de caché e invalidación.
Campos base:
- hashing
- retención
- invalidation_rules
- persist_enabled

## queues.yaml
Propósito: política de cola.
Campos base:
- concurrency
- retries
- priority_strategy
- shutdown_policy

## logging.yaml
Propósito: observabilidad.
Campos base:
- level
- format
- sinks
- rotation

## Regla sobre evolución del README
Si el contrato cambia durante un hito, la documentación de contrato sí debe actualizarse inmediatamente; sin embargo, el `README.md` sólo podrá reflejar ese cambio como capacidad del proyecto cuando el hito correspondiente quede cerrado con regresión acumulada en verde.
