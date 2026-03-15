from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.config.config_loader import ParsedConfigBundle
from src.integration.ytdl_sub.translator import (
    TranslatedYtdlSubModel,
    translate_bundle_to_ytdl_sub_model,
)


class ArtifactCompilationError(ValueError):
    """Error de compilación de artefactos finales para ytdl-sub."""


@dataclass(frozen=True)
class CompiledSubscriptionArtifact:
    subscription_id: str
    output_dir: Path
    layout_name: str
    artifact_yaml_path: Path
    metadata_json_path: Path
    compilation_signature: str
    effective_signature: str
    translation_signature: str
    reused_previous: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "subscription_id": self.subscription_id,
            "layout_name": self.layout_name,
            "artifact_yaml": self.artifact_yaml_path.name,
            "metadata_json": self.metadata_json_path.name,
            "compilation_signature": self.compilation_signature,
            "effective_signature": self.effective_signature,
            "translation_signature": self.translation_signature,
            "reused_previous": self.reused_previous,
            "is_invocable": True,
        }


@dataclass(frozen=True)
class CompiledArtifactBatch:
    output_root: Path
    artifacts: tuple[CompiledSubscriptionArtifact, ...]
    cleaned_paths: tuple[Path, ...]
    index_path: Path

    def to_dict(self) -> dict[str, Any]:
        return {
            "output_root": str(self.output_root),
            "artifacts": [item.to_dict() for item in self.artifacts],
            "cleaned_paths": [str(item) for item in self.cleaned_paths],
            "index_path": str(self.index_path),
        }


def compile_translated_model(
    translated: TranslatedYtdlSubModel,
    output_root: Path,
) -> CompiledSubscriptionArtifact:
    return compile_translated_batch((translated,), output_root, clean_stale=False).artifacts[0]


def compile_translated_batch(
    translated_models: tuple[TranslatedYtdlSubModel, ...],
    output_root: Path,
    *,
    clean_stale: bool = True,
) -> CompiledArtifactBatch:
    if not translated_models:
        raise ArtifactCompilationError("No hay modelos traducidos para compilar")

    ordered = tuple(sorted(translated_models, key=lambda item: item.subscription_id))
    root = output_root.resolve()
    root.mkdir(parents=True, exist_ok=True)

    artifacts: list[CompiledSubscriptionArtifact] = []
    keep_dirs: set[Path] = set()

    for item in ordered:
        artifact = _compile_single(item, root)
        artifacts.append(artifact)
        keep_dirs.add(artifact.output_dir)

    cleaned_paths: list[Path] = []
    if clean_stale:
        cleaned_paths = _clean_previous_outputs(root, keep_dirs)

    index_payload = {
        "batch_signature": _batch_signature(tuple(artifacts)),
        "layout_version": 1,
        "artifacts": [artifact.to_dict() for artifact in artifacts],
    }
    index_path = root / "index.json"
    _write_if_changed(index_path, _to_stable_json(index_payload))

    return CompiledArtifactBatch(
        output_root=root,
        artifacts=tuple(artifacts),
        cleaned_paths=tuple(sorted(cleaned_paths)),
        index_path=index_path,
    )


def compile_bundle_to_artifacts(
    bundle: ParsedConfigBundle,
    output_root: Path,
    *,
    clean_stale: bool = True,
) -> CompiledArtifactBatch:
    translated = translate_bundle_to_ytdl_sub_model(bundle)
    return compile_translated_batch(translated, output_root, clean_stale=clean_stale)


def _compile_single(
    translated: TranslatedYtdlSubModel,
    output_root: Path,
) -> CompiledSubscriptionArtifact:
    if translated.is_valid is False:
        raise ArtifactCompilationError(
            f"No se puede compilar '{translated.subscription_id}': traducción inválida"
        )
    model = translated.ytdl_sub_model
    _validate_invocable_payload(model)

    effective_signature = _get_meta_field(model, "effective_signature")
    layout_name = _build_layout_name(translated.subscription_id, translated.translation_signature)
    artifact_dir = output_root / layout_name
    artifact_dir.mkdir(parents=True, exist_ok=True)

    compilation_signature = _build_compilation_signature(model, translated.translation_signature)

    artifact_yaml_path = artifact_dir / "artifact.yaml"
    metadata_json_path = artifact_dir / "metadata.json"

    artifact_yaml = _to_simple_yaml(model)
    metadata_payload = {
        "layout_version": 1,
        "subscription_id": translated.subscription_id,
        "profile_id": translated.profile_id,
        "effective_signature": effective_signature,
        "translation_signature": translated.translation_signature,
        "compilation_signature": compilation_signature,
        "artifact_yaml": artifact_yaml_path.name,
        "is_invocable": True,
    }

    reused_yaml = _write_if_changed(artifact_yaml_path, artifact_yaml)
    reused_metadata = _write_if_changed(metadata_json_path, _to_stable_json(metadata_payload))

    return CompiledSubscriptionArtifact(
        subscription_id=translated.subscription_id,
        output_dir=artifact_dir,
        layout_name=layout_name,
        artifact_yaml_path=artifact_yaml_path,
        metadata_json_path=metadata_json_path,
        compilation_signature=compilation_signature,
        effective_signature=effective_signature,
        translation_signature=translated.translation_signature,
        reused_previous=reused_yaml and reused_metadata,
    )


