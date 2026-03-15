import json
import re
from pathlib import Path
from typing import Any

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.integration.ytdl_sub.compiler import compile_bundle_to_artifacts


@pytest.mark.regression
def test_hito11_artifact_compilation_regression_snapshot_stable(tmp_path: Path) -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito11/valid/multi"))
    snapshot = Path("tests/fixtures/hito11/snapshots/compiled-index.json")

    compiled = compile_bundle_to_artifacts(bundle, tmp_path)
    current = json.loads(compiled.index_path.read_text(encoding="utf-8"))
    expected = json.loads(snapshot.read_text(encoding="utf-8"))

    assert _normalize_hashes(current) == _normalize_hashes(expected)


def _normalize_hashes(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = json.loads(json.dumps(payload))

    batch_signature = normalized.get("batch_signature")
    if isinstance(batch_signature, str):
        assert len(batch_signature) == 64
        normalized["batch_signature"] = "<stable-hash>"

    for artifact in normalized.get("artifacts", []):
        layout_name = artifact.get("layout_name")
        subscription_id = artifact.get("subscription_id")
        if isinstance(layout_name, str):
            assert re.fullmatch(r".+--[0-9a-f]{12}", layout_name)
            if isinstance(subscription_id, str):
                artifact["layout_name"] = f"{subscription_id}--<stable-hash12>"

        for key in [
            "compilation_signature",
            "effective_signature",
            "translation_signature",
        ]:
            value = artifact.get(key)
            if isinstance(value, str):
                assert len(value) == 64
                artifact[key] = "<stable-hash>"

    return normalized
