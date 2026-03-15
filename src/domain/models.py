from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Mapping

PrimitiveValue = str | int | float | bool
NormalizedMap = dict[str, PrimitiveValue]


class DomainValidationError(ValueError):
    """Error de validación del dominio interno de Zenoytdl."""


class SubscriptionSourceKind(str, Enum):
    CHANNEL = "channel"
    PLAYLIST = "playlist"
    SEARCH = "search"


class PostProcessingKind(str, Enum):
    EMBED_THUMBNAIL = "embed_thumbnail"
    EXTRACT_AUDIO = "extract_audio"
    CLEANUP_METADATA = "cleanup_metadata"


class JobKind(str, Enum):
    VALIDATION = "validation"
    COMPILATION = "compilation"
    SYNC = "sync"
    DOWNLOAD = "download"
    POSTPROCESSING = "postprocessing"
    MAINTENANCE = "maintenance"
    COMPILE = "compilation"


class JobPriority(IntEnum):
    LOW = 10
    NORMAL = 50
    HIGH = 80
    CRITICAL = 100


class JobStatus(str, Enum):
    QUEUED = "queued"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY_PENDING = "retry_pending"
    CANCELLED = "cancelled"
    DEAD_LETTER = "dead_letter"
    PENDING = "queued"
    SUCCESS = "completed"


_JOB_ALLOWED_TRANSITIONS: dict[JobStatus, frozenset[JobStatus]] = {
    JobStatus.QUEUED: frozenset({JobStatus.SCHEDULED, JobStatus.RUNNING, JobStatus.CANCELLED}),
    JobStatus.SCHEDULED: frozenset(
        {JobStatus.RUNNING, JobStatus.WAITING, JobStatus.CANCELLED, JobStatus.RETRY_PENDING}
    ),
    JobStatus.RUNNING: frozenset(
        {
            JobStatus.WAITING,
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.RETRY_PENDING,
            JobStatus.CANCELLED,
            JobStatus.DEAD_LETTER,
        }
    ),
    JobStatus.WAITING: frozenset(
        {JobStatus.SCHEDULED, JobStatus.RUNNING, JobStatus.RETRY_PENDING, JobStatus.CANCELLED}
    ),
    JobStatus.RETRY_PENDING: frozenset(
        {JobStatus.QUEUED, JobStatus.SCHEDULED, JobStatus.CANCELLED, JobStatus.DEAD_LETTER}
    ),
    JobStatus.COMPLETED: frozenset(),
    JobStatus.FAILED: frozenset(
        {JobStatus.RETRY_PENDING, JobStatus.DEAD_LETTER, JobStatus.CANCELLED}
    ),
    JobStatus.CANCELLED: frozenset(),
    JobStatus.DEAD_LETTER: frozenset(),
}


class CompiledArtifactFormat(str, Enum):
    ZENO_INTERNAL = "zeno_internal"
    YTDL_SUB_CANDIDATE = "ytdl_sub_candidate"


def normalize_identifier(value: str, field_name: str = "id") -> str:
    normalized = value.strip().lower()
    if not normalized:
        raise DomainValidationError(f"{field_name} no puede estar vacío")
    return normalized


def _normalize_mapping(values: Mapping[str, PrimitiveValue], field_name: str) -> NormalizedMap:
    normalized: NormalizedMap = {}
    for raw_key, raw_value in values.items():
        key = raw_key.strip()
        if not key:
            raise DomainValidationError(f"{field_name} contiene clave vacía")
        normalized[key] = raw_value
    return normalized


@dataclass(frozen=True)
class GeneralConfig:
    id: str
    workspace: str
    library_dir: str
    timezone: str = "UTC"

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", normalize_identifier(self.id, "general_config.id"))
        for attr in ("workspace", "library_dir", "timezone"):
            value = getattr(self, attr).strip()
            if not value:
                raise DomainValidationError(f"general_config.{attr} no puede estar vacío")
            object.__setattr__(self, attr, value)


@dataclass(frozen=True)
class PostProcessing:
    id: str
    kind: PostProcessingKind
    parameters: NormalizedMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", normalize_identifier(self.id, "postprocessing.id"))
        normalized = _normalize_mapping(self.parameters, "postprocessing.parameters")
        if self.kind == PostProcessingKind.EXTRACT_AUDIO and "codec" not in normalized:
            raise DomainValidationError("extract_audio requiere parámetro 'codec'")
        object.__setattr__(self, "parameters", normalized)


@dataclass(frozen=True)
class Profile:
    id: str
    name: str
    base_options: NormalizedMap = field(default_factory=dict)
    postprocessing_ids: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", normalize_identifier(self.id, "profile.id"))
        name = self.name.strip()
        if not name:
            raise DomainValidationError("profile.name no puede estar vacío")
        object.__setattr__(self, "name", name)
        object.__setattr__(
            self,
            "base_options",
            _normalize_mapping(self.base_options, "profile.base_options"),
        )
        normalized_pp = tuple(
            normalize_identifier(pid, "profile.postprocessing_ids")
            for pid in self.postprocessing_ids
        )
        if len(set(normalized_pp)) != len(normalized_pp):
            raise DomainValidationError("profile.postprocessing_ids no puede contener duplicados")
        object.__setattr__(self, "postprocessing_ids", normalized_pp)


@dataclass(frozen=True)
class Override:
    id: str
    profile_id: str
    options: NormalizedMap

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", normalize_identifier(self.id, "override.id"))
        object.__setattr__(
            self,
            "profile_id",
            normalize_identifier(self.profile_id, "override.profile_id"),
        )
        normalized_options = _normalize_mapping(self.options, "override.options")
        if not normalized_options:
            raise DomainValidationError("override.options no puede estar vacío")
        object.__setattr__(self, "options", normalized_options)


