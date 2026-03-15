from pathlib import Path

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.integration.ytdl_sub.compiler import compile_bundle_to_artifacts
from src.integration.ytdl_sub.persisted_executor import execute_batch_with_operational_state
from src.persistence.sqlite_state import SQLiteOperationalState
from tests.helpers.fake_ytdl_sub import make_path_with_fake_binary, write_fake_ytdl_sub


@pytest.mark.regression
def test_hito15_regression_fixed_over_capacity_dataset_survivors_are_deterministic(
    tmp_path: Path,
) -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito11/valid/single"))
    compiled = compile_bundle_to_artifacts(bundle, tmp_path / "compiled")

    fake_bin = tmp_path / "bin"
    write_fake_ytdl_sub(fake_bin, 'raise SystemExit(0)\n')

    state = SQLiteOperationalState(tmp_path / "state.sqlite")
    sub = bundle.subscriptions[0]
    env = {"PATH": make_path_with_fake_binary(fake_bin)}

    dataset = (
        ("item-a", "sig-a", "2026-01-01T00:00:00+00:00"),
        ("item-b", "sig-b", "2026-01-04T00:00:00+00:00"),
        ("item-c", "sig-c", "2026-01-03T00:00:00+00:00"),
        ("item-d", "sig-d", None),
    )

    for item_id, signature, publication_at in dataset:
        file_path = tmp_path / "library" / f"{item_id}.mkv"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(item_id, encoding="utf-8")
        execute_batch_with_operational_state(
            compiled,
            state=state,
            config_signature=bundle.signature,
            subscription_sources={sub.name: ("channel", sub.sources[0])},
            env_overrides=env,
            timeout_seconds=5,
            max_items_by_subscription={sub.name: 2},
            item_context_by_subscription={
                sub.name: {
                    "item_identifier": f"{sub.name}::{item_id}",
                    "item_signature": signature,
                    "publication_at": publication_at,
                    "storage_path": str(file_path),
                }
            },
        )

    snapshot = state.get_subscription_state(sub.name)

    active = sorted(
        item["item_identifier"] for item in snapshot["known_items"] if item["is_purged"] is False
    )
    purged = sorted(
        item["item_identifier"] for item in snapshot["known_items"] if item["is_purged"] is True
    )

    assert active == [f"{sub.name}::item-b", f"{sub.name}::item-d"]
    assert purged == [f"{sub.name}::item-a", f"{sub.name}::item-c"]
    assert (tmp_path / "library" / "item-a.mkv").exists() is False
    assert (tmp_path / "library" / "item-c.mkv").exists() is False
