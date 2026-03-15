from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from src.config.yaml_contract import _parse_simple_yaml
from src.integration.ytdl_sub.compiler import CompiledArtifactBatch, CompiledSubscriptionArtifact


class ExecutionPreparationError(ValueError):
    """Error al preparar un artefacto compilado para ejecución."""


class ExecutionErrorType(str, Enum):
    NONE = "none"
    BINARY_NOT_FOUND = "binary_not_found"
    TIMEOUT = "timeout"
    NON_ZERO_EXIT = "non_zero_exit"
    INVALID_COMPILED_ARTIFACT = "invalid_compiled_artifact"
    ENVIRONMENT_ERROR = "environment_error"


class FailureSeverity(str, Enum):
    NONE = "none"
    RECOVERABLE = "recoverable"
    NON_RECOVERABLE = "non_recoverable"


@dataclass(frozen=True)
class ExecutionJobUnit:
    job_id: str
    subscription_id: str
    profile_id: str
    compilation_signature: str
    artifact_dir: Path
    artifact_yaml_path: Path
    metadata_json_path: Path

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "subscription_id": self.subscription_id,
            "profile_id": self.profile_id,
            "compilation_signature": self.compilation_signature,
            "artifact_dir": str(self.artifact_dir),
            "artifact_yaml_path": str(self.artifact_yaml_path),
            "metadata_json_path": str(self.metadata_json_path),
        }


@dataclass(frozen=True)
class PreparedExecutionCommand:
    binary: str
    binary_path: str
    args: tuple[str, ...]
    cwd: Path
    env: dict[str, str]
    timeout_seconds: float
    temporary_dir: Path
    invocation_metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "binary": self.binary,
            "binary_path": self.binary_path,
            "args": list(self.args),
            "cwd": str(self.cwd),
            "env": dict(self.env),
            "timeout_seconds": self.timeout_seconds,
            "temporary_dir": str(self.temporary_dir),
            "invocation_metadata": json.loads(
                json.dumps(self.invocation_metadata, sort_keys=True, ensure_ascii=False)
            ),
        }


@dataclass(frozen=True)
class ExecutedJobResult:
    job: ExecutionJobUnit
    command: PreparedExecutionCommand
    exit_code: int | None
    stdout: str
    stderr: str
    status: str
    error_type: ExecutionErrorType
    severity: FailureSeverity
    error_message: str | None

    @property
    def ok(self) -> bool:
        return self.error_type == ExecutionErrorType.NONE and self.exit_code == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "job": self.job.to_dict(),
            "command": self.command.to_dict(),
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "status": self.status,
            "error_type": self.error_type.value,
            "severity": self.severity.value,
            "error_message": self.error_message,
            "ok": self.ok,
        }


def prepare_execution_job(
    artifact: CompiledSubscriptionArtifact,
    *,
    work_unit_id: str | None = None,
) -> ExecutionJobUnit:
    metadata = _read_metadata_payload(artifact.metadata_json_path)
    profile_id = metadata.get("profile_id")
    if not isinstance(profile_id, str) or not profile_id:
        raise ExecutionPreparationError("metadata.profile_id inválido en compilado")

    suffix = artifact.compilation_signature[:12]
    job_id = work_unit_id or f"exec::{artifact.subscription_id}::{suffix}"

    return ExecutionJobUnit(
        job_id=job_id,
        subscription_id=artifact.subscription_id,
        profile_id=profile_id,
        compilation_signature=artifact.compilation_signature,
        artifact_dir=artifact.output_dir,
        artifact_yaml_path=artifact.artifact_yaml_path,
        metadata_json_path=artifact.metadata_json_path,
    )