def _validate_invocable_payload(model: dict[str, Any]) -> None:
    if not isinstance(model, dict) or not model:
        raise ArtifactCompilationError("Modelo traducido vacío; no es invocable")

    subscription = model.get("subscription")
    if not isinstance(subscription, dict):
        raise ArtifactCompilationError("Falta bloque subscription en modelo traducido")

    invocation = subscription.get("invocation")
    if not isinstance(invocation, dict):
        raise ArtifactCompilationError("Falta bloque invocation en modelo traducido")

    binary = invocation.get("binary")
    mode = invocation.get("mode")

    if not isinstance(binary, str) or not binary.strip():
        raise ArtifactCompilationError("invocation.binary inválido en compilado")
    if not isinstance(mode, str) or mode.strip() not in {"sub", "dl"}:
        raise ArtifactCompilationError("invocation.mode inválido en compilado")


def _clean_previous_outputs(output_root: Path, keep_dirs: set[Path]) -> list[Path]:
    removed: list[Path] = []
    for entry in sorted(output_root.iterdir()):
        if entry.name == "index.json":
            continue
        if entry.is_dir() and entry not in keep_dirs:
            for child in sorted(entry.rglob("*"), reverse=True):
                if child.is_file():
                    child.unlink()
                elif child.is_dir():
                    child.rmdir()
            entry.rmdir()
            removed.append(entry)
    return removed


def _to_stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"


def _write_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return True
    path.write_text(content, encoding="utf-8")
    return False


def _build_layout_name(subscription_id: str, translation_signature: str) -> str:
    safe_name = re.sub(r"[^a-zA-Z0-9._-]", "-", subscription_id).strip("-._")
    return f"{safe_name}--{translation_signature[:12]}"


def _batch_signature(artifacts: tuple[CompiledSubscriptionArtifact, ...]) -> str:
    payload = [
        {
            "subscription_id": item.subscription_id,
            "compilation_signature": item.compilation_signature,
        }
        for item in artifacts
    ]
    return hashlib.sha256(_to_stable_json({"artifacts": payload}).encode("utf-8")).hexdigest()


def _build_compilation_signature(model: dict[str, Any], translation_signature: str) -> str:
    payload = {
        "translation_signature": translation_signature,
        "model": model,
    }
    return hashlib.sha256(_to_stable_json(payload).encode("utf-8")).hexdigest()


def _get_meta_field(model: dict[str, Any], key: str) -> str:
    meta = model.get("meta")
    if not isinstance(meta, dict):
        raise ArtifactCompilationError("Falta bloque meta en modelo traducido")
    value = meta.get(key)
    if not isinstance(value, str) or not value:
        raise ArtifactCompilationError(f"meta.{key} inválido en modelo traducido")
    return value


def _to_simple_yaml(payload: Any, indent: int = 0) -> str:
    prefix = "  " * indent
    if isinstance(payload, dict):
        lines: list[str] = []
        for key in sorted(payload):
            value = payload[key]
            if isinstance(value, (dict, list)):
                lines.append(f"{prefix}{key}:")
                lines.append(_to_simple_yaml(value, indent + 1))
            else:
                lines.append(f"{prefix}{key}: {_yaml_scalar(value)}")
        return "\n".join(lines)

    if isinstance(payload, list):
        lines = []
        for value in payload:
            if isinstance(value, (dict, list)):
                lines.append(f"{prefix}-")
                lines.append(_to_simple_yaml(value, indent + 1))
            else:
                lines.append(f"{prefix}- {_yaml_scalar(value)}")
        return "\n".join(lines)

    return f"{prefix}{_yaml_scalar(payload)}"


def _yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)

    text = str(value)
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
