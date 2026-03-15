from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.api import CoreAPI, RetryRequest, SyncRequest
from src.core import CoreCacheSystem, QueueRuntime
from src.integration.ytdl_sub.executor import (
    ExecutedJobResult,
    ExecutionErrorType,
    ExecutionJobUnit,
    FailureSeverity,
    PreparedExecutionCommand,
)
from src.persistence import SQLiteOperationalState


@pytest.mark.e2e
def test_hito19_e2e_api_client_validation_queue_execution_state_and_retry(tmp_path: Path) -> None:
    state = SQLiteOperationalState(tmp_path / 'state.sqlite')
    state.init_schema()
    runtime = QueueRuntime(
        state=state,
        cache=CoreCacheSystem(),
        now_provider=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    api = CoreAPI(state=state, queue_runtime=runtime)

    config_dir = 'tests/fixtures/hito11/valid/single'
    output_root = str(tmp_path / 'compiled')

    assert api.validate_config(config_dir=config_dir)['data']['validation']['ok'] is True

    sync = api.trigger_sync(
        SyncRequest(config_dir=config_dir, output_root=output_root, priority=80, max_attempts=2)
    )
    assert sync['data']['sync']['total_enqueued'] == 1

    attempts = {'n': 0}

    def fake_execute(job, **kwargs):
        attempts['n'] += 1
        ok = attempts['n'] > 1
        return _result(job.job_id, ok=ok)

    runtime._execute_single = fake_execute

    step1 = api.process_queue_step(config_dir=config_dir, output_root=output_root)
    assert step1['data']['queue_step']['retry_jobs']

    for item in state.list_queue_jobs(include_terminal=True):
        if item.status == 'retry_pending':
            state.transition_queue_job_status(job_id=item.job_id, next_status='queued')

    step2 = api.process_queue_step(config_dir=config_dir, output_root=output_root)
    assert step2['data']['queue_step']['completed_jobs']

    history = api.get_history(config_dir=config_dir)
    assert history['ok'] is True

    # cubrir endpoint de retry sin pendientes/dead-letter
    retry = api.retry_failed_jobs(RetryRequest())
    assert retry['ok'] is True


def _result(job_id: str, *, ok: bool) -> ExecutedJobResult:
    return ExecutedJobResult(
        job=ExecutionJobUnit(
            job_id=job_id,
            subscription_id='tech_channel',
            profile_id='profile_tv',
            compilation_signature='sig',
            artifact_dir=Path('.'),
            artifact_yaml_path=Path('artifact.yaml'),
            metadata_json_path=Path('metadata.json'),
        ),
        command=PreparedExecutionCommand(
            binary='ytdl-sub',
            binary_path='/bin/ytdl-sub',
            args=('/bin/ytdl-sub', 'sub'),
            cwd=Path('.'),
            env={},
            timeout_seconds=1,
            temporary_dir=Path('.'),
            invocation_metadata={},
        ),
        exit_code=0 if ok else 1,
        stdout='ok' if ok else '',
        stderr='' if ok else 'boom',
        status='success' if ok else 'failed',
        error_type=ExecutionErrorType.NONE if ok else ExecutionErrorType.NON_ZERO_EXIT,
        severity=FailureSeverity.NONE if ok else FailureSeverity.RECOVERABLE,
        error_message=None if ok else 'boom',
    )
