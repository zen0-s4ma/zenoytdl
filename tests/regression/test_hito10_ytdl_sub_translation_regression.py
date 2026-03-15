import json
from pathlib import Path
from typing import Any

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.integration.ytdl_sub.translator import translate_bundle_to_ytdl_sub_model


@pytest.mark.regression
def test_hito10_translation_regression_snapshot_stable() -> None:
    fixture = Path("tests/fixtures/hito10/valid/base-bridge")
    snapshot = Path("tests/fixtures/hito10/snapshots/translated-model.json")

    bundle = load_parsed_config_bundle(fixture)
    translated = [item.to_dict() for item in translate_bundle_to_ytdl_sub_model(bundle)]

    expected = json.loads(snapshot.read_text(encoding="utf-8"))

    assert _normalize_environment_signatures(
        translated
    ) == _normalize_environment_signatures(expected)


def _normalize_environment_signatures(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = json.loads(json.dumps(items))
    for item in normalized:
        signature = item.get("translation_signature")
        if isinstance(signature, str):
            assert len(signature) == 64
            item["translation_signature"] = "<env-signature>"

        model = item.get("ytdl_sub_model")
        if not isinstance(model, dict):
            continue

        meta = model.get("meta")
        if not isinstance(meta, dict):
            continue

        effective_signature = meta.get("effective_signature")
        if isinstance(effective_signature, str):
            assert len(effective_signature) == 64
            meta["effective_signature"] = "<env-signature>"

    return normalized