def build_execution_command(
    job: ExecutionJobUnit,
    *,
    global_args: tuple[str, ...] = (),
    env_overrides: dict[str, str] | None = None,
    cwd: Path | None = None,
    timeout_seconds: float = 300.0,
    temporary_root: Path | None = None,
) -> PreparedExecutionCommand:
    payload = _read_artifact_invocation(job.artifact_yaml_path)
    binary = payload["binary"]
    mode = payload["mode"]
    invocation_extra_args = payload["extra_args"]

    execution_cwd = (cwd or job.artifact_dir).resolve()
    execution_env = dict(os.environ)
    if env_overrides:
        execution_env.update(env_overrides)

    binary_path = shutil.which(binary, path=execution_env.get("PATH"))
    if not binary_path:
        raise FileNotFoundError(f"No se encontró el binario requerido: {binary}")

    temp_root = (temporary_root or Path(tempfile.gettempdir())).resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    execution_tmp = Path(tempfile.mkdtemp(prefix="zenoytdl-exec-", dir=str(temp_root)))
    execution_env["ZENOYTDL_TMP_DIR"] = str(execution_tmp)

    args = (
        binary_path,
        mode,
        "--artifact",
        str(job.artifact_yaml_path),
        *global_args,
        *invocation_extra_args,
    )

    return PreparedExecutionCommand(
        binary=binary,
        binary_path=binary_path,
        args=args,
        cwd=execution_cwd,
        env=execution_env,
        timeout_seconds=timeout_seconds,
        temporary_dir=execution_tmp,
        invocation_metadata={
            "mode": mode,
            "global_args": list(global_args),
            "extra_args": list(invocation_extra_args),
        },
    )


def execute_prepared_command(
    job: ExecutionJobUnit,
    command: PreparedExecutionCommand,
) -> ExecutedJobResult:
    try:
        completed = subprocess.run(
            command.args,
            cwd=str(command.cwd),
            env=command.env,
            capture_output=True,
            text=True,
            timeout=command.timeout_seconds,
            check=False,
        )
    except TimeoutExpired as exc:
        return ExecutedJobResult(
            job=job,
            command=command,
            exit_code=None,
            stdout=(
                exc.stdout.decode("utf-8") if isinstance(exc.stdout, bytes) else exc.stdout or ""
            ),
            stderr=(
                exc.stderr.decode("utf-8") if isinstance(exc.stderr, bytes) else exc.stderr or ""
            ),
            status="failed",
            error_type=ExecutionErrorType.TIMEOUT,
            severity=FailureSeverity.RECOVERABLE,
            error_message=f"La ejecución excedió timeout de {command.timeout_seconds} segundos",
        )
    except OSError as exc:
        error_type = ExecutionErrorType.ENVIRONMENT_ERROR
        severity = FailureSeverity.NON_RECOVERABLE
        if "not found" in str(exc).lower() or "no such file" in str(exc).lower():
            error_type = ExecutionErrorType.BINARY_NOT_FOUND
            severity = FailureSeverity.RECOVERABLE

        return ExecutedJobResult(
            job=job,
            command=command,
            exit_code=None,
            stdout="",
            stderr=str(exc),
            status="failed",
            error_type=error_type,
            severity=severity,
            error_message=str(exc),
        )

    if completed.returncode == 0:
        return ExecutedJobResult(
            job=job,
            command=command,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            status="success",
            error_type=ExecutionErrorType.NONE,
            severity=FailureSeverity.NONE,
            error_message=None,
        )

    return ExecutedJobResult(
        job=job,
        command=command,
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        status="failed",
        error_type=ExecutionErrorType.NON_ZERO_EXIT,
        severity=FailureSeverity.RECOVERABLE,
        error_message=f"Ejecución finalizó con código {completed.returncode}",
    )


def execute_compiled_artifact(
    artifact: CompiledSubscriptionArtifact,
    *,
    work_unit_id: str | None = None,
    global_args: tuple[str, ...] = (),
    env_overrides: dict[str, str] | None = None,
    cwd: Path | None = None,
    timeout_seconds: float = 300.0,
    temporary_root: Path | None = None,
) -> ExecutedJobResult:
    try:
        job = prepare_execution_job(artifact, work_unit_id=work_unit_id)
        command = build_execution_command(
            job,
            global_args=global_args,
            env_overrides=env_overrides,
            cwd=cwd,
            timeout_seconds=timeout_seconds,
            temporary_root=temporary_root,
        )
    except FileNotFoundError as exc:
        job = _fallback_job_from_artifact(artifact, work_unit_id=work_unit_id)
        return ExecutedJobResult(
            job=job,
            command=_empty_command(job),
            exit_code=None,
            stdout="",
            stderr=str(exc),
            status="failed",
            error_type=ExecutionErrorType.BINARY_NOT_FOUND,
            severity=FailureSeverity.RECOVERABLE,
            error_message=str(exc),
        )
    except ExecutionPreparationError as exc:
        job = _fallback_job_from_artifact(artifact, work_unit_id=work_unit_id)
        return ExecutedJobResult(
            job=job,
            command=_empty_command(job),
            exit_code=None,
            stdout="",
            stderr=str(exc),
            status="failed",
            error_type=ExecutionErrorType.INVALID_COMPILED_ARTIFACT,
            severity=FailureSeverity.NON_RECOVERABLE,
            error_message=str(exc),
        )

    return execute_prepared_command(job, command)


