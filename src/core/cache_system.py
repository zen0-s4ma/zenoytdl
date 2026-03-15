from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from src.config.config_loader import ParsedConfigBundle
from src.config.validation import ValidationReport, validate_parsed_config_bundle
from src.integration.ytdl_sub.compiler import CompiledArtifactBatch, compile_bundle_to_artifacts
from src.integration.ytdl_sub.translator import (
    TranslatedYtdlSubModel,
    translate_bundle_to_ytdl_sub_model,
)
from src.persistence.sqlite_state import SQLiteOperationalState


@dataclass(frozen=True)
class CacheContext:
    file_fingerprint: str
    content_hash: str
    config_signature: str
    ytdl_sub_conf_signature: str


@dataclass(frozen=True)
class CacheMetrics:
    hits: int = 0
    misses: int = 0

    def register_hit(self) -> "CacheMetrics":
        return CacheMetrics(hits=self.hits + 1, misses=self.misses)

    def register_miss(self) -> "CacheMetrics":
        return CacheMetrics(hits=self.hits, misses=self.misses + 1)


@dataclass(frozen=True)
class CacheEntry:
    scope: str
    key: str
    value: Any
    context: CacheContext
    created_at: datetime
    expires_at: datetime


_DEFAULT_TTL_BY_SCOPE = {
    "config_compilation": 120,
    "validation": 120,
    "translation": 120,
    "metadata_resolution": 60,
    "operational_state_recent": 15,
}


