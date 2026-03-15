from pathlib import Path

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.integration.ytdl_sub.compiler import compile_bundle_to_artifacts
from src.integration.ytdl_sub.persisted_executor import execute_batch_with_operational_state
from src.persistence.sqlite_state import SQLiteOperationalState
from tests.helpers.fake_ytdl_sub import make_path_with_fake_binary, write_fake_ytdl_sub


@pytest.mark.e2e
def test_hito15_e2e_multiple_items_then_new_content_triggers_automatic_purge(
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
        (1, "2026-01-01T00:00:00+00:00"),
        (2, "2026-01-02T00:00:00+00:00"),
        (3, "2026-01-03T00:00:00+00:00"),
    )
    for idx, publication in dataset:
        file_path = tmp_path / "library" / f"item-{idx}.mkv"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(f"item-{idx}", encoding="utf-8")

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
                    "item_identifier": f"{sub.name}::item-{idx}",
                    "item_signature": f"sig-{idx}",
                    "publication_at": publication,
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

    assert active == [f"{sub.name}::item-2", f"{sub.name}::item-3"]
    assert purged == [f"{sub.name}::item-1"]
    assert (tmp_path / "library" / "item-1.mkv").exists() is False
    assert any(event["event_kind"] == "purge" for event in snapshot["events"])