def execute_compiled_batch(
    batch: CompiledArtifactBatch,
    *,
    global_args: tuple[str, ...] = (),
    env_overrides: dict[str, str] | None = None,
    timeout_seconds: float = 300.0,
) -> tuple[ExecutedJobResult, ...]:
    results = [
        execute_compiled_artifact(
            artifact,
            work_unit_id=f"batch::{artifact.subscription_id}::{artifact.compilation_signature[:8]}",
            global_args=global_args,
            env_overrides=env_overrides,
            timeout_seconds=timeout_seconds,
            temporary_root=batch.output_root / ".tmp_exec",
        )
        for artifact in batch.artifacts
    ]
    return tuple(results)


def _fallback_job_from_artifact(
    artifact: CompiledSubscriptionArtifact,
    *,
    work_unit_id: str | None,
) -> ExecutionJobUnit:
    suffix = artifact.compilation_signature[:12]
    return ExecutionJobUnit(
        job_id=work_unit_id or f"exec::{artifact.subscription_id}::{suffix}",
        subscription_id=artifact.subscription_id,
        profile_id="unknown",
        compilation_signature=artifact.compilation_signature,
        artifact_dir=artifact.output_dir,
        artifact_yaml_path=artifact.artifact_yaml_path,
        metadata_json_path=artifact.metadata_json_path,
    )


def _empty_command(job: ExecutionJobUnit) -> PreparedExecutionCommand:
    return PreparedExecutionCommand(
        binary="",
        binary_path="",
        args=tuple(),
        cwd=job.artifact_dir,
        env={},
        timeout_seconds=0,
        temporary_dir=job.artifact_dir,
        invocation_metadata={},
    )


def _read_metadata_payload(metadata_path: Path) -> dict[str, Any]:
    if not metadata_path.exists():
        raise ExecutionPreparationError("Falta metadata.json en compilado")

    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ExecutionPreparationError("metadata.json inválido en compilado") from exc

    if not isinstance(payload, dict):
        raise ExecutionPreparationError("metadata.json debe ser objeto")

    return payload


def _read_artifact_invocation(artifact_yaml_path: Path) -> dict[str, Any]:
    if not artifact_yaml_path.exists():
        raise ExecutionPreparationError("Falta artifact.yaml en compilado")

    payload = _parse_simple_yaml(artifact_yaml_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ExecutionPreparationError("artifact.yaml inválido en compilado")

    subscription = payload.get("subscription")
    if not isinstance(subscription, dict):
        raise ExecutionPreparationError("artifact.yaml sin bloque subscription")

    invocation = subscription.get("invocation")
    if not isinstance(invocation, dict):
        raise ExecutionPreparationError("artifact.yaml sin bloque invocation")

    binary = invocation.get("binary")
    mode = invocation.get("mode")
    extra_args = invocation.get("extra_args", [])

    if not isinstance(binary, str) or not binary.strip():
        raise ExecutionPreparationError("invocation.binary inválido en compilado")
    if not isinstance(mode, str) or mode not in {"sub", "dl"}:
        raise ExecutionPreparationError("invocation.mode inválido en compilado")
    if not isinstance(extra_args, list) or not all(isinstance(item, str) for item in extra_args):
        raise ExecutionPreparationError("invocation.extra_args inválido en compilado")

    return {"binary": binary, "mode": mode, "extra_args": tuple(extra_args)}


TimeoutExpired = subprocess.TimeoutExpired