@dataclass(frozen=True)
class Subscription:
    id: str
    profile_id: str
    source_kind: SubscriptionSourceKind
    source_value: str
    override_ids: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", normalize_identifier(self.id, "subscription.id"))
        object.__setattr__(
            self,
            "profile_id",
            normalize_identifier(self.profile_id, "subscription.profile_id"),
        )
        source_value = self.source_value.strip()
        if not source_value:
            raise DomainValidationError("subscription.source_value no puede estar vacío")
        object.__setattr__(self, "source_value", source_value)
        normalized_override_ids = tuple(
            normalize_identifier(oid, "subscription.override_ids") for oid in self.override_ids
        )
        if len(set(normalized_override_ids)) != len(normalized_override_ids):
            raise DomainValidationError("subscription.override_ids no puede contener duplicados")
        object.__setattr__(self, "override_ids", normalized_override_ids)


@dataclass(frozen=True)
class EffectiveConfig:
    id: str
    subscription_id: str
    profile_id: str
    resolved_options: NormalizedMap
    postprocessings: tuple[PostProcessing, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", normalize_identifier(self.id, "effective_config.id"))
        object.__setattr__(
            self,
            "subscription_id",
            normalize_identifier(self.subscription_id, "effective_config.subscription_id"),
        )
        object.__setattr__(
            self,
            "profile_id",
            normalize_identifier(self.profile_id, "effective_config.profile_id"),
        )
        options = _normalize_mapping(
            self.resolved_options,
            "effective_config.resolved_options",
        )
        if not options:
            raise DomainValidationError("effective_config.resolved_options no puede estar vacío")
        object.__setattr__(self, "resolved_options", options)


@dataclass(frozen=True)
class CompiledArtifact:
    id: str
    effective_config_id: str
    format: CompiledArtifactFormat
    payload: NormalizedMap

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", normalize_identifier(self.id, "compiled_artifact.id"))
        object.__setattr__(
            self,
            "effective_config_id",
            normalize_identifier(
                self.effective_config_id,
                "compiled_artifact.effective_config_id",
            ),
        )
        payload = _normalize_mapping(self.payload, "compiled_artifact.payload")
        if not payload:
            raise DomainValidationError("compiled_artifact.payload no puede estar vacío")
        object.__setattr__(self, "payload", payload)


@dataclass(frozen=True)
class Job:
    id: str
    job_kind: JobKind
    status: JobStatus
    effective_config_id: str | None = None
    artifact_id: str | None = None
    attempts: int = 0
    priority: int = int(JobPriority.NORMAL)
    subscription_id: str | None = None
    profile_id: str | None = None
    resource_kind: str | None = None
    resource_id: str | None = None
    payload: NormalizedMap = field(default_factory=dict)
    signature: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", normalize_identifier(self.id, "job.id"))
        if self.effective_config_id:
            object.__setattr__(
                self,
                "effective_config_id",
                normalize_identifier(self.effective_config_id, "job.effective_config_id"),
            )
        if self.artifact_id:
            object.__setattr__(
                self,
                "artifact_id",
                normalize_identifier(self.artifact_id, "job.artifact_id"),
            )
        if self.subscription_id:
            object.__setattr__(
                self,
                "subscription_id",
                normalize_identifier(self.subscription_id, "job.subscription_id"),
            )
        if self.profile_id:
            object.__setattr__(
                self,
                "profile_id",
                normalize_identifier(self.profile_id, "job.profile_id"),
            )
        if self.resource_kind:
            object.__setattr__(self, "resource_kind", self.resource_kind.strip())
        if self.resource_id:
            object.__setattr__(self, "resource_id", self.resource_id.strip())
        normalized_payload = _normalize_mapping(self.payload, "job.payload")
        object.__setattr__(self, "payload", normalized_payload)
        if self.attempts < 0:
            raise DomainValidationError("job.attempts no puede ser negativo")
        if self.priority < 0:
            raise DomainValidationError("job.priority no puede ser negativo")
        if (
            self.subscription_id is None
            and self.profile_id is None
            and self.resource_id is None
            and self.effective_config_id is None
        ):
            raise DomainValidationError(
                "job debe asociarse al menos a subscription_id, profile_id, "
                "resource_id o effective_config_id"
            )
        signature = self.signature or sign_job(
            job_kind=self.job_kind,
            subscription_id=self.subscription_id,
            profile_id=self.profile_id,
            resource_kind=self.resource_kind,
            resource_id=self.resource_id,
            payload=self.payload,
        )
        object.__setattr__(self, "signature", signature)

    def can_transition_to(self, next_status: JobStatus) -> bool:
        return next_status in _JOB_ALLOWED_TRANSITIONS[self.status]


def sign_job(
    *,
    job_kind: JobKind,
    subscription_id: str | None,
    profile_id: str | None,
    resource_kind: str | None,
    resource_id: str | None,
    payload: Mapping[str, PrimitiveValue],
) -> str:
    canonical = {
        "job_kind": job_kind.value,
        "subscription_id": subscription_id,
        "profile_id": profile_id,
        "resource_kind": resource_kind,
        "resource_id": resource_id,
        "payload": dict(sorted(payload.items())),
    }
    return hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
    ).hexdigest()


@dataclass(frozen=True)
class DomainState:
    general_config: GeneralConfig
    profiles: tuple[Profile, ...]
    subscriptions: tuple[Subscription, ...]
    effective_configs: tuple[EffectiveConfig, ...]
    artifacts: tuple[CompiledArtifact, ...]
    jobs: tuple[Job, ...]

    def __post_init__(self) -> None:
        if not self.profiles:
            raise DomainValidationError("domain_state.profiles no puede estar vacío")
