# Hito 2 — Modelo de dominio interno

Este documento fija el lenguaje interno de Zenoytdl para Hito 2, sin adelantar parseo YAML (Hito 3), persistencia real, colas reales, API real ni integración real con ytdl-sub.

## Entidades
- `GeneralConfig`
- `Profile`
- `Subscription`
- `PostProcessing`
- `Override`
- `EffectiveConfig`
- `CompiledArtifact`
- `Job`
- `DomainState`

## Enums y tipos base
- `SubscriptionSourceKind`
- `PostProcessingKind`
- `CompiledArtifactFormat`
- `JobKind`
- `JobStatus`
- `PrimitiveValue` y `NormalizedMap`

## Relaciones
- `Subscription.profile_id` debe existir en `Profile`.
- `Subscription.override_ids` debe resolver a `Override` y compartir `profile_id`.
- `Profile.postprocessing_ids` debe resolver a `PostProcessing`.
- `DomainCatalog.resolve_effective_config(...)` compone la configuración efectiva como:
  1. `Profile.base_options`
  2. overrides asociados a la suscripción
  3. `source` y `source_kind` internos de la suscripción

## Invariantes principales
- IDs normalizados y no vacíos.
- Campos de texto esenciales no vacíos.
- Sin IDs duplicados por colección de catálogo.
- Sin listas duplicadas de overrides o postprocesados.
- `Override.options` y `CompiledArtifact.payload` no vacíos.
- `PostProcessingKind.EXTRACT_AUDIO` exige `codec`.
- `Job.attempts >= 0`.

## Separación de modelos
- El modelo interno vive en `src/domain` y usa semántica de Zenoytdl.
- `CompiledArtifactFormat` distingue artefacto interno y candidato a ytdl-sub sin realizar traducción real.
- No existen llamadas a `subprocess`, SQLite ni módulos de API/persistencia dentro del dominio.