class CoreCacheSystem:
    def __init__(
        self,
        *,
        ttl_by_scope: dict[str, int] | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._ttl_by_scope = {**_DEFAULT_TTL_BY_SCOPE, **(ttl_by_scope or {})}
        self._now_provider = now_provider or (lambda: datetime.now(timezone.utc))
        self._entries: dict[tuple[str, str], CacheEntry] = {}
        self._metrics: dict[str, CacheMetrics] = {}

    def get(self, *, scope: str, key: str, context: CacheContext) -> Any | None:
        cache_key = (scope, key)
        entry = self._entries.get(cache_key)
        if entry is None:
            self._register_miss(scope)
            return None

        now = self._now_provider()
        if entry.expires_at <= now:
            self._entries.pop(cache_key, None)
            self._register_miss(scope)
            return None

        if entry.context.file_fingerprint != context.file_fingerprint:
            self._entries.pop(cache_key, None)
            self._register_miss(scope)
            return None

        if entry.context.content_hash != context.content_hash:
            self._entries.pop(cache_key, None)
            self._register_miss(scope)
            return None

        if entry.context.config_signature != context.config_signature:
            self._entries.pop(cache_key, None)
            self._register_miss(scope)
            return None

        if entry.context.ytdl_sub_conf_signature != context.ytdl_sub_conf_signature:
            self._entries.pop(cache_key, None)
            self._register_miss(scope)
            return None

        self._register_hit(scope)
        return entry.value

    def put(self, *, scope: str, key: str, context: CacheContext, value: Any) -> None:
        now = self._now_provider()
        ttl_seconds = self._ttl_by_scope.get(scope, 0)
        expires_at = now if ttl_seconds <= 0 else now + timedelta(seconds=ttl_seconds)
        self._entries[(scope, key)] = CacheEntry(
            scope=scope,
            key=key,
            value=value,
            context=context,
            created_at=now,
            expires_at=expires_at,
        )

    def purge(self, *, scope: str | None = None) -> None:
        if scope is None:
            self._entries.clear()
            return
        keys_to_delete = [cache_key for cache_key in self._entries if cache_key[0] == scope]
        for cache_key in keys_to_delete:
            self._entries.pop(cache_key, None)

    def invalidate_error(self, *, scope: str, key: str) -> None:
        self._entries.pop((scope, key), None)

    def metrics_snapshot(self) -> dict[str, dict[str, int]]:
        scopes = sorted(set(self._ttl_by_scope) | set(self._metrics))
        return {
            scope: {
                "hits": self._metrics.get(scope, CacheMetrics()).hits,
                "misses": self._metrics.get(scope, CacheMetrics()).misses,
            }
            for scope in scopes
        }

    def _register_hit(self, scope: str) -> None:
        self._metrics[scope] = self._metrics.get(scope, CacheMetrics()).register_hit()

    def _register_miss(self, scope: str) -> None:
        self._metrics[scope] = self._metrics.get(scope, CacheMetrics()).register_miss()


class CachedCorePipeline:
    def __init__(self, cache: CoreCacheSystem) -> None:
        self.cache = cache

    def validate(self, bundle: ParsedConfigBundle) -> ValidationReport:
        context = _context_from_bundle(bundle)
        key = f"validation::{bundle.signature}"
        cached = self.cache.get(scope="validation", key=key, context=context)
        if isinstance(cached, ValidationReport):
            return cached
        result = validate_parsed_config_bundle(bundle)
        self.cache.put(scope="validation", key=key, context=context, value=result)
        return result

    def translate(self, bundle: ParsedConfigBundle) -> tuple[TranslatedYtdlSubModel, ...]:
        context = _context_from_bundle(bundle)
        key = f"translation::{bundle.signature}"
        cached = self.cache.get(scope="translation", key=key, context=context)
        if isinstance(cached, tuple):
            return cached
        translated = translate_bundle_to_ytdl_sub_model(bundle)
        self.cache.put(scope="translation", key=key, context=context, value=translated)
        return translated

    def compile(self, bundle: ParsedConfigBundle, output_root: Path) -> CompiledArtifactBatch:
        context = _context_from_bundle(bundle)
        key = f"config_compilation::{bundle.signature}::{output_root.resolve()}"
        cached = self.cache.get(scope="config_compilation", key=key, context=context)
        if isinstance(cached, CompiledArtifactBatch):
            return cached
        batch = compile_bundle_to_artifacts(bundle, output_root)
        self.cache.put(scope="config_compilation", key=key, context=context, value=batch)
        return batch

    def resolve_metadata_profile_id(self, metadata_json_path: Path) -> str:
        payload = metadata_json_path.read_text(encoding="utf-8")
        file_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        context = CacheContext(
            file_fingerprint=_single_file_fingerprint(metadata_json_path),
            content_hash=file_hash,
            config_signature=file_hash,
            ytdl_sub_conf_signature=file_hash,
        )
        key = str(metadata_json_path.resolve())
        cached = self.cache.get(scope="metadata_resolution", key=key, context=context)
        if isinstance(cached, str) and cached:
            return cached
        profile_id = _extract_profile_id(payload)
        self.cache.put(scope="metadata_resolution", key=key, context=context, value=profile_id)
        return profile_id

    def get_recent_subscription_state(
        self,
        *,
        state: SQLiteOperationalState,
        subscription_id: str,
    ) -> dict[str, Any]:
        snapshot = state.get_subscription_state(subscription_id)
        runs = snapshot.get("runs", [])
        latest_run = runs[-1]["run_id"] if runs else 0
        context = CacheContext(
            file_fingerprint=f"{state.db_path}:{latest_run}",
            content_hash=str(latest_run),
            config_signature=snapshot["subscription"]["config_signature"],
            ytdl_sub_conf_signature=snapshot["subscription"]["config_signature"],
        )
        key = f"{state.db_path.resolve()}::{subscription_id}"
        cached = self.cache.get(scope="operational_state_recent", key=key, context=context)
        if isinstance(cached, dict):
            return cached
        self.cache.put(scope="operational_state_recent", key=key, context=context, value=snapshot)
        return snapshot


def _context_from_bundle(bundle: ParsedConfigBundle) -> CacheContext:
    payload_hash = hashlib.sha256(
        json.dumps(
            bundle.raw_documents,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    ytdl_conf_signature = hashlib.sha256(
        json.dumps(
            bundle.raw_documents["ytdl-sub-conf.yaml"],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    return CacheContext(
        file_fingerprint=_bundle_file_fingerprint(bundle),
        content_hash=payload_hash,
        config_signature=bundle.signature,
        ytdl_sub_conf_signature=ytdl_conf_signature,
    )


def _bundle_file_fingerprint(bundle: ParsedConfigBundle) -> str:
    parts: list[str] = []
    for file_name in sorted(bundle.file_paths):
        path = bundle.file_paths[file_name]
        stat = path.stat()
        parts.append(f"{file_name}:{stat.st_mtime_ns}:{stat.st_size}")
    return "|".join(parts)


def _single_file_fingerprint(path: Path) -> str:
    stat = path.stat()
    return f"{path.resolve()}:{stat.st_mtime_ns}:{stat.st_size}"


def _extract_profile_id(metadata_json: str) -> str:
    payload = json.loads(metadata_json)
    profile_id = payload.get("profile_id")
    if not isinstance(profile_id, str) or not profile_id:
        raise ValueError("metadata.profile_id inválido")
    return profile_id
