import json
from pathlib import Path

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.integration.ytdl_sub.compiler import compile_bundle_to_artifacts


@pytest.mark.e2e
def test_hito11_e2e_valid_config_to_compiled_artifacts_on_disk(tmp_path: Path) -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito11/valid/multi"))

    compiled = compile_bundle_to_artifacts(bundle, tmp_path)
    payload = compiled.to_dict()

    assert len(payload["artifacts"]) == 2
    assert payload["artifacts"][0]["is_invocable"] is True
    assert payload["artifacts"][1]["is_invocable"] is True

    index_payload = json.loads(compiled.index_path.read_text(encoding="utf-8"))
    assert len(index_payload["batch_signature"]) == 64
