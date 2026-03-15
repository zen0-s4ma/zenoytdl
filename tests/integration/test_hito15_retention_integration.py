from pathlib import Path

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.integration.ytdl_sub.compiler import compile_bundle_to_artifacts
from src.integration.ytdl_sub.persisted_executor import execute_batch_with_operational_state
from src.persistence.sqlite_state import SQLiteOperationalState
from tests.helpers.fake_ytdl_sub import make_path_with_fake_binary, write_fake_ytdl_sub


@pytest.mark.integration
def test_hito15_integration_retention_keeps_db_and_disk_consistent(tmp_path: Path) -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito11/valid/single"))
    compiled = compile_bundle_to_artifacts(bundle, tmp_path / "compiled")

    fake_bin = tmp_path / "bin"
    write_fake_ytdl_sub(fake_bin, 'raise SystemExit(0)\n')

    state = SQLiteOperationalState(tmp_path / "state.sqlite")
    sub = bundle.subscriptions[0]
    env = {"PATH": make_path_with_fake_binary(fake_bin)}

    item1 = tmp_path / "library" / "item-1.mkv"
    item2 = tmp_path / "library" / "item-2.mkv"
    item1.parent.mkdir(parents=True, exist_ok=True)
    item1.write_text("old", encoding="utf-8")
    item2.write_text("new", encoding="utf-8")

    execute_batch_with_operational_state(
        compiled,
        state=state,
        config_signature=bundle.signature,
        subscription_sources={sub.name: ("channel", sub.sources[0])},
        env_overrides=env,
        timeout_seconds=5,
        max_items_by_subscription={sub.name: 1},
        item_context_by_subscription={
            sub.name: {
                "item_identifier": f"{sub.name}::item-1",
                "item_signature": "sig-1",
                "publication_at": "2026-01-01T00:00:00+00:00",
                "storage_path": str(item1),
            }
        },
    )
    execute_batch_with_operational_state(
        compiled,
        state=state,
        config_signature=bundle.signature,
        subscription_sources={sub.name: ("channel", sub.sources[0])},
        env_overrides=env,
        timeout_seconds=5,
        max_items_by_subscription={sub.name: 1},
        item_context_by_subscription={
            sub.name: {
                "item_identifier": f"{sub.name}::item-2",
                "item_signature": "sig-2",
                "publication_at": "2026-01-02T00:00:00+00:00",
                "storage_path": str(item2),
            }
        },
    )

    snapshot = state.get_subscription_state(sub.name)

    active = [item for item in snapshot["known_items"] if item["is_purged"] is False]
    purged = [item for item in snapshot["known_items"] if item["is_purged"] is True]

    assert [item["item_identifier"] for item in active] == [f"{sub.name}::item-2"]
    assert [item["item_identifier"] for item in purged] == [f"{sub.name}::item-1"]
    assert item1.exists() is False
    assert item2.exists() is True
    assert any(
        event["event_kind"] == "purge"
        and event["item_identifier"] == f"{sub.name}::item-1"
        and event["detail"]["criterion"] == "publication_at"
        for event in snapshot["events"]
    )
